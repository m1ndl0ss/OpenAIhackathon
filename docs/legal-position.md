# Legal position of Redwood

Corporate banking agent | Dutch bank deployment assessment | 21 November 2026

**Scope.** The submission uses synthetic cases. The organizer assigns desk reviews, bank code calculates credit capacity, and staff sign the current file. Across six live letter-of-credit calls, the bank observed zero planted private fields in its outgoing requests. BRANE reported the downstream routes. Production review must also cover identity, logs, retention and support access. [Case evidence](evidence/submission-live.json) · [Workflow research](../research/bank-data-classification/README.md)

## Controller and processor chain

For processing on the bank’s instructions, the proposed cloud chain is **bank (controller) → AI-Z/BRANE (processor) → OpenRouter (subprocessor) → OpenAI (onward subprocessor)**. The bank determines why and how the service handles client data. Verify contracting entities and any independent provider purposes, agree Article 28 terms, authorise subprocessors in writing and pass those obligations down the chain. The rehearsal verified routing. Contract status and certification remain open for deployment. [GDPR Articles 4, 24 and 28](https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng)

## Lawful processing and international transfers

Document an Article 6 basis per purpose, such as a specific AML legal obligation or a balanced legitimate interest for corporate contact data. Apply Articles 9 or 10 where relevant. For each disclosure of personal data to a provider outside the EEA, including remote access and onward transfers, identify a Chapter V mechanism. For a US recipient, verify active, in-scope EU-US Data Privacy Framework participation under Article 45. Otherwise use applicable Article 46 safeguards, such as the correct standard contractual clauses (SCCs), a transfer impact assessment and effective supplementary measures. Until verified, keep personal data on an approved EEA-only path. [GDPR](https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng) · [EU-US adequacy](https://commission.europa.eu/law/law-topic/data-protection/international-dimension-data-protection/eu-us-data-transfers_en) · [SCCs](https://eur-lex.europa.eu/eli/dec_impl/2021/914/oj/eng)

## When can the bank send tokens?

Keep the identity map at the bank. In *EDPS v SRB*, C-413/23 P, the Court held that pseudonymised data may cease to be personal data in a recipient’s hands if it has no means reasonably likely to identify the people involved. Under the EU-institutions regulation, the controller’s duty to inform arose at collection from its own perspective. A bank that can relink a token still handles personal data. Assess what each recipient can infer from context and logs, and explain disclosures to the people concerned. Tokenisation reduces exposure. A Chapter V mechanism is still required for transfers of personal data. [Judgment, paragraphs 79–87 and 110–115](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A62023CJ0413)

## Is a data protection impact assessment (DPIA) required?

**Yes, before the proposed live bank deployment.** Linking financial and screening records about identifiable people across desks using AI creates likely high risk under Article 35. Involve the bank’s DPO, assess necessity, proportionality, access, re-identification and alternatives, and consult the supervisory authority under Article 36 if high residual risk remains. The synthetic rehearsal supplies evidence for this assessment. [GDPR Articles 35–36](https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng) · [WP29 DPIA criteria](https://autoriteitpersoonsgegevens.nl/uploads/imported/20171013_wp248_rev01_enpdf.pdf)

## EU AI Act classification

**The submitted use falls outside the high-risk categories.** Redwood prepares corporate reviews. It neither scores natural persons nor assesses their creditworthiness under Annex III 5(b). Its HR task routes administrative requests. The bank acts as deployer and gives staff meaningful decision authority. Reassess before scoring a sole trader or guarantor, ranking job candidates, or changing the intended purpose. [Article 6](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-6) · [Annex III points 4 and 5](https://ai-act-service-desk.ec.europa.eu/en/ai-act/annex-3) · [Bank’s decision mandate](../legal/case-answer-key.md)
