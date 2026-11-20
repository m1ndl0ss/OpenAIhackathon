# Run the Redwood demo

Follow a USD 2 million import letter of credit from a missing invoice to three signed findings and a simulated issuance. All cases and staff identities are synthetic.

## Run from a fresh clone

Install Python 3.11 or later, Node.js 22.12 or later and npm. From the repository root, run `make setup` once to install dependencies, build the console and seed the cases. To use the local fixtures, run `make run` and open the [staff console on port 8000](http://127.0.0.1:8000). Fixture mode works without a model credential.

## Run the live BRANE rehearsal

After setup, copy `.env.example` to `.env` if you do not already have a local configuration. Set `BRANE_API_KEY` to the credential for your assigned department. Check the policy and start the console from the repository root.

```sh
make brane-check
make run-live
```

Open the [live console on port 8001](http://127.0.0.1:8001). Each launch creates a fresh, temporary case database. The launcher verifies the department policy at startup and the adapter checks it again before each model request. If a policy check fails, analysis stops and the case stays pending. [Configuration example](../.env.example) · [BRANE configuration](../policy/README.md)

## Walk the case

Use **Human approval** to open each signer’s form. **Review as** switches to the named demo identity. Enter a reason of at least ten characters or select **Use demo reason** when available.

1. **Mira Vos, Coverage.** Open **Coverage**, select **LC-001** and click **Run analysis**. In **Agent reply**, open **Review findings and sources**. Trade Finance needs the supplier invoice. Credit Risk calculates USD 2.5 million available before the proposed issuance and USD 500,000 afterward. **Request routing** shows the three desks.
2. **Asha Reed, Credit Risk, and Noor Bakker, Compliance.** As Asha, choose **Clear** and **Sign desk finding**. As Noor, choose **Hold** and the **Invoice required** reason code, then **Sign hold finding**. Coverage receives the invoice request. The officer’s approval is locked.
3. **Mira Vos, Coverage.** Click **Attach supplier invoice**, select Noor’s request and enter an evidence note. Click **Attach invoice and revise file** and run analysis on revision 2. The first credit signature stays in the history. The Compliance hold is still open.
4. **Leon Park, Asha Reed and Noor Bakker.** Leon signs for Trade Finance and Asha signs again for Credit Risk. As Noor, choose **Clear**, select the open hold and the reviewed invoice `DOC-INV-01@1`, then click **Release hold and sign**. The dashboard now shows **3 of 3 signed** for revision 2.
5. **Eva Lin, mandated officer, and Amir Cole, Operations.** Open **Final approve** beside Eva’s name, enter a reason and confirm the decision. Switch to **Operations**, open **LC-001** and select **Simulate issuance**. The case shows one receipt for the approved revision.

The bank calculates the figures and retrieves the source records locally. In live mode each desk sends BRANE its registered next step and two candidate wordings. The bank validates the returned choice and attaches the figures and citations. The recorded run includes the six provider observations, the rejected approval attempts, the signatures and the simulated receipt. [Case answer key](../legal/case-answer-key.md) · [Live case record](evidence/submission-live.json)

## Try a specialist desk

Choose **Corporate banking → Payments & Cash**, open **PAY-001** and run analysis. Sam Reed reviews the matched payment return and signs the finding. Amir Cole signs for Operations. Ari Fox can then confirm the return match or refer the case for further review. In **PAY-002**, the analyst must first select **Verify supporting record** and rerun analysis on the new revision. [Department workflows and case IDs](department-workflows.md)

To enter a new synthetic case, use **New request**, choose **Payment exception triage** and select **Fill demo example**. After **Submit request**, read the agent’s recommendation and select **Send for desk review** to deliver the current revision to the named reviewers.

## Developer commands

| Command | Result |
| --- | --- |
| `make test` | Run the backend and workspace tests against disposable data. |
| `make evidence` | Generate local fixture and outage results under `.clearance/evidence/`. |
| `make live-evidence` | Run both letter-of-credit revisions through the API and BRANE using scripted staff identities. |
| `make reset` | Restore the seeded cases in the persistent local demo database. Stop the fixture server first. |
