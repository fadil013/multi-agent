"""Base agent interface shared by every AURA agent.

All specialized agents (manager, researcher, analyst, verifier, ...) inherit
from BaseAgent so the orchestrator can treat them uniformly.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentResult:
    """Standard result object returned by every agent."""

    agent: str
    output: Any
    sources: list[str] = field(default_factory=list)
    ok: bool = True


class BaseAgent(ABC):
    """Abstract base class for all AURA agents."""

    name: str = "base"

    @abstractmethod
    def run(self, task: str, context: dict | None = None) -> AgentResult:
        """Execute the agent's task and return an AgentResult."""
        raise NotImplementedError
