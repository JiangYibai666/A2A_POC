from tools.flight_search import FlightSearchTool


async def handle_task(task) -> str:
    params = task.message.parts[0].metadata
    origin_candidates = params.get("origin_candidates") or [params.get("origin", "SIN")]
    dest_candidates = (
        params.get("destination_candidates") or [params.get("destination", "SHA")]
    )
    departure_date = params.get("departure_date", "")
    return_date = params.get("return_date")

    # Call the tool directly — the orchestrator has already parsed all parameters,
    # so going through an LLM ReAct agent adds no value and introduces unreliability.
    tool = FlightSearchTool()
    return tool._run(
        origin_candidates=origin_candidates,
        destination_candidates=dest_candidates,
        departure_date=departure_date,
        return_date=return_date,
    )