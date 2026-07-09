"""Verification / Critic Agent - AURA's key differentiator.

Checks facts, sources, and calculations; flags hallucinations before results
reach the user.
Owner: Danish
"""
from __future__ import annotations

from agents.base import AgentResult, BaseAgent


class VerifierAgent(BaseAgent):
    name = "verifier"

    def run(self, task: str, context: dict | None = None) -> AgentResult:
        # TODO: cross-check each claim against its source; recompute numbers
        # TODO: return ok=False with corrections when something is wrong
        raise NotImplementedError
