# Redwood demo and developer guide

Run these commands from the repository root. For the judging requirements, completed CSVs and baseline comparison, open the [submission guide](../SUBMISSION.md).

## Run from a fresh clone

Install Python 3.11+ and Node 22.12+ with npm, then run these commands from the repository root.

```sh
make setup
make run
```

Open the console and click **New request**. Choose one of 27 workflows. **Fill demo example** fills in a request for that desk. **Next demo example** loads a case with missing evidence. You can enter your own details, including an amount and currency for monetary workflows. Click **Submit request** to open the case and run the organizer. [Local staff console](http://127.0.0.1:8000) · [Example request form](../docs/evidence/request-intake.jpg)

After submission, **Agent reply** appears above **Human approval** on the dashboard and in the case workspace. Read the recommended next step and the agent’s returned wording. **Review findings and sources** opens the other drafts and the records your desk can inspect. The reply stays attached to its analyzed revision throughout sign-off and after the final decision. Green calls for human review and amber flags an issue such as a missing invoice.

On the dashboard, **Request routing** sits between **Agent reply** and **Human approval**. The diagram follows the request through the organizer to three agents. **Replay run** shows the recorded handoffs. For an existing unrun case, use **Preview route** or **Run analysis**. [Recorded handoffs](../docs/evidence/request-routing.gif)

Click **Send for desk review** under the recommendation. Each named reviewer receives the current revision in **My approvals**. For a payment exception, Sam Reed and Amir Cole each review and sign. Once both have signed and the evidence checks pass, Redwood sends the request to **Ari Fox** for a final decision. Ari can approve the request or refer it for further review. The case shows each signature and who still needs to act.

In the **Human approval** panel, click **Review finding** for your desk or **Review as** beside a colleague’s name in the local demo. The form shows the signer, revision and evidence. Enter a reason or click **Use demo reason**, then **Sign desk finding**. The signature count updates immediately. **Final approve** opens the assigned officer’s decision form once all required desks have cleared. Staff deployments use individual tokens. Preloaded walkthrough cases reach their reviewers automatically when you run analysis.

Setup installs the dependencies, builds the React console, creates the six original demo identities and two identities per specialist desk, seeds SQLite and prepares evidence worksheets. An existing checkout can run `make seed` and `make build`, then restart its server to pick up the new directory. Setup keeps existing cases, logins and worksheet edits. The default mode runs entirely on local fixtures after installation. The console uses Neue Haas Grotesk Display when installed and bundles Inter, IBM Plex Mono and its icons for offline use. [Bundled font and icon licenses](../console/public/design-licenses.txt)

## Try a specialist desk

1. Choose **Corporate banking → Payments & Cash**. The analyst’s dashboard opens with two cases. Select **PAY-001** and click **Run analysis**. The routing map follows evidence review, policy review and the handover draft.
2. As **Sam Reed**, click **Review finding**, inspect the return-match record, enter a reason and click **Sign desk finding**. Click **Review as Amir Cole** to sign the Operations finding on the same screen.
3. Under **Ari Fox**, click **Final approve**. Inspect the signed packet, enter a reason and click **Final approve** to confirm the return match, or **Refer for further review**. The dashboard identifies the person who made the decision. The case workspace includes the outcome reference.
4. Try **PAY-002** as the analyst for an incomplete record. **Verify supporting record** creates revision 2. Run the organizer again to prepare that revision for the human reviewers. To submit another payment, click **New request**, choose **Payment exception triage**, enter the payment details and click **Submit request**.

Use the four department groups or search for a desk. Each specialist has its own examples, prompts, evidence and final action. M&A, AML & Financial Crime and Regulatory Surveillance keep all three drafting tasks inside the bank. The other 23 specialist desks use BRANE in live mode. All outcomes are simulated internal records. [Browse the 26 desks and their examples](../docs/department-workflows.md) · [See the organizer running a payment case](../docs/evidence/specialist-workflow.jpg)

## Run the live BRANE rehearsal

On a fresh clone, copy `.env.example` to `.env` and put the assigned AI-Z team credential in `BRANE_API_KEY`. The rehearsal reads the BRANE variables from that file. Run the following after `make setup`.

```sh
make brane-check
make run-live
```

Open the [live staff console](http://127.0.0.1:8001). Choose **Coverage**, then **Run analysis**. This loopback-only launcher creates temporary synthetic cases and desk identities. Stopping the live rehearsal discards its cases. Starting it again gives the next presenter a clean run. The offline console keeps its own SQLite file.

## Walk the case

Choose the named role on the desk picker. The dashboard, case workspace and personal inbox refresh automatically while visible. Use **Human approval** to sign or inspect the packet, and **Open case** for messages and case history.

1. **Coverage** (`coverage`) selects `LC-001` in the queue and clicks **Run analysis**.
2. Click **Review as Asha Reed** for Credit Risk, choose **Clear**, enter a reason and click **Sign desk finding**. **Noor Bakker** in Compliance chooses **Hold** and **Invoice required**, enters a reason and clicks **Sign hold finding**. Coverage receives the request.
3. Click **Attach supplier invoice** to open **Mira Vos**’s evidence form. Select the Compliance request, enter an evidence note and click **Attach invoice and revise file**. Click **Run analysis** for revision 2. The hold stays open and the earlier Credit signature is historical.
4. **Leon Park** in Trade Finance and **Asha Reed** each sign **Clear** on revision 2. **Noor Bakker** selects the open hold, cites `DOC-INV-01@1`, enters a reason and clicks **Release hold and sign**.
5. With **3 of 3 signed**, click **Final approve** beside **Eva Lin**. Confirm the decision and reason in Eva’s form. The dashboard shows **Approved by Eva Lin**. **Operations** can then open the case and click **Simulate issuance**.

`LC-002` starts with a complete invoice. Use it to demonstrate that a Compliance hold alone prevents final approval. `make reset` replaces the local demo cases with their original seeded state and keeps logins and evidence worksheets. Stop the local server before resetting a rehearsal.

## Team entry points

| Owner | Start here | Handoff |
| --- | --- | --- |
| Matvei | [BRANE setup](../policy/README.md), [BRANE connection](../backend/brane_client.py), [case access interface](../backend/integrations.py) | Maintain the assigned department, committed policy and measured gateway results. |
| Tasos | [Synthetic case and facility](../data/trade/demo.json), [agent runtime](../backend/agent/runtime.py), [packet display](../console/src/PacketList.tsx) | Supply validated desk packets through `prepare_packets(snapshot, mode, run_id=…, authorize=…)`. Each fact carries a case-scoped versioned source. |
| Ilaria | [Case answer key](../legal/case-answer-key.md), [evidence instructions](../docs/evidence/README.md), [utility scorecard](../eval/utility-scorecard.csv) | Maintain the case answer key, cited matrix and business evidence. |
| Nikita | [Case API](../backend/main.py), [workflow](../backend/workflow.py), [staff console](../console/src/main.tsx), [API tests](../tests/test_trade_workflow.py) | Own the six-role workflow, the live rehearsal and the simulated receipt. |

## Developer commands

| Command | Result |
| --- | --- |
| `make submission` | From a Git checkout, export the committed runnable app, PDFs, CSVs and evidence to a jury ZIP under `.clearance/submission/`. |
| `make test` | Run the backend and workspace checks against disposable data. |
| `make evidence` | Exercise holds, revisions, receipt retries, the bank outage and five fault scenarios with dummy credentials, and run both fixture scenarios. Save results under `.clearance/evidence/`. |
| `python -m tools.agent_utility` | Score both synthetic revisions against Ilaria's answer key and export `.clearance/evidence/agent-utility-fixture.json`. |
| `make doctor` | Check local database, logins, console build and configured mode. |
| `make brane-check` | Read the assigned department and verify its active policy against the committed hardened rules. |
| `make run-live` | Launch the one-click live rehearsal on port 8001 with an isolated database. |
| `make live-evidence` | Exercise both revisions and all six human roles through the API and BRANE. Export measured results to `.clearance/evidence/submission-live.json`. |
| `.venv/bin/python -m tools.department_rehearsal` | Rehearse the first example and record a human outcome at each specialist desk. Add `--mode live` to use the assigned BRANE service on permitted cases. |
| `make dev-console` | Run the Vite development server on port 5173. Run the API on port 8000 alongside it. |
| `make build` | Type-check and bundle the console for the single-origin server. |

The API reference is at [local OpenAPI docs](http://127.0.0.1:8000/docs). Configuration variables are listed in [.env.example](../.env.example). Shell variables take precedence over the BRANE settings in the local file. [Full specification](../docs/corporate-banking-hackathon-spec.md) · [Who builds what](../docs/team-build-plan.md) · [Specialist workflow directory](../docs/department-workflows.md)

The bank calculates capacity, looks up evidence and retrieves the current synthetic policy. The drafting prompt contains the desk, the next-step code and two approved wordings. The bank validates the returned wording and attaches the local figures and citations. The live rehearsal records the observed model, usage, policy digest, request IDs, decisions and simulated receipt. [BRANE setup](../policy/README.md) · [Case answer key](../legal/case-answer-key.md)
