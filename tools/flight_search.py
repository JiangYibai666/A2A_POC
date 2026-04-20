import json
from typing import List, Optional, Type

from langchain.tools import BaseTool
from pathlib import Path
from pydantic import BaseModel, Field


class FlightSearchInput(BaseModel):
    origin_candidates: List[str] = Field(
        description="List of origin IATA airport codes, for example ['SIN'] or ['BKK']"
    )
    destination_candidates: List[str] = Field(
        description="List of destination IATA airport codes, for example ['PEK', 'SHA', 'HKG']; may contain multiple candidates"
    )
    departure_date: str = Field(description="Departure date in YYYY-MM-DD format")
    return_date: Optional[str] = Field(
        default=None, description="Return date in YYYY-MM-DD format; omit for one-way trips"
    )


class FlightSearchTool(BaseTool):
    name: str = "search_flights"
    description: str = (
        "Search flights in the mock dataset. Supports multi-airport candidate matching "
        "such as PEK/SHA/HKG for a country-level destination. Requires origin and destination "
        "IATA candidate lists plus a departure date."
    )
    args_schema: Type[BaseModel] = FlightSearchInput

    def _run(
        self,
        origin_candidates: List[str],
        destination_candidates: List[str],
        departure_date: str,
        return_date: Optional[str] = None,
    ) -> str:
        try:
            origin_set = {c.upper() for c in origin_candidates}
            destination_set = {c.upper() for c in destination_candidates}

            data_path = Path(__file__).resolve().parents[1] / "mock_data" / "flights.json"
            with open(data_path, "r", encoding="utf-8") as f:
                flights = json.load(f)

            outbound = [
                flight for flight in flights
                if flight["origin"].upper() in origin_set
                and flight["destination"].upper() in destination_set
                and flight["departure_time"].startswith(departure_date)
            ]
            return_flights: List = []
            if return_date:
                return_flights = [
                    flight for flight in flights
                    if flight["origin"].upper() in destination_set
                    and flight["destination"].upper() in origin_set
                    and flight["departure_time"].startswith(return_date)
                ]

            return json.dumps(
                {"outbound": outbound[:5], "return": return_flights[:5]},
                ensure_ascii=False,
            )
        except Exception as e:
            return json.dumps({"error": str(e), "outbound": [], "return": []})

    async def _arun(
        self,
        origin_candidates: List[str],
        destination_candidates: List[str],
        departure_date: str,
        return_date: Optional[str] = None,
    ) -> str:
        return self._run(
            origin_candidates, destination_candidates, departure_date, return_date
        )