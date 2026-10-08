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

from eval.metrics import (
    aggregate_metrics,
    evaluate_case,
)


DATASET_PATH = (
    ROOT
    / "eval"
    / "dataset.json"
)

RESULTS_PATH = (
    ROOT
    / "eval"
    / "results.json"
)


def load_dataset():
    with open(
        DATASET_PATH,
        "r",
        encoding="utf-8-sig",
    ) as file:
        return json.load(file)


def run_case(case):

    provider = MockAgentProvider(
        decisions=case["decisions"],
        final_answer=case.get(
            "final_answer",
            "Mock answer.",
        ),
    )

    engine = AgentDecisionEngine(
        provider=provider
    )

    service = AgenticService(
        decision_engine=engine,
        executor=AgentActionExecutor(),
        provider=provider,
    )

    result = service.process(
        case["query"]
    )

    evaluation = evaluate_case(
        case,
        result,
    )

    evaluation["trajectory"] = (
        result.get(
            "trajectory",
            [],
        )
    )

    evaluation["answer"] = (
        result.get(
            "answer"
        )
    )

    return evaluation


def main():

    dataset = load_dataset()

    evaluations = []

    print("=" * 70)
    print("W16 AGENT EVALUATION")
    print("=" * 70)

    for index, case in enumerate(
        dataset,
        start=1,
    ):

        print(
            f"[{index}/{len(dataset)}] "
            f"{case['id']}"
        )

        try:

            evaluation = run_case(
                case
            )

            evaluations.append(
                evaluation
            )

            print(
                "  status:",
                evaluation["status"],
            )

            print(
                "  completion:",
                evaluation["completion"],
            )

            print(
                "  actions:",
                evaluation["actual_actions"],
            )

            print(
                "  tokens:",
                evaluation["tokens"],
            )

            print(
                "  latency:",
                evaluation["latency_ms"],
            )

        except Exception as exc:

            print(
                "  HARNESS ERROR:",
                type(exc).__name__,
                str(exc),
            )

            evaluations.append(
                {
                    "id": case["id"],
                    "category": case["category"],
                    "completion": False,
                    "status_correct": False,
                    "tool_calls_correct": False,
                    "arguments_correct": False,
                    "hard_failure": True,
                    "soft_failure": False,
                    "cascading_soft_failure": False,
                    "error": (
                        f"{type(exc).__name__}: "
                        f"{exc}"
                    ),
                }
            )

    aggregate = aggregate_metrics(
        evaluations
    )

    output = {
        "evaluation_type": (
            "deterministic_controller_regression"
        ),
        "provider": "MockAgentProvider",
        "metrics": aggregate,
        "cases": evaluations,
    }

    with open(
        RESULTS_PATH,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            output,
            file,
            indent=2,
        )

    print()
    print("=" * 70)
    print("AGGREGATE RESULTS")
    print("=" * 70)

    for key, value in aggregate.items():
        print(
            f"{key}: {value}"
        )

    print()
    print(
        f"Results written to: {RESULTS_PATH}"
    )


if __name__ == "__main__":
    main()
