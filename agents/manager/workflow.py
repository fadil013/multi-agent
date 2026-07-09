"""LangGraph workflow that wires the agents together.

Owner: Danish
"""
from __future__ import annotations


def build_workflow(manager, researcher, analyst, verifier, reporter=None):
    """Build and return the agent graph (e.g. a LangGraph StateGraph)."""
    # TODO: define nodes (each agent) and edges (control flow)
    # TODO: return a compiled graph that ManagerAgent can invoke
    raise NotImplementedError("Danish: define the LangGraph state machine")
