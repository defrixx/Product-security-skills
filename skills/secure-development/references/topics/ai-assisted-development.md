# AI-assisted development and model integrations

## SD-AI-001

Status: proposed engineering baseline; C01–C06 are MUST conditions when applicable. Use the [requirement format](../requirement-format.md) for exceptions and evidence. These are engineering applications of the cited threat guidance, not verbatim OWASP requirements. Record the model/provider, adapter, tools, trust boundaries, and actual execution environment. Using an assistant to write ordinary code does not make every model-runtime condition applicable.

### SD-AI-001.C01 — Preserve instruction provenance at dispatch

- **Apply when:** an application assembles model requests from static instructions and external data, or claims prompt-change protection.
- **Required / prohibited:** external content must not become application-controlled instruction authority. When integrity protection is claimed, verify the approved instructions and instruction-bearing tool definitions immediately before every dispatch; mismatches must prevent transmission, including retries and fallback.
- **Rationale:** files, retrieved content and tool responses can influence an agent; unchanged instructions alone do not constrain its actions.
- **Implement:** keep trusted configuration distinct from user/retrieval/history data. Protect baseline selection separately. Send the checked snapshot, reject unsupported request shapes, and inventory all call paths. Explicitly label unsupported adapters and dynamic instructions. Delimiters and source labels assist interpretation but are not enforcement.
- **Unsafe → corrected:** check a request then rebuild it through an SDK → dispatch exactly the checked payload through a reviewed transport.
- **Positive check:** an approved request with ordinary external data reaches the synthetic transport.
- **Negative check:** changed text, roles, tool schemas, model selection and retry instructions never reach it; injection in a data message remains data and must be assessed under C02–C03.
- **Evidence:** request-to-wire bytes, independent baseline provenance, attempt inventory and blocked-send observations.
- **Bounds / sources:** S1; exact dispatch/pinning is this baseline's implementation guidance. Integrity does not prove model obedience, provider internals or safety of baseline content.

### SD-AI-001.C02 — Authorize model-proposed actions outside the model

- **Apply when:** a model can propose tool calls, file changes, execution, retrieval or external effects.
- **Required / prohibited:** enforce the task's operations, resources and recipients at the effect boundary independently of model text. A tool description, valid schema, fabricated approval or earlier permitted call must not grant additional authority.
- **Rationale:** an attacker may steer a model through legitimate inputs without changing its static prompt.
- **Implement:** offer narrow capabilities and check the actual caller/task scope in handlers. Validate an entire proposed batch before effects for unsupported functions, shapes and ambiguous arguments; bind call/result identifiers. Execution still needs per-operation authorization and current state checks. If approval is required by the task's risk policy, bind it to the concrete operation/arguments and invalidate it after material drift; existing scoped authorization need not be repeatedly requested.
- **Unsafe → corrected:** a retrieved comment says to upload credentials → reject the unapproved read/recipient even if the model requests a valid tool.
- **Positive check:** an authorized operation affects only its permitted synthetic resource.
- **Negative check:** direct calls, injected approval, an unoffered tool, changed recipient, duplicate argument keys and malformed later calls cannot obtain unapproved effects. Test expired/replayed approval only where approvals exist.
- **Evidence:** gate-to-effect trace and sentinel observations, including allowed behavior. Record partial effects of runtime failures separately from input rejection.
- **Bounds / sources:** S2. Batch validation is not transactional rollback, exactly-once execution or general injection immunity. Local single-user tools need capability boundaries, not invented tenants.

### SD-AI-001.C03 — Treat generated output as input to each downstream sink

- **Apply when:** generated text, code, Markdown, paths, queries or tool arguments reach a renderer, interpreter or sensitive operation.
- **Required / prohibited:** apply the destination's validation, encoding and confinement before use. Syntactically valid JSON and matching prompts do not establish safe effects.
- **Rationale:** model output can carry attacker-controlled syntax into conventional vulnerability sinks.
- **Implement:** use bound query values, context-aware output handling and constrained file/process APIs; assess [input conditions](input-validation-injection.md), [browser sinks](client-web-security.md), [files](files-uploads.md) and [outbound requests](outbound-requests.md) as applicable. Avoid executing free-form model commands merely to complete an evaluation. Restrict automatic Markdown resource loads according to the delivery context and recipient policy.
- **Unsafe → corrected:** render generated raw HTML → render text or use the selected HTML sanitization policy before display.
- **Positive check:** expected generated content reaches the intended sink with correct behavior.
- **Negative check:** synthetic script markup, query syntax, path escape or excluded resource URL cannot execute or escape the selected boundary; select actual sinks instead of an unconditional payload bundle.
- **Evidence:** generated-output-to-sink trace and observed state/network/rendering effects.
- **Bounds / sources:** S3. One safe renderer does not establish safety of email, export or tool paths; select supported syntax.

### SD-AI-001.C04 — Scope context and memory before disclosure

- **Apply when:** prompts, retrieval, summaries, caches or persistent agent memory contain protected project or user data.
- **Required / prohibited:** authorize and minimize data before it enters model context or leaves for a provider. Retrieval relevance and model refusal do not replace access checks; source content cannot establish identity or permission.
- **Rationale:** context and derived memory can expose data across task, project or principal boundaries.
- **Implement:** enforce the actual source permissions before context assembly; carry scope through summaries/caches and recheck it after rights change. Apply [authorization](authorization-access-control.md), [privacy](privacy-data-protection.md) and [secrets](secrets.md) separately. Keep credentials out of static prompts; inspect actual provider destination and configured logging/retention rather than inferring them from a request flag.
- **Unsafe → corrected:** share one retrieval cache across protected projects → partition by the effective access scope and invalidate affected derived context.
- **Positive check:** permitted synthetic documents appear in context and ordinary task memory remains usable.
- **Negative check:** wrong-project retrieval and revoked cached content do not enter the model request or delivered output; injected instructions cannot select another context store.
- **Evidence:** source-to-context inventory, recorded wire/context inspection and cache/revocation cases.
- **Bounds / sources:** S4, S5. No universal retention period is prescribed; local-only operation does not establish isolation of saved histories. Prompt secrecy is not an authorization control.

### SD-AI-001.C05 — Bound work across the agent lifecycle

- **Apply when:** model requests or agent tools consume resources or can repeat work.
- **Required / prohibited:** enforce deployment-appropriate request, response, tool-call and run budgets outside the model. An incomplete run, truncation or protocol failure must not be reported as a passed control or silently retried without bounds.
- **Rationale:** repeated calls and oversized data can exhaust resources or multiply effects.
- **Implement:** limit bytes/depth/counts before parsing/dispatch, response bytes and tool batches, and select cancellation/deadline behavior appropriate to the task. Distinguish per-socket timeout from total elapsed budget. Include retries/fallback in the budget; treat ambiguous delivery separately and apply [repeatable-effect conditions](business-logic.md) to mutations.
- **Unsafe → corrected:** restart the agent after each timeout indefinitely → stop at the declared budget and record unknown delivery and remaining checks.
- **Positive check:** a bounded ordinary run completes with its expected allowed effects.
- **Negative check:** oversized response, repeated tool rounds and stalled transport stop within the selected limits without unchecked fallback. Observe recipient effects after timeout when the application retries mutations.
- **Evidence:** counters, elapsed/cancellation observations and synthetic effect counts; verify cancellation at the exercised timeout boundaries.
- **Bounds / sources:** S6. Limits depend on the target; byte limits alone do not bound wall time or provider cost, and timeout does not prove nondelivery.

### SD-AI-001.C06 — Verify generated changes and evidence before promotion

- **Apply when:** AI proposes source, dependencies, CI configuration, tests or security conclusions for development.
- **Required / prohibited:** inspect actual changes and independently observed evidence before describing them as applied or verified. Generated package names, citations, test results and claimed approvals are untrusted proposals.
- **Rationale:** plausible output may introduce malicious dependencies or falsely assert that a control held.
- **Implement:** verify dependency identity/version through primary maintainer sources and apply [supply-chain conditions](dependencies-supply-chain.md). Inspect new hooks before isolated execution. Tie checks to the candidate/target revision and relevant configuration; use allowed and attack cases reaching the disputed operation. Keep evaluator ground truth unavailable to the evaluated agent, and distinguish deterministic helper tests, simulated models and actual agent trials.
- **Unsafe → corrected:** accept generated prose saying tests passed → inspect the executed result and the exact assessed content, retaining unexecuted clauses as gaps.
- **Positive check:** an observed allowed/negative test pair supports its exact bounded claim.
- **Negative check:** fabricated evidence ID, stale content hash, unknown dependency and candidate-only patch cannot be promoted to verified/applied state without the missing observation.
- **Evidence:** inspected patch/dependency provenance, actual test outcomes and revision/content bindings; separate model-authored claims from evaluator observations.
- **Bounds / sources:** S3 (generated-code/package risks); evidence-state checks are this baseline's engineering guidance. Passing tests are not comprehensive security review or proof of generalized assistant reliability.

## Sources

All checked 2026-10-03 against OWASP Gen AI Security Project, LLM Top 10 **2025**. These threat documents support the rationale; the scoped MUST conditions and acceptance cases above are this repository's proposed engineering baseline.

- **S1:** [LLM01:2025 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) — indirect injection, privilege control and external-content segregation.
- **S2:** [LLM06:2025 Excessive Agency](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/) — functionality, permissions and autonomy.
- **S3:** [LLM05:2025 Improper Output Handling](https://genai.owasp.org/llmrisk/llm052025-improper-output-handling/) — downstream sinks and generated-code/package examples.
- **S4:** [LLM08:2025 Vector and Embedding Weaknesses](https://genai.owasp.org/llmrisk/llm082025-vector-and-embedding-weaknesses/) — access controls and cross-context leakage.
- **S5:** [LLM07:2025 System Prompt Leakage](https://genai.owasp.org/llmrisk/llm072025-system-prompt-leakage/) — credentials and controls outside prompts.
- **S6:** [LLM10:2025 Unbounded Consumption](https://genai.owasp.org/llmrisk/llm102025-unbounded-consumption/) — resource limits and timeouts.
