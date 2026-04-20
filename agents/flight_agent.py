import json
import os

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

from tools.flight_search import FlightSearchTool

load_dotenv()

_FLIGHT_AGENT_PROMPT = """\
You are a flight search assistant.
Your task is to call the search_flights tool with the provided parameters.

Rules:
1. You must call the search_flights tool. Never invent flight data.
2. origin_candidates and destination_candidates must be uppercase IATA codes.
3. If the destination refers to China at the country level, the candidates should include ["PEK", "SHA", "HKG"].
4. After searching, return the tool's raw JSON result without changing any fields.
"""

_agent = None


def _get_agent():
    global _agent
    if _agent is None:
        llm = ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            temperature=0,
            google_api_key=os.getenv("GEMINI_API_KEY"),
        )
        _agent = create_react_agent(llm, [FlightSearchTool()])
    return _agent


async def handle_task(task) -> str:
    params = task.message.parts[0].metadata
    origin_candidates = params.get("origin_candidates") or [params.get("origin", "SIN")]
    dest_candidates = (
        params.get("destination_candidates") or [params.get("destination", "SHA")]
    )
    departure_date = params.get("departure_date", "")
    return_date = params.get("return_date")

    task_msg = (
        f"Search flights with the following parameters:\n"
        f"- Origin candidates (IATA): {origin_candidates}\n"
        f"- Destination candidates (IATA): {dest_candidates}\n"
        f"- Departure date: {departure_date}\n"
        f"- Return date: {return_date or 'None (one-way)'}\n"
        f"Please call the search_flights tool to complete the search."
    )

    agent = _get_agent()
    result = await agent.ainvoke(
        {
            "messages": [
                SystemMessage(content=_FLIGHT_AGENT_PROMPT),
                HumanMessage(content=task_msg),
            ]
        }
    )

    # Extract the raw JSON from the last ToolMessage.
    for msg in reversed(result["messages"]):
        if isinstance(msg, ToolMessage):
            try:
                json.loads(msg.content)
                return msg.content
            except (json.JSONDecodeError, Exception):
                pass

    return json.dumps({"outbound": [], "return": []})