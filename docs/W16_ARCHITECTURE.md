````markdown
# W16 Architecture â€” ShopAssist AI

## 1. System Overview

W16 extends the W15 ShopAssist AI system with a bounded single-agent architecture.

The agent dynamically selects the next action based on the user query and the evidence collected from previous actions.

```mermaid
flowchart TD
    A[User] --> B[FastAPI /agent/chat]
    B --> C[AgenticService]
    C --> D[AgentState]
    D --> E[AgentDecisionEngine]

    E --> F{Next Action}

    F -->|get_order_status| G[Order Tool]
    F -->|get_product_info| H[Product Tool]
    F -->|check_return_eligibility| I[Return Tool]
    F -->|search_knowledge| J[RAG / Knowledge Base]
    F -->|ask_clarification| K[Clarification]
    F -->|final_answer| L[Final Answer]

    G --> M[Compact Evidence]
    H --> M
    I --> M
    J --> M

    M --> D
    D --> E

    K --> N[Return Clarification]
    L --> O[User Response]
````

---

## 2. Core Agentic Loop

The central W16 behavior is an iterative decision loop.

```text
User Query
    â†“
Initialize AgentState
    â†“
AgentDecisionEngine
    â†“
Validate Decision
    â†“
Execute Selected Action
    â†“
Compact Result into Evidence
    â†“
Update AgentState
    â†“
AgentDecisionEngine
    â†“
Execute Another Action / Clarify / Finish
```

Unlike a fixed workflow, the next action is determined from the current state.

For example:

```text
User:
"Can I return ORD-1003 and what does the return policy say?"

        â†“

check_return_eligibility
        â†“
observe result
        â†“
search_knowledge
        â†“
observe result
        â†“
final_answer
```

Another request may require only one action:

```text
get_order_status
        â†“
final_answer
```

---

## 3. Component Architecture

```text
backend/
â”‚
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
â”œâ”€â”€ llm/
â”‚   â””â”€â”€ gemini_provider.py
â”‚
â””â”€â”€ main.py
```

---

## 4. Component Responsibilities

### FastAPI

Provides the HTTP API.

W16 introduces:

```text
POST /agent/chat
```

The existing W15 endpoint remains available:

```text
POST /chat
```

### AgenticService

`AgenticService` is the main runtime controller.

Responsibilities:

* initialize agent state,
* invoke the decision engine,
* execute actions,
* update evidence,
* enforce iteration limits,
* handle clarification,
* handle failures,
* generate the final response,
* record token and latency information.

### AgentState

Stores the complete state of the current agent run.

Important fields include:

```text
user_query
iteration
evidence
unresolved_questions
conflicts
trajectory
sources
status
final_answer
total_tokens
total_latency_ms
```

This state allows later decisions to depend on earlier observations.

### AgentDecisionEngine

The decision engine communicates with the language model.

It receives:

* user query,
* current iteration,
* collected evidence,
* unresolved questions,
* conflicts,
* recent trajectory.

It returns a structured `AgentDecision`.

### AgentDecision Schema

The model must return:

```json
{
  "action": "get_order_status",
  "arguments": {
    "order_id": "ORD-1003"
  },
  "reason": "The order status is required to answer the user's request.",
  "confidence": 0.98
}
```

The schema restricts actions to the supported action set.

### AgentActionExecutor

The executor maps validated actions to deterministic application operations.

```text
Agent Action
     â†“
Validation
     â†“
Allowlist
     â†“
Executor
     â†“
Tool
```

The executor does not permit arbitrary model-generated functions.

---

## 5. Tool Architecture

The W16 agent can use the following tools:

```text
get_order_status
get_product_info
check_return_eligibility
search_knowledge
```

The tools are deterministic application operations.

The agent decides **when** to use them.

The tools determine **how** the operation is performed.

---

## 6. Tool Registry

The existing W15 transactional tools are registered through the tool registry.

```text
TOOL_REGISTRY
    â”‚
    â”œâ”€â”€ get_order_status
    â”œâ”€â”€ get_product_info
    â””â”€â”€ check_return_eligibility
```

Knowledge retrieval is invoked separately through the RAG retrieval layer.

---

## 7. Evidence Flow

Raw tool results are converted into compact observations.

```text
Tool Result
    â†“
Evidence Compaction
    â†“
Structured Observation
    â†“
AgentState.evidence
    â†“
Next Agent Decision
```

Example:

```json
{
  "facts": {
    "order_id": "ORD-1003",
    "status": "shipped"
  },
  "sources": [
    "orders.json"
  ]
}
```

This prevents unnecessary raw data from accumulating in the agent context.

---

## 8. Context Engineering

The main context-engineering technique is **structured evidence compaction**.

Instead of repeatedly passing complete raw tool outputs to the model, the system retains only the information required for subsequent decisions.

For retrieval results, the system also limits the amount of retrieved information before placing it into the agent state.

```text
Raw Retrieval
     â†“
Top-k Results
     â†“
Relevant Evidence
     â†“
Compact Observation
     â†“
Agent Context
```

This keeps the context bounded and reduces unnecessary token usage.

---

## 9. Decision Boundary

The model controls the decision layer.

```text
                 â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                 â”‚       Agent          â”‚
                 â”‚                      â”‚
                 â”‚ "What should happen  â”‚
                 â”‚      next?"          â”‚
                 â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                            â”‚
                            â–¼
                 â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                 â”‚   Allowed Actions    â”‚
                 â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                            â”‚
                            â–¼
                 â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                 â”‚    Application       â”‚
                 â”‚                      â”‚
                 â”‚ Validate + Execute   â”‚
                 â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

This separation prevents the LLM from directly controlling application internals.

---

## 10. Bounded Loop

The agent uses:

```text
MAX_ITERATIONS = 6
```

The loop terminates when:

```text
final_answer
```

or:

```text
ask_clarification
```

is selected.

It also terminates on:

* fatal execution failure,
* maximum iteration count.

Therefore, the system cannot continue indefinitely.

---

## 11. Single-Agent Architecture

W16 uses a single-agent architecture.

```text
                 â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                 â”‚   Single Agent  â”‚
                 â””â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                          â”‚
            â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
            â”‚             â”‚             â”‚
            â–¼             â–¼             â–¼
         Orders        Products       RAG
```

A single agent is sufficient because the task requires adaptive evidence gathering rather than independent parallel reasoning.

Using multiple agents would introduce:

* additional coordination,
* additional context passing,
* increased token usage,
* sequential bottlenecks,
* possible disagreement between agents.

The single-agent design keeps the architecture simpler while still satisfying the agentic-loop requirement.

---

## 12. Failure Handling Architecture

Tool failures are converted into structured observations.

```text
Tool
 â†“
Exception / Invalid Result
 â†“
Executor catches failure
 â†“
Structured failure observation
 â†“
AgentState
 â†“
Safe response
```

The agent is instructed not to invent information when required evidence is unavailable.

Failure cases tested include:

```text
Tool unavailable
Malformed tool response
Retrieval timeout
```

---

## 13. Clarification Flow

When required information is missing:

```text
User Query
    â†“
Agent Decision
    â†“
ask_clarification
    â†“
AgenticService
    â†“
Clarification Response
```

Example:

```text
User:
"Check my order."

Agent:
"What is the order ID you want me to check?"
```

The system does not fabricate an order identifier.

---

## 14. Final Answer Flow

When sufficient evidence has been collected:

```text
Agent
  â†“
final_answer
  â†“
Final Answer Generation
  â†“
User
```

The final response is generated from the collected evidence rather than unsupported assumptions.

---

## 15. Request Lifecycle

A complete request follows:

```text
1. User sends query
        â†“
2. FastAPI receives request
        â†“
3. AgenticService creates AgentState
        â†“
4. AgentDecisionEngine selects action
        â†“
5. Decision is schema-validated
        â†“
6. Executor runs allowed action
        â†“
7. Result is compacted into evidence
        â†“
8. AgentState is updated
        â†“
9. Agent decides again
        â†“
10. Loop continues until termination
        â†“
11. Final response returned
```

---

## 16. Observability

Each run records:

* action sequence,
* action arguments,
* decision reasons,
* confidence,
* tool results,
* evidence,
* token usage,
* latency,
* trajectory length,
* final status.

A response from `/agent/chat` therefore exposes enough information for evaluation and debugging without exposing hidden chain-of-thought.

---

## 17. Evaluation Architecture

The evaluation harness uses a deterministic mock provider.

```text
Evaluation Dataset
        â†“
Evaluation Harness
        â†“
AgenticService
        â†“
AgentDecisionEngine
        â†“
Mock Provider
        â†“
AgentActionExecutor
        â†“
Tools
        â†“
Evaluation Metrics
```

The harness evaluates:

```text
Task Completion
Tool-Call Correctness
Argument Correctness
Trajectory Length
Token Usage
Latency
Hard Failures
Soft Failures
Cascading Soft Failures
```

---

## 18. Failure Injection Architecture

Failure injection replaces normal tool behavior with controlled failures.

```text
                â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                â”‚ Failure Test    â”‚
                â””â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                         â†“
                 AgentActionExecutor
                         â†“
              â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
              â†“          â†“          â†“
          Unavailable  Malformed   Timeout
             Tool       Result    Retrieval
```

The objective is to verify that the agent fails safely instead of hallucinating missing information.

---

## 19. W15 â†’ W16 Evolution

### W15

```text
User
 â†“
FastAPI
 â†“
Intent / RAG
 â†“
Tool or Retrieval
 â†“
Response
```

### W16

```text
User
 â†“
FastAPI
 â†“
Agent
 â†“
Decision
 â†“
Tool / RAG
 â†“
Evidence
 â†“
Agent
 â†“
Decision Again
 â†“
Tool / RAG / Clarification / Final Answer
```

The major architectural change is the introduction of a stateful, bounded decision loop.

---

## 20. Design Principles

The W16 architecture follows these principles:

1. **Dynamic action selection** â€” the next action depends on previous results.
2. **Bounded execution** â€” maximum six iterations.
3. **Deterministic tools** â€” business operations remain controlled by application code.
4. **Structured decisions** â€” model output is schema-validated.
5. **Evidence-based responses** â€” final answers rely on collected evidence.
6. **Context compaction** â€” raw results are converted into concise observations.
7. **Safe failure handling** â€” unavailable or malformed tools do not cause hallucinated answers.
8. **Explicit clarification** â€” missing information results in a clarification request.
9. **Measurable behavior** â€” trajectories, tokens, latency, and failures are recorded.
10. **Single-agent simplicity** â€” one focused agent is used instead of unnecessary multi-agent coordination.

```
```

