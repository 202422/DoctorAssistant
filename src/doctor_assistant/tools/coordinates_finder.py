import requests
import time
from typing import List, Dict, Optional, Tuple, Union
from langchain_core.tools import Tool

# ====================== SINGLE LOCATION (unchanged) ======================
def get_coordinates(
    place: str, 
    city: str, 
    country: str
) -> Tuple[Optional[float], Optional[float]]:
    """
    Get lat/lon for ONE location using Nominatim.
    """
    query = f"{place}, {city}, {country}"
    
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": query, "format": "json", "limit": 1}
    
    headers = {
        "User-Agent": "Harold COMPAORE"   # ← CHANGE THIS!
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
        else:
            print(f"No results for: {query}")
            return None, None
    except Exception as e:
        print(f"Error for {query}: {e}")
        return None, None


# ====================== BATCH / MULTIPLE LOCATIONS ======================
def get_coordinates_batch(
    locations: List[Dict[str, str]]
) -> List[Dict[str, str]]:
    """
    Get coordinates for MULTIPLE locations at once.
    
    Input example:
    locations = [
        {"place": "Clinique Ghandi", "city": "Casablanca", "country": "Morocco"},
        {"place": "Eiffel Tower",    "city": "Paris",      "country": "France"},
        {"place": "Burj Khalifa",    "city": "Dubai",      "country": "UAE"}
    ]
    
    Returns the same list with added "lat" and "lon" keys.
    Automatically waits 1.1 seconds between requests (Nominatim policy).
    """
    results = []
    
    for i, loc in enumerate(locations):
        place = loc.get("place", "")
        city = loc.get("city", "")
        country = loc.get("country", "")
        
        lat, lon = get_coordinates(place, city, country)
        
        # Add coordinates to a copy of the original dict
        result = loc.copy()
        result["lat"] = lat
        result["lon"] = lon
        results.append(result)
        
        # Respect Nominatim rate limit (max 1 request per second)
        if i < len(locations) - 1:   # no sleep after the last request
            time.sleep(1.1)
    
    return results


# =========================== USAGE EXAMPLES ===========================
if __name__ == "__main__":
    # 1. Single location (still works exactly as before)
    lat, lon = get_coordinates("Clinique Ghandi", "Casablanca", "Morocco")
    print(f"Single → {lat}, {lon}")
    
    # 2. Multiple locations (new batch mode)
    locations = [
        {"place": "Clinique Ghandi", "city": "Casablanca", "country": "Morocco"},
        {"place": "Eiffel Tower",    "city": "Paris",      "country": "France"},
        {"place": "Burj Khalifa",    "city": "Dubai",      "country": "UAE"},
        {"place": "Statue of Liberty", "city": "New York", "country": "USA"}
    ]
    
    results = get_coordinates_batch(locations)
    
    for r in results:
        print(f"{r['place']}, {r['city']}, {r['country']} → {r['lat']}, {r['lon']}")

