import json
from langchain_core.tools import StructuredTool, StructuredTool, Tool

from src.doctor_assistant.tools.coordinates_finder import get_coordinates_batch
from src.doctor_assistant.tools.distance_computer import StreetDistanceInput, street_distance_osrm



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
StructuredTool.from_function(
    func=street_distance_osrm,
    name="street_distance_osrm",
    description=(
        "Calculate the real street distance in kilometers between two GPS coordinates "
        "using OSRM. Provide lon1/lat1 (origin) and lon2/lat2 (destination), "
        "and a travel profile: 'driving', 'walking', or 'cycling'."
    ),
    args_schema=StreetDistanceInput,
)
]
