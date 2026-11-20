# BRANE team setup

The default fixture workflow works offline. Matvei owns the team department, BRANE policy and security testing. The provider-specific setup and allowed configuration values are in the [official starter kit](../docs/MAIN_Participant_Starter_Kit/starter-kit/README.md).

1. Obtain the assigned team endpoint and credential from AI-Z. Copy `.env.example` to the ignored `.env`, set the assigned HTTPS API base, `BRANE_API_KEY` and `TEAM_BUILD` there. Run `set -a; . ./.env; set +a` in the shell used for the check. The key stays on the server.
2. Run `make brane-check`. It reads the team's current policy and reports connection status. Save a redacted export of the starting configuration before editing any live rules. Record the department alias, policy version, capture date and available trace fields.
3. Map the reviewed rules in Ilaria’s worksheet to the actual BRANE controls. Keep baseline and hardened exports separate. Share sanitised exports here after review. Store the originals under the ignored local evidence directory.
4. Connect the assigned model route in [the server adapter](../backend/brane_client.py). Tasos plugs the validated model output into [the packet interface](../backend/integrations.py). Preserve role and case scope on tool reads. Sensitive unknowns, refusals and outages must leave the current file unsealed.

The probe reads policy. The analysis adapter calls BRANE only in live mode, with the server's assigned endpoint and model. Set `BRANE_MODEL` to the assigned model ID and `BRANE_POLICY_VERSION` to the label of Matvei's configured department policy. The version supplied by the operator is recorded separately from any version returned by BRANE. Set `CLEARANCE_MODE=live` before starting the server. A missing or inconsistent BRANE routing verdict leaves the case unsealed.

Fixture runs, mocked adapter tests and policy probes provide no live model or cloud-egress evidence. Use the approved BRANE read-back to establish what reached an external provider.
