# Redwood | Three-minute pitch

| Time | Speaker | Screen |
| --- | --- | --- |
| 0:00–0:30 | Ilaria | Community Bank’s SEC filing, Item 1.05 |
| 0:30–0:55 | Ilaria | Staff request, bank and department desks |
| 0:55–1:20 | Anastasios narrates, Nikita drives | LC-001, Agent reply and Request routing |
| 1:20–2:20 | Matvei | Trust boundaries, model input, BRANE route and recorded results |
| 2:20–2:45 | Ilaria | Breach-cost estimates, rehearsal timing and department reach |
| 2:45–3:00 | Ilaria | Human approval |

## Script

**0:00–0:30 · Why a bank needs this**

> In May, Community Bank discovered that an unapproved AI application had handled customer names, Social Security numbers and dates of birth. Its parent reported the incident to the US securities regulator. The bank called the incident material because of how much sensitive information was involved. The Dutch privacy regulator has also documented data disclosures through AI chatbots. How do you give bank staff a useful AI tool that the bank can actually govern?

**0:30–0:55 · What Redwood does**

> Redwood helps bank staff review requests that involve several departments. One desk may need the documents, another needs the credit figures, and each can see only the evidence its role allows. The bank keeps the records and runs the calculations. BRANE screens requests before they reach a model. The dashboard shows how the work moves between people and agents.

**0:55–1:20 · Where the AI works**

> Watch the organizer route this letter of credit to three agents for Trade Finance, Credit Risk and Compliance. Each calls a model to draft its finding. We run this case at the strictest setting, so the model chooses between two approved wordings. Here the supplier invoice is missing. When Coverage supplies it, Redwood updates the file and the reviewers sign that version.

**1:20–2:20 · Bounded autonomy**

> We call this bounded autonomy. The bank decides what evidence each agent can read, computes the figures and attaches the sources. The model receives the desk, the next step and the permitted wordings. The bank validates the reply before a reviewer sees it. In six observed requests, none of our planted private fields left the application for BRANE.
>
> We also tested the hardened BRANE policy on realistic synthetic invoice and screening text. It routed sensitive content locally and exposed gaps in name masking. That gives a bank evidence for deciding where to widen the task. A richer draft would first need to pass its own data and quality checks.
>
> If BRANE’s policy cannot be verified, the app stops before calling a model. In our rehearsal, KYC and Credit Risk had tasks run on BRANE’s local model. Three restricted desks used bank-side rules with zero model calls. People made every final decision.

Use Matvei’s [trust boundaries](pitch/1_trust_boundaries.png), [model input](pitch/2_model_never_sees_case.png) and [egress](pitch/3_egress_fail_closed.png) slides. For the results, show the [security test worksheet](evidence/submission-tests.csv).

**2:20–2:45 · Why it is worth doing**

> IBM’s 2025 study estimated the average financial-sector breach at 5.56 million dollars. Across industries, heavy use of unauthorised AI was associated with 670,000 dollars more per breach. Avoiding one comparable incident could pay for years of operation. We also measured the work itself. Redwood prepared six cited drafts in about thirty seconds, and all 26 specialist workflows reached a signed outcome.

**2:45–3:00 · Close**

> Redwood gives banks a secure way to use agents and speed up reviews. People make every decision. Banks can choose which desks work together, giving teams flexibility while the same security controls protect every handoff.

## Likely questions

**Where’s the AI? Could a rules engine pick the sentence?** Yes. At the strictest setting, a rule could make that choice. The organizer launches three specialist agents. Each makes a real, policy-checked model call and returns a draft for its desk. Evidence selection, arithmetic, permissions and approval stay in bank code. That is **bounded autonomy**. The bank can evaluate a broader task, such as drafting discrepancies from a permitted invoice excerpt, against the document-text tests before it gives the model that discretion. The submitted app uses fixed drafting prompts. [Model inputs and validation](../backend/agent/runtime.py) · [Six real calls and citations](evidence/submission-live.json) · [Document-text tests](../evidence/MAIN_Five_Tests_Template.csv)

**What does “local” mean for sensitive desks?** BRANE reported 12 local-model calls across ten workflows, including the KYC handover and the Credit & Counterparty Risk evidence and handover tasks. It reported 57 cloud calls across the specialist rehearsal. M&A, AML & Financial Crime and Regulatory Surveillance completed nine internal tasks with zero model calls. A bank-side rules task and a BRANE local-model call have distinct entries in the audit trail. [Per-task route and model](evidence/department-rehearsal-live.json)

**What did you test on document text?** The security team sent synthetic document passages to the real hardened gateway. Some raw name variants escaped masking and some ordinary trade wording was over-masked. In the frozen comparison, one benign health-related scheduling note was refused intermittently. These results set limits on any future expansion to document drafting. The submitted case keeps source documents in the bank. [Frozen test results](https://github.com/m1ndl0ss/OpenAIhackathon/blob/evidence-freeze-v1/evidence/REPORT.md) · [Submission policy matrix](evidence/submission-policy-matrix.csv)

**What did the separate security review establish?** Across 30 checks of the final build, the team recorded 29 controls holding and one inconclusive result. The raw-firewall comparison is a different test set and its failures are reported separately. [Frozen security review](https://github.com/m1ndl0ss/OpenAIhackathon/blob/evidence-freeze-v1/docs/redteam_findings.md) · [Policy comparison](https://github.com/m1ndl0ss/OpenAIhackathon/blob/evidence-freeze-v1/evidence/REPORT.md)

**How do you know what left the bank? What happens if the policy changes?** The bank observed its outgoing request bodies. All six were free of the tested private markers. Downstream routing is reported by BRANE’s headers. The adapter verifies the active policy digest before each call. In the controlled outage it attempted one policy lookup and sent zero model requests. [Live observation](evidence/submission-live.json) · [Adapter](../backend/brane_client.py) · [Outage trace](evidence/firewall-outage.json)

**How does one incident pay for years of operation?** That is a conditional estimate. At an illustrative all-in cost of USD 100,000 a year, avoiding USD 300,000 of loss on one incident covers three years. The bank in the opening filing gave no loss figure. A pilot needs its own service cost, incident likelihood and estimate of how much loss Redwood could prevent. The USD 670,000 is a difference between study groups. [SEC filing](https://www.sec.gov/Archives/edgar/data/1605301/000160530126000021/cbfv-20260507.htm) · [Business case and assumptions](../SUBMISSION.md#business-case)

**Can a bank lawfully deploy it?** The submitted purpose is to prepare corporate reviews for people to decide. The agent does not score natural persons. For the proposed deployment with real personal data, the bank needs a DPIA, processor agreements, documented transfer safeguards and meaningful human review. Tokenisation reduces exposure and requires a recipient-specific identification assessment. [Legal position of Redwood](legal-position.md) · [Printable one-page brief](../output/pdf/redwood-legal-position.pdf)

## Evidence for the stage

| Claim | Source |
| --- | --- |
| Unauthorised AI use at Community Bank, reported in May 2026 | [CB Financial Services, SEC Form 8-K, Item 1.05](https://www.sec.gov/Archives/edgar/data/1605301/000160530126000021/cbfv-20260507.htm) |
| Dutch regulator documented chatbot disclosures | [Autoriteit Persoonsgegevens, 2024 data-breach report](https://www.autoriteitpersoonsgegevens.nl/system/files?file=2025-07%2FRapportage+datalekken+2024.pdf) |
| Two benchmarks from IBM’s 2025 study (USD 5.56M financial-sector mean and USD 670K cross-industry difference by shadow-AI use) | [IBM financial-industry brief, p. 1](https://www.northdoor.co.uk/wp-content/uploads/2025/08/2025-Financial-CODB-Industry_Final.pdf) · [IBM study release](https://newsroom.ibm.com/2025-07-30-ibm-report-13-of-organizations-reported-breaches-of-ai-models-or-applications%2C-97-of-which-reported-lacking-proper-ai-access-controls) |
| Six cited drafts, 29.55 seconds and 1,029 tokens across two revisions (staff decision time unmeasured) | [Live staff API scorecard](../eval/utility-scorecard.csv) |
| 26 specialist workflows exercised through a human decision in addition to the letter-of-credit case | [Specialist rehearsal](evidence/department-rehearsal-live.json) · [Case approval and simulated receipt](evidence/submission-live.json) |
