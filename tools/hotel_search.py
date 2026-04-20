import json
from datetime import datetime, timedelta
from typing import Optional, Type

from langchain.tools import BaseTool
from pathlib import Path
from pydantic import BaseModel, Field


class HotelSearchInput(BaseModel):
    city: str = Field(
        description="Destination IATA city or airport code, such as 'SHA', 'PEK', 'HKG', or 'BKK'"
    )
    arrive_time: str = Field(
        description="Flight arrival time in ISO8601 format with timezone; used to infer earliest hotel check-in"
    )
    depart_time: str = Field(
        description="Return flight departure time in ISO8601 format with timezone; used to infer latest hotel checkout"
    )
    checkin_window_hours: int = Field(
        default=3, description="Maximum allowed wait time after arrival before hotel check-in, default 3 hours"
    )
    checkout_buffer_hours: int = Field(
        default=1, description="Minimum number of hours required between hotel checkout and return departure, default 1 hour"
    )


class HotelSearchTool(BaseTool):
    name: str = "search_hotels"
    description: str = (
        "Search hotels in the mock dataset. Filters by destination city code and finds hotels "
        "whose check-in and checkout windows fit the flight arrival and return departure times."
    )
    args_schema: Type[BaseModel] = HotelSearchInput

    def _run(
        self,
        city: str,
        arrive_time: str,
        depart_time: str,
        checkin_window_hours: int = 3,
        checkout_buffer_hours: int = 1,
    ) -> str:
        try:
            data_path = Path(__file__).resolve().parents[1] / "mock_data" / "hotels.json"
            with open(data_path, "r", encoding="utf-8") as f:
                hotels = json.load(f)

            arrive_dt = datetime.fromisoformat(arrive_time)
            depart_dt = datetime.fromisoformat(depart_time)

            filtered = []
            for hotel in hotels:
                # City match is mandatory before time-window filtering.
                if hotel.get("city", "").upper() != city.upper():
                    continue
                checkin = datetime.fromisoformat(hotel["checkin_time"])
                checkout = datetime.fromisoformat(hotel["checkout_time"])
                if checkin > arrive_dt + timedelta(hours=checkin_window_hours):
                    continue
                if checkout > depart_dt - timedelta(hours=checkout_buffer_hours):
                    continue
                filtered.append(hotel)

            return json.dumps(filtered[:5], ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})

    async def _arun(
        self,
        city: str,
        arrive_time: str,
        depart_time: str,
        checkin_window_hours: int = 3,
        checkout_buffer_hours: int = 1,
    ) -> str:
        return self._run(
            city, arrive_time, depart_time, checkin_window_hours, checkout_buffer_hours
        )