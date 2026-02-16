"""Geographic bounds for the target observation region."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BoundingBox:
    """SW/NE lat-lon bounding box."""

    swlat: float
    swlng: float
    nelat: float
    nelng: float

    def as_query_params(self) -> str:
        """Return URL query string fragment (no leading &)."""
        return f"swlat={self.swlat}&swlng={self.swlng}&nelat={self.nelat}&nelng={self.nelng}"


# NW Oregon / SW Washington target region
TARGET_REGION_BBOX = BoundingBox(swlat=44.5, swlng=-124.2, nelat=46.5, nelng=-121.5)

# Pre-built query string for iNaturalist URLs
TARGET_REGION_PARAMS = TARGET_REGION_BBOX.as_query_params()
