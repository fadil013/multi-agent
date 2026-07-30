"""LangGraph workflow that wires the agents together.
Owner: Danish
"""
from langgraph.graph import StateGraph, END
from agents.manager.memory import ProjectState
from agents.manager.agent_manager import manager_node
from agents.analyst.analyst_agent import analyst_node

VALID_AGENTS = {"data_analyst"}
MAX_RETRIES = 2


def route_task(state: ProjectState) -> str:
    """
    Acts as a traffic cop. Checks for an error status first — if the last
    node failed, route back to the Manager instead of continuing, up to
    MAX_RETRIES consecutive failures before halting the run entirely.
    """
    status = state.get("status")
    retry_count = state.get("retry_count", 0)

    if status == "error":
        if retry_count > MAX_RETRIES:
            print(f"[Router] Exceeded max retries ({MAX_RETRIES}) — halting run.")
            return END
        print(f"[Router] Task failed (attempt {retry_count}/{MAX_RETRIES}) — routing back to Manager.")
        return "manager"

    tasks = state.get("task_list", [])
    if not tasks:
        return END

    next_task = tasks[0]
    assigned_agent = next_task.get("assigned_agent", "")

    if assigned_agent not in VALID_AGENTS:
        print(f"[Warning] No node built for '{assigned_agent}' — ending run for this task.")
        return END

    return assigned_agent


workflow = StateGraph(ProjectState)

workflow.add_node("data_analyst", analyst_node)
workflow.add_node("manager", manager_node)

workflow.set_entry_point("manager")

workflow.add_conditional_edges("manager", route_task)
workflow.add_conditional_edges("data_analyst", route_task)

app = workflow.compile()