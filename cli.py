import readline
import asyncio
from typing import List, Dict
from agents.orchestrator import OrchestratorState


async def cli_loop(orchestrator_graph):
    chat_history: List[Dict[str, str]] = []

    while True:
        try:
            user_input = input("> ").strip()
            if not user_input:
                continue
            if user_input.lower() in ['exit', 'quit']:
                break

            print('[Searching for options...]')

            initial_state: OrchestratorState = {
                "user_input": user_input,
                "chat_history": chat_history.copy(),
                "parsed_params": {},
                "intent": "",
                "flight_options": {},
                "hotel_options": [],
                "combined_options": [],
                "selected_option": {},
                "llm_summary": "",
            }

            result = await orchestrator_graph.ainvoke(initial_state)

            # Show the LLM summary first.
            summary = result.get('llm_summary', '').strip()
            intent = result.get('intent', '')
            if summary:
                print(f"\n{summary}\n")

            # If structured options exist, print a compact list.
            combined = result.get('combined_options', [])
            if combined:
                print("-- Option List --")
                for i, option in enumerate(combined[:5], 1):
                    outbound = option.get('outbound', {})
                    return_flight = option.get('return', {})
                    hotel = option.get('hotel', {})
                    if intent == 'hotel_only':
                        print(
                            f"  Option {i}: {hotel.get('name','')} | {hotel.get('area','')} | {hotel.get('stars','')} | "
                            f"check-in {hotel.get('checkin_time','')} | checkout {hotel.get('checkout_time','')} | {hotel.get('price','')}"
                        )
                        continue
                    ret_str = (
                        f"return {return_flight.get('flight_number','')} {return_flight.get('departure_time','')} "
                        if return_flight.get('flight_number') not in (None, '-', 'One-way') else ''
                    )
                    hotel_str = (
                        f"hotel: {hotel.get('name','')} ({hotel.get('area','')})"
                        if hotel.get('name') not in (None, '-', 'No hotel selected', 'No hotel match') else ''
                    )
                    print(
                        f"  Option {i}: {outbound.get('flight_number','')} "
                        f"{outbound.get('departure_time','')[:10]} "
                        f"{outbound.get('origin','')}->{outbound.get('destination','')} "
                        f"{outbound.get('price','')} "
                        + ret_str + hotel_str
                    )
            elif not summary:
                print('No matching options found.')

            # Keep history for the next turn.
            chat_history.append({"role": "user", "content": user_input})
            chat_history.append({"role": "assistant", "content": summary or "Search completed."})

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    # This will be called from main.py
    pass