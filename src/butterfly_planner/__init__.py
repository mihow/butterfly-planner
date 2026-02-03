"""
Butterfly Planner - GIS layers for butterfly abundance and species diversity forecasting.

This package helps create GIS layers to indicate butterfly abundance and species
diversity by general location by week of the year, focusing on Oregon and Washington.
"""

__version__ = "0.1.0"
__author__ = "Michael Howden"

from butterfly_planner.config import Settings
from butterfly_planner.schemas import Example

__all__ = ["Example", "Settings", "__version__"]
