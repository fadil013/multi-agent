import sys
import os

# Tell Python to look in the parent directory (the project root) for modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.manager.workflow import app

initial_state = {
    # Let's give it a slightly more advanced prompt to test the new ML tools!
    "user_objective": "Perform an EDA on our sales dataset. Also, please check for any mathematical anomalies or outliers in the data.",
    
    # ---> THIS IS REQUIRED NOW BASED ON OUR MEMORY.PY FIX
    "target_file_path": "sales.csv", 
    
    "task_list": [],
    "short_term_memory": []
}

def run_test():
    print("--- STARTING AURA MANAGER AGENT ---\n")
    
    result = app.invoke(initial_state)
    
    print("\n--- FINAL SYSTEM MEMORY ---")
    for memory in result.get("short_term_memory", []):
        print(f"[{memory['agent']}]: {memory['finding']}\n")

if __name__ == "__main__":
    run_test()