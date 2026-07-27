"""LangGraph workflow that wires the agents together.
Owner: Danish
"""
from langgraph.graph import StateGraph, END
from agents.manager.memory import ProjectState
from agents.manager.agent_manager import manager_node
from agents.analyst.analyst_agent import analyst_node

# Only the Data Analyst is active right now. 
# Research Agent is parked to avoid missing file errors on fresh clones.
VALID_AGENTS = {"data_analyst"}

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
workflow.add_node("manager", manager_node)

# 3. Set the Entry Point
workflow.set_entry_point("manager")

# 4. Add the Conditional Edges
# Manager hands out tasks, workers complete them and route to the next task
workflow.add_conditional_edges("manager", route_task)
workflow.add_conditional_edges("data_analyst", route_task)

# 5. Compile the application
app = workflow.compile()