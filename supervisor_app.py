# supervisor_app.py
"""
Supervisor-based multi-agent system that coordinates specialist agents.
"""

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph_supervisor import create_supervisor

from agents import invoice_agent, entity_agent

# Create the supervisor workflow.
supervisor = create_supervisor(
    agents=[invoice_agent, entity_agent],
    model=ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0),
    prompt=(
        "You are the supervisor of an enterprise assistant system. You manage two specialist agents:\n"
        "1. invoice_agent: handles invoice-related queries\n"
        "2. entity_agent: handles company entity information queries\n\n"
        "Choose the appropriate agent based on the user's question. "
        "If the request spans multiple domains, call multiple agents in sequence. "
        "Do not answer questions yourself. Always delegate the task to the specialist agent."
    )
)

# Compile the workflow.
app = supervisor.compile()