"""Task Planner - decomposes a business goal into ordered subtasks.

Owner: Danish
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Task:
    id: int
    description: str
    agent: str                      # which agent should handle it
    depends_on: list[int] | None = None


class Planner:
    def decompose(self, goal: str) -> list[Task]:
        """Turn a high-level goal into a list of assigned Tasks."""
        # TODO: use an LLM to break `goal` into subtasks and assign agents
        raise NotImplementedError("Danish: implement goal decomposition")
