"""Static butterfly-related constants.

Reference data that doesn't change with API calls: viewing thresholds,
geographic bounds, species taxonomy constants.

Adding a new module:
1. Create ``reference/{name}.py`` with constants/dataclasses
2. Re-export from this ``__init__.py``
"""

from butterfly_planner.reference.geography import TARGET_REGION_BBOX as TARGET_REGION_BBOX
from butterfly_planner.reference.geography import TARGET_REGION_PARAMS as TARGET_REGION_PARAMS
from butterfly_planner.reference.geography import BoundingBox as BoundingBox
from butterfly_planner.reference.viewing import MIN_GOOD_SUNSHINE_HOURS as MIN_GOOD_SUNSHINE_HOURS
from butterfly_planner.reference.viewing import MIN_GOOD_SUNSHINE_PCT as MIN_GOOD_SUNSHINE_PCT
