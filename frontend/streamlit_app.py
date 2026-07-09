"""AURA - minimal Streamlit UI (quick-start prototype).

Run:  streamlit run frontend/streamlit_app.py
Owner: Ahmad
"""
from __future__ import annotations

import requests
import streamlit as st

st.set_page_config(page_title="AURA", layout="centered")
st.title("AURA - Autonomous AI Business Assistant")
st.write("Give AURA a business goal and it will plan, research, verify, and report.")

goal = st.text_area(
    "Your business goal",
    placeholder="Analyze our laptop sales and prepare a growth strategy.",
)

if st.button("Run AURA"):
    if not goal.strip():
        st.warning("Please enter a goal first.")
    else:
        # TODO: point this at your deployed backend URL
        try:
            resp = requests.post(
                "http://localhost:8000/goal", json={"goal": goal}, timeout=10
            )
            st.json(resp.json())
        except Exception as exc:  # noqa: BLE001
            st.error(f"Backend not reachable yet: {exc}")
