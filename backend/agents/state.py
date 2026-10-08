from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AgentState:
    """
    Mutable working state for the W16 bounded agentic loop.

    The state stores compact evidence and execution metadata rather
    than repeatedly appending raw tool/RAG outputs to the LLM context.
    """

    user_query: str

    iteration: int = 0

    evidence: List[Dict[str, Any]] = field(default_factory=list)

    unresolved_questions: List[str] = field(default_factory=list)

    conflicts: List[Dict[str, Any]] = field(default_factory=list)

    trajectory: List[Dict[str, Any]] = field(default_factory=list)

    sources: List[str] = field(default_factory=list)

    status: str = "running"

    final_answer: Optional[str] = None

    total_tokens: int = 0

    total_latency_ms: float = 0.0

    def add_evidence(self, evidence: Dict[str, Any]) -> None:
        self.evidence.append(evidence)

        for source in evidence.get("sources", []):
            if source not in self.sources:
                self.sources.append(source)

    def add_trajectory_step(self, step: Dict[str, Any]) -> None:
        self.trajectory.append(step)

    def add_unresolved_question(self, question: str) -> None:
        if question and question not in self.unresolved_questions:
            self.unresolved_questions.append(question)

    def add_conflict(self, conflict: Dict[str, Any]) -> None:
        self.conflicts.append(conflict)

    def mark_completed(self, answer: str) -> None:
        self.status = "completed"
        self.final_answer = answer

    def mark_clarification_required(self) -> None:
        self.status = "clarification_required"

    def mark_failed(self) -> None:
        self.status = "failed"

    def mark_max_iterations(self) -> None:
        self.status = "max_iterations"
