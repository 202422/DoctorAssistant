import json
import time
from typing import List, Dict, Any, Union

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, field_validator
import requests

import re
from openlocationcode import openlocationcode as olc


# Detect Open Location Code (Plus Code)
PLUS_CODE_PATTERN = r'^[23456789CFGHJMPQRVWX]{4,}\+[23456789CFGHJMPQRVWX]{2,}$'


def is_plus_code(text: str) -> bool:
    """Return True if the text looks like a Plus Code."""
    if not text:
        return False
    return re.match(PLUS_CODE_PATTERN, text.strip().upper()) is not None



def resolve_plus_code(plus_code: str, city: str, country: str) -> tuple[float | None, float | None]:
    """
    Resolve a short Plus Code using locality reference.
    """
    if not city and not country:
        raise ValueError("Short Plus Code requires at least a city or country.")

    reference_query = f"{city}, {country}".strip(", ")

    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": reference_query, "format": "json", "limit": 1}
    headers = {"User-Agent": "Harold COMPAORE"}

    try:
        ref_resp = requests.get(url, params=params, headers=headers, timeout=10)
        ref_resp.raise_for_status()
        ref_data = ref_resp.json()

        if not ref_data:
            return None, None

        ref_lat = float(ref_data[0]["lat"])
        ref_lon = float(ref_data[0]["lon"])

        # Recover full code using locality anchor
        full_code = olc.recoverNearest(plus_code, ref_lat, ref_lon)

        decoded = olc.decode(full_code)

        return decoded.latitudeCenter, decoded.longitudeCenter

    except Exception:
        return None, None

# ====================== SINGLE LOCATION ======================
def get_coordinates(place: str, city: str, country: str) -> tuple[float | None, float | None]:
    """
    Get lat/lon for ONE location using:
    - Plus Code decoding (if detected)
    - Nominatim geocoding otherwise
    """

    # ---------------------------
    # CASE 1 — PLUS CODE INPUT
    # ---------------------------
    if is_plus_code(place):
        print(f"Detected Plus Code: {place}")
        return resolve_plus_code(place, city, country)

    # ---------------------------
    # CASE 2 — NORMAL ADDRESS
    # ---------------------------
    query = ", ".join(p for p in [place, city, country] if p)

    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": query, "format": "json", "limit": 1}

    headers = {"User-Agent": "Harold COMPAORE"}

    print(f"Geocoding: {query}")

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
        else:
            return None, None

    except Exception:
        return None, None


# ====================== BATCH / MULTIPLE LOCATIONS ======================
class CoordinatesBatchInput(BaseModel):
    locations: List[Union[str, Dict[str, str]]] = Field(
        ...,
        description="List of places. Can be simple strings or dicts with 'place', 'city', 'country' keys."
    )

    @field_validator("locations", mode="before")
    @classmethod
    def normalize_locations(cls, v):
        # FIX #1 (Pydantic layer): Handle raw semicolon-separated string from LLM
        if isinstance(v, str):
            return [loc.strip() for loc in v.split(";") if loc.strip()]
        return v


def get_coordinates_batch(locations: List[Union[str, Dict[str, str]]]) -> List[Dict[str, Any]]:
    """
    Get coordinates for multiple locations.
    
    Accepts:
    - List of strings: ["Clinique Ghandi, Casablanca, Morocco", "Eiffel Tower, Paris, France"]
    - List of dicts: [{"place": "Clinique Ghandi", "city": "Casablanca", "country": "Morocco"}, ...]
    - Semicolon-separated string: "Place A, City, Country; Place B, City, Country"
    
    Returns list of dicts with added "lat" and "lon".
    """
    # FIX #1 (function layer): Guard in case StructuredTool bypasses Pydantic validation
    if isinstance(locations, str):
        locations = [loc.strip() for loc in locations.split(";") if loc.strip()]

    normalized = []
    print(f"Processing these batches: {locations}")

    for item in locations:
        if isinstance(item, str):
            # FIX #2: Use rsplit with max 2 splits (from the right) so place names
            # containing commas (e.g. "Café de la Paix, Paris, France") are handled correctly.
            parts = [p.strip() for p in item.rsplit(",", 2)]
            if len(parts) == 3:
                normalized.append({
                    "place": parts[0],
                    "city": parts[1],
                    "country": parts[2]
                })
            else:
                normalized.append({"place": item, "city": "", "country": ""})
        elif isinstance(item, dict):
            normalized.append({
                "place": item.get("place") or item.get("name") or str(item),
                "city": item.get("city", ""),
                "country": item.get("country", "")
            })
        else:
            normalized.append({"place": str(item), "city": "", "country": ""})

    results = []

    for i, loc in enumerate(normalized):
        place = loc.get("place", "")
        city = loc.get("city", "")
        country = loc.get("country", "")
        
        lat, lon = get_coordinates(place, city, country)
        
        result = loc.copy()
        result["lat"] = lat
        result["lon"] = lon
        results.append(result)
        
        # Respect Nominatim rate limit (1 req/sec)
        if i < len(normalized) - 1:
            time.sleep(1.1)
    
    return results


# =========================== TOOL REGISTRATION ===========================
coordinates_batch_tool = StructuredTool.from_function(
    func=get_coordinates_batch,
    name="get_coordinates_batch",
    description=(
        "Get latitude/longitude coordinates for one or more places. "
        "Input must be a JSON list of strings (e.g. ['Place, City, Country', ...]) "
        "or a list of dicts with 'place', 'city', 'country' keys. "
        "Always use this when you have place names and need GPS coordinates."
    ),
    args_schema=CoordinatesBatchInput,
)


# =========================== USAGE EXAMPLES ===========================
if __name__ == "__main__":
    # 1. Single location
    lat, lon = get_coordinates("Clinique Ghandi", "Casablanca", "Morocco")
    print(f"Single → {lat}, {lon}")
    
    # 2. Batch with mixed input types
    locations = [
        "Clinique Ghandi, Casablanca, Morocco",
        {"place": "Eiffel Tower", "city": "Paris", "country": "France"},
        "Burj Khalifa, Dubai, UAE",
        "Café de la Paix, Paris, France",   # name with comma — handled by rsplit fix
    ]
    
    results = get_coordinates_batch(locations)
    
    for r in results:
        print(f"{r.get('place')} → {r.get('lat')}, {r.get('lon')}")