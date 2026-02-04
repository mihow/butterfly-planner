"""
Domain models for butterfly planner.

Pydantic models for data from external APIs and internal processing.
These define the canonical schema - services normalize API responses to these.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

# =============================================================================
# Core (used by existing code in core.py)
# =============================================================================


class Status(StrEnum):
    """Status enum for tracking item state."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Example(BaseModel):
    """Placeholder model - replace with domain models."""

    model_config = {"str_strip_whitespace": True}

    id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="Display name")
    status: Status = Field(default=Status.PENDING)
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, str] = Field(default_factory=dict)


class Result(BaseModel):
    """Generic result wrapper for operations."""

    success: bool
    message: str
    data: dict[str, Any] | None = None
    error: str | None = None


# =============================================================================
# Taxonomy
# =============================================================================


class TaxonRank(StrEnum):
    """Taxonomic rank levels."""

    ORDER = "order"
    FAMILY = "family"
    SUBFAMILY = "subfamily"
    TRIBE = "tribe"
    GENUS = "genus"
    SPECIES = "species"
    SUBSPECIES = "subspecies"


class Taxon(BaseModel):
    """A taxonomic entity (species, genus, etc)."""

    id: int = Field(..., description="Source taxon ID")
    source: str = Field(..., description="Data source (inat, gbif)")
    scientific_name: str
    common_name: str | None = None
    rank: TaxonRank = TaxonRank.SPECIES
    family: str | None = None
    genus: str | None = None
    is_active: bool = True


# =============================================================================
# Observations
# =============================================================================


class QualityGrade(StrEnum):
    """Observation verification level."""

    RESEARCH = "research"
    NEEDS_ID = "needs_id"
    CASUAL = "casual"


class Location(BaseModel):
    """Geographic point with optional uncertainty."""

    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    uncertainty_m: float | None = None
    place_name: str | None = None


class Observation(BaseModel):
    """A butterfly observation record, normalized across sources."""

    id: str = Field(..., description="Source observation ID")
    source: str = Field(..., description="Data source (inat, gbif)")
    taxon_id: int
    scientific_name: str
    common_name: str | None = None
    location: Location
    observed_on: date
    quality_grade: QualityGrade = QualityGrade.CASUAL
    observer: str | None = None
    url: str | None = None
    photos: list[str] = Field(default_factory=list)

    @property
    def week_of_year(self) -> int:
        """ISO week number (1-53)."""
        return self.observed_on.isocalendar()[1]


# =============================================================================
# Geographic
# =============================================================================


class BoundingBox(BaseModel):
    """Geographic bounding box for spatial queries."""

    south: float = Field(..., ge=-90, le=90)
    west: float = Field(..., ge=-180, le=180)
    north: float = Field(..., ge=-90, le=90)
    east: float = Field(..., ge=-180, le=180)

    @classmethod
    def oregon_washington(cls) -> BoundingBox:
        """Default bbox for OR/WA region."""
        return cls(south=41.99, west=-124.57, north=49.0, east=-116.46)


# =============================================================================
# Weather
# =============================================================================


class DailyForecast(BaseModel):
    """Single day weather forecast."""

    date: date
    temp_high_c: float
    temp_low_c: float
    precip_mm: float
    conditions: str | None = None


class Forecast(BaseModel):
    """Multi-day weather forecast for a location."""

    location: Location
    fetched_at: datetime = Field(default_factory=datetime.now)
    daily: list[DailyForecast] = Field(default_factory=list)


# =============================================================================
# Recreation
# =============================================================================


class Campground(BaseModel):
    """A campground or recreation facility."""

    id: str
    name: str
    location: Location
    facility_type: str | None = None
    reservable: bool = False
    url: str | None = None
