# BRANE configuration

The Redwood application connects to its assigned department at `https://brane.ai-z.io/api/v1`. The recorded live run used the model `openrouter:openai/gpt-6-luna` and policy `hardened-v2`. The policy digest was `sha256:7238362ad6b930085f5f850bc1dbf6cf`, the first 32 hexadecimal characters of SHA-256 over the authored policy fields. [Policy](hardened-v2.json) · [Recorded live case](../docs/evidence/submission-live.json)

1. Copy `.env.example` to `.env` and set `BRANE_API_KEY` to your assigned credential.
2. Run `make setup` and `make brane-check`. The check compares the deployed policy with the committed configuration and checks for disabled semantic rules.
3. Run `make run-live` to open the local staff console on port 8001 with a fresh synthetic database. For an automated live case, `make live-evidence` records its observations under `.clearance/evidence/`.

Before every model call the adapter verifies the policy and restricts inputs to the bank’s registered desk messages. An unavailable or inconsistent verdict leaves the case unsealed. The gateway tests compare the delivered baseline with two hardened policies and record the remaining gaps. [Adapter behaviour](../docs/brane_adapter_contract.md) · [Gateway results](../evidence/REPORT.md) · [Completed security cases](../submission/MAIN_Five_Tests_Template.csv)
