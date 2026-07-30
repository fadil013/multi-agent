"""Data Analyst Agent - Processes and analyzes structured data tables.

Owner: Danish (Agent Architecture)
"""
import os
import time
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_groq import ChatGroq

from agents.manager.memory import ProjectState
from agents.analyst.schemas import AnalystOutput
from tools.data_agent import (
    load_table,
    clean,
    generate_eda_summary,
    detect_anomalies,
    format_anomaly_table_for_pdf,
    build_schema_description,
)
from tools.analytics import generate_dynamic_charts
from tools.reporter import export_final_report, export_json_report
from tools.database_tool import fetch_table, execute_query, analysis_job_repo, report_repo
from dotenv import load_dotenv

load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")

llm = ChatGroq(
    temperature=0.1,
    model_name="llama-3.3-70b-versatile",
    api_key=groq_api_key
)

structured_llm = llm.with_structured_output(AnalystOutput)

MAX_CHARTS = 3
MAX_RETRIES = 2
BASE_OUTPUT_DIR = "output"

REQUIRED_FIELDS_BY_CHART_TYPE = {
    "scatter": ["x_column", "y_column"],
    "histogram": ["column"],
    "bar": ["x_column", "y_column"],
    "line": ["y_column"],  # x_column is allowed to be None — analytics.py falls back to a detected datetime column
    "box": [],  # validated specially below: needs EITHER 'column' OR both x_column+y_column
    "heatmap": [],  # no fields required — always uses all numeric columns
    "countplot": ["column"],
}

def validate_chart_configs(chart_configs: list, valid_columns: set) -> list:
    """
    Validates chart configs against the exact column set the LLM was shown,
    AND checks that required fields for each chart_type are actually
    present and non-null — not just that any provided columns are real.
    """
    validated = []
    for i, cfg in enumerate(chart_configs[:MAX_CHARTS]):
        cfg_dict = cfg.model_dump() if hasattr(cfg, "model_dump") else dict(cfg)
        chart_type = cfg_dict.get("chart_type", "")

        # --- Check 1: required fields for this chart_type are non-null ---
        required = REQUIRED_FIELDS_BY_CHART_TYPE.get(chart_type, [])
        missing_required = [f for f in required if not cfg_dict.get(f)]

        if chart_type == "box":
            has_single = bool(cfg_dict.get("column"))
            has_grouped = bool(cfg_dict.get("x_column")) and bool(cfg_dict.get("y_column"))
            if not (has_single or has_grouped):
                missing_required = ["column' OR ('x_column' + 'y_column"]

        if missing_required:
            print(f"[Warning] Chart {i+1} ('{chart_type}') missing required field(s) {missing_required} — skipping.")
            continue

        # --- Check 2: any provided columns actually exist in the dataset ---
        referenced_cols = [
            cfg_dict.get(k) for k in ("x_column", "y_column", "column", "hue")
            if cfg_dict.get(k)
        ]
        missing_cols = [c for c in referenced_cols if c not in valid_columns]
        if missing_cols:
            print(f"[Warning] Chart {i+1} ('{chart_type}') references unknown column(s) {missing_cols} — skipping.")
            continue

        validated.append(cfg_dict)

    return validated

def _error_result(current_tasks: list, message: str, retry_count: int, job_id: int = None) -> dict:
    """
    Standardized error return — sets status so the router can act on it.
    job_id is echoed back (if already created) so it isn't lost from state
    on an error return, since LangGraph only persists keys a node explicitly
    returns.
    """
    print(f"[Error] {message}")
    result = {
        "task_list": current_tasks,  # task is NOT popped on error — stays queued for retry
        "short_term_memory": [{"agent": "Data Analyst", "finding": message}],
        "status": "error",
        "retry_count": retry_count + 1,
    }
    if job_id is not None:
        result["job_id"] = job_id
    return result


def analyst_node(state: ProjectState) -> dict:
    """
    Locates the target data (file OR database), ingests and cleans it, runs
    EDA, generates analytical summaries, and dynamically dictates chart
    visuals. Records job/report metadata to the OLTP database.
    """
    t_start = time.perf_counter()
    print("\n[System] Data Analyst Agent is waking up...")

    current_tasks = state.get("task_list", [])
    retry_count = state.get("retry_count", 0)

    if not current_tasks:
        print("[Warning] No active tasks found for Data Analyst.")
        return {"task_list": current_tasks, "status": "success"}

    active_task = current_tasks[0]
    task_description = active_task.get("task_name", "")

    completed_count = len(state.get("short_term_memory", []))
    task_index = completed_count + 1
    task_output_dir = os.path.join(BASE_OUTPUT_DIR, f"task_{task_index}")

    # === OLTP (NEW): ensure this run has an AnalysisJob row ===
    # Created once, on the first task of the run, and reused for every
    # subsequent task via job_id persisted in ProjectState.
    job_id = state.get("job_id")
    if job_id is None:
        if analysis_job_repo is not None:
            try:
                job_id = analysis_job_repo.create_job(state.get("user_objective", ""))
                print(f"[System] Created new AnalysisJob with job_id={job_id} for this run.")
            except Exception as e:
                print(f"[Warning] Could not create analysis job record (database unavailable?): {e}")
                job_id = None
        else:
            print("[Warning] Database is not available — skipping job tracking for this run.")


    # === Stage 0 (MODIFIED — was previously a single load_table() call) ===
    # Resolves data from either a file or the OLTP database. Everything
    # from this point onward is unchanged — the rest of the pipeline only
    # ever sees `raw_df`, regardless of where it came from.
    data_source = state.get("data_source", "file")

    if data_source == "database":
        database_table = state.get("database_table")
        database_query = state.get("database_query")

        if not database_table and not database_query:
            return _error_result(
                current_tasks,
                "Analysis halted: data_source is 'database' but neither "
                "'database_table' nor 'database_query' was provided.",
                retry_count,
                job_id=job_id,
            )

        try:
            if database_query:
                raw_df = execute_query(database_query)
            else:
                raw_df = fetch_table(database_table)
        except Exception as e:
            return _error_result(
                current_tasks,
                f"Database fetch failed: {str(e)}",
                retry_count,
                job_id=job_id,
            )
    else:
        file_path = state.get("target_file_path")
        if not file_path:
            return _error_result(
                current_tasks,
                "Analysis halted: no 'target_file_path' was provided in the project state.",
                retry_count,
                job_id=job_id,
            )
        if not os.path.exists(file_path):
            return _error_result(
                current_tasks,
                f"Analysis halted: the data file at '{file_path}' was not found.",
                retry_count,
                job_id=job_id,
            )
        raw_df = load_table(file_path)

    # --- Stage 1: clean, EDA, anomaly detection (UNCHANGED) ---
    t0 = time.perf_counter()
    try:
        cleaned_df = clean(raw_df, use_knn_imputation=True)
        eda_stats = generate_eda_summary(cleaned_df)
        flagged_df, anomaly_summary = detect_anomalies(cleaned_df)
        anomaly_table_for_pdf = format_anomaly_table_for_pdf(flagged_df, max_rows=5)
        schema_description, shown_columns = build_schema_description(cleaned_df)
    except Exception as e:
        return _error_result(current_tasks, f"Data processing failure: {str(e)}", retry_count, job_id=job_id)
    t1 = time.perf_counter()
    print(f"[Timing] Load + clean + EDA + anomaly detection: {t1 - t0:.2f}s")

    # --- Stage 2: Structured LLM call (UNCHANGED) ---
    system_prompt = (
        "You are an expert Data Analyst Agent inside the AURA multi-agent system.\n"
        "Review the Exploratory Data Analysis (EDA) statistics and any detected anomalies.\n\n"
        "For 'executive_summary': write plain prose paragraphs. Identify interesting trends,\n"
        "averages, extreme values, and whether anomalies look like genuine business outliers\n"
        "or data quality issues. No markdown, no bullet points.\n\n"
        f"For 'charts': design charts that best visualize the core findings — use as many as\n"
        f"the task genuinely needs, up to a maximum of {MAX_CHARTS}. A narrow, specific task\n"
        "may only need one focused chart; do not pad with extra charts that don't add insight.\n"
        "CRITICAL: only use column names from the 'Available columns' list provided in the\n"
        "user message. Do not invent, guess, or assume any column name not explicitly listed.\n"
        "Column names must match exactly, case-sensitive."
    )

    human_content = (
        f"Assigned Analysis Task: {task_description}\n\n"
        f"{schema_description}\n\n"
        f"Statistical Data:\n{eda_stats}\n\n"
        f"Anomaly Detection Results:\n{anomaly_summary}"
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_content)
    ]

    try:
        result: AnalystOutput = structured_llm.invoke(messages)
    except Exception as e:
        return _error_result(current_tasks, f"LLM structured output call failed: {str(e)}", retry_count, job_id=job_id)

    t2 = time.perf_counter()
    print(f"[Timing] Groq LLM call (structured): {t2 - t1:.2f}s")

    analysis_text = result.executive_summary.strip()

    valid_columns = set(shown_columns)
    chart_configs = validate_chart_configs(result.charts, valid_columns)

    if not chart_configs:
        numeric_cols = cleaned_df.select_dtypes(include=['number']).columns.tolist()
        if numeric_cols:
            fallback_col = numeric_cols[0]
        elif shown_columns:
            fallback_col = shown_columns[0]
        else:
            fallback_col = None

        if fallback_col:
            print(f"[Warning] No valid charts configured by LLM. Using fallback histogram on '{fallback_col}'.")
            chart_configs = [{"chart_type": "histogram", "column": fallback_col, "title": f"Distribution of {fallback_col}"}]
        else:
            print("[Warning] No valid charts configured and no fallback column available. Skipping charts.")
            chart_configs = []

    # --- Stage 3: Charts + PDF + JSON export (UNCHANGED) ---
    print(f"\n[System] Generating comprehensive visual charts and exporting final report to '{task_output_dir}'...")
    try:
        chart_suite = generate_dynamic_charts(cleaned_df, chart_configs, output_dir=task_output_dir)

        t3 = time.perf_counter()
        print(f"[Timing] Chart generation ({len(chart_suite)} charts): {t3 - t2:.2f}s")

        full_stats_section = (
            f"{eda_stats}\n\n"
            f"=== Anomalous Rows (Key Columns) ===\n{anomaly_table_for_pdf}"
        )

        final_report_paths = export_final_report(
            flagged_df, full_stats_section, analysis_text, chart_suite, output_dir=task_output_dir
        )
        json_report_paths = export_json_report(
            task_description=task_description,
            eda_stats=eda_stats,
            anomaly_summary=anomaly_summary,
            analysis_output=analysis_text,
            chart_paths=chart_suite,
            output_dir=task_output_dir,
        )

        t4 = time.perf_counter()
        print(f"[Timing] PDF + JSON export: {t4 - t3:.2f}s")

        # === OLTP (NEW): record report metadata ===
        # A failure here does not fail the task — the report files were
        # already written successfully; this is bookkeeping on top of that.
        try:
            if report_repo is not None and job_id is not None:
                report_repo.create_report(
                    job_id=job_id,
                    task_name=task_description,
                    pdf_path=final_report_paths.get("PDF"),
                    json_path=json_report_paths.get("JSON"),
                )
            else:
                print("[Warning] Skipping report metadata recording — database unavailable or no job_id.")
        except Exception as e:
            print(f"[Warning] Failed to record report metadata to database: {e}")

        analysis_text += (
            f"\n\n[System Note: Full report exported to '{task_output_dir}/'. "
            f"Included EDA Stats, Anomaly Detection, Analysis, {len(chart_suite)} Plots, and JSON summary.]"
        )

    except Exception as e:
        return _error_result(current_tasks, f"Failed to export final report bundle: {str(e)}", retry_count, job_id=job_id)

    t_end = time.perf_counter()
    print(f"[Timing] TOTAL analyst_node runtime: {t_end - t_start:.2f}s")
    print("[System] Data Analyst Agent completed operations.")

    remaining_tasks = current_tasks[1:]

    # === OLTP (NEW): close out the job once no tasks remain ===
    if not remaining_tasks and job_id is not None and analysis_job_repo is not None:
        try:
            analysis_job_repo.mark_completed(job_id, status="completed")
        except Exception as e:
            print(f"[Warning] Failed to mark analysis job as completed: {e}")

    return {
        "task_list": remaining_tasks,
        "short_term_memory": [{"agent": "Data Analyst Agent", "finding": analysis_text}],
        "status": "success",
        "retry_count": 0,
        "job_id": job_id,
    }