"""Pydantic schemas for structured Manager Agent output.

Owner: Danish
"""
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class Task(BaseModel):
    task_name: str
    assigned_agent: Literal["data_analyst"]


class InitialPlan(BaseModel):
    """Output schema for first-time planning (no prior errors)."""
    tasks: List[Task]


class RecoveryDecision(BaseModel):
    """
    Output schema for recovery mode — used when the previous agent
    reported an error and the router sent control back to the Manager.
    """
    action: Literal["retry", "modify", "skip", "abort"] = Field(
        description=(
            "retry: try the exact same task again (use for likely-transient failures, "
            "e.g. an API call error). "
            "modify: replace the failed task with an adjusted version (use if the task "
            "itself seems malformed given the error, e.g. wrong file path). "
            "skip: drop the failed task and move to the next one (use if the task isn't "
            "essential to the objective). "
            "abort: stop the entire run (use if the failure indicates the objective "
            "cannot be completed at all, e.g. a fundamentally missing required input)."
        )
    )
    modified_task: Optional[Task] = Field(
        default=None,
        description="Required only when action is 'modify' — the replacement task."
    )
    reasoning: str = Field(description="One or two sentences explaining the decision.")