"""
Routing and isochrone (drive-time) analysis.

Uses OpenRouteService: https://openrouteservice.org/
Free tier: 2000 requests/day
Requires API key: OPENROUTESERVICE_API_KEY env var

Example:
    from butterfly_planner.services import routing
    isochrone = routing.get_isochrone(lat=45.5, lon=-122.6, minutes=120)
"""

ORS_API = "https://api.openrouteservice.org/v2"

# TODO: Implement isochrone and directions
