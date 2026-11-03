"""Forecast locations and their geographic bounds.

Each ``Location`` holds everything the fetch and build steps need to produce
one site: the observation search box, the weather point, the timezone, and
the map view. ``LOCATIONS`` is the registry; ``DEFAULT_LOCATION`` is the one
published at the site root.
"""

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

    def as_dict(self) -> dict[str, float]:
        """Return the box as iNaturalist ``swlat``/``swlng``/``nelat``/``nelng`` params."""
        return {"swlat": self.swlat, "swlng": self.swlng, "nelat": self.nelat, "nelng": self.nelng}

    def contains(self, lat: float, lon: float) -> bool:
        """Return True if the point lies inside the box, edges included."""
        return self.swlat <= lat <= self.nelat and self.swlng <= lon <= self.nelng

    @property
    def center(self) -> tuple[float, float]:
        """Midpoint of the box as (lat, lon)."""
        return ((self.swlat + self.nelat) / 2, (self.swlng + self.nelng) / 2)

    @property
    def leaflet_bounds(self) -> list[list[float]]:
        """Corners in Leaflet's ``[[south, west], [north, east]]`` order."""
        return [[self.swlat, self.swlng], [self.nelat, self.nelng]]


@dataclass(frozen=True)
class PointOfInterest:
    """A named place drawn as a marker on the sightings map."""

    name: str
    lat: float
    lon: float
    url: str = ""


@dataclass(frozen=True)
class Location:
    """One forecast area, published as its own static site.

    ``lat``/``lon`` is the single point used for weather and GDD requests.
    ``bbox`` bounds the iNaturalist observation search. ``site_subdir`` is
    the folder under the site root; an empty string means the root itself.
    """

    slug: str
    name: str
    region_label: str
    lat: float
    lon: float
    bbox: BoundingBox
    timezone: str
    map_center: tuple[float, float]
    map_zoom: int
    site_subdir: str
    points_of_interest: tuple[PointOfInterest, ...] = ()


PORTLAND = Location(
    slug="portland",
    name="Portland, OR",
    region_label="NW Oregon / SW Washington",
    lat=45.5,
    lon=-122.6,
    bbox=BoundingBox(swlat=44.5, swlng=-124.2, nelat=46.5, nelng=-121.5),
    timezone="America/Los_Angeles",
    map_center=(45.5, -122.8),
    map_zoom=8,
    site_subdir="",
)

LOCATIONS: dict[str, Location] = {loc.slug: loc for loc in (PORTLAND,)}

DEFAULT_LOCATION = PORTLAND


def get_location(slug: str) -> Location:
    """Return the registered location for ``slug``.

    Raises:
        KeyError: If the slug is unknown. The message lists the valid slugs.
    """
    try:
        return LOCATIONS[slug]
    except KeyError:
        valid = ", ".join(sorted(LOCATIONS))
        raise KeyError(f"Unknown location {slug!r}; valid locations: {valid}") from None


# Single-region aliases kept for existing callers until they take a Location.
TARGET_REGION_BBOX = PORTLAND.bbox
TARGET_REGION_PARAMS = TARGET_REGION_BBOX.as_query_params()
