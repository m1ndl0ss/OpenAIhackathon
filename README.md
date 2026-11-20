# Clearance

An internal corporate banking demo for one USD 2 million import letter of credit. Three bank desks review a versioned file. A separate officer makes the final decision and Operations records one simulated issuance.

## Run from a fresh clone

Install Python 3.11+ and Node 22.12+ with npm, then run these commands from the repository root.

```sh
make setup
make run
```

Open [the local staff console](http://127.0.0.1:8000). In a second terminal, run `make login ROLE=coverage` and paste the generated token into the sign-in screen. Use `make logins` to list all six staff roles. Use a separate browser tab for each role or sign out between actions. Tokens belong to this checkout. Keep them out of screenshots and commits.

Setup installs the dependencies, builds the React console, creates six private synthetic logins, seeds SQLite and prepares evidence worksheets. Running setup again keeps existing cases, logins and worksheet edits. The default mode runs entirely on local fixtures after installation.

## Walk the case

Use `make login ROLE=<role>` with the role shown below. When returning to an already-open tab, click **Refresh** to load the latest case.

1. **Coverage** (`coverage)) selects `LC-001` in the queue and clicks **Run analysis**.
2. **Credit Risk** (`credit_risk)) chooses **Clear**, enters a reason and clicks **Sign desk finding**. **Compliance** (`compliance`) chooses **Hold** and **Invoice required**, enters a reason and signs. Coverage receives the request.
3. **Coverage** refreshes, selects the Compliance request under **Attach supplier invoice**, enters an evidence note, then clicks **Attach invoice and revise file**. Click **Run analysis** for revision 2. The hold stays open and the earlier Credit signature is historical.
4. **Trade Finance** (`trade_finance`) and **Credit Risk** each sign **Clear** on revision 2. **Compliance** chooses **Clear**, selects its open hold, selects `DOC-INV-01@1` as the reviewed evidence, enters a reason and signs.
5. **Final officer** (`final_officer`) selects **Approve**, enters a reason and clicks **Record final decision**. **Operations** (`operations`) clicks **Simulate issuance**. Refresh the case to see the same saved receipt.

`LC-002` starts with a complete invoice. Use it to demonstrate that a Compliance hold alone prevents final approval. `make reset` replaces the local demo cases with their original seeded state and keeps logins and evidence worksheets. Stop the local server before resetting a rehearsal.

## Team entry points

| Owner | Start here | Handoff |
| --- | --- | --- |
| Matvei | [BRANE setup](policy/README.md), [BRANE connection](backend/brane_client.py), [case access interface](backend/integrations.py) | Configure the assigned department and governed model route. Deliver redacted policy versions and route observations for Ilaria. |
| Tasos | [Synthetic case and facility](data/trade/demo.json), [agent runtime](backend/agent/runtime.py), [packet display](console/src/PacketList.tsx) | Supply validated desk packets through `prepare_packets(snapshot, mode, run_id=…, authorize=…)`. Each fact carries a case-scoped versioned source. |
| Ilaria | [Case answer key](legal/case-answer-key.md), [evidence instructions](docs/evidence/README.md), [utility scorecard](eval/utility-scorecard.csv) | Review the desk language and expectations, complete the cited policy matrix and assemble actual evidence. |
| Nikita | [Case API](backend/main.py), [workflow](backend/workflow.py), [staff console](console/src/main.tsx), [API tests](tests/test_trade_workflow.py) | Run the six-role workflow, exercise E3/E4, and hand over the observed results. |

## Developer commands

| Command | Result |
| --- | --- |
| `make test` | Run the backend and workspace checks against disposable data. |
| `make evidence` | Execute E3/E4 and write the observed fixture results under `.clearance/evidence/`. |
| `python -m tools.agent_utility` | Score both synthetic revisions against Ilaria's answer key and export `.clearance/evidence/agent-utility-fixture.json`. |
| `make doctor` | Check local database, logins, console build and configured mode. |
| `make brane-check` | Check that the assigned live endpoint accepts the credential for a read-only team policy request. |
| `make dev-console` | Run the Vite development server on port 5173. Run the API on port 8000 alongside it. |
| `make build` | Type-check and bundle the console for the single-origin server. |

The API reference is at [local OpenAPI docs](http://127.0.0.1:8000/docs). Configuration variables are listed in [.env.example](.env.example). Export overrides in the shell before starting the app. [Full specification](docs/corporate-banking-hackathon-spec.md) · [Who builds what](docs/team-build-plan.md) · [Planned workflows](docs/team-build-plan.md#2-support-multiple-banking-workflows)

The packet builder uses server-computed facts and a versioned synthetic policy library. The model drafts within a closed set of review wording for each desk. Unsupported numbers, references, requests or wording leave the revision unsealed. After Matvei confirms the live settings, `python -m tools.agent_utility --mode live` exports a separate live scorecard. Missing model usage, manual timing and staff timing remain explicit in the report. [BRANE setup](policy/README.md) · [Case answer key](legal/case-answer-key.md)
