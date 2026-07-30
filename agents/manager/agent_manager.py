"""Manager Agent - the brain of AURA.

Understands the user's goal, breaks it into subtasks, assigns them to the
Data Analyst Agent, monitors progress, and — on failure — decides whether
to retry, modify, skip, or abort.

Owner: Danish (Agent Architecture)
"""
import os
from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from agents.manager.memory import ProjectState
from agents.manager.planner import get_manager_prompt, get_manager_recovery_prompt
from agents.manager.schemas import InitialPlan, RecoveryDecision

api_key = os.getenv("GOOGLE_API_KEY")

llm = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash",
    temperature=0,
    google_api_key=api_key,
)

# Structured output bindings — Gemini is contractually bound to these
# schemas, so no manual JSON parsing or markdown-fence stripping is needed.
planning_llm = llm.with_structured_output(InitialPlan)
recovery_llm = llm.with_structured_output(RecoveryDecision)

MAX_RETRIES = 2


def _plan_initial_tasks(objective: str) -> dict:
    """First-time planning: generate a fresh task list from the objective."""
    print("\n[System] Manager Agent is planning (Powered by Gemini)...")

    messages = [
        SystemMessage(content=get_manager_prompt()),
        HumanMessage(content=f"Objective: {objective}")
    ]

    try:
        plan: InitialPlan = planning_llm.invoke(messages)
        new_task_list = [t.model_dump() for t in plan.tasks]
    except Exception as e:
        print(f"[Error] Manager planning call failed: {e}")
        new_task_list = [{"task_name": "Failed to generate task list", "assigned_agent": "data_analyst"}]

    return {
        "task_list": new_task_list,
        "status": "success",
        "retry_count": 0,
    }


def _handle_recovery(state: ProjectState) -> dict:
    """
    Recovery mode: the Data Analyst Agent reported an error. Read the
    failure context from short_term_memory and decide how to proceed,
    instead of blindly regenerating the whole plan (which would lose
    track of remaining/completed tasks).
    """
    print("\n[System] Manager Agent is reviewing a task failure (Powered by Gemini)...")

    current_tasks = state.get("task_list", [])
    retry_count = state.get("retry_count", 0)
    memory = state.get("short_term_memory", [])

    last_error = memory[-1]["finding"] if memory else "No error details available."
    failed_task = current_tasks[0] if current_tasks else None

    if failed_task is None:
        return {"task_list": [], "status": "success", "retry_count": 0}

    human_content = (
        f"Failed task: {failed_task}\n\n"
        f"Error reported by the agent: {last_error}\n\n"
        f"This task has failed {retry_count} time(s) so far (max allowed: {MAX_RETRIES}).\n"
        "Decide how to proceed."
    )

    messages = [
        SystemMessage(content=get_manager_recovery_prompt()),
        HumanMessage(content=human_content)
    ]

    try:
        decision: RecoveryDecision = recovery_llm.invoke(messages)
    except Exception as e:
        print(f"[Error] Manager recovery call failed: {e} — defaulting to 'abort' for safety.")
        return {"task_list": [], "status": "success", "retry_count": 0}

    print(f"[System] Recovery decision: {decision.action.upper()} — {decision.reasoning}")

    if decision.action == "retry":
        return {"task_list": current_tasks, "status": "success"}

    elif decision.action == "modify":
        if decision.modified_task:
            new_task_list = [decision.modified_task.model_dump()] + current_tasks[1:]
        else:
            print("[Warning] Manager chose 'modify' but provided no modified_task — falling back to skip.")
            new_task_list = current_tasks[1:]
        return {"task_list": new_task_list, "status": "success", "retry_count": 0}

    elif decision.action == "skip":
        return {"task_list": current_tasks[1:], "status": "success", "retry_count": 0}

    else:  # abort
        print("[System] Manager decided to abort the remaining run.")
        return {"task_list": [], "status": "success", "retry_count": 0}


def manager_node(state: ProjectState) -> dict:
    """
    Entry point for the Manager node. Routes internally to either initial
    planning (first run) or recovery handling (a prior task errored).
    """
    status = state.get("status")

    if status == "error":
        return _handle_recovery(state)

    objective = state.get("user_objective", "")
    return _plan_initial_tasks(objective)