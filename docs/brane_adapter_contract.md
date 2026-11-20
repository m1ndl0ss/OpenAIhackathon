# BRANE adapter contract

**Owner of this contract:** Matvei Kandalintsev (BRANE setup and security).
**Implementer:** Anastasios — `backend/brane_client.py`.
**Reference implementation:** `scripts/brane_client.py` in this repo. It is the
security workstream's own client, host-pinned and already used to produce every
row in `evidence/`. Copy its behaviour; do not re-derive it.

This document specifies what the adapter must do, not how to structure it. Every
requirement below is marked **MUST** or **SHOULD**, and each is testable by one of
the five acceptance tests in §6.

---

## 1. Scope

Every model-bound byte in Clearance goes through this adapter. That includes
prompts, system messages, retrieved policy passages, **tool results**, intermediate
summaries and final drafting turns. A model call with no tools still uses this path.

**MUST:** route tool output back through the adapter before it reaches a model on the
next turn. A tool result is untrusted document text — T4a/T4b/T4c show that an
instruction embedded in an invoice is caught only because the text crossed BRANE.

**MUST NOT:** call any model provider directly. No OpenRouter key, no Anthropic key,
no OpenAI key anywhere in application code or environment.

## 2. Inputs

Per spec §5, the adapter takes:

```
case_ref, revision, run_id, task, policy_version, messages, tool_schema
```

`policy_version` **MUST** be recorded on every call and persisted with the result.
Get it from `GET /policy` and hash it the way `brane_client.policy_hash()` does —
the canonical form projects semantic rules onto their authored fields, because BRANE
assigns a fresh `id` per rule on every write and the hash must stay reproducible from
the policy file.

## 3. Normalised outcomes

The adapter **MUST** return exactly one of these five, never a provider-shaped
response:

| Outcome | When | Observed signal |
| --- | --- | --- |
| `direct` | Permitted cloud route, nothing redacted | HTTP 200, `X-Brane-Routed-To: cloud`, `X-Brane-Redacted: false` |
| `pseudonymized` | Cloud route with placeholders substituted | HTTP 200, `X-Brane-Routed-To: cloud`, `X-Brane-Redacted: true`, `X-Brane-Placeholder-Types` present |
| `local` | Whole turn stayed on the internal GPU model | HTTP 200, `X-Brane-Routed-To: local`, `X-Brane-Model-Resolved: vllm:*` |
| `blocked` | Policy refusal before any model ran | HTTP 422, `X-Brane-Routed-To: refused`, `X-Brane-Refused-By` names the rule |
| `unavailable` | No policy decision was observed at all | transport failure, timeout, DNS failure, TLS failure, non-2xx that is not 422, or HTTP 200 with no `X-Brane-Routed-To` |

Rules that make this safe:

- **MUST** treat a missing `X-Brane-Routed-To` on a 200 as `unavailable`, not as
  `direct`. A response we cannot attribute to a policy decision is not a permitted
  route. This is the same rule the evidence harness applies, where an absent header
  is `UNVERIFIED` and never a pass.
- **MUST** distinguish `blocked` from `unavailable`. `blocked` is a successful policy
  decision and is a legitimate, final answer to give a desk. `unavailable` is an
  absence of decision.
- **MUST NOT** collapse `pseudonymized` into `direct`. The two carry different
  disclosure facts and the audit record must tell them apart.
- **MUST NOT** infer an outcome from response body text. Only headers and status.

## 4. What to persist

Per call, persist alongside `case_ref`, `revision`, `run_id`, `task`,
`policy_version` and `policy_hash`:

| Field | Source | Note |
| --- | --- | --- |
| `http_status` | status line | |
| `routed_to` | `X-Brane-Routed-To` | |
| `action` | `X-Brane-Action` | |
| `model_resolved` | `X-Brane-Model-Resolved` | records cloud vs `vllm:*` |
| `redacted` | `X-Brane-Redacted` | |
| `pii_detected`, `pii_types` | `X-Brane-Pii-Detected`, `-Pii-Types` | |
| `placeholder_types`, `allowed_types` | corresponding headers | absent when not applicable |
| `semantic_matches` | `X-Brane-Semantic-Matches` | |
| `local_cause` | `X-Brane-Local-Cause` | **see warning below** |
| `refused_by` | `X-Brane-Refused-By` | the citable rule for a `blocked` outcome |
| **`policy_triggers`** | **`X-Brane-Policy-Triggers`** | **MUST persist when present** |
| `lane` | `X-Brane-Lane` | undocumented, captured for completeness |
| `timestamp_utc` | adapter clock, UTC | |

**`X-Brane-Policy-Triggers` is the only accurate attribution we found and it is
undocumented.** It carries the full trigger list, e.g.
`prompt_injection_guard:prompt-guard,category:DATE_OF_BIRTH->local,semantic:SANCTIONS_SCREENING_DETAIL->local`.

**Warning, measured on E3:** `X-Brane-Local-Cause` reported
`prompt_injection_local` when the real triggers were a category rule and a semantic
rule, and `POST /policy/test` reported `promptInjection.detected: false` for the same
prompt. **MUST** prefer `policy_triggers` for any audit claim about *which rule*
caused a route, and **MUST NOT** present `local_cause` to a reviewer as the reason
when `policy_triggers` is present and disagrees.

**MUST NOT** persist: the `Authorization` header, the API key in any form, or raw
restricted source text in the shared audit. Use `brane_client.scrub()`, which strips
the key from anything on its way to disk or a log, and redacts
`Authorization`-shaped keys in captured header maps.

## 5. Transport rules

- **MUST** read the endpoint from `BRANE_BASE_URL`. **MUST** reject any host other
  than `brane.ai-z.io` and any scheme other than `https` by raising, not by falling
  back. `brane_client.base_url()` does this; it is five lines and it removes a whole
  class of incident.
- **MUST NOT** retry against any other host, port, scheme or provider. There is no
  fallback path anywhere in this system.
- **MAY** retry **once**, against the same endpoint, on a known transient failure, and
  only inside the run's existing step and time budget (spec §5). A second failure is
  `unavailable`.
- **SHOULD** use a 60 s per-call timeout for drafting turns and 30 s for policy reads,
  inside the 60 s per-run budget. Log the actual limits used.
- **MUST** surface HTTP 422 as a normal result with its headers intact. Do not let an
  HTTP library raise the refusal away — the 422 and its `X-Brane-Refused-By` are the
  evidence that the control worked.
- **MUST** send `model: "auto"` unless a caller needs a specific model. `auto`
  resolves to `openrouter:anthropic/claude-haiku-5.5` today and is **not** listed by
  `GET /models`; do not validate the model name against that list.

## 6. Acceptance tests

The adapter is done when these five pass. Each asserts on the normalised outcome and
on what was persisted — not on model text.

| # | Test | Setup | MUST assert |
| --- | --- | --- | --- |
| **A** | **Success, permitted route** | A public LC question with no case data (T1's prompt) | outcome `direct`; `routed_to == "cloud"`; `redacted == "false"`; `model_resolved` persisted; `policy_version` + `policy_hash` persisted |
| **B** | **422 refusal** | C2's prompt (score a sole trader's personal creditworthiness) | outcome `blocked`; `http_status == 422`; `refused_by` contains `semantic:NATURAL_PERSON_CREDIT_SCORING->refuse`; **zero** model-output text stored; the orchestrator does not seal a packet |
| **C** | **Local route** | E3's prompt (raw watchlist + adverse media note) | outcome `local`; `model_resolved` starts `vllm:`; `policy_triggers` persisted and contains the semantic rule; the restricted text is **not** forwarded to another desk, only a permitted disposition |
| **D** | **Timeout** | Point `BRANE_BASE_URL` at an unroutable address in the same host/scheme, or set a 1 ms timeout | outcome `unavailable`; **no** retry to a different host; **no** cloud call; case left pending; `analysis_unavailable` surfaced with a safe reason; no signature, no packet, no receipt |
| **E** | **DNS failure** | `BRANE_BASE_URL` host that does not resolve | outcome `unavailable`; the error is caught, not raised to the user as a stack trace; **independently observe zero outbound egress to any other host** (packet capture, proxy log, or an egress-deny test environment) — an application log alone does not establish this |

Tests D and E together are the gate check **A5** (firewall unavailable). Both **MUST**
show that a BRANE outage stops model work rather than degrading to a direct provider
call.

## 7. What the adapter must never do

1. Fabricate a successful packet to fill a gap. An infrastructure error cannot seal a
   packet (spec §5).
2. Retry a sensitive call "directly" after a BRANE failure.
3. Treat `blocked` as an error to be retried. It is a decision; escalate to a human.
4. Let model output choose a mandate, recipient, hold, reviewer or role. Fixed code
   assigns those.
5. Log the API key, the `Authorization` header, or the local alias map
   (`local/case_alias_map.json` — the rehydration key, git-ignored).

## 8. Known behaviour the adapter should expect

Measured on `hardened-v1`, recorded in `evidence/REPORT.md`:

- A Dutch IBAN is labelled `ACCOUNT_NUMBER`, not `IBAN`. A passport number and an
  invoice reference were also labelled `ACCOUNT_NUMBER`. Do not infer data type from
  the label.
- Health language is **not** reliably detected. `HEALTH_DATA: local` did not fire on
  "cardiac surgery" or "cardiologist's certificate". The adapter cannot assume
  Art. 9 text will route local; keep restricted attachments out of model-bound
  projections in application code as well.
- Pseudonymisation is per surface form. One identity can receive two tokens, and an
  unrecognised spelling receives none. Use `scripts/case_tokeniser.py` to collapse
  known case parties to one case-scoped token **before** calling the adapter
  (defence in depth, check T3b). Bracketed token shapes such as `[[ACCT-A]]` survive
  BRANE unchanged; word-like ones get re-detected as names in some positions.
- `POST /policy/test` is a dry run against the live policy. It is useful for
  pre-flighting a prompt, but its `simulatedHeaders` are **not** evidence of what the
  graded call did.
