"""Data Analyst Agent - analyzes Excel/CSV/DB data and produces insights.

Uses the data + analytics tools (tools/ - owned by Ahmad).
Owner: Danish (agent) + Ahmad (tools)
"""
from __future__ import annotations

from agents.base import AgentResult, BaseAgent


class AnalystAgent(BaseAgent):
    name = "analyst"

    def run(self, task: str, context: dict | None = None) -> AgentResult:
        # TODO: load data, find patterns, generate charts + written insights
        raise NotImplementedError
