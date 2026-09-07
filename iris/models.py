from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Agent:
    id: str
    name: str
    capabilities: tuple[str, ...]
    model: str
    tools: tuple[str, ...]
    cost_per_turn: float
    latency_ms: int
    reliability: float
    mandate: str = ""


@dataclass
class TaskState:
    title: str
    prompt: str
    task_type: str
    complexity: int
    risk: int
    capabilities: list[str]
    budget: float
    baseline: str = "B8"


@dataclass
class Strategy:
    agents: list[Agent]
    topology: str
    communication: str
    verification: bool
    experience_id: int | None = None
    score: float = 0.0
    execution_mode: str = "parallel-startup-squad"

    def public(self) -> dict[str, Any]:
        return {"agents": [asdict(a) for a in self.agents], "topology": self.topology,
                "communication": self.communication, "verification": self.verification,
                "experience_id": self.experience_id, "score": round(self.score, 3),
                "execution_mode": self.execution_mode}


@dataclass
class RunResult:
    output: str
    success: bool
    confidence: float
    cost: float
    latency_ms: int
    tokens: int
    messages: int
    recovered: bool
    stopped_early: bool
    trace: list[dict[str, Any]] = field(default_factory=list)
