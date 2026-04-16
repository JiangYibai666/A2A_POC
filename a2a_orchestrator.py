"""
A2A orchestrator that discovers and invokes specialist agents via the A2A protocol.
"""

import requests
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, MessagesState, END
from langgraph.checkpoint.memory import MemorySaver


class A2AOrchestrator:
    """Discover agents and route tasks through A2A."""
    
    def __init__(self, registry_url: str = "http://localhost:5000"):
        self.registry_url = registry_url
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
        self.agents = self._discover_agents()
    
    def _discover_agents(self):
        """Discover all available agents through agent cards."""
        try:
            resp = requests.get(f"{self.registry_url}/.well-known/agent.json")
            agents = resp.json().get("agents", [])
            # Fetch detailed metadata for each discovered agent.
            for agent in agents:
                card_resp = requests.get(f"{self.registry_url}/.well-known/{agent['name']}.json")
                agent["card"] = card_resp.json()
            return {a["name"]: a for a in agents}
        except Exception as e:
            print(f"[WARNING] Agent discovery failed: {e}")
            return {}
    
    def classify_intent(self, query: str) -> str:
        """
        Use the LLM to analyze the user's intent and choose the target agent.
        This is the intent-classification step described in the Doxa Connex docs.
        """
        prompt = f"""Analyze the user's intent and choose the most appropriate agent.

Available agents:
- invoice_agent: handles invoices, bills, and payment status questions
- entity_agent: handles company information, registration details, addresses, and similar requests

User question: {query}

Return only the agent name (invoice_agent or entity_agent), with no extra text.
If the intent is unclear, return "unknown".
"""
        response = self.llm.invoke(prompt)
        content = response.content.strip().strip("`").strip()
        
        # Extract the intent conservatively.
        if "invoice_agent" in content:
            return "invoice_agent"
        elif "entity_agent" in content:
            return "entity_agent"
        else:
            return "unknown"
    
    def call_agent(self, agent_name: str, query: str, task_id: str) -> str:
        """Invoke an agent through the A2A protocol."""
        if agent_name not in self.agents:
            return f"Agent {agent_name} is unavailable."
        
        endpoint = self.agents[agent_name]["card"]["endpoints"]["tasks"]
        url = f"{self.registry_url}{endpoint}"
        
        # Build the A2A JSON-RPC request.
        payload = {
            "jsonrpc": "2.0",
            "method": "tasks/send",
            "id": task_id,
            "params": {
                "id": task_id,
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": query}]
                }
            }
        }
        
        resp = requests.post(url, json=payload)
        result = resp.json()
        
        if "result" in result:
            artifacts = result["result"].get("artifacts", [])
            if artifacts:
                return artifacts[0]["parts"][0]["text"]
        return f"Failed to call {agent_name}"
    
    def process(self, query: str, thread_id: str = "default") -> str:
        """Main entry point for processing a user query."""
        # 1. Classify the intent.
        agent_name = self.classify_intent(query)
        
        if agent_name == "unknown":
            return "Sorry, I am not sure how to answer that. You can ask about invoices or company information."
        
        # 2. Call the specialist agent.
        return self.call_agent(agent_name, query, thread_id)


# Build the LangGraph orchestration workflow.
def create_orchestrator_graph():
    """Wrap the A2A orchestrator in a LangGraph workflow."""
    orchestrator = A2AOrchestrator()
    memory = MemorySaver()
    
    def orchestrate(state: MessagesState):
        query = state["messages"][-1].content
        response = orchestrator.process(query, thread_id=state.get("thread_id", "default"))
        return {"messages": [AIMessage(content=response)]}
    
    graph = StateGraph(MessagesState)
    graph.add_node("orchestrate", orchestrate)
    graph.set_entry_point("orchestrate")
    graph.add_edge("orchestrate", END)
    
    return graph.compile(checkpointer=memory)