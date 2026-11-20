# AI-Z Challenge Track: The Secure Enterprise AI Challenge

Text transcribed from `AI-Z-Track-Description.pdf` (MAIN Summit 2026, Maastricht, 20–21 November 2026; powered by BRANE, the AI interaction firewall). Layout simplified; wording kept.

> **Build the Agent. Define the Rules. Make It Work.**
> How do you build an AI agent for a legally demanding business process and make sure it follows the rules that apply to it?

## Introduction

AI agents can take on tasks, analyse information, automate processes and carry out work steps on their own. Yet some of the most valuable applications of AI involve information that companies may not process without restriction or pass on to external AI models. This includes personal data, health information, confidential contracts and trade secrets.

**Your mission:** Develop your own AI agent for a legally demanding use case. Research the applicable requirements, translate them into technical rules and build your agent so that it works reliably within those rules.

There are no predefined use cases. You combine three disciplines: Technology, Business, Legal & Governance.

## 01 · The challenge

Within two days, develop an AI agent that automates or significantly simplifies a realistic business process. We are looking for tasks in which data protection, confidentiality or regulatory requirements pose a real challenge. Your job is to develop a suitable and legally permissible solution.

You need to find out for yourselves:
- Which legal requirements apply to your use case?
- Which data may your agent process?
- Which information may an external AI model receive?
- Which data must be removed, pseudonymised or processed locally?
- Which processing steps are not permitted?
- Which decisions must be controlled by humans?
- How can the resulting rules be enforced technically?

You then build an agent that takes these requirements into account every time it runs. The challenge lies not only in understanding legal requirements, but in translating them into working software.

## 02 · What is BRANE?

BRANE is an AI firewall that sits between an application and the AI models it uses. It inspects requests, detects sensitive information and applies defined security policies before any data is sent to an AI model.

1. **Detect:** sensitive information in requests (personal data, contract details, confidential company content).
2. **Classify:** according to defined data categories and security policies.
3. **Protect:** remove, mask or pseudonymise sensitive content before forwarding to an external model.
4. **Route or Block:** forward to an approved model, restrict to available local processing, or block.
5. **Document:** teams record applied policies and decisions in a traceable test protocol.

Your task is not to program a complete data protection firewall yourselves. You research the necessary rules; BRANE enforces them. **The legal assessment and the definition of the right rules remain your responsibility. BRANE does not decide on its own what is legally permitted.**

## 03 · An example: privacy-aware recruiting agent

A company receives 40 applications. HR wants an agent that analyses the documents, summarises qualifications and prepares a structured comparison against job-related criteria. The final hiring decision remains with authorised people.

**Research questions:** legal bases for applicant data; GDPR requirements; EU AI Act requirements for AI in recruiting; which information is necessary; handling of special categories; automated assessments and human oversight. Answers must be backed by concrete legal sources.

**Example policy:**

| Data category | Example technical rule |
|---|---|
| Applicant name | Replace with an identifier before external transfer |
| Email address | Remove before external transfer |
| Professional qualifications | Release for analysis after reviewing legal basis and necessity |
| Health information | Exclude from analysis and block transfer |
| Final hiring decision | No autonomous decision by the agent |

The table is an example, not a generally applicable legal assessment. There is no blanket obligation to always pseudonymise applicant names.

**Flow:** original input (name, email, experience, unnecessary medical disclosure) → BRANE policy enforcement → protected model input ("Application CANDIDATE_01 …") → agent output. The mapping between CANDIDATE_01 and the person stays in the protected environment.

**Prove it works (five test cases for the example):**
- Permitted control case: clean application analysed as intended.
- Protected data: a medical disclosure in running text never reaches the external model.
- Repeated details: names and contact details handled at every occurrence, not only the first.
- Bypass attempt: rephrased requests or instructions hidden in a document do not override the rules.
- Check failure: if the BRANE check is unavailable, nothing is sent. An automatic cloud fallback fails this test.

Every decision must be traceable in the test protocol. **A single impermissible transfer means the security test has failed.** Depending on functionality, additional requirements may apply, including those for high-risk AI systems.

## 04 · Your mission in five steps

1. **Identify:** choose a legally challenging use case with relevant AI value and concrete legal/data protection challenges. Define the task, data and desired outcome.
2. **Research:** use verifiable sources: GDPR and national data protection laws, EU AI Act, publications by data protection authorities, case law, sector-specific regulations. Every material legal decision must be backed by a documented, traceable source.
3. **Define:** convert findings into policies using **ALLOW** (approve a permissible transfer), **PROTECT** (pseudonymise, mask or sanitise), **LOCAL ONLY** (process only in an approved local environment), **BLOCK** (prevent impermissible processing or transfer). Also cover human approvals, access rights and organisational requirements. Not every use case can be made lawful through pseudonymisation alone.
4. **Build:** integrate BRANE as an upstream control layer. Policies must apply to every relevant model request. The agent must be able to perform the task repeatedly.
5. **Validate:** test with different synthetic datasets and scenarios. Show the task completes, data categories are handled correctly, impermissible transfers are prevented, rules still apply when inputs change, and every decision is traceable in the test protocol.

## 05 · What you need to deliver

1. **Working AI Agent:** functional, reusable, with BRANE integration.
2. **Legal Research:** structured analysis of applicable requirements with concrete sources.
3. **Policy Matrix:** data categories, permitted processing, technical measures and legal justification.
4. **Live Demo & Business Case:** shows both the value of the agent and its technical safeguards.

**Minimum requirements:**
- A self-selected, legally demanding and fundamentally permissible use case
- At least three justified and implemented protection rules
- Five documented test cases covering the required scenarios
- Concrete, verifiable legal sources for the key policy decisions
- A working agent that can perform its task repeatedly
- Exclusively synthetic data, no real personal or confidential company data

## 06 · How you will be evaluated

| Category | Criteria | Points |
|---|---|---|
| Technology & Execution | Functionality, architecture, BRANE integration, technical enforcement and robustness | 40 |
| Legal Research & Governance | Quality of legal analysis, sources, data classification and derived policies | 40 |
| Business Impact | Problem relevance, practical value and scalability | 20 |
| **Total** | | **100** |

**Security tests (pass or fail).** Every team must pass five security tests. Any impermissible transfer counts as a failed test, regardless of total score.

| Test case | What must happen |
|---|---|
| Permitted control case | A permissible request is transferred as intended and the agent completes its task |
| Protected data | Data your rules protect is removed, pseudonymised, kept local or blocked before any external transfer |
| Repeated details | Every occurrence of protected information is handled, not only the first |
| Bypass attempt | Rephrased requests or instructions embedded in documents do not override your rules |
| Check failure | If the protection check is unavailable, the request is not sent. An automatic fallback to the cloud model fails this test |

Each test result and the decision taken (allow, protect, local only, block) must be traceable in your test protocol.

> An agent that completes its task but violates its protection rules is not a successful solution. A strong legal analysis without a working technical implementation is not enough. The best teams combine both.

## 07 · Format

- **Friday 20 November:** Research. Design. Build. Choose use case, research the law, define policies, develop the agent with BRANE.
- **Saturday 21 November:** Test. Demonstrate. Defend. Test, finalise and present to the jury.

| | |
|---|---|
| Teams | 4 to 5 students |
| Disciplines | Computer Science, AI, Business, Law, Compliance and other fields |
| Use case | Freely selectable, with a real legal or data protection challenge |
| Technology | OpenAI via BRANE |
| Data | Exclusively synthetic |
| Final | 21 November 2026 |

## 08 · Why participate

You learn how agentic AI applications are developed, how legal requirements are researched and assessed, how regulatory requirements become technical policies, how BRANE supports controlled processing of sensitive information, and how AI applications can be systematically tested for compliance with defined rules.

## Reference resources

- BRANE: AI Interaction Firewall
- EU General Data Protection Regulation (GDPR)
- EU Artificial Intelligence Act
- European Data Protection Board (EDPB): Automated Decision-Making
- EDPB: Pseudonymisation Guidelines

---

## Note: conflicts with the starter kit

| Topic | Track description (this doc) | Starter kit brief / README |
|---|---|---|
| Test 5 | **Check failure:** BRANE unavailable → nothing sent, no cloud fallback | **Special category / local:** Art. 9 data kept local or refused (HTTP 422) |
| Models | "OpenAI via BRANE" | OpenRouter cloud models + local vLLM models |

The five-tests CSV template uses "Check unavailable / unverifiable", which matches this document. Covering both variants (T5a + T5b) is the safe choice until the AI-Z desk confirms.
