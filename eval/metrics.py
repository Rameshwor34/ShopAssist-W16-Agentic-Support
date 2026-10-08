from typing import Any, Dict, List


def action_sequence(result: Dict[str, Any]) -> List[str]:
    return [
        item["action"]
        for item in result.get("trajectory", [])
        if item.get("type") == "tool_execution"
    ]


def argument_sequence(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        item.get("arguments", {})
        for item in result.get("trajectory", [])
        if item.get("type") == "tool_execution"
    ]


def evaluate_case(
    case: Dict[str, Any],
    result: Dict[str, Any],
) -> Dict[str, Any]:

    expected_status = case["expected_status"]
    expected_actions = case["expected_actions"]
    expected_arguments = case.get(
        "expected_arguments",
        [],
    )

    actual_actions = action_sequence(
        result
    )

    actual_arguments = argument_sequence(
        result
    )

    status_correct = (
        result.get("status")
        == expected_status
    )

    actions_correct = (
        actual_actions
        == expected_actions
    )

    arguments_correct = (
        actual_arguments
        == expected_arguments
    )

    completion = (
        status_correct
        and (
            actions_correct
            or (
                expected_status == "clarification_required"
                and result.get("status") == "clarification_required"
            )
        )
        and (
            arguments_correct
            or expected_status == "clarification_required"
        )
    )

    iterations = result.get(
        "iterations",
        0,
    )

    max_iterations = case.get(
        "max_iterations",
        6,
    )

    hard_failure = (
        result.get("status") == "failed"
        or iterations > max_iterations
    )

    soft_failure = (
        not hard_failure
        and not completion
        and result.get("status")
        in {
            "completed",
            "clarification_required",
        }
    )

    cascading_soft_failure = (
        soft_failure
        and len(actual_actions)
        > len(expected_actions)
    )

    return {
        "id": case["id"],
        "category": case["category"],
        "completion": completion,
        "status_correct": status_correct,
        "tool_calls_correct": actions_correct,
        "arguments_correct": arguments_correct,
        "expected_actions": expected_actions,
        "actual_actions": actual_actions,
        "expected_arguments": expected_arguments,
        "actual_arguments": actual_arguments,
        "status": result.get("status"),
        "iterations": iterations,
        "tool_calls": result.get(
            "tool_calls",
            0,
        ),
        "tokens": result.get(
            "total_tokens",
            0,
        ),
        "latency_ms": result.get(
            "total_latency_ms",
            0,
        ),
        "hard_failure": hard_failure,
        "soft_failure": soft_failure,
        "cascading_soft_failure": (
            cascading_soft_failure
        ),
    }


def aggregate_metrics(
    evaluations: List[Dict[str, Any]],
) -> Dict[str, Any]:

    total = len(evaluations)

    if total == 0:
        return {}

    completed = sum(
        item["completion"]
        for item in evaluations
    )

    tool_correct = sum(
        item["tool_calls_correct"]
        for item in evaluations
    )

    argument_correct = sum(
        item["arguments_correct"]
        for item in evaluations
    )

    hard_failures = sum(
        item["hard_failure"]
        for item in evaluations
    )

    soft_failures = sum(
        item["soft_failure"]
        for item in evaluations
    )

    cascading = sum(
        item["cascading_soft_failure"]
        for item in evaluations
    )

    return {
        "total_cases": total,
        "task_completion_rate": round(
            completed / total,
            4,
        ),
        "tool_call_correctness": round(
            tool_correct / total,
            4,
        ),
        "argument_correctness": round(
            argument_correct / total,
            4,
        ),
        "average_trajectory_length": round(
            sum(
                item["iterations"]
                for item in evaluations
            )
            / total,
            4,
        ),
        "average_tool_calls": round(
            sum(
                item["tool_calls"]
                for item in evaluations
            )
            / total,
            4,
        ),
        "average_tokens": round(
            sum(
                item["tokens"]
                for item in evaluations
            )
            / total,
            4,
        ),
        "average_latency_ms": round(
            sum(
                item["latency_ms"]
                for item in evaluations
            )
            / total,
            4,
        ),
        "hard_failures": hard_failures,
        "soft_failures": soft_failures,
        "cascading_soft_failures": cascading,
    }

