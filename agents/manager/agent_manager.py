"""Manager Agent - the brain of AURA.

Understands the user's goal, breaks it into subtasks, assigns them to the
right specialist agents, monitors progress, and merges the results.

Owner: Danish (Agent Architecture)"""

import json
import os
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from agents.manager.memory import ProjectState
from agents.manager.planner import get_manager_prompt

# Explicitly fetch the key
api_key = os.getenv("GOOGLE_API_KEY")

llm = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash", 
    temperature=0,
    google_api_key=api_key,
)

def manager_node(state: ProjectState) -> dict:
    """
    Reads the user objective and uses Gemini to generate a structured list of subtasks.
    """
    print("\n[System] Manager Agent is thinking (Powered by Gemini)...")

    objective = state.get("user_objective", "")

    # Dynamically load the advanced prompt from planner.py
    system_prompt = get_manager_prompt()

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Objective: {objective}")
    ]

    response = llm.invoke(messages)
    content = response.content

    # Normalize response text (handles both string and block formats)
    if isinstance(content, list):
        raw = "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        ).strip()
    else:
        raw = content.strip()

    # Defensive cleanup to strip markdown fences
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[len("json"):].strip()

    try:
        plan = json.loads(raw)
        new_task_list = plan.get("tasks", [])
    except json.JSONDecodeError:
        print(f"[Error] Failed to parse Gemini's response: {content}")
        new_task_list = [{"task_name": "Failed to parse task list", "assigned_agent": "Manager"}]

    return {"task_list": new_task_list}