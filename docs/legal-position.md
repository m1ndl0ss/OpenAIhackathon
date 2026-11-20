# Legal position of Redwood

**Status: draft for Ilaria's verification.** Each source below should be checked against the official text before submission. Mark anything you change or reject. The hackathon runs only on synthetic data; this note covers what a bank would need for a real deployment.

The [workflow research](../research/bank-data-classification/README.md) classifies the bank's data, desk by desk. This note covers the agent we submit: who is responsible, what leaves the bank, and which rules apply to the system itself.

## 1. What leaves the bank

In the letter-of-credit workflow, the cloud request carries three things: the desk, the next-step code and the bank's approved wordings. Bank code reads the case, computes the figures and attaches the citations locally. In the live run, six model requests contained **zero** of the planted private fields (names, email, financial fields). [Live transport observation](evidence/submission-live.json) · [Drafting messages](../backend/agent/runtime.py)

So in this workflow, **no personal data reaches the cloud model**. For workflows that do forward text, BRANE pseudonymises identifiers or routes the request to the bank's local model (policy matrix CB-02, CB-03, CB-04, CB-10).

## 2. Roles

| Party | Role | Basis | What the bank needs |
| --- | --- | --- | --- |
| The bank | Controller | GDPR Art. 4(7), Art. 24 | Lawful basis per purpose (Art. 6), records of processing (Art. 30) |
| AI-Z GmbH (BRANE), Germany | Processor | GDPR Art. 28 | Processing agreement meeting Art. 28(3) |
| OpenRouter and OpenAI, United States | Sub-processors, where personal data reaches them | GDPR Art. 28(2) and 28(4) | Prior written authorisation of sub-processors; same obligations passed down |

**Pseudonymised tokens.** For the bank, a token such as `[[SIGNATORY-1]]` is still personal data, because the bank holds the mapping (GDPR Art. 4(5), Recital 26). For a recipient that cannot re-identify anyone, the CJEU held that pseudonymised data may not be personal data from that recipient's perspective. **Case C-413/23 P, EDPS v SRB, judgment of 4 September 2025.** We still treat tokenised data as personal data throughout, which is the cautious reading. [Judgment](https://curia.europa.eu/juris/liste.jsf?num=C-413/23)

## 3. Transfers outside the EU

If personal data were sent to OpenRouter or OpenAI in the United States, GDPR Chapter V applies (Art. 44). Two routes:

- **Adequacy:** the EU-US Data Privacy Framework, Commission Implementing Decision (EU) 2023/1795, if the recipient is certified. [Decision](https://eur-lex.europa.eu/eli/dec_impl/2023/1795/oj)
- **Otherwise:** Standard Contractual Clauses, Commission Implementing Decision (EU) 2021/914, plus a transfer impact assessment. [Decision](https://eur-lex.europa.eu/eli/dec_impl/2021/914/oj)

In the submitted letter-of-credit workflow no personal data is transferred, so Chapter V is not triggered for that flow.

## 4. Data protection impact assessment

A DPIA is required where processing is likely to result in a high risk, particularly when using new technologies (GDPR Art. 35(1)). The EDPB-endorsed DPIA guidelines (WP248 rev.01) treat two or more criteria as a strong indicator. Redwood meets at least three: innovative use of new technology, data of a highly personal nature (financial and screening data), and matching or combining datasets (KYC, screening and facility records).

**Position:** a DPIA is required before production, even though the cloud requests themselves carry no personal data. The system as a whole processes signatories' data and screening results.

## 5. Automated decisions

No decision is automated. Three named desk reviewers and a separate mandated officer decide, and the agent has no signing capability (server-enforced, tests Y3–Y9). GDPR Art. 22 is therefore not triggered. It would also apply only to decisions about natural persons, and the applicant here is a company. The human mandate is bank policy regardless.

## 6. EU AI Act

- Redwood is an AI system (Art. 3(1)) and the bank is its **deployer** (Art. 3(4)).
- **Not high-risk.** Annex III point 5(b) covers creditworthiness assessment of *natural persons*. Redwood prepares a corporate letter-of-credit file and scores nobody. It must not be repurposed to score sole traders or personal guarantors without reassessment; our BRANE rule `NATURAL_PERSON_CREDIT_SCORING` refuses such requests (check C2).
- **Not a prohibited practice** under Art. 5.
- **AI literacy (Art. 4)** applies to deployers: staff using Redwood need training on its limits.
- Obligations for the general-purpose model sit with its provider, not the bank.

Check the application dates in force at deployment. [AI Act](https://eur-lex.europa.eu/eli/reg/2024/1689)

## 7. Financial-sector rules

- **DORA (Regulation (EU) 2022/2554):** AI-Z, OpenRouter and OpenAI are ICT third-party service providers. The bank must manage them under Art. 28, record them in its register of information (Art. 28(3)), and meet the contract requirements of Art. 30. BRANE unavailable means no model work (policy CB-07).
- **AML confidentiality:** screening detail stays with Compliance and on the local model, and other desks see only a disposition. Wwft Art. 23 and Directive (EU) 2015/849 Art. 39 now; Regulation (EU) 2024/1624 Art. 73 from 10 July 2027 (policy CB-03).
- **Client confidentiality:** client prices, terms and limits are computed locally and never sent (policy CB-09).

## 8. Security of processing

GDPR Art. 25 (data protection by design) and Art. 32 (security) are met by the controls in the [policy matrix](evidence/submission-policy-matrix.csv). Evidence:
- minimised model input
- exact-match output validation
- policy hash checked before every call
- fail closed when BRANE is unavailable
- a red team of 30 attacks against the final build

[Security report](../evidence/REPORT.md)

## Open points before production

1. Sign Art. 28 agreements with AI-Z, and authorise OpenRouter and OpenAI as sub-processors.
2. Confirm Data Privacy Framework certification of each US recipient, or put SCCs and a transfer impact assessment in place.
3. Complete the DPIA.
4. Add the three providers to the DORA register and review the contracts against Art. 30.
5. Name the Art. 6 basis for each purpose, and an Art. 9(2) exception for any special-category classification step (policy CB-04).
