from agents.manager.workflow import app

initial_state = {
    "user_objective": "Perform an EDA on our sales.csv file and tell me about the revenue and units.",
    "task_list": []
}

def run_test():
    print("--- STARTING AURA MANAGER AGENT ---\n")
    
    result = app.invoke(initial_state)
    
    # ---> THIS IS THE CRITICAL FIX FOR THE OUTPUT
    print("\n--- FINAL SYSTEM MEMORY ---")
    for memory in result.get("short_term_memory", []):
        print(f"[{memory['agent']}]: {memory['finding']}\n")

if __name__ == "__main__":
    run_test()