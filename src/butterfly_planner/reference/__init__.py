"""Static butterfly-related constants.

Reference data that doesn't change with API calls: viewing thresholds,
geographic bounds, species taxonomy constants.

Adding a new module:
1. Create ``reference/{name}.py`` with constants/dataclasses
2. Re-export from this ``__init__.py``
"""

from butterfly_planner.reference.geography import BISBEE as BISBEE
from butterfly_planner.reference.geography import DEFAULT_LOCATION as DEFAULT_LOCATION
from butterfly_planner.reference.geography import LOCATIONS as LOCATIONS
from butterfly_planner.reference.geography import PORTLAND as PORTLAND
from butterfly_planner.reference.geography import BoundingBox as BoundingBox
from butterfly_planner.reference.geography import Location as Location
from butterfly_planner.reference.geography import PointOfInterest as PointOfInterest
from butterfly_planner.reference.geography import get_location as get_location
from butterfly_planner.reference.viewing import MIN_GOOD_SUNSHINE_HOURS as MIN_GOOD_SUNSHINE_HOURS
from butterfly_planner.reference.viewing import MIN_GOOD_SUNSHINE_PCT as MIN_GOOD_SUNSHINE_PCT
