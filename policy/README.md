# BRANE configuration

The bank uses the assigned Redwood department at `https://brane.ai-z.io/api/v1`. The live OpenAI model is `openrouter:openai/gpt-6-luna`. The submitted policy is `hardened-v2`. The digest is the first 32 hex characters of SHA-256 over the authored policy fields. The observed value is `sha256:7238362ad6b930085f5f850bc1dbf6cf`. [Policy definition](hardened-v2.json) · [Baseline snapshot](baseline-open.json)

1. On a fresh clone, copy `.env.example` to `.env`. Enter the team credential under `BRANE_API_KEY`. The application reads only the BRANE settings from this file and respects environment overrides.
2. Run `make setup` and `make brane-check`. The read-only check compares the deployed policy with the committed configuration and checks for disabled semantic rules.
3. Run `make run-live` for one-click role selection with a fresh, temporary, synthetic bank database. Run `make live-evidence` for a separate scripted staff-API rehearsal and measured report.
4. For a persistent local staff deployment, export `CLEARANCE_MODE=live` before `make run`. That deployment requires individual staff tokens. Use the disposable launcher for the stage demonstration.

The adapter verifies the policy immediately before each model call and checks the returned route, action and redaction information. It accepts only the bank's fixed desk prompts. An unavailable or inconsistent verdict leaves the case unsealed. The team’s security harness and its historical baseline use the same assigned department, and the baseline is preserved as recorded evidence. [Bank adapter](../backend/brane_client.py) · [Judge-facing test protocol](../docs/evidence/submission-tests.csv) · [Organizers' original starter kit](../docs/MAIN_Participant_Starter_Kit/starter-kit/README.md)
