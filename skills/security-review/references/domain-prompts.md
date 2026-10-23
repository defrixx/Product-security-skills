# Web and agent discovery prompts

Use these prompts to expand actual entry-to-effect traces, not to count category labels as coverage. Apply [analysis and validation](analysis-and-validation.md) to every candidate. Do not prescribe controls for architecture absent from the target.

## Web-facing paths

| Surface | Investigate |
| --- | --- |
| Identity and access | Recovery, session invalidation, token issuer/audience; object, property, bulk and tenant authorization through alternate routes |
| Parsing and execution | Input becoming SQL, shell, template or deserializer instructions; framework binding and escaping counterevidence |
| Browser boundary | DOM/rendering sinks, message origins, credentialed cross-origin requests, CSRF and actual browser request feasibility |
| Files and network | Archive/manifest paths, symlinks, upload consumption, redirects and resolution before outbound requests |
| Design and resource use | Workflow abuse, absent cost bounds, dependency failure, repeated side effects and unsafe recovery |
| Configuration and supply chain | Debug exposure, proxy trust, packaged dependencies, untrusted CI inputs and install hooks |
| Data and observation | Peer verification, key/nonce lifecycle, sensitive errors/logs and security event attribution |

Select adjacent paths with different guards. A framework default is useful counterevidence only if it applies to the actual call/configuration. OWASP category membership is navigation, not proof or a complete testing standard.

## Agent indicators and abuse paths

Load this section for model-selected tools, MCP, agent loops, delegated work, persistent memory, retrieval or approval gates. Single-shot text generation still requires assessment of untrusted input and generated-output sinks; do not force an agent taxonomy onto it.

| Agent boundary | Questions that change the investigation |
| --- | --- |
| Goal and context | Can retrieved text, tool descriptions or outputs redirect an authorized task? Where is scope enforced before effects? |
| Tool and identity | Can direct synthetic arguments bypass policy, caller/tenant restrictions or scoped credentials? Does model choice grant authority? |
| Supply chain and execution | Can a changed tool, prompt or generated command gain host files, ambient credentials or network access? |
| Memory | Can one actor persist instructions or data consumed with greater trust by another actor or later task? Check attribution and deletion paths |
| Delegation | Are sender identity, delegated authority and replay protection enforced at the receiver? Can message content impersonate approval? |
| Failure and budgets | Can retries, fallback or fan-out bypass a denial or multiply effects/cost? Inspect bounded recovery and interruption |
| Human approval | Does consent bind the actual tool, target, arguments and revision? Can the agent rewrite the displayed action or reuse approval after a change? |
| Autonomous operation | Can scheduled goals or configuration be altered by a weaker actor? Can the workflow be stopped and its effects attributed? |

Inspect reach (accessible data/tools/credentials) separately from latitude (decisions allowed without further authorization). Require only controls justified by the target's risk and authorization contract. Delimiters, canaries and model refusals alone do not establish an enforced action boundary. An out-of-band approval UI is an implementation option, not a universal requirement.

For scoped agent tests, define the expected output, authorization decision and downstream effect separately. Missing traces or unrelated denials are inconclusive. Record configuration/state and attack budgets, compare matched budgets and include benign controls. Select cases by risk; no complete red-team engagement is implied.

## Sources

- [OWASP GenAI Red Teaming Manual](https://genai.owasp.org/resource/genai-red-teaming-manual-version-1-0/), version 1.0, §7.2–7.4 (pp. 119–122), methodological guidance; verified 2026-10-23.

- [OWASP Top 10:2025](https://top10.owasp.org/2025/), 2025 edition, category overview; verified 2026-10-18. Use the edition explicitly when classifying; do not infer a one-to-one mapping from older editions.
- [OWASP Top 10 for Agentic Applications for 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/), 2026 edition, ASI01–ASI10; verified 2026-10-18. These prompts synthesize investigation questions; taxonomy labels do not establish exploitability or an official CWE mapping.
