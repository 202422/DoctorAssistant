import json
from langchain_core.tools import Tool

from src.doctor_assistant.tools.coordinates_finder import get_coordinates_batch
from src.doctor_assistant.tools.distance_computer import street_distance_osrm



non_mcp_tools = [
    Tool(name="get_coordinates_batch", 
        func=get_coordinates_batch,
        description=(
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
    )),

    Tool(name="street_distance_osrm",
        func=street_distance_osrm,
        description=(
        """
    Compute street network distance between two points using OSRM.

    Parameters:
        lon1 (float): Origin longitude
        lat1 (float): Origin latitude
        lon2 (float): Destination longitude
        lat2 (float): Destination latitude
        profile (str): Routing profile ("driving", "walking", "cycling")

    Returns:
        float: Distance in kilometers
    """))  
]