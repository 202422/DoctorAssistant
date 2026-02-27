import json
import time
from typing import List, Dict, Any, Union

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, field_validator
import requests

import re
from openlocationcode import openlocationcode as olc


# Detect Open Location Code (Plus Code) — no $ anchor so compound addresses like "H9X2+7W9, Av. de Nice" are caught
PLUS_CODE_PATTERN = r'^[23456789CFGHJMPQRVWX]{4,}\+[23456789CFGHJMPQRVWX]{2,}(?:[,\s]|$)'

def is_plus_code(text: str) -> bool:
    """Return True if the text looks like a Plus Code (pure or compound)."""
    if not text:
        return False
    return re.match(PLUS_CODE_PATTERN, text.strip().upper()) is not None


def resolve_plus_code(plus_code: str, city: str, country: str) -> tuple[float | None, float | None]:
    """
    Resolve a Plus Code (pure or compound like 'H9X2+7W9, Av. de Nice')
    using locality reference.
    """
    # Extract pure Plus Code from compound strings
    code_match = re.match(r'^([23456789CFGHJMPQRVWX]{4,}\+[23456789CFGHJMPQRVWX]{2,})', plus_code.strip().upper())
    if not code_match:
        return None, None
    pure_code = code_match.group(1)

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

        # Recover full code using locality anchor — pass pure_code, not the compound string
        full_code = olc.recoverNearest(pure_code, ref_lat, ref_lon)
        decoded   = olc.decode(full_code)

        return decoded.latitudeCenter, decoded.longitudeCenter

    except Exception:
        return None, None
    
# ====================== SINGLE LOCATION ======================
import requests

def get_coordinates(place: str, city: str, country: str) -> tuple[float | None, float | None]:
    """
    Get lat/lon for ONE location using:
    - Plus Code decoding (if detected)
    - Nominatim geocoding otherwise
    """

    print(f"Getting coordinates for: place='{place}', city='{city}', country='{country}'")

    # ---------------------------
    # CASE 1 — PLUS CODE INPUT
    # ---------------------------
    if is_plus_code(place):
        print(f"Detected Plus Code: {place}")
        return resolve_plus_code(place, city, country)

    # ---------------------------
    # CASE 2 — NORMAL ADDRESS
    # ---------------------------
    # Avoid duplicating city/country if already in place
    parts = [p for p in [place, city, country] if p]  # only include non-empty
    query = ", ".join(parts)

    print(f"Geocoding: {query}")

    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": query, "format": "json", "limit": 1}

    headers = {"User-Agent": "Harold COMPAORE"}

    print(f"params: {params}")

    

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
        else:
            return None, None

    except Exception as e:
        print(f"Geocoding error: {e}")
        return None, None
    
    
class LocationInput(BaseModel):
    place: str = Field(..., description="Street or place name")
    city: str = Field(..., description="City name")
    country: str = Field(..., description="Country name")

# ====================== BATCH / MULTIPLE LOCATIONS ======================
class CoordinatesBatchInput(BaseModel):
    locations: List[LocationInput] = Field(
        ...,
        description="List of places. Can be simple strings or dicts with 'place', 'city', 'country' keys."
    )

def get_coordinates_batch(
    locations: Union[str, Dict[str, Any], List[Union[str, Dict[str, str]]]]
) -> List[Dict[str, Any]]:
    """
    Get coordinates for multiple locations.

    Accepts:
    - Wrapped dict:            {"locations": [{"place": "...", "city": "...", "country": "..."}]}
    - Single dict:             {"place": "...", "city": "...", "country": "..."}
    - List of dicts:           [{"place": "Clinique Ghandi", "city": "Casablanca", "country": "Morocco"}, ...]
    - List of strings:         ["Clinique Ghandi, Casablanca, Morocco", ...]
    - Semicolon-separated str: "Place A, City, Country; Place B, City, Country"

    Returns list of dicts with added "lat" and "lon".
    """

    # ------------------------------------------------------------------ #
    # STEP 1 — Normalise top-level input into a flat list                 #
    # ------------------------------------------------------------------ #
    if isinstance(locations, dict):
        if "locations" in locations:
            # Wrapped dict: {"locations": [...]}
            locations = locations["locations"]
        else:
            # Bare single dict: {"place": "...", "city": "...", "country": "..."}
            locations = [locations]

    elif isinstance(locations, str):
        # Semicolon-separated string
        locations = [loc.strip() for loc in locations.split(";") if loc.strip()]

    if not isinstance(locations, list):
        raise TypeError(f"Unsupported input type: {type(locations)}")

    print(f"Locations to process: {locations}")

    # ------------------------------------------------------------------ #
    # STEP 2 — Normalise every item to {"place", "city", "country"}       #
    # ------------------------------------------------------------------ #
    normalized = []

    for item in locations:

        if isinstance(item, str):
            match = re.match(r"place='(.*?)'\s+city='(.*?)'\s+country='(.*?)'", item)
            if match:
                place, city, country = match.groups()
            else:
                parts = [p.strip() for p in item.rsplit(",", 2)]
                place, city, country = parts if len(parts) == 3 else (item, "", "")

        else:
            # Handles: plain dict, Pydantic v1 (.dict()), Pydantic v2 (.model_dump()), dataclasses (vars())
            if hasattr(item, "model_dump"):
                item = item.model_dump()       # Pydantic v2
            elif hasattr(item, "dict"):
                item = item.dict()             # Pydantic v1
            elif not isinstance(item, dict):
                item = vars(item)              # dataclass / plain object fallback

            place   = item.get("place") or item.get("name") or str(item)
            city    = item.get("city", "")
            country = item.get("country", "")

            if (not city or not country) and "," in place:
                parts = [p.strip() for p in place.rsplit(",", 2)]
                if len(parts) == 3:
                    place, city, country = parts

        normalized.append({"place": place, "city": city, "country": country})

    # ------------------------------------------------------------------ #
    # STEP 3 — Geocode: single item skips the rate-limit sleep            #
    # ------------------------------------------------------------------ #
    results  = []
    is_batch = len(normalized) > 1

    for i, loc in enumerate(normalized):
        lat, lon = get_coordinates(loc["place"], loc["city"], loc["country"])
        results.append({**loc, "lat": lat, "lon": lon})

        # Respect geocoder rate limit only between batch calls
        if is_batch and i < len(normalized) - 1:
            time.sleep(1.1)

    return results


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