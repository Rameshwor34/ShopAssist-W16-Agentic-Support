W16 Agent Design â€” ShopAssist AI
1. Overview

Week 16 extends the Week 15 ShopAssist AI assistant with a bounded agentic loop.

The key difference is that the system no longer follows a fixed application-defined sequence of steps. Instead, an agent decides what action to take next based on:

the user's request,
evidence collected so far,
unresolved information,
previous tool results,
conflicts or uncertainty.

The system can perform multiple actions before producing the final response.

The implemented agent supports:

search_knowledge
get_order_status
get_product_info
check_return_eligibility
ask_clarification
final_answer

The loop is bounded by a maximum of six iterations.

2. Agentic Loop

The runtime follows this general process:

User Query
    |
    v
AgenticService
    |
    v
AgentState
    |
    v
AgentDecisionEngine
    |
    v
Select Next Action
    |
    v
AgentActionExecutor
    |
    v
Tool / RAG
    |
    v
Compact Observation
    |
    v
Update AgentState
    |
    +----------------------+
    |                      |
    v                      |
AgentDecisionEngine <------+
    |
    v
Next Action
    |
    +--> Another Tool
    |
    +--> Ask Clarification
    |
    +--> Final Answer

The important property is that the next action is selected dynamically after observing the previous action's result.

For example, for:

Can I return ORD-1003, and what does the return policy say?

the agent may decide:

check_return_eligibility
        â†“
search_knowledge
        â†“
final_answer

However, this sequence is not hard-coded. A different query can produce a different trajectory.

3. Agent State

The agent maintains an explicit AgentState.

The state contains:

original user query,
current iteration,
collected evidence,
unresolved questions,
detected conflicts,
trajectory of previous actions,
sources,
execution status,
final answer,
token usage,
latency.

This state allows the decision engine to reason from previous tool results rather than restarting from the original query after every action.

4. Agent Decision

Each iteration produces a structured AgentDecision.

The decision contains:

action
arguments
reason
confidence

The action is restricted to an allowlist.

The application validates the model output using a Pydantic schema before execution.

This prevents arbitrary model-generated actions from being executed.

Example:

{
  "action": "get_order_status",
  "arguments": {
    "order_id": "ORD-1003"
  },
  "reason": "The user is asking about the current state of this order.",
  "confidence": 0.98
}
5. Available Actions
get_order_status

Retrieves the current status of an order.

Example:

get_order_status("ORD-1003")
get_product_info

Retrieves product information such as:

product name,
price,
description,
availability.
check_return_eligibility

Checks whether an order is eligible for return.

The result can include:

eligibility,
reason,
relevant order information.
search_knowledge

Searches the knowledge base for policy and FAQ information.

This is used when the agent needs information that is not available from transactional tools.

Examples include:

return policy,
refund policy,
shipping policy,
general support information.
ask_clarification

The agent uses this action when required information is missing.

For example:

What is the order ID you want me to check?

The application stops the loop when clarification is required.

final_answer

The agent selects this action when sufficient evidence has been collected.

The application then generates the final user-facing response from the available evidence.

6. Bounded Execution

The agent is intentionally bounded.

MAX_ITERATIONS = 6

The loop terminates when:

the agent selects final_answer,
the agent selects ask_clarification,
a fatal execution failure occurs,
the maximum number of iterations is reached.

The application, rather than the model, enforces the iteration limit.

This prevents:

infinite loops,
uncontrolled tool usage,
excessive token consumption,
repeated actions.
7. Tool Execution Boundary

The agent does not directly execute arbitrary Python functions.

Instead:

Agent Decision
      |
      v
Schema Validation
      |
      v
Action Allowlist
      |
      v
AgentActionExecutor
      |
      v
Specific Tool

The executor maps validated actions to known application tools.

Therefore, the model controls which allowed operation should happen next, while the application controls whether and how that operation can execute.

8. Context Engineering Technique
Structured Evidence Compaction

The primary context-engineering technique used in W16 is structured evidence compaction.

Raw tool and retrieval outputs are not continuously appended to the agent context.

Instead, each result is transformed into a compact structured observation containing only information relevant to future decisions.

For example, a raw order result may contain many fields:

{
  "success": true,
  "order": {
    "order_id": "ORD-1003",
    "status": "shipped",
    "customer": "...",
    "items": "...",
    "address": "...",
    "internal_metadata": "..."
  }
}

The agent state stores the relevant evidence in a compact form:

{
  "facts": {
    "order_id": "ORD-1003",
    "status": "shipped"
  },
  "sources": ["orders.json"]
}

This reduces unnecessary context growth and makes subsequent decisions easier to interpret.

Retrieval Compaction

Knowledge retrieval is also bounded.

The retrieval layer returns a small number of relevant results, and the executor converts them into compact evidence containing:

source,
relevant content,
result metadata.

This prevents large retrieval payloads from accumulating across iterations.

9. Why Single-Agent?

The implementation uses a single-agent architecture.

The task is primarily adaptive evidence gathering. The same controller can:

inspect the user request,
choose a relevant tool,
inspect its result,
decide whether additional evidence is required,
produce or request the final response.

A multi-agent architecture would introduce additional coordination overhead without providing a clear benefit for this task.

Potential multi-agent structural failure modes include:

Context saturation: multiple agents may duplicate or accumulate overlapping evidence.
Sequential bottleneck: one agent may have to wait for another before continuing.
Skill dilution: agents may have overlapping responsibilities instead of focused roles.
Coordination errors: one agent may misunderstand or incorrectly summarize another agent's result.
Self-verification paradox: agents may repeatedly validate each other's assumptions without obtaining independent evidence.

The single-agent design avoids these unnecessary coordination costs while still providing dynamic multi-step behavior.

10. Skill vs Agent

A skill provides reusable instructions or capabilities for performing a known type of task.

An agent is required when the system must dynamically decide what to do next based on intermediate results.

In this implementation:

Skill:
    "How to retrieve product information"

Agent:
    "Do I need product information next?"

The W16 feature requires the second behavior.

Therefore, the decision loop belongs to an agent rather than being implemented as another fixed skill.

11. Tool vs Agent Boundary

The tools are deterministic operations.

Examples:

get_order_status
get_product_info
check_return_eligibility
search_knowledge

The agent is responsible for selecting among those operations.

Therefore:

Tool = perform an operation
Agent = decide which operation should happen next

This separation keeps business operations deterministic while allowing adaptive reasoning at the orchestration layer.

12. Handling Missing Information

The agent checks whether required information is available.

For example:

User:
"What is the status of my order?"

If no order ID is available, the agent can select:

ask_clarification

instead of inventing an order ID.

The resulting state becomes:

clarification_required

and the loop terminates safely.

13. Handling Conflicting Evidence

The state can maintain a list of detected conflicts.

When evidence conflicts, the agent can:

perform another useful verification action,
search for authoritative policy information,
acknowledge uncertainty if the conflict cannot be resolved.

The system does not silently select unsupported information.

Transactional results are treated as authoritative for the mock transactional data, while policy and FAQ questions are resolved through the knowledge base.

14. Failure Handling

Tool failures are represented as structured observations.

The executor catches tool exceptions and returns controlled failure information instead of allowing an uncontrolled exception to propagate through the agent loop.

Examples include:

unavailable order service,
malformed tool response,
retrieval timeout.

The agent must not fabricate information when evidence is unavailable.

For example:

Tool:
Order service unavailable.

Agent:
I could not verify the order status because the order service is unavailable.

This provides a safe failure path.

15. Failure Injection

W16 includes explicit failure-injection tests.

The following scenarios are tested:

Tool unavailable

The order-status tool is replaced with a failing implementation.

Expected behavior:

failure is captured,
unsupported information is not invented,
the final response acknowledges that verification was unavailable.
Malformed tool response

A tool returns an unexpected structure.

Expected behavior:

malformed evidence is not treated as trustworthy,
the agent produces a safe response,
no hallucinated product information is generated.
Retrieval timeout

Knowledge retrieval is replaced with a timeout failure.

Expected behavior:

timeout is captured,
policy information is not fabricated,
the final answer clearly states that the policy could not be verified.
16. Evaluation Harness

The W16 evaluation harness uses deterministic mock model decisions so that the evaluation does not depend on Gemini API availability or quota.

The dataset contains 10 representative cases covering:

simple order lookup,
product lookup,
return eligibility,
multi-step policy verification,
combined order and policy queries,
missing order IDs,
missing product IDs,
unknown orders,
knowledge-base queries,
combined order and product queries.

The harness records:

task completion,
tool-call correctness,
argument correctness,
trajectory length,
number of tool calls,
token usage,
latency,
hard failures,
soft failures,
cascading soft failures.
17. Evaluation Metrics
Task Completion

Measures whether the agent reaches the expected final state.

A clarification request is considered successful when the expected behavior is to request missing information.

Tool-Call Correctness

Measures whether the agent selected the expected tools for the task.

Argument Correctness

Measures whether the agent supplied the correct identifiers and arguments.

Trajectory Length

Measures the number of decision steps required to complete a task.

Token Usage

Tracks model token usage for decision and final-answer generation.

Latency

Tracks end-to-end processing latency.

Hard Failures

Failures where the system cannot safely complete the task.

Soft Failures

Cases where the system completes the task but takes an unnecessary or suboptimal path.

Cascading Soft Failures

Cases where an early incorrect action causes additional unnecessary downstream actions.

18. Evaluation Results

The deterministic W16 evaluation currently reports:

Total cases:                  10
Task completion rate:         100%
Tool-call correctness:        80%
Argument correctness:         80%
Average trajectory length:    2.1
Average tool calls:           1.1
Average tokens:               1976.3
Average latency:              202.9877 ms
Hard failures:                0
Soft failures:                0
Cascading soft failures:      0

The evaluation demonstrates that the implementation can complete the defined task set while performing multi-step trajectories where required.

19. Token and Cost Accounting

Token usage is recorded for each agent decision and final-answer generation.

The state maintains:

total_tokens

and each trajectory step records token usage where available.

This allows the system to measure the cost of additional agent iterations.

A simple query typically requires one decision step, while a multi-step query consumes additional decision tokens because the agent must inspect intermediate evidence and choose another action.

This provides a direct way to compare:

Single-step baseline
        vs
Bounded agentic execution

The agentic approach may use more tokens for complex queries, but those additional calls enable adaptive evidence gathering that cannot be represented by a single fixed tool sequence.

20. Example Trajectories
Simple order query

User:

Where is order ORD-1003?

Trajectory:

get_order_status
        â†“
final_answer
Product query

User:

Tell me about PROD-101.

Trajectory:

get_product_info
        â†“
final_answer
Return query

User:

Can I return ORD-1003?

Trajectory:

check_return_eligibility
        â†“
final_answer
Multi-step query

User:

Can I return ORD-1003, and what does the return policy say?

Possible trajectory:

check_return_eligibility
        â†“
search_knowledge
        â†“
final_answer

The important point is that the second action is selected after observing the first result.

Missing information

User:

Can you check my order?

Trajectory:

ask_clarification

The agent does not invent an order ID.

21. Implementation-Specific Design

The implementation is divided into focused components:

backend/
â”œâ”€â”€ agents/
â”‚   â”œâ”€â”€ agent.py
â”‚   â”œâ”€â”€ evidence.py
â”‚   â”œâ”€â”€ executor.py
â”‚   â”œâ”€â”€ prompts.py
â”‚   â”œâ”€â”€ schemas.py
â”‚   â””â”€â”€ state.py
â”‚
â”œâ”€â”€ services/
â”‚   â””â”€â”€ agentic_service.py
â”‚
â”œâ”€â”€ tools/
â”‚   â”œâ”€â”€ definitions.py
â”‚   â”œâ”€â”€ orders.py
â”‚   â”œâ”€â”€ products.py
â”‚   â”œâ”€â”€ returns.py
â”‚   â””â”€â”€ registry.py
â”‚
â””â”€â”€ main.py

Responsibilities:

AgentState

Maintains the current execution state.

AgentDecisionEngine

Requests and validates the model's next action.

AgentActionExecutor

Executes only supported actions.

evidence.py

Converts raw results into compact structured observations.

AgenticService

Controls the bounded agentic loop.

schemas.py

Defines and validates the decision contract.

prompts.py

Defines the agent's operating instructions.

22. Safety and Control

The model is responsible for adaptive decisions, but the application remains responsible for execution safety.

Application-level controls include:

action allowlisting,
Pydantic validation,
required-argument validation,
exception handling,
bounded iterations,
structured failure handling,
safe clarification behavior,
evidence compaction,
no arbitrary code execution.

This creates a clear separation:

LLM:
Choose the next allowed action.

Application:
Validate, execute, observe, and enforce limits.
23. Summary

The W16 implementation transforms ShopAssist from a primarily request-response/RAG assistant into a bounded agentic support system.

The defining characteristic is the adaptive loop:

Observe
   â†“
Decide
   â†“
Act
   â†“
Observe Result
   â†“
Decide Again
   â†“
...

The system can perform multiple actions when necessary, stop when sufficient evidence is available, request clarification when information is missing, and fail safely when tools or retrieval systems are unavailable.

The architecture intentionally uses a single focused agent, structured evidence compaction, deterministic tools, explicit state, schema validation, bounded execution, failure injection, and an evaluation harness to make the agentic behavior measurable and reliable.

