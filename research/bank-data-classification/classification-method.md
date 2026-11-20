# Classification and verification method

[Research index](README.md)

## Scope and assumptions

This library models a representative Dutch corporate bank and its group functions as of 20 November 2026. The names, records, thresholds, payloads and case outcomes are synthetic. Bank-local workflows, model contracts, permissions, provider retention, actual data residency, and BRANE account configuration require confirmation before deployment. The documents are a policy design and test specification.

The labels below are a proposed bank taxonomy. The same field can require a different action in a different workflow. For example, a published ISIN can be eligible on its own. A custody message linking it to a client's holding is confidential even though the ISIN is public.

## Classification and handling

| Sensitivity | Decision criterion |
|---|---|
| Public | Independently verified public information or an explicitly cleared generic template. Verify provenance and usage rights. |
| Internal | Routine nonpublic work information. Release requires an approved recipient and specific purpose. |
| Confidential | Client, employee, supplier or bank information whose disclosure could cause harm or breach a duty. |
| Restricted | Information needing stronger access or transfer restrictions, including credentials, medical details, live order context, protected investigations and potentially privileged content. |

Record overlapping tags where applicable. Personal data applies to identifiable natural persons. Special-category data is the GDPR Article 9 category, not a shorthand for every sensitive field. A tag for **potential inside information** triggers a scoped assessment under MAR Articles 2 and 7. Professional secrecy and financial-crime tags flag a need to check the specific confidentiality rule. Classification is independent of the four actions.

| Action | Meaning in these files |
|---|---|
| Allow as-is | The specific value may be included in the approved external request after purpose, recipient, context and schema checks. It stays omitted if the task does not need it. |
| Transform before transfer | Local processing derives an approved code, controlled generalization or permitted substitute. Check the new value and its combination with other fields. |
| Internal only | An authorized process can use the raw value locally. Model prompts sent externally, attachments and telemetry exclude it. Any local AI use has its own approval and access rules. |
| Block | Exclude the material from the drafting context. For a case-level stop, or when isolation cannot be verified, stop the complete outbound request. Where local processing is itself restricted, route the record to the designated owner and use their procedures. |

Separate collection from disclosure. A source describing data collected for reporting, underwriting, or fraud controls is evidence of the field and its purpose. It does not grant permission to share it with a different recipient. Reversible tokenization is a safeguard. Treat the result as personal data wherever a natural person remains reasonably identifiable. See GDPR Recital 26 and Articles 4(5) and 5. [GDPR](https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng/) · [EDPB on anonymisation and pseudonymisation](https://www.edpb.europa.eu/topics/ai-and-technology/anonymisation-pseudonymisation_en)

## Application and BRANE controls

1. **Authorize the case and retrieval locally.** Check the user's entitlement and source classification before document parsing, OCR, connector access or any tool call that might disclose data. Source material remains in authorized bank systems. Treat embedded instructions as untrusted input.
2. **Derive the minimum payload.** Validate known keys, values and provenance against an allowlist. Check headers, filenames, attachments, retrieved passages, prompt history, tool arguments, telemetry and logs. Evaluate combinations and prior requests that could identify a trade or case. Keep source copies, identifier maps and evidence pointers inside the bank. Exclude internal keys and exact timestamps unless the rule explicitly permits their transfer. Include only fields and transformations permitted for the workflow. Stop the whole request if a case-level stop applies or if blocked material cannot be isolated.
3. **Enforce and observe the route.** All in-scope external model requests go through the approved BRANE path. Use its configured checks and retain a minimal trace with policy version, random request trace, action, destination and verdict. BRANE describes pattern and semantic checks, routing and masking. Actual support for the prototype fields, approval integration and failure behavior must be checked in the configured instance. [BRANE technical protections](https://ai-z-group.com/en/product/how-it-protects)
4. **Keep the failure path closed.** A timeout, a missing verdict or a policy denial stops the external call. Keep the case pending for internal review. An approved local process may resume subject to the case policy. Keep recipients, sensitive values and evidence links in the local interface. The authorized employee controls the consequential action for each workflow.

## Source verification

- **Legal requirements:** Link the act, exact provision and jurisdiction. Check whether it applies to the workflow and whether the version was effective at the research date. GDPR Articles 5–6 govern purpose, necessity and lawful basis. Articles 9–10 cover defined categories, Article 28 concerns processors, Article 32 security and Chapter V transfers. DORA Articles 28–30 govern in-scope ICT third-party risk and contractual arrangements. DORA applies from 17 January 2025 under Article 64. The Dutch Trade Secrets Protection Act requires its own definition and disclosure analysis. [GDPR](https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng/) · [DORA](https://eur-lex.europa.eu/eli/reg/2022/2554/oj/eng/pdf) · [Dutch Trade Secrets Protection Act](https://zoek.officielebekendmakingen.nl/stb-2018-369.html)
- **Supervisory guidance, market practice and specs:** Check the issuing authority, affected firms, version, and table or section. **Source** marks a field label or field path published in the cited material, including reporting categories. **Bank** marks a proposed local name or data grouping. Neither label claims a real bank's internal schema.
- **Temporal checks:** The EU AML Regulation generally applies from 10 July 2027 under Article 90. Use the Dutch Wwft framework for the 2026 scenario. The 5 November 2026 EBA internal-governance revision was published with application and repeal dates still shown as placeholders in §3 of the final report. The files use EBA/GL/2021/05 for the governance baseline and flag the revision for deployment review. MAR citations use the 5 June 2026 consolidated text. The M&A file uses the 2026 insider list implementing regulation. [EU AML Regulation](https://eur-lex.europa.eu/eli/reg/2024/1624/oj/eng/pdf) · [EBA revision and final report](https://www.eba.europa.eu/publications-and-media/press-releases/eba-publishes-revised-guidelines-internal-governance-delivering-greater-proportionality-and) · [MAR](https://eur-lex.europa.eu/eli/reg/2014/596/2026-06-05/eng) · [Insider-list implementing regulation](https://eur-lex.europa.eu/eli/reg_impl/2026/1291/oj/eng)
- **Design and open decisions:** Treat the proposed action as a synthetic prototype policy unless a cited rule establishes the constraint. Confirm the exact mandate, laws, internal classification, contracts, licences, provider settings, human review and approved recipients. Where the relevant source is unavailable, record the gap or qualify the claim. Check payloads and test expectations against the field table.

## Test record

Use synthetic cases only. Capture the case and expected action, actual action, policy version, observed external request count, whether the payload matches the allowlist, and whether the employee got a useful result. Keep raw protected values out of logs. For a blocked scenario, prove no provider request was made. Every workflow supplies the five track cases. Obtain a live BRANE verdict and inspect the outbound boundary before recording a pass.

For optional business-case evidence, time the same synthetic task manually and with the agent. Record missing or incorrect findings for both runs and verify that the authorized staff review is still possible.
