import sys
import os
from dotenv import load_dotenv

# Tell Python to look in the parent directory (the project root) for modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv()

from agents.manager.workflow import app

initial_state = {
    "user_objective": "Analyze sales.csv for revenue trends.",
    "task_list": [],
    "data_source": "file",
    "target_file_path": "sales.csv",
}

def run_test():
    print("--- STARTING AURA MANAGER AGENT ---\n")

    result = app.invoke(initial_state)

    print("\n--- FINAL SYSTEM MEMORY ---")
    for memory in result.get("short_term_memory", []):
        print(f"[{memory['agent']}]: {memory['finding']}\n")

if __name__ == "__main__":
    run_test()