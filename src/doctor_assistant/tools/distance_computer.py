import requests
from typing import Literal

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field


# =========================== PYDANTIC SCHEMA ===========================
class StreetDistanceInput(BaseModel):
    lon1: float = Field(..., description="Longitude of the starting point")
    lat1: float = Field(..., description="Latitude of the starting point")
    lon2: float = Field(..., description="Longitude of the destination point")
    lat2: float = Field(..., description="Latitude of the destination point")
    profile: Literal["driving", "walking", "cycling"] = Field(
        ..., description="Travel mode: 'driving', 'walking', or 'cycling'"
    )


# =========================== CORE FUNCTION ===========================
def street_distance_osrm(
    lon1: float,
    lat1: float,
    lon2: float,
    lat2: float,
    profile: Literal["driving", "walking", "cycling"],
) -> float:
    """Calculate real street distance (in km) between two GPS points using OSRM."""

    url: str = (
        f"http://router.project-osrm.org/route/v1/"
        f"{profile}/{lon1},{lat1};{lon2},{lat2}"
    )

    response: requests.Response = requests.get(url, timeout=10)
    response.raise_for_status()

    data: dict = response.json()

    distance_meters: float = data["routes"][0]["distance"]
    return distance_meters / 1000.0


# =========================== TOOL REGISTRATION ===========================
