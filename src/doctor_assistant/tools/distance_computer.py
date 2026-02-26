import requests
from typing import Literal


def street_distance_osrm(
    lon1: float,
    lat1: float,
    lon2: float,
    lat2: float,
    profile: Literal["driving", "walking", "cycling"],
) -> float:
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
    """

    url: str = (
        f"http://router.project-osrm.org/route/v1/"
        f"{profile}/{lon1},{lat1};{lon2},{lat2}"
    )

    response: requests.Response = requests.get(url, timeout=10)
    response.raise_for_status()

    data: dict = response.json()

    distance_meters: float = data["routes"][0]["distance"]
    return distance_meters / 1000.0
