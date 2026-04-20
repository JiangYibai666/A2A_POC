import json
import os

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

from tools.hotel_search import HotelSearchTool

load_dotenv()

_HOTEL_AGENT_PROMPT = """\
You are a hotel search assistant.
Your task is to call the search_hotels tool with the provided city, arrival time, and return departure time.

Rules:
1. You must call the search_hotels tool. Never invent hotel data.
2. city must be an uppercase IATA code such as SHA, PEK, HKG, or BKK.
3. arrive_time and depart_time must be full ISO8601 timestamps with timezone.
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
        _agent = create_react_agent(llm, [HotelSearchTool()])
    return _agent


async def handle_task(task) -> str:
    params = task.message.parts[0].metadata
    city = params.get("city", "SHA")
    arrive_time = params.get("arrive_time", "")
    depart_time = params.get("depart_time", "")

    task_msg = (
        f"Search hotels with the following parameters:\n"
        f"- City IATA: {city}\n"
        f"- Arrival time: {arrive_time}\n"
        f"- Return departure time: {depart_time}\n"
        f"Please call the search_hotels tool to complete the search."
    )

    agent = _get_agent()
    result = await agent.ainvoke(
        {
            "messages": [
                SystemMessage(content=_HOTEL_AGENT_PROMPT),
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

    return json.dumps([])