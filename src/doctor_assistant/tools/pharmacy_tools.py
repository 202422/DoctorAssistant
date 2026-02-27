from langchain_core.tools import StructuredTool

from src.doctor_assistant.tools.coordinates_finder import (
    get_coordinates_batch,
    CoordinatesBatchInput,
)

from src.doctor_assistant.tools.distance_computer import (
    StreetDistanceInput,
    street_distance_osrm,
)


non_mcp_tools = [

    StructuredTool.from_function(
        func=get_coordinates_batch,
        name="get_coordinates_batch",
        description=(
               "Get coordinates for MULTIPLE locations.\n\n"
        "You MUST pass a JSON array of objects under the 'locations' key.\n"
        "Each object MUST have exactly three fields: 'place', 'city', 'country'.\n"
        "Do NOT combine city or country into 'place'.\n\n"
        "Example:\n"
        '{\n'
        '  "locations": [\n'
        '    {"place": "1 Rue des Hôpitaux", "city": "Casablanca", "country": "Morocco"},\n'
        '    {"place": "Eiffel Tower", "city": "Paris", "country": "France"}\n'
        '  ]\n'
        '}'
        ),
        args_schema=CoordinatesBatchInput,
    ),

    StructuredTool.from_function(
        func=street_distance_osrm,
        name="street_distance_osrm",
        description=(
            "Calculate the real street distance in kilometers between two GPS coordinates "
            "using OSRM. Provide lon1/lat1 (origin) and lon2/lat2 (destination), "
            "and a travel profile: 'driving', 'walking', or 'cycling'."
        ),
        args_schema=StreetDistanceInput,
    ),
]