"""AURA backend - FastAPI application entry point.

Run:  uvicorn backend.main:app --reload
Owner: Ahmad
"""
from __future__ import annotations

import json
import os
import tempfile
from typing import Any

from fastapi import FastAPI
from fastapi import File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from tools.olap import OLAPError, OLAPQuery, analyze_file

app = FastAPI(title="AURA API", version="0.1.0")


class GoalRequest(BaseModel):
    goal: str


class OLAPRequest(BaseModel):
    dimensions: list[str] = Field(default_factory=list)
    measures: list[str] = Field(default_factory=list)
    aggregations: list[str] = Field(default_factory=lambda: ["sum"])
    filters: dict[str, Any] = Field(default_factory=dict)
    pivot: bool = False
    rows: list[str] = Field(default_factory=list)
    columns: list[str] = Field(default_factory=list)
    top_n: int | None = 10
    max_rows: int = 100


def _model_data(model: BaseModel) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


@app.get("/health")
def health() -> dict:
    """Simple health check."""
    return {"status": "ok"}


@app.post("/goal")
def submit_goal(req: GoalRequest) -> dict:
    """Accept a business goal and (eventually) run the agent pipeline."""
    # TODO: hand `req.goal` to ManagerAgent and return a job id
    return {"received": req.goal, "status": "not_implemented"}


@app.post("/olap/analyze")
async def analyze_olap_upload(
    file: UploadFile = File(...),
    request: str = Form("{}"),
) -> dict:
    """Analyze an uploaded CSV/Excel file with OLAP cube operations."""
    try:
        payload = json.loads(request or "{}")
        olap_request = OLAPRequest(**payload)
    except Exception as error:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Invalid OLAP request: {error}") from error

    suffix = os.path.splitext(file.filename or "")[1].lower()
    if suffix not in {".csv", ".xlsx", ".xls"}:
        raise HTTPException(status_code=400, detail="Upload a CSV or Excel file.")

    temp_path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(await file.read())
            temp_path = temp_file.name

        result = analyze_file(temp_path, OLAPQuery(**_model_data(olap_request)))
        return {"status": "ok", "filename": file.filename, "result": result}
    except OLAPError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"OLAP analysis failed: {error}") from error
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
