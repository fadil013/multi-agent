"""Research Agent - gathers live external facts and tracks sources.

Uses the web search tool (tools/search_tool.py - owned by Ahmad).
Owner: Danish (agent) + Ahmad (tool)
"""
from __future__ import annotations

from agents.base import AgentResult, BaseAgent


class ResearchAgent(BaseAgent):
    name = "researcher"

    def run(self, task: str, context: dict | None = None) -> AgentResult:
        # TODO: call the search tool, extract useful facts, keep source URLs
        raise NotImplementedError
