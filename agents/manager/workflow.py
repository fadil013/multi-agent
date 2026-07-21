"""LangGraph workflow that wires the agents together.
Owner: Danish
"""
import time
from langgraph.graph import StateGraph, END
from agents.manager.memory import ProjectState
from agents.manager.agent_manager import manager_node
from agents.analyst.analyst_agent import analyst_node
from agents.researcher.research_agent import ResearchAgent

research_agent_instance = ResearchAgent()

# Gemini's free tier is rate-limited enough to need this. Groq is not —
# don't apply the same guard there unless you actually hit a 429.
RESEARCH_QUOTA_GUARD_DELAY_SECONDS = 6

VALID_AGENTS = {"data_analyst", "research_agent"}


def with_quota_guard(node_fn, delay: int):
    """Wraps a node function with a fixed delay to protect against API rate limits."""
    def wrapper(state: ProjectState) -> dict:
        print(f"\n   [Quota Guard] Pausing for {delay} seconds to protect API limits...")
        time.sleep(delay)
        return node_fn(state)
    return wrapper


def _research_node(state: ProjectState) -> dict:
    """Wrapper to handle LangGraph state for the Object-Oriented ResearchAgent."""
    current_tasks = state.get("task_list", [])
    if not current_tasks:
        return {"task_list": current_tasks}

    active_task = current_tasks[0]
    task_description = active_task.get("task_name", "")

    result = research_agent_instance.run(task_description)

    remaining_tasks = current_tasks[1:]
    new_insight = {"agent": "Research Agent", "finding": result.output}

    return {
        "task_list": remaining_tasks,
        "short_term_memory": [new_insight]
    }


def route_task(state: ProjectState) -> str:
    """Acts as a traffic cop. Routes to the next agent, or ends the graph
    if the task queue is empty or the assigned agent has no registered node."""
    tasks = state.get("task_list", [])
    if not tasks:
        return END

    next_task = tasks[0]
    assigned_agent = next_task.get("assigned_agent", "")

    if assigned_agent not in VALID_AGENTS:
        print(f"[Warning] No node built yet for '{assigned_agent}' — ending run for this task.")
        return END

    return assigned_agent


# 1. Initialize the graph
workflow = StateGraph(ProjectState)

# 2. Add the Nodes
# Data Analyst uses Groq — no artificial delay needed, its whole value prop is speed.
workflow.add_node("data_analyst", analyst_node)
# Research Agent uses Gemini free tier — keep the guard.
workflow.add_node("research_agent", with_quota_guard(_research_node, RESEARCH_QUOTA_GUARD_DELAY_SECONDS))
workflow.add_node("manager", manager_node)

# 3. Set the Entry Point
workflow.set_entry_point("manager")

# 4. Add the Conditional Edges
workflow.add_conditional_edges("manager", route_task)
workflow.add_conditional_edges("data_analyst", route_task)
workflow.add_conditional_edges("research_agent", route_task)

# 5. Compile the application
app = workflow.compile()