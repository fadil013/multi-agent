"""Memory - short-term (current run) and long-term (vector store) memory.
Owner: Danish  (long-term recall is backed by the RAG layer - coordinate with Manan)
"""
from typing import TypedDict, List, Annotated, Optional
import operator


class ProjectState(TypedDict):
    """
    This replaces the Memory class. LangGraph will pass this dictionary
    to every agent in the workflow.
    """
    user_objective: str
    task_list: List[dict]
    short_term_memory: Annotated[List[dict], operator.add]
    final_report: str

    # --- Data source configuration ---
    # "file": read from target_file_path (CSV/Excel).
    # "database": read from the OLTP database, via either database_table
    # (whole-table fetch) or database_query (custom SQL SELECT).
    data_source: Optional[str]  # "file" | "database"
    target_file_path: Optional[str]
    database_table: Optional[str]
    database_query: Optional[str]

    # --- OLTP tracking ---
    # job_id links every report generated in this run back to one
    # AnalysisJob row. Created once by the Data Analyst Agent on its first
    # task and persisted across subsequent tasks via LangGraph state.
    job_id: Optional[int]

    # --- Node status signaling ---
    status: Optional[str]  # "success" | "error" | None (not yet run)
    retry_count: Optional[int]