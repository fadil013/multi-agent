# Manager Agent

The **brain** of AURA. Understands the user's objective, breaks it into subtasks,
assigns them to specialist agents, monitors progress, and combines results.

**Planned modules**
- `agent_manager.py` — orchestration entry point
- `planner.py` — task decomposition & assignment
- `workflow.py` — LangGraph workflow definition
- `memory.py` — short- and long-term memory
