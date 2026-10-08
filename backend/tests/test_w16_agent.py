from backend.agents.schemas import AgentDecision
from backend.agents.state import AgentState
from backend.tests.mock_provider import MockAgentProvider


def test_agent_decision_schema():
    decision = AgentDecision(
        action="get_order_status",
        arguments={"order_id": "ORD-1003"},
        reason="The order status is required.",
        confidence=0.99,
    )

    assert decision.action == "get_order_status"
    assert decision.arguments["order_id"] == "ORD-1003"
    assert 0.0 <= decision.confidence <= 1.0


def test_agent_state_tracks_evidence_and_trajectory():
    state = AgentState(
        user_query="What is the status of ORD-1003?"
    )

    state.add_evidence(
        {
            "success": True,
            "facts": {"order_id": "ORD-1003"},
            "sources": ["orders.json"],
        }
    )

    state.add_trajectory_step(
        {
            "type": "tool_execution",
            "action": "get_order_status",
        }
    )

    assert len(state.evidence) == 1
    assert "orders.json" in state.sources
    assert len(state.trajectory) == 1


def test_mock_provider_returns_decision():
    provider = MockAgentProvider(
        decisions=[
            {
                "action": "get_order_status",
                "arguments": {"order_id": "ORD-1003"},
                "reason": "The order status must be checked.",
                "confidence": 0.99,
            }
        ]
    )

    result = provider.generate(
        system_prompt="Select the next action.",
        user_prompt="What is the status of ORD-1003?",
    )

    assert result["action"] == "get_order_status"
    assert result["arguments"]["order_id"] == "ORD-1003"
    assert "_usage" in result