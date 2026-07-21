"""Data Analyst Agent - Processes and analyzes structured data tables.

Owner: Danish (Agent Architecture)
"""
import os
import time
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_groq import ChatGroq

from agents.manager.memory import ProjectState
from tools.data_agent import load_table, clean, generate_eda_summary, detect_anomalies
from tools.analytics import make_chart
from tools.reporter import export_final_report, export_json_report
from dotenv import load_dotenv
load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")

llm = ChatGroq(
    temperature=0.1,
    model_name="llama-3.3-70b-versatile",
    api_key=groq_api_key
)


def analyst_node(state: ProjectState) -> dict:
    """
    Locates the target data file, ingests and cleans it (with KNN imputation),
    runs anomaly detection and EDA, and generates analytical summaries.
    """
    t_start = time.perf_counter()
    print("\n[System] Data Analyst Agent is waking up...")

    current_tasks = state.get("task_list", [])
    if not current_tasks:
        print("[Warning] No active tasks found for Data Analyst.")
        return {"task_list": current_tasks}

    active_task = current_tasks[0]
    task_description = active_task.get("task_name", "")

    file_path = state.get("target_file_path", "sales.csv")

    if not os.path.exists(file_path):
        error_finding = f"Analysis halted: The data file at '{file_path}' was not found."
        print(f"[Error] {error_finding}")

        remaining_tasks = current_tasks[1:]
        return {
            "task_list": remaining_tasks,
            "short_term_memory": [{"agent": "Data Analyst", "finding": error_finding}]
        }

    # --- Stage 1: Load, clean, EDA, anomaly detection ---
    t0 = time.perf_counter()
    try:
        raw_df = load_table(file_path)
        cleaned_df = clean(raw_df, use_knn_imputation=True)
        eda_stats = generate_eda_summary(cleaned_df)
        flagged_df, anomaly_summary = detect_anomalies(cleaned_df)
    except Exception as e:
        error_msg = f"Data processing failure: {str(e)}"
        print(f"[Error] {error_msg}")
        return {
            "task_list": current_tasks[1:],
            "short_term_memory": [{"agent": "Data Analyst", "finding": error_msg}]
        }
    t1 = time.perf_counter()
    print(f"[Timing] Load + clean + EDA + anomaly detection: {t1 - t0:.2f}s")

    # --- Stage 2: LLM call ---
    # IMPORTANT: explicitly forbid JSON/markdown output. Llama models via Groq
    # will sometimes default to structured/JSON-like formatting unless told
    # very directly not to — this was causing raw braces/quotes to show up
    # in the PDF instead of clean prose.
    system_prompt = (
        "You are an expert Data Analyst Agent inside the AURA multi-agent system.\n"
        "Your task is to review the Exploratory Data Analysis (EDA) statistics and any\n"
        "detected anomalies provided to you.\n"
        "Identify the most interesting trends, averages (mean/median), extreme values,\n"
        "and flag if the anomalies suggest data quality issues or genuine business outliers.\n\n"
        "OUTPUT FORMAT RULES (STRICT):\n"
        "- Write in plain prose paragraphs only, like a business memo.\n"
        "- Do NOT use JSON, dictionaries, code blocks, or markdown formatting.\n"
        "- Do NOT use asterisks, hashtags, backticks, or bullet symbols like '-' or '*'.\n"
        "- Do NOT wrap your answer in curly braces or quotation marks.\n"
        "- Write complete sentences and paragraphs, as if writing directly into a printed report."
    )

    human_content = (
        f"Assigned Analysis Task: {task_description}\n\n"
        f"Statistical Data:\n{eda_stats}\n\n"
        f"Anomaly Detection Results:\n{anomaly_summary}\n\n"
        "Provide your formal analysis finding below, as plain prose only:"
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_content)
    ]

    response = llm.invoke(messages)
    t2 = time.perf_counter()
    print(f"[Timing] Groq LLM call: {t2 - t1:.2f}s")

    analysis_output = ""
    if isinstance(response.content, list):
        for block in response.content:
            if isinstance(block, dict) and "text" in block:
                analysis_output += block["text"] + "\n"
    elif isinstance(response.content, str):
        analysis_output = response.content
    else:
        analysis_output = str(response.content)

    analysis_output = analysis_output.strip()

    # --- Stage 3: Charts + PDF + JSON export ---
    print("\n[System] Generating comprehensive visual charts and exporting final report...")
    exported_files = {}
    try:
        chart_suite = []

        c1 = make_chart(cleaned_df, kind="histogram", path="output/plot_1_hist.png")
        chart_suite.append(c1)

        c2 = make_chart(cleaned_df, kind="scatter", path="output/plot_2_scatter.png")
        chart_suite.append(c2)

        try:
            c3 = make_chart(cleaned_df, kind="heatmap", path="output/plot_3_heatmap.png")
            chart_suite.append(c3)
        except ValueError as heatmap_err:
            print(f"[Warning] Skipped heatmap: {heatmap_err}")

        t3 = time.perf_counter()
        print(f"[Timing] Chart generation ({len(chart_suite)} charts): {t3 - t2:.2f}s")

        full_stats_section = f"{eda_stats}\n\n{anomaly_summary}"

        exported_files.update(
            export_final_report(flagged_df, full_stats_section, analysis_output, chart_suite)
        )

        # New: structured JSON export alongside the PDF
        exported_files.update(
            export_json_report(
                task_description=task_description,
                eda_stats=eda_stats,
                anomaly_summary=anomaly_summary,
                analysis_output=analysis_output,
                chart_paths=chart_suite,
            )
        )

        t4 = time.perf_counter()
        print(f"[Timing] PDF + JSON export: {t4 - t3:.2f}s")

        analysis_output += (
            f"\n\n[System Note: Full report exported to 'output/'. "
            f"Included EDA Stats, Anomaly Detection, Analysis, {len(chart_suite)} Plots, and JSON summary.]"
        )

    except Exception as e:
        print(f"[Error] Failed to export final report bundle: {e}")

    t_end = time.perf_counter()
    print(f"[Timing] TOTAL analyst_node runtime: {t_end - t_start:.2f}s")
    print("[System] Data Analyst Agent completed operations.")

    remaining_tasks = current_tasks[1:]
    new_insight = {"agent": "Data Analyst Agent", "finding": analysis_output}

    return {
        "task_list": remaining_tasks,
        "short_term_memory": [new_insight]
    }