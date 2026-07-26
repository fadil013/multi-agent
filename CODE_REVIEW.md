# AURA — Code Review (Week 1)

A review of the first work pushed to each member's branch. The goal is simple:
recognise what is already good, and list the exact fixes needed so that every
branch runs, integrates cleanly, and is ready to merge into `main`.

Please read the **Executive Summary**, then your own section, then the
**Repo-Wide Issues** and **Action Items** that apply to everyone.

| | |
|---|---|
| **Date** | 2026-07-26 |
| **Base** | `main` at `714e1c2` (seed commit — nothing merged yet) |
| **Branches reviewed** | `danish/agents` (`f9ece6b`), `manan/rag` (`a9bde55`), `ahmad/backend-tools` (`a47f0eb`) |
| **Method** | Full read of every changed file per branch, plus a simulated merge to detect conflicts |

---

## 1. Executive Summary

This is a strong first delivery. All three branches contain real, working
implementations — not placeholder stubs. That said, **nothing is merge-ready
yet.** There is one branch that will not run on a clean clone, one hard
conflict shared between two branches, one shared file deleted on all three
branches, and a set of import and dependency inconsistencies to standardise
before more code is layered on top.

| Member | Branch | Delivered | Merge-ready | Top blocker |
|--------|--------|-----------|:-----------:|-------------|
| **Danish** | `danish/agents` | Manager, Planner, Memory, LangGraph Workflow, Analyst agent, PDF/JSON reporter | No | Branch crashes on a clean clone (imports a deleted file) |
| **Manan** | `manan/rag` | Document loader + chunker, BGE embeddings, Pinecone store, RAG pipeline | Nearly | Package imports break when used from the app |
| **Ahmad** | `ahmad/backend-tools` | Analytics toolkit, data cleaning + structure detection | Nearly | Shares a hard conflict with Danish over `tools/` |

---

## 2. What Went Well

- **Danish** — A genuinely working multi-agent design on LangGraph: a Manager
  that plans with an LLM, a shared `ProjectState`, a routed workflow, and a
  full Analyst agent that cleans data (KNN imputation), detects anomalies
  (Isolation Forest), runs EDA, and exports a PDF **and** a structured JSON
  report. Architect-level thinking.
- **Manan** — The cleanest branch: fully inside his lane, correct BGE query
  prefixing, deterministic (idempotent) vector IDs, batched upserts, and
  page-level citations. Well-documented.
- **Ahmad** — A deep, careful analytics toolkit: multi-encoding CSV loading,
  heuristic column-type detection, chart-count caps to prevent runaway output,
  and headless-safe Matplotlib. Solid, in-lane engineering.

---

## 3. Severity Legend

| Level | Meaning |
|-------|---------|
| **Blocker** | Must be fixed before this branch can merge — it breaks the build or another person's code. |
| **Major** | Will cause a runtime failure or a real integration problem; fix before merge. |
| **Minor** | Should be fixed, but does not block a merge. |
| **Note** | Not a defect — context or a heads-up. |

---

## 4. Findings by Member

### 4.1 Danish — `danish/agents`

Excellent work in isolation, but as pushed the branch does not run for anyone
except on the machine it was written on.

| Severity | Location | Issue | Fix |
|----------|----------|-------|-----|
| **Blocker** | `agents/manager/workflow.py:9,11` | Imports and instantiates `ResearchAgent` from `agents/researcher/research_agent.py`, but that file was removed from the branch and `agents/researcher/` was added to `.gitignore`. On a fresh clone the import fails immediately, so the workflow and `test_main.py` cannot start. It only runs locally because the file still exists on your machine. | Push the researcher file (remove it from `.gitignore`), **or** remove the researcher import and node until it is ready. |
| **Blocker** | `tools/data_agent.py`, `tools/analytics.py` | These were rebuilt inside Ahmad's lane with a **different API** than Ahmad's versions (Danish exposes `load_table` / `clean` / `generate_eda_summary` / `detect_anomalies` / `make_chart`; Ahmad exposes `load_file` / `clean_data` / `detect_structure` / `analyze` / `generate_charts`). A merge will conflict, and even after resolving the text one side's imports break. | Consolidate under a single owner and API — see **5.C**. |
| **Major** | `agents/manager/agent_manager.py` | `model="gemini-3.5-flash"` is very likely **not a valid Gemini model ID** (current IDs are of the form `gemini-2.5-flash` / `gemini-2.0-flash`). It will 404 at runtime. | Set a valid model ID and verify it against the provider. |
| **Major** | `agents/manager/agent_manager.py` | The Gemini client is built at **import time** reading `GOOGLE_API_KEY`, but `load_dotenv()` only runs later (in `analyst_agent.py`). So the key is `None` when the client is created and authentication fails. | Call `load_dotenv()` once at startup, before any LLM client is constructed (ideally a shared config module — see **5.E**). |
| **Major** | `tools/reporter.py` | `fpdf`'s core fonts (Helvetica/Courier) are Latin-1 only. The first time the LLM emits a smart quote or em-dash, `pdf.output()` raises `UnicodeEncodeError`. | Switch to `reportlab` (already in `requirements.txt`) or register a Unicode TTF font in `fpdf`. |
| **Major** | `requirements.txt` | New dependencies are not declared: `scikit-learn`, `fpdf2` (or `reportlab`), `langchain-groq`, `langchain-google-genai`. A fresh install cannot run the code. | Add them — see **5.D**. |
| **Minor** | `planner.py` vs `workflow.py` | The planner prompt advertises three agents (`research_agent`, `data_analyst`, `document_agent`) but only `data_analyst` has a working node; `document_agent` tasks silently route to `END`. | Build/stub the missing nodes, or narrow the planner's agent list to what exists. |
| **Minor** | `test_main.py` (repo root) | A test file is sitting at the project root. | Move it into a `tests/` folder. |
| **Minor** | `agents/manager/memory.py` | `ProjectState` does not declare `target_file_path` (read by the analyst) and never populates `final_report`. Harmless today, but inconsistent. | Add the field and wire `final_report` when the report step lands. |
| **Minor** | (branch) | `.env.example` deleted. | See **5.A**. |

### 4.2 Manan — `manan/rag`

The cleanest branch. In-lane and well-built; the issues are about being
importable from the rest of the app.

| Severity | Location | Issue | Fix |
|----------|----------|-------|-----|
| **Major** | `rag/vector_db.py`, `rag/rag_pipeline.py` | Uses bare intra-folder imports (`from document_loader import Chunk`, `from embedding import Embedder`, `from vector_db import VectorDB`). These only resolve when Python runs **inside** `rag/`. The moment the app does `from rag.rag_pipeline import RAGPipeline`, they fail. | Use package paths (`from rag.document_loader import Chunk`) or relative imports (`from .document_loader import Chunk`), and add `rag/__init__.py` — see **5.B**. |
| **Major** | (config) | The switch to Pinecone introduces two new required env vars — `PINECONE_API_KEY` and `PINECONE_INDEX_NAME` — that are documented nowhere (and `.env.example` was deleted). Teammates cannot run RAG without guessing. | Restore `.env.example` and add these keys — see **5.A**. |
| **Minor** | `requirements.txt` | `pinecone` was added correctly; `python-dotenv` was already present, so that line is a duplicate. | Remove the duplicate in a later cleanup. |
| **Minor** | `rag/document_loader.py` (`chunk_text`) | If `overlap >= size` the loop never advances (infinite loop). Defaults are safe, but it is unguarded. | Add a guard: require `overlap < size`. |
| **Note** | `rag/rag_pipeline.py` (`query`) | `query()` returns `answer=None` — it retrieves context and sources but does not generate the final answer. This is correct for the RAG layer; answer generation belongs to the agent layer. Flagged only so everyone knows the generation step is still to come. | — |

### 4.3 Ahmad — `ahmad/backend-tools`

Strong, thorough toolkit. Same import-path fix as Manan, plus the shared
`tools/` ownership question.

| Severity | Location | Issue | Fix |
|----------|----------|-------|-----|
| **Blocker** | `tools/data_agent.py`, `tools/analytics.py` | Shared conflict with Danish — both wrote different versions of these two files. | Single owner + agreed API — see **5.C**. |
| **Major** | `tools/data_agent.py` | Uses a bare import `from analytics import compute_summary_stats, generate_charts`, which only resolves when run inside `tools/`. It breaks when imported as `from tools.data_agent import ...` from the app. | Use `from tools.analytics import ...` (or relative), and add `tools/__init__.py` — see **5.B**. |
| **Minor** | `tools/analytics.py` | `from mpl_toolkits.mplot3d import Axes3D` is imported but effectively unused in modern Matplotlib (3D is enabled via `projection="3d"`). | Remove the unused import. |
| **Note** | (scope) | `tools/` is well underway; the rest of the lane — `backend/` (FastAPI), `frontend/`, `deployment/`, `database/` — is still to come. The API layer that exposes all of this is the key next piece. | — |
| **Note** | `requirements.txt` | `pandas` / `numpy` / `matplotlib` are already declared — no dependency action needed. | — |

---

## 5. Repo-Wide Issues (everyone)

### 5.A — Restore `.env.example`

All three branches deleted `.env.example`. This file contains **no secrets** —
it is the template that lists which keys the project needs, with placeholder
values, and it is meant to stay committed. `main` still has it, but every
branch will try to delete it on merge.

```bash
git checkout main -- .env.example   # run on your branch, then commit + push
```

Then add the keys we now use across the stack:
`GROQ_API_KEY`, `GOOGLE_API_KEY`, `PINECONE_API_KEY`, `PINECONE_INDEX_NAME`.

### 5.B — One Import Convention

The repo currently mixes two incompatible import styles:

- `agents/` uses **root-absolute** imports (`from tools.data_agent import ...`).
- `rag/` and `tools/` use **folder-relative** imports (`from analytics import ...`).

These cannot coexist. Standard going forward:

1. Always import from the repo-root package path: `from rag.document_loader import Chunk`, `from tools.analytics import ...`, `from agents.manager.workflow import app`.
2. Add `__init__.py` to each package folder that needs one.
3. Run everything from the **project root** (e.g. `python -m tools.data_agent`), never `cd tools && python data_agent.py`.

This is the single most important thing to standardise now — it is why some
modules cannot import each other yet.

### 5.C — `tools/` Ownership (Danish + Ahmad)

`tools/` has one owner: **Ahmad.** Both Danish and Ahmad currently maintain
separate, incompatible versions of `tools/data_agent.py` and
`tools/analytics.py`. Plan to resolve:

1. Danish sends Ahmad the exact functions his Analyst needs, plus his KNN
   imputation, Isolation-Forest anomaly detection, and the PDF/JSON reporter.
2. Ahmad folds them into `tools/` under one agreed API, keeping his own
   cleaning, structure detection, and chart generation.
3. Danish's Analyst then imports Ahmad's API.

Nothing is thrown away — we simply stop keeping two copies. Until this is
agreed, please do not both keep editing those two files separately.

### 5.D — Dependency Discipline

If you `import` a new library, add it to `requirements.txt` **in the same
commit**. A fresh `pip install -r requirements.txt` must be enough to run the
whole app. (Outstanding: Danish's `scikit-learn`, `fpdf2`/`reportlab`,
`langchain-groq`, `langchain-google-genai`.)

### 5.E — Centralise Configuration

The stack now spans several providers (Google, Groq, Pinecone, HuggingFace/BGE),
each with its own key. Create a single config module that calls `load_dotenv()`
once and exposes the settings. This removes the import-order bug in 4.1 and
gives one place to manage keys.

---

## 6. Action Items

**Danish**
- [ ] Fix the Researcher import so the branch runs on a clean clone (4.1, Blocker #1).
- [ ] Coordinate with Ahmad on `tools/` ownership (5.C).
- [ ] Correct the Gemini model ID (4.1).
- [ ] Load `.env` before any LLM client is built (4.1 / 5.E).
- [ ] Fix the PDF Unicode issue (`reportlab` or a TTF font) (4.1).
- [ ] Add missing dependencies to `requirements.txt` (5.D).
- [ ] Align planner agents with built nodes; move `test_main.py` into `tests/` (4.1).

**Manan**
- [ ] Convert `rag/` imports to package paths and add `rag/__init__.py` (5.B).
- [ ] Restore `.env.example` and add `PINECONE_API_KEY`, `PINECONE_INDEX_NAME` (5.A).
- [ ] Remove the duplicate `python-dotenv` line (4.2).

**Ahmad**
- [ ] Convert `tools/` imports to package paths and add `tools/__init__.py` (5.B).
- [ ] Coordinate with Danish on `tools/` ownership (5.C).
- [ ] Remove the unused `Axes3D` import (4.3).

**Everyone**
- [ ] Restore `.env.example` on your branch (5.A).
- [ ] Follow the one import convention and run from the project root (5.B).
- [ ] Add every new dependency to `requirements.txt` (5.D).
- [ ] Keep to `WORKFLOW.md`: never commit to `main`, one PR per feature, pull `main` daily.

---

## 7. Merge Readiness & Order of Operations

No branch should merge until it runs on a clean clone and follows the shared
conventions above. Suggested order:

1. **Danish** fixes the Researcher import (his branch must run first).
2. **Everyone** restores `.env.example`.
3. **Danish + Ahmad** agree on `tools/` ownership and consolidate.
4. **Manan + Ahmad** fix their import paths and add `__init__.py`.
5. Open one Pull Request per branch; the owner reviews and merges in the order above.

This is a very good foundation. The remaining work is mostly about making the
three parts speak the same language before they are joined.

---

## Appendix — How These Findings Were Checked

```bash
# Sync every branch
git fetch --all --prune

# What each branch changed vs main
git log --oneline main..origin/<branch>
git diff --stat main..origin/<branch>

# Confirm the broken import on danish/agents
git cat-file -e origin/danish/agents:agents/researcher/research_agent.py   # fails: file absent
git show origin/danish/agents:agents/manager/workflow.py | grep -n researcher

# Confirm the tools/ API mismatch
git show origin/danish/agents:tools/data_agent.py | grep '^def '
git show origin/ahmad/backend-tools:tools/data_agent.py | grep '^def '

# Simulate merging both tool branches to detect conflicts
BASE=$(git merge-base origin/danish/agents origin/ahmad/backend-tools)
git merge-tree "$BASE" origin/danish/agents origin/ahmad/backend-tools

# Confirm .env.example deleted on every branch
for b in danish/agents manan/rag ahmad/backend-tools; do
  git cat-file -e origin/$b:.env.example 2>/dev/null && echo "$b: present" || echo "$b: deleted"
done
```
