"""AURA backend - FastAPI application entry point.

Run:  uvicorn backend.main:app --reload
Owner: Ahmad
"""
from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="AURA API", version="0.1.0")


class GoalRequest(BaseModel):
    goal: str


@app.get("/health")
def health() -> dict:
    """Simple health check."""
    return {"status": "ok"}


@app.post("/goal")
def submit_goal(req: GoalRequest) -> dict:
    """Accept a business goal and (eventually) run the agent pipeline."""
    # TODO: hand `req.goal` to ManagerAgent and return a job id
    return {"received": req.goal, "status": "not_implemented"}
