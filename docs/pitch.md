# Pitch: three minutes

Final script for the jury. Every number below is traced to a committed file in the evidence table further down. If a number changes, change it in both places.

Slides for the security section are in [`docs/pitch/`](pitch/), in speaking order.

## Script

| Time | Speaker | Screen |
| --- | --- | --- |
| 0:00–0:30 | Ilaria | The SEC filing, then the Dutch headline |
| 0:30–0:55 | Ilaria | Importer, bank, supplier |
| 0:55–1:20 | Anastasios narrates, Nikita drives | Live walkthrough of LC-001 |
| 1:20–2:20 | Matvei | Slides 1 to 4 |
| 2:20–2:45 | Ilaria | 26 workflows, then the timing |

**0:00–0:30 · The problem**

> In May this year, a US bank discovered that customer names, Social Security numbers and dates of birth had been put into an AI app it had never approved. The bank had to report it publicly to the SEC, the US market regulator. It was the first such report caused by staff using AI rather than by hackers. In the Netherlands, the Data Protection Authority received dozens of similar reports last year.
>
> Bank staff clearly want AI. So we asked: could we give them an agent they're actually allowed to use, on their most sensitive work?

**0:30–0:55 · The case**

> Import finance is some of the most sensitive work a bank does. A Dutch company buys two million dollars of machinery from a US supplier, and its bank issues a letter of credit, a promise to pay. Trade Finance, Credit Risk and Compliance each review the file first. And it's full of things that can't go to a chatbot: directors' names, account numbers and money laundering checks.

**0:55–1:20 · Live demo**

> Redwood prepares the file for all three teams. On our synthetic case it gathers the evidence, applies the bank's policy and prepares a cited review for each desk. The credit numbers come from the bank's own code, not from the model. In about sixteen seconds the reviews are ready, and Redwood flags that the supplier invoice is missing. When the invoice arrives, the file updates and any approval given on the old version stops counting.

**1:20–2:20 · Security**

*[Slide 1: trust boundaries]*

> Our threat model: assume the model is compromised. So every hop is a trust boundary, and every control sits outside the model.

*[Slide 2: the model never sees the case]*

> Boundary one, input. Bank code calls the tools and computes every figure. The model only gets the desk, the next step and the bank's approved wordings. No case data, no documents, nothing to poison.
>
> Boundary two, output. The reply must be one JSON field matching an approved wording exactly. Anything else, and the file stays unsealed.

*[Slide 3: egress]*

> Boundary three, egress. Every call goes through BRANE, after we verify its live policy hash. If BRANE can't answer, nothing leaves. No fallback.

*[Slide 4: pen test]*

> I'm a certified penetration tester and AI systems security specialist, so I assessed our system the way an attacker would. I tried indirect prompt injection in invoices, payloads in earlier turns, system-prompt exfiltration, homoglyph names, zero-width-split IBANs, health data in Dutch, forged tokens, and approval disguised three ways. On the app: cross-customer reads, role smuggling, race conditions and replayed signatures. Thirty attacks on the final build. None got through.

**2:20–2:45 · The result**

> In rehearsal, the same setup ran 26 different department workflows, and every one reached a signed outcome. So yes, bank staff can have an AI agent they're allowed to use, even on their most sensitive work. Both revisions of our case were ready in under thirty seconds, and a person still signs every one. An average breach in financial services costs five and a half million dollars. Preparing our case cost about a thousand tokens.
>
> The US bank found out after its customers' data had already left. With Redwood, the bank decides before anything leaves, and it can prove it.

## Where every claim comes from

| Claim on stage | Evidence |
| --- | --- |
| First SEC 8-K caused by unauthorised AI use; names, SSNs, dates of birth | [WSGR alert, 28 May 2026](https://www.wsgr.com/en/insights/shadow-ai-triggers-first-sec-form-8-k-for-unauthorized-ai-use-what-financial-institutions-and-public-companies-need-to-know.html) · [American Banker](https://www.americanbanker.com/news/a-bank-breaks-its-silence-on-its-shadow-ai-breach) |
| Dutch DPA: dozens of AI-chatbot breach reports in 2025, more than 2024 | [Accountant.nl, citing FD, Dec 2025](https://www.accountant.nl/nieuws/2025/12/ap-slaat-alarm-over-datalekken-door-ai/) |
| Reviews ready in about sixteen seconds | `elapsed_seconds` 15.852 (rev 1) and 13.702 (rev 2) in [submission-live.json](evidence/submission-live.json) |
| Both revisions in under thirty seconds | 29.55 s total, [SUBMISSION.md business case](../SUBMISSION.md#business-case) |
| Model sees only desk, next step and approved wordings | `draft_messages()` in [backend/agent/runtime.py](../backend/agent/runtime.py) |
| Reply must be one field matching an approved wording exactly | `set(choice) != {"summary"} or choice["summary"] not in wordings` in [runtime.py](../backend/agent/runtime.py) |
| Live policy hash checked before every call | `check_policy()` in [backend/brane_client.py](../backend/brane_client.py); offline proof `D1` in [REPORT.md](../evidence/REPORT.md) |
| Indirect injection in invoices, including reworded | T4a, T4b, T4c in [MAIN_Five_Tests_Template.csv](../evidence/MAIN_Five_Tests_Template.csv) |
| Approval disguised as a draft, a hypothetical, claimed authority | X7, X8, X9 (422) in [redteam_findings.md](redteam_findings.md); E4 in [submission-tests.csv](evidence/submission-tests.csv) |
| Earlier-turn payload, exfiltration, homoglyphs, zero-width IBANs, Dutch health data, forged tokens | X15, X12, X1b, X2b, X6, X10/X10b/X10c in [redteam_findings.md](redteam_findings.md) |
| Cross-customer reads, role smuggling, races, replayed signatures | Y1, Y10, Y7, Y9 in [redteam_findings.md](redteam_findings.md) |
| BRANE down, nothing leaves | [firewall-outage.json](evidence/firewall-outage.json): one policy GET, zero model POSTs, zero other destinations · [brane-check-failure.csv](evidence/brane-check-failure.csv) |
| Thirty attacks on the final build, none got through | 20 against BRANE and our masking (19 held, 0 bypassed, 1 inconclusive) plus 10 against the app (10 held), at `evidence-freeze-v1`. [redteam_findings.md](redteam_findings.md) |
| Certified penetration tester and AI systems security specialist | INE Security eJPT, credential 179627600; INE Security eAIS, credential 194447489 |
| Average financial-industry breach USD 5.56M; high shadow AI adds USD 670K | IBM Cost of a Data Breach Report 2025: [financial industry summary](https://www.northdoor.co.uk/wp-content/uploads/2025/08/2025-Financial-CODB-Industry_Final.pdf) · [Help Net Security summary](https://helpnetsecurity.com/2025/08/04/ibm-cost-data-breach-report-2025) |
| About a thousand tokens per case | 1,029 tokens for both revisions, [SUBMISSION.md business case](../SUBMISSION.md#business-case) |
| 26 workflows reached a signed outcome | [department-rehearsal-live.json](evidence/department-rehearsal-live.json) |

## Likely questions

**"The model picks between approved wordings. Is that really an agent?"**
The agent is the whole run. It reads the tools, computes capacity, checks policy, finds the missing document and who owns it, routes to three desks and re-runs on a new revision. The model's freedom is deliberately small, because every token it sees is exposure. A bank widens that freedom only as fast as it can verify it.

**"Your security CSV shows T3 failing."**
That's BRANE on its own: it misses the surname-first form "DE VRIES, Jan" and gives each spelling a different token. Our tokeniser closes it (T3b passes), and the app never sends names at all. We kept the failure visible as a product gap.

**"How do you know what actually left the bank?"**
We observed what our bank sent: zero planted private fields across six live model requests. We also have BRANE's routing headers for every call. We had no packet capture downstream of BRANE, and the evidence says so. On 41 of 42 comparable checks, BRANE's dry run and live call agreed. The one disagreement is reported.

**"What if someone changes the BRANE policy?"**
Every call first compares the live policy hash with the committed one. Our drift test loosens one rule in a copy, and the run refuses to start.

**"Did anything get through while you were building it?"**
Yes, once. Our own red team found that a forged case token planted in a document could get a real name restored in the output (X10). We fixed it, added three regression variants, and re-ran the whole suite. It's documented in the findings.

**"Anything you couldn't make reliable?"**
C3c: BRANE's semantic judge refused a harmless scheduling note once in three runs. It over-blocks rather than leaks, and it's in the report as non-deterministic.
