import asyncio
from a2a.router import router
from agents.flight_agent import handle_task as flight_handler
from agents.hotel_agent import handle_task as hotel_handler
from agents.orchestrator import orchestrator_graph

async def start_agents():
    # Register agents
    router.register_agent('flight_agent', flight_handler)
    router.register_agent('hotel_agent', hotel_handler)

    print("✓ Orchestrator agent ready")
    print("✓ Flight agent ready")
    print("✓ Hotel agent ready")

    return orchestrator_graph