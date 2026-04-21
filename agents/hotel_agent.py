from tools.hotel_search import HotelSearchTool


async def handle_task(task) -> str:
    params = task.message.parts[0].metadata
    city = params.get("city", "SHA")
    arrive_time = params.get("arrive_time", "")
    depart_time = params.get("depart_time", "")
    checkin_window_hours = params.get("checkin_window_hours", 3)
    checkout_buffer_hours = params.get("checkout_buffer_hours", 1)

    # Call the tool directly — the orchestrator has already parsed all parameters,
    # so going through an LLM ReAct agent adds no value and introduces unreliability.
    tool = HotelSearchTool()
    return tool._run(
        city=city,
        arrive_time=arrive_time,
        depart_time=depart_time,
        checkin_window_hours=checkin_window_hours,
        checkout_buffer_hours=checkout_buffer_hours,
    )