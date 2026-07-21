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

    # Remove markdown emphasis/heading symbols
    cleaned = re.sub(r'[*#`]', '', cleaned)

    # Remove leading bullet dashes at the start of lines (keep the text after them)
    cleaned = re.sub(r'(?m)^\s*[-•]\s*', '', cleaned)

    # If the model wrapped the whole thing in a JSON object despite instructions,
    # try to detect and unwrap it rather than printing raw braces.
    stripped = cleaned.strip()
    if stripped.startswith('{') and stripped.endswith('}'):
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, dict):
                # Flatten values into prose, dropping keys/braces/quotes
                cleaned = "\n\n".join(str(v) for v in parsed.values())
        except json.JSONDecodeError:
            # Not actually valid JSON — just strip stray braces/quotes as a fallback
            cleaned = re.sub(r'[{}"]', '', cleaned)

    # Collapse excessive blank lines but preserve paragraph breaks
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    cleaned = cleaned.strip()

    return cleaned


def export_final_report(df: pd.DataFrame, eda_stats: str, ai_text: str, chart_paths: list, output_dir: str = "output") -> dict:
    """Packages the analysis, stats, and multiple charts into a PDF."""
    os.makedirs(output_dir, exist_ok=True)
    paths = {}

    # 1. Raw Cleaned Data -> CSV
    csv_path = os.path.join(output_dir, "1_cleaned_data.csv")
    df.to_csv(csv_path, index=False)
    paths["CSV"] = csv_path

    # 2. Main Report -> PDF
    pdf_path = os.path.join(output_dir, "2_executive_report.pdf")
    pdf = FPDF()

    # --- PAGE 1: TEXT AND STATS ---
    pdf.add_page()

    pdf.set_font("Helvetica", style="B", size=16)
    pdf.cell(200, 10, txt="AURA Executive Data & EDA Report", ln=1, align='C')
    pdf.ln(5)

    # Section 1: Raw EDA Statistics
    pdf.set_font("Helvetica", style="B", size=12)
    pdf.cell(200, 10, txt="1. Exploratory Data Analysis (EDA) Statistics", ln=1)

    pdf.set_font("Courier", size=9)
    pdf.multi_cell(0, 5, txt=eda_stats)
    pdf.ln(5)

    # Section 2: AI Analysis — now properly cleaned before rendering
    pdf.set_font("Helvetica", style="B", size=12)
    pdf.cell(200, 10, txt="2. Executive Business Insight", ln=1)

    clean_text = clean_text_for_pdf(ai_text)
    pdf.set_font("Helvetica", size=11)

    # Render paragraph-by-paragraph so blank lines create actual visual spacing
    for paragraph in clean_text.split("\n\n"):
        if paragraph.strip():
            pdf.multi_cell(0, 7, txt=paragraph.strip())
            pdf.ln(3)

    # --- PAGE 2+: VISUAL EVIDENCE ---
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
    Exports a structured JSON version of the report — useful for programmatic
    consumption (e.g. by the Manager Agent, Verification Agent, or frontend)
    instead of parsing the PDF or free-text finding string.
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