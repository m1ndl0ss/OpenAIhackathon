# BRANE adapter contract

The letter-of-credit workflow permits seven fixed message combinations. Each BRANE-enabled department adds a versioned set for evidence review, policy review and handover. The adapter checks that a message matches its registered workflow, task and step. Model inputs contain bank-authored wording. Case evidence and human notes stay in the bank. M&A, AML & Financial Crime and Regulatory Surveillance use an internal drafting path with zero model calls. The standalone experiments below also evaluate free-text inputs. [Department definitions](../data/workflows/departments-v1.json) · [Letter-of-credit run](evidence/submission-live.json) · [Submission guide](../SUBMISSION.md)

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

Every model-bound byte in Redwood goes through this adapter. That includes
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

### 6.1 Run the outage checks

The reference client and the staff API share the same verdict classifier. Five fault scenarios cover a DNS failure, a refused connection, a timeout, an HTTP 503 and an HTTP 200 with a completion but no routing verdict. A sixth, healthy control requires a usable response and an observed connection to the assigned BRANE endpoint.

```sh
.venv/bin/python scripts/check_failure_test.py --only a,b,c,d,e --runs 1 --output-dir .clearance/evidence/brane-outage
.venv/bin/python scripts/check_failure_test.py --runs 3 --output-dir .clearance/evidence/brane-live
```

The first command uses dummy credentials. The runner scopes each fault to a reserved test hostname or an exact loopback address and port. The second command also reads the team credential for the healthy control and its policy readback. The observer records DNS and connection attempts from the client process. The merged harness passed all 18 runs. [Measured results](evidence/brane-check-failure.csv)

The staff API checks the active policy before submitting a drafting turn. Run `make evidence` for the independently observed bank-level outage and `make live-evidence` for both case revisions through the assigned firewall. [Outage trace](evidence/firewall-outage.json) · [Signed case and receipt](evidence/submission-live.json)

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
  (defence in depth, check T3b).

## 9. Case tokens: `[[…]]` is the only permitted shape

**MUST** use the bracketed form `[[NAME]]` for every app-side case token, as
`scripts/case_tokeniser.py` does. This is a measured requirement, not a style
preference. On the T3b prompt, 4 identical calls per shape:

| Token shape | Occurrences surviving BRANE | Label BRANE applied |
| --- | --- | --- |
| `SIGNATORY_1_ACCOUNT` | 1 of 3 | `PERSON` |
| `CASE_ACCOUNT_A` | 2 of 3 | `PERSON` |
| `SIGNATORY_1` | 6 of 7 | `PERSON`, matching the span `"confirms SIGNATORY_1"` |
| `[[ACCT-A]]`, `[[EMAIL-A]]`, `[[PHONE-A]]` | 3 of 3 | none |

A word-like token is re-detected as a name in *some* positions only. Two things then
go wrong: one identity ends up with two surfaces in the same payload, and in the
`"confirms SIGNATORY_1"` case the detector **consumed the adjacent verb**, so the
cloud model received "Correspondence from `[[EMAIL-A]]` `PERSON_REF_1` holds signing
authority" — the word "confirms" deleted. Pseudonymisation silently changed what the
desk wrote. Check **T3c** is the regression guard for this.

**MUST NOT** invent a token shape in application code. If a new party type is needed,
add it to `CASE_PARTIES` in `scripts/case_tokeniser.py` and re-run `--self-test`.

When `[[SIGNATORY-1]]` *is* re-detected, BRANE replaces **all** occurrences with a
single `PERSON_REF_1`, so identity consistency survives. That is acceptable; a partial
substitution is not.

### 9.1 Over-detection corrupts the prompt, and the adapter SHOULD pre-flight for it

Token shape is not the whole problem. On `hardened-v2` at `piiSensitivity: high`, T3c
measured BRANE labelling **ordinary trade-finance English as person names** and
substituting it:

| Input span | Label applied | What the cloud model received |
| --- | --- | --- |
| `expiry on` | `PERSON` | `before the instrument PERSON_REF_2 2027-01-31` |
| `Beneficiary` | `PERSON` | `PERSON_REF_3 ORG_DEMO_02 disputes the treatment…` |
| `confirms SIGNATORY_1` | `PERSON` | `Correspondence from [[EMAIL-A]] PERSON_REF_1 holds…` |

Three words deleted from a five-sentence case note. The routing decision was correct
every time; the *content* was not. A model asked to reason about an instrument whose
"expiry on" has become a person reference can produce a confidently wrong packet, and
no routing header will show it.

**SHOULD** therefore pre-flight any prompt that will carry case text: call
`POST /policy/test`, diff `outgoingCloudPayloadPreview` against the prompt ignoring
token spans, and if non-token words were dropped or altered, treat the turn as
`unavailable` rather than sending it — or escalate to a human with the diff. The
harness check `T3c` is the reference implementation of that diff
(`run_checks.v_t3c_meaning`).

Two caveats the implementer must know: `/policy/test` is a dry run, so a clean
pre-flight does not guarantee the graded call behaves identically, and the extra call
costs a round trip inside the run budget. It is a canary, not a proof.

## 10. Rehydration round trip: an output-validator rule

The adapter tokenises on the way out; something must validate on the way back.

**MUST** reject a model reply containing any `[[token]]` that this case did not issue.
Use `case_tokeniser.validate_reply_tokens(reply)`, which returns
`(ok, report)` and flags two failure classes:

- **unknown token** — well-formed but not in the case's alias map
  (`[[SIGNATORY-2]]` on a case with one signatory, `[[ACCT-B]]` where only
  `[[ACCT-A]]` was issued). The model invented a party, or crossed cases.
- **malformed span** — bracket fragments that do not parse as a token
  (`[[SIGNATORY-1`, double-wrapped `[[[[ACCT-A]]]]`, truncated spans). The reply
  cannot be rehydrated deterministically.

On either, **MUST**:

1. **Not rehydrate.** Rehydrating an unknown token either leaves a raw `[[…]]` string
   in front of a reviewer as though it were a fact, or — worse, if a loose mapping is
   used — substitutes the wrong party's identity into a signed desk packet.
2. **Not seal a packet** from that output. Treat it like a schema-validation failure:
   stop, or request one bounded correction under the same route (spec §5).
3. Record the rejection with the `run_id` and the offending tokens, and surface a safe
   reason to the desk. The rejected text does not go into the shared audit.

**MUST** also confirm the complement: no raw alias may appear in a reply that is about
to be stored or displayed to a desk without entitlement.
`case_tokeniser.surviving_aliases(reply)` must be empty for any projection leaving the
bank's entitled view.

This is the one rule in this contract that is **not** about BRANE. BRANE protects the
outbound path; nothing in the product validates the inbound one, so it is ours to do.
- `POST /policy/test` is a dry run against the live policy. It is useful for
  pre-flighting a prompt, but its `simulatedHeaders` are **not** evidence of what the
  graded call did.
