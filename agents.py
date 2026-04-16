"""
Create specialist agents for invoices and company entities.
"""

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from mcp_tools import query_invoices, query_entity
from dotenv import load_dotenv

load_dotenv()

model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
memory = MemorySaver()

# Invoice agent
invoice_agent = create_react_agent(
    model=model,
    tools=[query_invoices],
    checkpointer=memory,
    name="invoice_agent",
    prompt=(
        "You are a specialist assistant for invoice lookup. "
        "You help users query invoice information for a specific company, including filtering by status. "
        "List each invoice clearly with its ID, amount, status, and vendor. "
        "Use tools to fetch data and do not make up information."
    )
)

# Entity agent
entity_agent = create_react_agent(
    model=model,
    tools=[query_entity],
    checkpointer=memory,
    name="entity_agent",
    prompt=(
        "You are an assistant for company information lookup. "
        "You help users query company registration details, address, industry, and related information. "
        "Present the answer in a structured format. "
        "Use tools to fetch data and do not make up information."
    )
)