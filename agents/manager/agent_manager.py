"""Manager Agent - the brain of AURA.

Understands the user's goal, breaks it into subtasks, assigns them to the
right specialist agents, monitors progress, and merges the results.

Owner: Danish (Agent Architecture)
"""
from __future__ import annotations

from agents.base import AgentResult


class ManagerAgent:
    def __init__(self, agents: dict | None = None):
        # agents: mapping of name -> agent instance (researcher, analyst, ...)
        self.agents = agents or {}

    def run(self, goal: str) -> AgentResult:
        """Plan -> delegate -> verify -> report."""
        # TODO 1: call Planner to decompose `goal` into tasks
        # TODO 2: dispatch each task to the matching agent
        # TODO 3: send the results to the Verifier agent
        # TODO 4: hand verified findings to the Report agent
        raise NotImplementedError("Danish: implement the orchestration loop")
