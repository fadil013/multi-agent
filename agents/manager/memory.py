"""Memory - short-term (current run) and long-term (vector store) memory.

Owner: Danish  (long-term recall is backed by the RAG layer - coordinate with Manan)
"""
from typing import TypedDict, List, Annotated
import operator

class ProjectState(TypedDict):
    """
    This replaces the Memory class. LangGraph will pass this dictionary 
    to every agent in the workflow.
    """
    # The original goal given by the user
    user_objective: str
    
    # ---> FIX: Added the target file path so agents know what data to load
    target_file_path: str
    
    # The active plan broken down by the Manager Agent
    task_list: List[dict]
    
    # This replaces your self._short_term list and self.remember() method!
    # 'Annotated' and 'operator.add' tell LangGraph: "When an agent returns 
    # new memory items, append them to this list, don't overwrite it."
    short_term_memory: Annotated[List[dict], operator.add]
    
    # A placeholder for the final output
    final_report: str

# Note on Long-Term Memory (Recall):
# You won't define a recall() method here. Instead, when an agent needs 
# long-term memory, it will call a specialized Tool (built by Intern 3) 
# that queries the VectorDB (built by Intern 2).