# BRANE endpoint shape — observed, not assumed

Team Redwood · security workstream · department reported by the API as **`Team 09`**
(`departmentId 8b0703c1-174a-436e-8dab-8fc8efdc1b14`).

Everything below was read from the live endpoint on **2026-11-20** by
`scripts/discover.py`. Raw responses are in this directory. Where the README and
the endpoint disagree, the endpoint is recorded and the difference is called out.

## 1. `GET /policy` — the policy object

```json
{
  "team": "Team 09",
  "departmentId": "8b0703c1-...",
  "routingMode": "cloud-preferred",
  "piiSensitivity": "low",
  "categories": { "PERSON": "allow", "...": "...24 more..." },
  "semanticCategories": [],
  "summary": { "allow": 25, "placeholder": 0, "local": 0, "refuse": 0,
               "activeSemanticCategories": 0, "isOpenBaseline": true },
  "updatedAt": null,
  "availableActions": ["allow", "placeholder", "local", "refuse"],
  "catalogEndpoint": "/api/v1/policy/catalog",
  "testEndpoint": "/api/v1/policy/test"
}
```

**Writable vs server-owned.** `PUT /policy` accepts exactly four fields:
`routingMode`, `piiSensitivity`, `categories`, `semanticCategories`. The rest
(`team`, `departmentId`, `summary`, `updatedAt`, `availableActions`,
`catalogEndpoint`, `testEndpoint`) is server-owned and must not be echoed back.
`scripts/brane_client.py:WRITABLE_POLICY_FIELDS` is the single definition of
that split; `policy/baseline-open.json` therefore stores only the writable
subset plus a `_meta` block, so it can be PUT back verbatim to restore.

`categories` is a **flat `label -> action` map**. There is no per-workflow, per
sub-step or per-recipient dimension. See the product gap in `evidence/REPORT.md`.

**Starting state matches the brief exactly:** 25/25 `allow`,
`semanticCategories: []`, `isOpenBaseline: true`. One difference worth noting:
`piiSensitivity` starts at **`low`**, not `standard`, so moving to `high` is a
two-step change from the delivered baseline.

## 2. Category labels (25) — the field is `label`, not `code`

`GET /policy/catalog` returns `categories` as a list of objects keyed on
**`label`**. Writing `code` would silently build the wrong matrix.

```json
{ "label": "PERSON", "group": "contact", "floor": "allow", "title": "Person Name",
  "detectors": ["Presidio", "GLiNER", "OPF"], "example": "Lisa Becker, Dr. Jonas Weber",
  "gdprHint": "GDPR Art. 4(1) personal identifier", "openBaselineDefault": "allow",
  "allowedActions": ["allow", "placeholder", "local", "refuse"] }
```

| Group (`id`) | Labels |
| --- | --- |
| `contact` | `PERSON`, `EMAIL`, `PHONE`, `ADDRESS`, `IP_ADDRESS` |
| `company` | `ORG`, `TRADE_REGISTER`, `VAT_ID` |
| `identifiers` | `DATE_OF_BIRTH`, `SSN`, `PASSPORT`, `TAX_NUMBER`, `INSURANCE_NUMBER` |
| `financial` | `IBAN`, `CREDIT_CARD`, `ACCOUNT_NUMBER` |
| `credentials` | `PASSWORD`, `SECRET_KEY` |
| `special` | `HEALTH_DATA`, `ETHNIC_ORIGIN`, `POLITICAL_OPINION`, `RELIGIOUS_BELIEF`, `SEXUAL_ORIENTATION`, `TRADE_UNION`, `SENSITIVE_CONTEXT` |

All 25 report `floor: "allow"` and all four `allowedActions`. **Nothing is
locked**, so every rule in `policy/hardened-v1.json` is expressible. Each of the
25 proposed assignments was checked against this list before being written.

## 3. Actions and precedence

| `id` | `rank` | `route` | Meaning |
| --- | --- | --- | --- |
| `allow` | 0 | `cloud` | Value leaves as typed |
| `placeholder` | 1 | `cloud` | Replaced with `<CATEGORY_1>`, rehydrated locally in the answer |
| `local` | 2 | `local` | Whole turn on the internal GPU model, zero cloud egress |
| `refuse` | 3 | `refused` | HTTP 422 before any model runs |

Precedence is by `rank`, **strictest wins per prompt**: one `local` category
pulls the entire request local. This is the trade-off documented in the report.

## 4. Semantic categories

Shape per rule (confirmed against `catalog.semanticTemplates`):
`{code, name, description, keywords[], legalBasis, action}` with `action` limited
to `local` or `refuse`. Up to 25 rules. `description` is evaluated by the
internal GPU LLM; `keywords` are fast deterministic triggers.

## 5. `POST /policy/test` — the post-policy observation

This is the only mechanism AI-Z exposes for seeing what *would* leave the bank,
and it is what T3/T4/E5 verify against.

```json
{ "team": "Team 09",
  "decision": {"winningAction": "allow", "route": "cloud", "httpStatus": 200, "triggers": []},
  "detectedCategories": [{"label": "PERSON", "sampleText": "Jan de Vries",
                          "detector": "presidio", "confidence": 0.85, "action": "allow"}],
  "matchedSemanticCategories": [],
  "promptInjection": {"detected": false, "score": 0.377, "source": "clean"},
  "outgoingCloudPayloadPreview": "…the exact text the cloud model receives…",
  "simulatedHeaders": {"X-Brane-Routed-To": "cloud", "…": "…"},
  "liveCompletion": null }
```

Two caveats recorded as evidence limitations:

- The response carries **no real `X-Brane-*` headers** — `simulatedHeaders` is a
  simulation, and `outgoingCloudPayloadPreview` is a *preview*. It is a
  dry-run of the same policy, not an observation of the graded `/chat/completions`
  request. The harness therefore records both and never presents the preview as
  proof of what left the bank during the live call.
- `promptInjection` detection is **native**, independent of our semantic rules.

## 6. `GET /models`

`openrouter:anthropic/claude-haiku-5.5`, `openrouter:mistralai/mistral-large-4-0`,
`openrouter:openai/gpt-6-luna` (`owned_by: openrouter`);
`vllm:qwen3.8-27b-nvfp4`, `vllm:deepseek-v4.1-flash` (`owned_by: local`).

## 7. Differences from the README (all minor, none blocking)

1. **`auto` is not listed by `/models`** but is accepted by
   `/chat/completions` and resolves to `openrouter:anthropic/claude-haiku-5.5`.
   The harness sends `auto`, as the starter kit does, and records
   `X-Brane-Model-Resolved` on every row.
2. **`X-Brane-Lane: governed` is returned but undocumented** — not in the
   README's header table. Captured in the raw JSONL for completeness.
3. **A Dutch IBAN is detected as `ACCOUNT_NUMBER`, not `IBAN`.**
   `NL02ABNA0123456789` came back as
   `{"label": "ACCOUNT_NUMBER", "sampleText": "NL02ABNA0123456789"}`. A policy
   that hardens `IBAN` alone leaves a hole; both labels must carry the same
   action. Ours do.
4. On a clean prompt only six headers appear (`routed-to`, `action`, `lane`,
   `model-resolved`, `pii-detected`, `redacted`). `pii-types`,
   `placeholder-types`, `allowed-types`, `semantic-matches`, `local-cause` and
   `refused-by` are **absent, not empty**, when they do not apply — which is why
   every verifier treats a missing header as `UNVERIFIED` rather than a pass.

## 8. `PUT /policy` — full replace or partial merge?

**Verdict: partial merge.** Established empirically on 2026-11-20 by
`scripts/apply_policy.py --probe-put-semantics`, recorded in `put_semantics.json`.

A `PUT` carrying only `{"routingMode": "cloud-preferred"}` left everything else
untouched: non-`allow` categories 25 → 25, semantic rules 5 → 5, policy hash
identical before and after (`sha256:4c293e42…`). Fields absent from the body are
not reset to the open-baseline default.

Two consequences:

- A partial PUT cannot silently un-harden the department, so an interrupted or
  minimal update is not a security event.
- It also means **drift accumulates**: a rule PUT once stays until explicitly
  changed, so "what is live" cannot be inferred from the last PUT body alone.
  `apply_policy.py` therefore always sends the complete document and always
  verifies by read-back, and `run_checks.py` refuses to run unless the live
  policy hash matches the policy file it was given.

## 9. What BRANE adds on storage

`PUT /policy` returns 200 and stores semantic rules with two server-owned fields
added per rule: **`id`** (a fresh UUID) and **`enabled`** (`true`). Nothing we
send is dropped or modified.

Because `id` is regenerated per write, hashing it would make the policy hash
unreproducible from the policy file. `canonical_policy_text()` therefore projects
each semantic rule onto the six authored fields
(`code`, `name`, `description`, `keywords`, `legalBasis`, `action`). A stored rule
with `enabled: false` would enforce nothing, so that case is caught as drift by
`apply_policy.diff_policy` rather than being hashed over.

Verified: policy file and live read-back now produce the identical hash
`sha256:4c293e4248d51401c51d9437d41ec60c`, and re-applying the same file is a
no-op that still exits 0.
