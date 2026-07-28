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
    """Standard result object returned by every agent.

    `sources` holds one dict per cited source:
      {"label": "sales_report.pdf (page 1)", "text": "<actual retrieved text>"}
    This lets downstream consumers (e.g. VerificationAgent) check claims
    against real source text, not just a display label.
    """

    agent: str
    output: Any
    sources: list[dict] = field(default_factory=list)
    ok: bool = True


class BaseAgent(ABC):
    """Abstract base class for all AURA agents."""

    name: str = "base"

    @abstractmethod
    def run(self, task: str, context: dict | None = None) -> AgentResult:
        """Execute the agent's task and return an AgentResult."""
        raise NotImplementedError