import math
import time
import requests
from typing import Literal, TypedDict
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


# =========================== RETURN TYPE ===========================
class DistanceResult(TypedDict):
    km: float
    source: Literal["osrm", "haversine"]


# =========================== HAVERSINE FALLBACK ===========================
def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6_371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# =========================== SINGLE DISTANCE ===========================
def street_distance_osrm(
    lon1: float, lat1: float,
    lon2: float, lat2: float,
    profile: Literal["driving", "walking", "cycling"] = "driving",
    timeout: int = 10,
) -> DistanceResult:
    """Single point-to-point distance. Falls back to haversine on failure."""
    try:
        url = f"http://router.project-osrm.org/route/v1/{profile}/{lon1},{lat1};{lon2},{lat2}"
        response = requests.get(url, timeout=timeout)
        if response.status_code == 429:
            raise requests.exceptions.RequestException("Rate limited")
        response.raise_for_status()
        meters = response.json()["routes"][0]["distance"]
        return DistanceResult(km=meters / 1000.0, source="osrm")
    except Exception as e:
        print(f"OSRM fallback ({e}) — using haversine")
        return DistanceResult(km=_haversine_km(lat1, lon1, lat2, lon2), source="haversine")


# =========================== BATCH DISTANCES (1 REQUEST) ===============
def street_distances_batch_osrm(
    origin_lat: float,
    origin_lon: float,
    destinations: list[dict],           # [{"lat": ..., "lon": ..., ...}, ...]
    profile: Literal["driving", "walking", "cycling"] = "driving",
    timeout: int = 15,
) -> list[DistanceResult]:
    """
    Compute distances from ONE origin to MANY destinations in a single OSRM call
    using the /table endpoint (returns a distance matrix).

    Falls back to haversine for all destinations if OSRM fails.
    """
    # Build coordinate string: origin first, then all destinations
    coords = f"{origin_lon},{origin_lat}"
    for d in destinations:
        coords += f";{d['lon']},{d['lat']}"

    # sources=0 means only compute distances FROM index 0 (the origin)
    url = (
        f"http://router.project-osrm.org/table/v1/{profile}/{coords}"
        f"?sources=0&annotations=distance"
    )

    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code == 429:
            raise requests.exceptions.RequestException("Rate limited")
        response.raise_for_status()

        data = response.json()
        # distances[0] = list of distances in meters from origin to each destination
        distances_m = data["distances"][0][1:]  # skip index 0 (origin → origin = 0)

        return [
            DistanceResult(km=d / 1000.0, source="osrm") if d is not None
            else DistanceResult(km=_haversine_km(origin_lat, origin_lon, dest["lat"], dest["lon"]), source="haversine")
            for d, dest in zip(distances_m, destinations)
        ]

    except Exception as e:
        print(f"OSRM batch fallback ({e}) — using haversine for all")
        return [
            DistanceResult(km=_haversine_km(origin_lat, origin_lon, d["lat"], d["lon"]), source="haversine")
            for d in destinations
        ]