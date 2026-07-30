"""Report Generation Engine for the Data Analyst.
Exports the final analysis into a comprehensive PDF (including EDA stats and multiple charts)
and a structured JSON summary.
"""
import pandas as pd
import os
import re
import json
from datetime import datetime
from fpdf import FPDF


def clean_text_for_pdf(text: str) -> str:
    """
    Strips markdown, JSON-like artifacts, and normalizes whitespace so the
    LLM's output renders as clean prose in the PDF instead of raw symbols.
    """
    if not text:
        return ""

    cleaned = text
    cleaned = re.sub(r'[*#`]', '', cleaned)
    cleaned = re.sub(r'(?m)^\s*[-•]\s*', '', cleaned)

    stripped = cleaned.strip()
    if stripped.startswith('{') and stripped.endswith('}'):
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, dict):
                cleaned = "\n\n".join(str(v) for v in parsed.values())
        except json.JSONDecodeError:
            cleaned = re.sub(r'[{}"]', '', cleaned)

    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    cleaned = cleaned.strip()

    return cleaned


def export_final_report(df: pd.DataFrame, eda_stats: str, ai_text: str, chart_paths: list, output_dir: str = "output") -> dict:
    """Packages the analysis, stats, and multiple charts into a PDF.

    output_dir should be a unique folder per task/run (e.g. "output/task_1")
    when this is called multiple times in one program invocation — otherwise
    each call overwrites the previous one's PDF/CSV under the same filenames.
    """
    os.makedirs(output_dir, exist_ok=True)
    paths = {}

    csv_path = os.path.join(output_dir, "1_cleaned_data.csv")
    df.to_csv(csv_path, index=False)
    paths["CSV"] = csv_path

    pdf_path = os.path.join(output_dir, "2_executive_report.pdf")
    pdf = FPDF()

    pdf.add_page()

    pdf.set_font("Helvetica", style="B", size=16)
    pdf.cell(200, 10, txt="AURA Executive Data & EDA Report", ln=1, align='C')
    pdf.ln(5)

    pdf.set_font("Helvetica", style="B", size=12)
    pdf.cell(200, 10, txt="1. Exploratory Data Analysis (EDA) Statistics", ln=1)
    pdf.ln(3)

    pdf.set_font("Courier", size=6.5)
    safe_eda = eda_stats.replace('"', '').replace('\u2018', "'").replace('\u2019', "'")
    pdf.multi_cell(0, 3.5, txt=safe_eda)
    pdf.ln(5)

    pdf.set_font("Helvetica", style="B", size=12)
    pdf.cell(200, 10, txt="2. Executive Business Insight", ln=1)

    clean_text = clean_text_for_pdf(ai_text)
    pdf.set_font("Helvetica", size=11)

    for paragraph in clean_text.split("\n\n"):
        if paragraph.strip():
            safe_text = (
                paragraph.strip()
                .replace('\u2019', "'")
                .replace('\u2018', "'")
                .replace('\u201c', '"')
                .replace('\u201d', '"')
                .replace('\u2014', '-')
            )
            pdf.multi_cell(0, 7, txt=safe_text)
            pdf.ln(3)

    pdf.add_page()
    pdf.set_font("Helvetica", style="B", size=14)
    pdf.cell(200, 10, txt="3. Visual Evidence & Plots", ln=1)
    pdf.ln(5)

    y_offset = pdf.get_y()
    for img_path in chart_paths:
        if os.path.exists(img_path):
            if y_offset > 200:
                pdf.add_page()
                y_offset = 20

            pdf.image(img_path, x=15, y=y_offset, w=180)
            y_offset += 130

    pdf.output(pdf_path)
    paths["PDF"] = pdf_path
    return paths


def export_json_report(
    task_description: str,
    eda_stats: str,
    anomaly_summary: str,
    analysis_output: str,
    chart_paths: list,
    output_dir: str = "output"
) -> dict:
    """
    Exports a structured JSON version of the report.

    output_dir should match the same unique folder used in export_final_report
    for the same task, so the PDF/CSV/JSON/charts for one task stay grouped together.
    """
    os.makedirs(output_dir, exist_ok=True)
    json_path = os.path.join(output_dir, "3_report_summary.json")

    report_data = {
        "generated_at": datetime.now().isoformat(),
        "task_description": task_description,
        "eda_statistics": eda_stats,
        "anomaly_summary": anomaly_summary,
        "executive_insight": clean_text_for_pdf(analysis_output),
        "charts": chart_paths,
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    return {"JSON": json_path}