from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, StateGraph

#local protocols and router
from a2a.protocol import Message, MessagePart, Task
from a2a.router import router
from tools.hotel_search import HotelSearchTool

load_dotenv()


# ─────────────────────────────────────────────────────────────────────────────
# State--Workflow memory
# ─────────────────────────────────────────────────────────────────────────────
class OrchestratorState(TypedDict):
    user_input: str
    chat_history: List[Dict[str, str]]  # [{"role": "user"|"assistant", "content": "..."}]
    parsed_params: Dict[str, Any]       # Parameters extracted by the LLM.
    intent: str                         # flight_only | hotel_only | flight_and_hotel | other
    flight_options: Dict[str, Any]
    hotel_options: List[Any]
    combined_options: List[Any]
    selected_option: Dict[str, Any]
    llm_summary: str                    # Natural language summary for UI and CLI.


# ─────────────────────────────────────────────────────────────────────────────
# LLM factory--A new instance is created each time LLM needs to be called.
# ─────────────────────────────────────────────────────────────────────────────
def _get_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        temperature=0,
        google_api_key=os.getenv("GEMINI_API_KEY"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Prompts--Tell the LLM how to convert the user's natural language into structured parameters
# ─────────────────────────────────────────────────────────────────────────────
_INTENT_SYSTEM = """\
You are the intent parsing module for a travel booking assistant. Use the latest user message plus chat history to extract booking parameters.

Known IATA mappings:
    Singapore -> SIN | Shanghai -> SHA | Beijing -> PEK | Hong Kong -> HKG
    Bangkok / Thailand -> BKK | San Francisco / United States -> SFO
    Country-level China / Mainland China -> destination_candidates should be ["PEK", "SHA", "HKG"]

Support both English and Chinese user input.
Today's date: {today}

Output strict JSON only. Do not include Markdown or any other text:
{{
  "intent": "flight_and_hotel" | "flight_only" | "hotel_only" | "other",
  "origin_candidates": ["IATA..."],
  "destination_candidates": ["IATA..."],
  "departure_date": "YYYY-MM-DD",
    "return_date": "YYYY-MM-DD or null",
    "hotel_city": "IATA or null"
}}

Rules:
1. If the year is omitted, use the current year if the date has not passed yet; otherwise use the next year.
2. If the request mentions only flights, set intent to flight_only. If it also mentions hotels, set intent to flight_and_hotel.
3. For a request like "Thailand to China", set origin_candidates to ["BKK"] and destination_candidates to ["PEK", "SHA", "HKG"].
4. If the request is hotel-only, set hotel_city to the hotel destination city and use departure_date as check-in date and return_date as checkout date if available.
5. If intent is other, the remaining fields may be empty lists or null.
"""

_SUMMARY_SYSTEM = """\
You are a travel assistant. Summarize search results for the user in clear, natural English.
- Keep it concise and easy to scan.
- If there are no results, explain likely reasons and suggest adjustments.
- Do not mention a return flight for one-way results.
- Do not list every option in detail; provide an overview and suggest a next step.
"""

# ─────────────────────────────────────────────────────────────────────────────
# Node 1: LLM intent parsing
# ─────────────────────────────────────────────────────────────────────────────
async def llm_parse_intent(state: OrchestratorState) -> OrchestratorState:
    llm = _get_llm()
    today = datetime.now().strftime("%Y-%m-%d")
    system_msg = _INTENT_SYSTEM.format(today=today)

  # Build a message list: history + system prompts + current user input
    messages: List = [SystemMessage(content=system_msg)]
    for h in (state.get("chat_history") or []):
        if h["role"] == "user":
            messages.append(HumanMessage(content=h["content"]))
        else:
            messages.append(AIMessage(content=h["content"]))
    messages.append(HumanMessage(content=state["user_input"]))

  # call Gemini LLM
    response = await llm.ainvoke(messages)
    raw = response.content.strip()

    # Strip a possible Markdown code block wrapper.
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1].lstrip("json").strip() if len(parts) > 1 else raw

#  Attempt to parse JSON; return a default value if it fails.
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {
            "intent": "flight_and_hotel",
            "origin_candidates": ["SIN"],
            "destination_candidates": ["SHA"],
            "departure_date": today,
            "return_date": None,
            "hotel_city": None,
        }
    # renew state
    state["parsed_params"] = parsed
    state["intent"] = parsed.get("intent", "flight_and_hotel")
    return state


# ─────────────────────────────────────────────────────────────────────────────
# Routing helpers
# ─────────────────────────────────────────────────────────────────────────────
def _route_after_intent(state: OrchestratorState) -> str:
    intent = state.get("intent", "flight_and_hotel")
    if intent == "hotel_only":
        return "call_hotel"
    if intent == "other":
        return "llm_summarize"
    return "call_flight"  # flight_only or flight_and_hotel

# Return the name of the next node.

def _route_after_flight(state: OrchestratorState) -> str:
    if state.get("intent") == "flight_only":
        return "llm_summarize"
    return "call_hotel"


CITY_TIMEZONE_MAP = {
    "SIN": "+08:00",
    "SHA": "+08:00",
    "PEK": "+08:00",
    "HKG": "+08:00",
    "BKK": "+07:00",
    "SFO": "-07:00",
}


def _hotel_only_query_from_params(params: Dict[str, Any]) -> Dict[str, Any]:
    # Determine the target city (priority: explicitly specified > destination_candidates first > default SHA)
    hotel_city = (
        params.get("hotel_city")
        or (params.get("destination_candidates") or [None])[0]
        or "SHA"
    )
    # Confirm check-in/check-out dates
    checkin_date = params.get("departure_date") or datetime.now().strftime("%Y-%m-%d")
    checkout_date = params.get("return_date")
    if not checkout_date:
        checkout_date = (
            datetime.fromisoformat(checkin_date) + timedelta(days=3)
        ).strftime("%Y-%m-%d")

    # Get time zone suffix
    timezone_suffix = CITY_TIMEZONE_MAP.get(hotel_city, "+08:00")
    # Construct the complete query object
    return {
        "city": hotel_city,
        "arrive_time": f"{checkin_date}T12:00:00{timezone_suffix}",
        "depart_time": f"{checkout_date}T20:00:00{timezone_suffix}",
        "checkin_window_hours": 6,
        "checkout_buffer_hours": 4,
    }

# ─────────────────────────────────────────────────────────────────────────────
# call flight agent
# ─────────────────────────────────────────────────────────────────────────────

async def call_flight_agent(state: OrchestratorState) -> OrchestratorState:
    # Construct the task object: target = flight_agent, data = parsed_params
    task = Task(
        sender='orchestrator',
        receiver='flight_agent',
        message=Message(
            role='user',
            parts=[MessagePart(text='Search flights', metadata=state['parsed_params'])]
        )
    )
    # Send the task via router and wait for the result.
    result = await router.send_task(task)
    state['flight_options'] = json.loads(result)

    # For flight_only intent, call_hotel is skipped so build combined_options here.
    if state.get('intent') == 'flight_only':
        outbound_flights = state['flight_options'].get('outbound', [])
        return_flights = state['flight_options'].get('return', [])
        state['combined_options'] = []
        no_hotel = {'name': 'No hotel selected', 'area': '-', 'stars': '-',
                    'checkin_time': '-', 'checkout_time': '-', 'price': 0}
        no_return = {'flight_number': 'One-way', 'airline': '-',
                     'departure_time': '-', 'arrival_time': '-', 'duration': '-', 'price': 0}
        
        # If there is a return flight, combine all round-trip flights.
        if return_flights:
            for outbound in outbound_flights:
                for ret in return_flights:
                    state['combined_options'].append(
                        {'outbound': outbound, 'return': ret, 'hotel': no_hotel}
                    )
         # Otherwise, each outbound flight will be assigned a "one-way" reservation.
        else:
            for outbound in outbound_flights:
                state['combined_options'].append(
                    {'outbound': outbound, 'return': no_return, 'hotel': no_hotel}
                )

    return state

# ─────────────────────────────────────────────────────────────────────────────
# call hotel agent
# ─────────────────────────────────────────────────────────────────────────────

async def call_hotel_agent(state: OrchestratorState) -> OrchestratorState:
    if state.get("intent") == "hotel_only":
        hotel_query = _hotel_only_query_from_params(state["parsed_params"])
        hotels: List[Dict[str, Any]] = []
        try:
            task = Task(
                sender='orchestrator',
                receiver='hotel_agent',
                message=Message(
                    role='user',
                    parts=[MessagePart(text='Search hotels', metadata=hotel_query)]
                )
            )
            result = await router.send_task(task)
            hotels = json.loads(result)
        except Exception:
            # Fallback for temporary LLM/model outages in hotel-only flow.
            raw = HotelSearchTool()._run(**hotel_query)
            try:
                hotels = json.loads(raw)
            except json.JSONDecodeError:
                hotels = []

        state['hotel_options'] = hotels if isinstance(hotels, list) else []
        state['combined_options'] = []

        # Create "virtual flights" (placeholders) for each hotel
        for hotel in state['hotel_options']:
            state['combined_options'].append({
                'outbound': {
                    'flight_number': 'Hotel-only',
                    'airline': '-',
                    'origin': '-',
                    'destination': hotel_query['city'],
                    'departure_time': hotel_query['arrive_time'],
                    'arrival_time': hotel_query['arrive_time'],
                    'duration': '-',
                    'price': 0,
                },
                'return': {
                    'flight_number': 'No return flight',
                    'airline': '-',
                    'departure_time': hotel_query['depart_time'],
                    'arrival_time': '-',
                    'duration': '-',
                    'price': 0,
                },
                'hotel': hotel,
            })

        if not state['combined_options']:
            state['combined_options'].append({
                'outbound': {
                    'flight_number': 'Hotel-only',
                    'airline': '-',
                    'origin': '-',
                    'destination': hotel_query['city'],
                    'departure_time': hotel_query['arrive_time'],
                    'arrival_time': hotel_query['arrive_time'],
                    'duration': '-',
                    'price': 0,
                },
                'return': {
                    'flight_number': 'No return flight',
                    'airline': '-',
                    'departure_time': hotel_query['depart_time'],
                    'arrival_time': '-',
                    'duration': '-',
                    'price': 0,
                },
                'hotel': {
                    'name': 'No hotel match',
                    'area': '-',
                    'stars': '-',
                    'checkin_time': hotel_query['arrive_time'],
                    'checkout_time': hotel_query['depart_time'],
                    'price': 0,
                },
            })
        return state

    outbound_flights = state['flight_options'].get('outbound', [])
    return_flights = state['flight_options'].get('return', [])
    state['combined_options'] = []
    state['hotel_options'] = []

    # Fallback for one-way or flight-only requests to avoid empty result pages.
    if not return_flights and outbound_flights:
        for outbound in outbound_flights:
            state['combined_options'].append({
                'outbound': outbound,
                'return': {
                    'flight_number': 'One-way',
                    'airline': '-',
                    'departure_time': '-',
                    'arrival_time': '-',
                    'duration': '-',
                    'price': 0
                },
                'hotel': {
                    'name': 'No hotel selected',
                    'area': '-',
                    'stars': '-',
                    'checkin_time': '-',
                    'checkout_time': '-',
                    'price': 0
                }
            })
        return state

    # Round-trip flights and hotel (normal situation)
    for outbound in outbound_flights:
        for return_flight in return_flights:
            hotel_query = {
                'city': outbound['destination'],
                'arrive_time': outbound['arrival_time'],
                'depart_time': return_flight['departure_time'],
                'checkin_window_hours': 3,
                'checkout_buffer_hours': 1
            }
            # For this flight, search for hotels
            task = Task(
                sender='orchestrator',
                receiver='hotel_agent',
                message=Message(
                    role='user',
                    parts=[MessagePart(text='Search hotels', metadata=hotel_query)]
                )
            )
            result = await router.send_task(task)
            hotels = json.loads(result)
            # Pair each hotel with the flight
            state['hotel_options'].extend(hotels)
            for hotel in hotels:
                state['combined_options'].append({
                    'outbound': outbound,
                    'return': return_flight,
                    'hotel': hotel
                })

            # If no hotels are listed, add a "No match" placeholder.
            if not hotels:
                state['combined_options'].append({
                    'outbound': outbound,
                    'return': return_flight,
                    'hotel': {
                        'name': 'No hotel match',
                        'area': '-',
                        'stars': '-',
                        'checkin_time': '-',
                        'checkout_time': '-',
                        'price': 0
                    }
                })

    return state



# ─────────────────────────────────────────────────────────────────────────────
# Node 4: LLM summary
# ─────────────────────────────────────────────────────────────────────────────
async def llm_summarize(state: OrchestratorState) -> OrchestratorState:
    llm = _get_llm()
    combined = state.get("combined_options") or []
    intent = state.get("intent", "flight_and_hotel")
    params = state.get("parsed_params") or {}

    # Scenario A: No results
    if not combined:
        prompt = (
            f"User request intent={intent}, "
            f"origin={params.get('origin_candidates')}, "
            f"destination={params.get('destination_candidates')}, "
            f"hotel_city={params.get('hotel_city')}, "
            f"departure_date={params.get('departure_date')}. "
            f"No matching results were found. Please provide a friendly explanation and next-step suggestions."
        )
    # Scenario B: Results are available; extract the first 3 options to create a summary.
    else:
        snippets = []
        for i, opt in enumerate(combined[:3], 1):
            ob = opt.get("outbound", {})
            rt = opt.get("return", {})
            ht = opt.get("hotel", {})
            # Pure Hotel Format
            if intent == "hotel_only":
                line = (
                    f"Option {i}: hotel {ht.get('name','')} in {ht.get('area','')}, "
                    f"check-in {ht.get('checkin_time','')[:10]}, checkout {ht.get('checkout_time','')[:10]}"
                )
            # flight + hotel format
            else:
                line = f"Option {i}: {ob.get('flight_number','')} departs on {ob.get('departure_time','')[:10]}"
                if rt.get("flight_number") and rt.get("flight_number") != "One-way":
                    line += f", return {rt.get('flight_number','')}"
                if ht.get("name") and ht.get("name") not in ("No hotel selected", "No hotel match"):
                    line += f", hotel: {ht.get('name','')} ({ht.get('area','')})"
            snippets.append(line)
        prompt = (
            f"Found {len(combined)} options. Here are the first {len(snippets)}:\n"
            + "\n".join(snippets)
            + "\n\nPlease summarize briefly and guide the user on what to do next."
        )

    response = await llm.ainvoke(
        [SystemMessage(content=_SUMMARY_SYSTEM), HumanMessage(content=prompt)]
    )
    state["llm_summary"] = response.content
    return state


# ─────────────────────────────────────────────────────────────────────────────
# Graph with conditional routing
# ─────────────────────────────────────────────────────────────────────────────
graph = StateGraph(OrchestratorState)
# Add 4 nodes
graph.add_node("llm_parse_intent", llm_parse_intent)
graph.add_node("call_flight", call_flight_agent)
graph.add_node("call_hotel", call_hotel_agent)
graph.add_node("llm_summarize", llm_summarize)

# Setting up an entry point
graph.set_entry_point("llm_parse_intent")

# Conditional edge: after intent resolution
graph.add_conditional_edges(
    "llm_parse_intent",
    _route_after_intent,
    {
        "call_flight": "call_flight",
        "call_hotel": "call_hotel",
        "llm_summarize": "llm_summarize",
    },
)
# Conditional side: After flight search
graph.add_conditional_edges(
    "call_flight",
    _route_after_flight,
    {
        "call_hotel": "call_hotel",
        "llm_summarize": "llm_summarize",
    },
)
# Unconditional edge: Hotel search always includes summary
graph.add_edge("call_hotel", "llm_summarize")
# Unconditional edge: Ends after summary
graph.add_edge("llm_summarize", END)
# Compile into an executable graph
orchestrator_graph = graph.compile()
