import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from backend.agents.agent import AgentDecisionEngine
from backend.agents.executor import AgentActionExecutor
from backend.services.agentic_service import AgenticService
from backend.tests.mock_provider import MockAgentProvider


class UnavailableToolExecutor(
    AgentActionExecutor
):

    def execute(
        self,
        action,
        arguments,
    ):

        if action == "get_order_status":
            return {
                "success": False,
                "error": (
                    "Injected failure: "
                    "order service unavailable."
                ),
            }

        return super().execute(
            action,
            arguments,
        )


class MalformedToolExecutor(
    AgentActionExecutor
):

    def execute(
        self,
        action,
        arguments,
    ):

        if action == "get_product_info":
            return {
                "success": True,
                "malformed": True,
                "unexpected": object(),
            }

        return super().execute(
            action,
            arguments,
        )


class RetrievalFailureExecutor(
    AgentActionExecutor
):

    def execute(
        self,
        action,
        arguments,
    ):

        if action == "search_knowledge":
            return {
                "success": False,
                "type": "knowledge_search",
                "error": (
                    "Injected failure: "
                    "retrieval service timeout."
                ),
            }

        return super().execute(
            action,
            arguments,
        )


def run_failure_case(
    name,
    query,
    decisions,
    executor,
    final_answer,
):

    provider = MockAgentProvider(
        decisions=decisions,
        final_answer=final_answer,
    )

    engine = AgentDecisionEngine(
        provider=provider
    )

    service = AgenticService(
        decision_engine=engine,
        executor=executor,
        provider=provider,
    )

    result = service.process(
        query
    )

    return {
        "name": name,
        "query": query,
        "status": result.get(
            "status"
        ),
        "answer": result.get(
            "answer"
        ),
        "trajectory": result.get(
            "trajectory",
            [],
        ),
        "tokens": result.get(
            "total_tokens",
            0,
        ),
        "latency_ms": result.get(
            "total_latency_ms",
            0,
        ),
    }


def main():

    results = []

    results.append(
        run_failure_case(
            name="tool_unavailable",
            query=(
                "What is the status "
                "of ORD-1003?"
            ),
            decisions=[
                {
                    "action": "get_order_status",
                    "arguments": {
                        "order_id": "ORD-1003"
                    },
                    "reason": (
                        "The order status "
                        "must be checked."
                    ),
                    "confidence": 0.99,
                },
                {
                    "action": "final_answer",
                    "arguments": {},
                    "reason": (
                        "The failed lookup "
                        "must not be replaced "
                        "with an invented fact."
                    ),
                    "confidence": 0.90,
                },
            ],
            executor=UnavailableToolExecutor(),
            final_answer=(
                "I could not verify the "
                "order status because the "
                "order service is unavailable."
            ),
        )
    )

    results.append(
        run_failure_case(
            name="malformed_tool_response",
            query=(
                "Tell me about "
                "product PROD-001."
            ),
            decisions=[
                {
                    "action": "get_product_info",
                    "arguments": {
                        "product_id": "PROD-001"
                    },
                    "reason": (
                        "Product information "
                        "is required."
                    ),
                    "confidence": 0.99,
                },
                {
                    "action": "final_answer",
                    "arguments": {},
                    "reason": (
                        "The malformed response "
                        "must not be treated "
                        "as verified product data."
                    ),
                    "confidence": 0.90,
                },
            ],
            executor=MalformedToolExecutor(),
            final_answer=(
                "I could not safely verify "
                "the product information."
            ),
        )
    )

    results.append(
        run_failure_case(
            name="retrieval_timeout",
            query=(
                "What is the return policy?"
            ),
            decisions=[
                {
                    "action": "search_knowledge",
                    "arguments": {
                        "query": "return policy"
                    },
                    "reason": (
                        "The request requires "
                        "knowledge-base evidence."
                    ),
                    "confidence": 0.99,
                },
                {
                    "action": "final_answer",
                    "arguments": {},
                    "reason": (
                        "The retrieval failure "
                        "must not result in "
                        "a fabricated policy."
                    ),
                    "confidence": 0.90,
                },
            ],
            executor=RetrievalFailureExecutor(),
            final_answer=(
                "I could not verify the return "
                "policy because the knowledge "
                "retrieval service timed out."
            ),
        )
    )

    output_path = (
        ROOT
        / "eval"
        / "failure_results.json"
    )

    with open(
        output_path,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            results,
            file,
            indent=2,
            default=str,
        )

    print("=" * 70)
    print("W16 FAILURE INJECTION TESTS")
    print("=" * 70)

    for result in results:

        print()
        print(
            "TEST:",
            result["name"],
        )

        print(
            "STATUS:",
            result["status"],
        )

        print(
            "ANSWER:",
            result["answer"],
        )

        print(
            "TOKENS:",
            result["tokens"],
        )

        print(
            "LATENCY:",
            result["latency_ms"],
        )

    print()
    print(
        "Results written to:",
        output_path,
    )


if __name__ == "__main__":
    main()
