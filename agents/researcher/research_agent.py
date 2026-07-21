"""Research Agent - gathers live external facts and tracks sources.

Uses the web search tool (tools/search_tool.py - owned by Ahmad).
Owner: Danish (agent) + Ahmad (tool)
"""
from __future__ import annotations
import os

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from agents.base import AgentResult, BaseAgent
from tools.search_tool import web_search  # Importing Ahmad's tool

class ResearchAgent(BaseAgent):
    name = "researcher"

    def run(self, task: str, context: dict | None = None) -> AgentResult:
        print(f"\n[Research Agent] Waking up. Task: {task}")

        # 1. Initialize Gemini
        api_key = os.getenv("GOOGLE_API_KEY")
        llm = ChatGoogleGenerativeAI(
            model="gemini-3.5-flash", 
            temperature=0, 
            google_api_key=api_key
        )

        # 2. Equip the Agent with Ahmad's web search tool
        llm_with_tools = llm.bind_tools([web_search])

        # 3. Define the AI's persona
        system_prompt = """You are the Research Agent. 
        You have access to the 'web_search' tool. 
        Use it to search the live internet, extract the most relevant facts, and summarize them. 
        Always focus on current market trends, competitors, and external facts."""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Task: {task}")
        ]

        # 4. Let Gemini think and decide on the search query
        ai_msg = llm_with_tools.invoke(messages)

        finding = "No web data found."

        # 5. Execute the Tool Loop (using the dynamic args fix we learned!)
        if ai_msg.tool_calls:
            for tool_call in ai_msg.tool_calls:
                if tool_call["name"] == "web_search":
                    # Dynamically extract whatever search query Gemini generated
                    generated_args = tool_call["args"]
                    
                    # Run the DuckDuckGo search tool
                    finding = web_search.invoke(generated_args)

        print(f"[Research Agent] Task complete. Finding snippet: {str(finding)[:100]}...")

        # 6. Return the AgentResult 
        # (Note: Depending on how your team defined AgentResult in base.py, 
        # you may need to adjust the kwargs, e.g., output=finding, data=finding, etc.)
        return AgentResult(agent=self.name, output=finding)