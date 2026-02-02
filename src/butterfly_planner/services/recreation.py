"""
Recreation.gov API integration for campground data.

API docs: https://ridb.recreation.gov/docs
Requires API key: RECREATION_GOV_API_KEY env var

Example:
    from butterfly_planner.services import recreation
    camps = recreation.search_facilities(lat=45.5, lon=-122.6, radius=50)
"""

RIDB_API = "https://ridb.recreation.gov/api/v1"

# TODO: Implement facility search and details
