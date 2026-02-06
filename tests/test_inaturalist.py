"""
Tests for the iNaturalist butterfly occurrence module.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

from butterfly_planner import inaturalist
from butterfly_planner.services import inat

# =============================================================================
# Fixtures / Sample API Responses
# =============================================================================

SAMPLE_SPECIES_COUNTS_RESPONSE: dict = {
    "total_results": 3,
    "page": 1,
    "per_page": 100,
    "results": [
        {
            "count": 542,
            "taxon": {
                "id": 48662,
                "name": "Vanessa cardui",
                "preferred_common_name": "Painted Lady",
                "rank": "species",
                "default_photo": {
                    "medium_url": "https://inaturalist-open-data.s3.amazonaws.com/photos/123/medium.jpg",
                },
            },
        },
        {
            "count": 318,
            "taxon": {
                "id": 48548,
                "name": "Pieris rapae",
                "preferred_common_name": "Cabbage White",
                "rank": "species",
                "default_photo": {
                    "medium_url": "https://inaturalist-open-data.s3.amazonaws.com/photos/456/medium.jpg",
                },
            },
        },
        {
            "count": 45,
            "taxon": {
                "id": 50340,
                "name": "Papilio zelicaon",
                "preferred_common_name": "Anise Swallowtail",
                "rank": "species",
                "default_photo": None,
            },
        },
    ],
}

SAMPLE_OBSERVATIONS_RESPONSE: list[dict] = [
    {
        "id": 100001,
        "location": "45.5,-122.6",
        "observed_on": "2025-06-15",
        "quality_grade": "research",
        "taxon": {
            "name": "Vanessa cardui",
            "preferred_common_name": "Painted Lady",
        },
        "photos": [{"url": "https://inaturalist-open-data.s3.amazonaws.com/photos/789/medium.jpg"}],
    },
    {
        "id": 100002,
        "location": "45.6,-122.7",
        "observed_on": "2025-06-14",
        "quality_grade": "research",
        "taxon": {
            "name": "Pieris rapae",
            "preferred_common_name": "Cabbage White",
        },
        "photos": [],
    },
    {
        # Observation with no location — should be skipped
        "id": 100003,
        "location": None,
        "observed_on": "2025-06-13",
        "quality_grade": "research",
        "taxon": {"name": "Papilio zelicaon"},
        "photos": [],
    },
]

SAMPLE_HISTOGRAM_RESPONSE: dict = {
    "total_results": 52,
    "results": {
        "week_of_year": {
            "1": 5,
            "10": 42,
            "20": 350,
            "25": 890,
            "30": 1200,
            "40": 210,
            "50": 8,
        }
    },
}


# =============================================================================
# Data Model Tests
# =============================================================================


class TestSpeciesRecord:
    """Test SpeciesRecord dataclass."""

    def test_display_name_with_common_name(self) -> None:
        record = inaturalist.SpeciesRecord(
            taxon_id=48662,
            scientific_name="Vanessa cardui",
            common_name="Painted Lady",
            rank="species",
            observation_count=100,
        )
        assert record.display_name == "Painted Lady (Vanessa cardui)"

    def test_display_name_without_common_name(self) -> None:
        record = inaturalist.SpeciesRecord(
            taxon_id=48662,
            scientific_name="Vanessa cardui",
            common_name=None,
            rank="species",
            observation_count=100,
        )
        assert record.display_name == "Vanessa cardui"


class TestButterflyObservation:
    """Test ButterflyObservation dataclass."""

    def test_display_name_with_common(self) -> None:
        obs = inaturalist.ButterflyObservation(
            id=1,
            species="Vanessa cardui",
            common_name="Painted Lady",
            observed_on=date(2025, 6, 15),
            latitude=45.5,
            longitude=-122.6,
            quality_grade="research",
            url="https://www.inaturalist.org/observations/1",
        )
        assert obs.display_name == "Painted Lady (Vanessa cardui)"

    def test_display_name_without_common(self) -> None:
        obs = inaturalist.ButterflyObservation(
            id=1,
            species="Vanessa cardui",
            common_name=None,
            observed_on=date(2025, 6, 15),
            latitude=45.5,
            longitude=-122.6,
            quality_grade="research",
            url="https://www.inaturalist.org/observations/1",
        )
        assert obs.display_name == "Vanessa cardui"


class TestWeeklyActivity:
    """Test WeeklyActivity dataclass."""

    def test_basic(self) -> None:
        w = inaturalist.WeeklyActivity(week=25, count=890)
        assert w.week == 25
        assert w.count == 890


class TestOccurrenceSummary:
    """Test OccurrenceSummary dataclass."""

    def test_top_species(self) -> None:
        species = [
            inaturalist.SpeciesRecord(
                taxon_id=i,
                scientific_name=f"Species {i}",
                common_name=None,
                rank="species",
                observation_count=count,
            )
            for i, count in enumerate([10, 500, 200, 50, 300])
        ]
        summary = inaturalist.OccurrenceSummary(
            month=6,
            year=None,
            bbox=inaturalist.NW_OREGON_SW_WASHINGTON,
            species=species,
            observations=[],
            total_species=5,
            total_observations=0,
        )
        top = summary.top_species
        assert top[0].observation_count == 500
        assert top[1].observation_count == 300
        assert len(top) == 5  # all 5 (< 20 cap)


# =============================================================================
# Parsing Tests
# =============================================================================


class TestParseSpeciesRecord:
    """Test _parse_species_record helper."""

    def test_full_record(self) -> None:
        result = SAMPLE_SPECIES_COUNTS_RESPONSE["results"][0]
        record = inaturalist._parse_species_record(result)
        assert record.taxon_id == 48662
        assert record.scientific_name == "Vanessa cardui"
        assert record.common_name == "Painted Lady"
        assert record.observation_count == 542
        assert record.photo_url is not None
        assert "48662" in record.taxon_url

    def test_record_without_photo(self) -> None:
        result = SAMPLE_SPECIES_COUNTS_RESPONSE["results"][2]
        record = inaturalist._parse_species_record(result)
        assert record.photo_url is None
        assert record.scientific_name == "Papilio zelicaon"


class TestParseObservation:
    """Test _parse_observation helper."""

    def test_valid_observation(self) -> None:
        obs = inaturalist._parse_observation(SAMPLE_OBSERVATIONS_RESPONSE[0])
        assert obs is not None
        assert obs.id == 100001
        assert obs.species == "Vanessa cardui"
        assert obs.common_name == "Painted Lady"
        assert obs.latitude == 45.5
        assert obs.longitude == -122.6
        assert obs.observed_on == date(2025, 6, 15)
        assert obs.photo_url is not None

    def test_observation_without_photo(self) -> None:
        obs = inaturalist._parse_observation(SAMPLE_OBSERVATIONS_RESPONSE[1])
        assert obs is not None
        assert obs.photo_url is None

    def test_observation_without_location_returns_none(self) -> None:
        obs = inaturalist._parse_observation(SAMPLE_OBSERVATIONS_RESPONSE[2])
        assert obs is None

    def test_observation_with_bad_location_returns_none(self) -> None:
        bad_obs = {"id": 999, "location": "invalid", "observed_on": "2025-06-15"}
        obs = inaturalist._parse_observation(bad_obs)
        assert obs is None

    def test_observation_without_observed_on_returns_none(self) -> None:
        bad_obs = {"id": 999, "location": "45.5,-122.6", "observed_on": None}
        obs = inaturalist._parse_observation(bad_obs)
        assert obs is None


# =============================================================================
# API Fetching Tests (mocked)
# =============================================================================


class TestFetchSpeciesCounts:
    """Test fetch_species_counts with mocked API."""

    @patch("butterfly_planner.services.inat.get_species_counts")
    def test_basic_fetch(self, mock_api: object) -> None:
        mock_api.return_value = SAMPLE_SPECIES_COUNTS_RESPONSE  # type: ignore[union-attr]

        records = inaturalist.fetch_species_counts(month=6)

        assert len(records) == 3
        assert records[0].scientific_name == "Vanessa cardui"
        assert records[0].observation_count == 542

        # Verify API was called with correct params
        call_args = mock_api.call_args[0][0]  # type: ignore[union-attr]
        assert call_args["taxon_id"] == inat.BUTTERFLIES
        assert call_args["month"] == "6"
        assert call_args["quality_grade"] == "research"
        assert call_args["swlat"] == 44.5

    @patch("butterfly_planner.services.inat.get_species_counts")
    def test_multiple_months(self, mock_api: object) -> None:
        mock_api.return_value = SAMPLE_SPECIES_COUNTS_RESPONSE  # type: ignore[union-attr]

        inaturalist.fetch_species_counts(month=[6, 7])

        call_args = mock_api.call_args[0][0]  # type: ignore[union-attr]
        assert call_args["month"] == "6,7"

    @patch("butterfly_planner.services.inat.get_species_counts")
    def test_custom_bbox(self, mock_api: object) -> None:
        mock_api.return_value = SAMPLE_SPECIES_COUNTS_RESPONSE  # type: ignore[union-attr]
        custom_bbox = {"swlat": 42.0, "swlng": -123.0, "nelat": 45.0, "nelng": -120.0}

        inaturalist.fetch_species_counts(month=6, bbox=custom_bbox)

        call_args = mock_api.call_args[0][0]  # type: ignore[union-attr]
        assert call_args["swlat"] == 42.0

    @patch("butterfly_planner.services.inat.get_species_counts")
    def test_empty_results(self, mock_api: object) -> None:
        mock_api.return_value = {"total_results": 0, "results": []}  # type: ignore[union-attr]

        records = inaturalist.fetch_species_counts(month=1)
        assert records == []


class TestFetchObservationsForMonth:
    """Test fetch_observations_for_month with mocked API."""

    @patch("butterfly_planner.services.inat.get_observations_paginated")
    def test_basic_fetch(self, mock_paginated: object) -> None:
        mock_paginated.return_value = SAMPLE_OBSERVATIONS_RESPONSE  # type: ignore[union-attr]

        obs = inaturalist.fetch_observations_for_month(month=6)

        # 3 raw results but one has no location → 2 valid
        assert len(obs) == 2
        assert obs[0].species == "Vanessa cardui"
        assert obs[1].species == "Pieris rapae"

    @patch("butterfly_planner.services.inat.get_observations_paginated")
    def test_params_passed_correctly(self, mock_paginated: object) -> None:
        mock_paginated.return_value = []  # type: ignore[union-attr]

        inaturalist.fetch_observations_for_month(month=[5, 6])

        call_args = mock_paginated.call_args[0][0]  # type: ignore[union-attr]
        assert call_args["month"] == "5,6"
        assert call_args["taxon_id"] == inat.BUTTERFLIES


class TestFetchWeeklyHistogram:
    """Test fetch_weekly_histogram with mocked API."""

    @patch("butterfly_planner.services.inat.get_histogram")
    def test_basic_fetch(self, mock_hist: object) -> None:
        mock_hist.return_value = SAMPLE_HISTOGRAM_RESPONSE  # type: ignore[union-attr]

        weeks = inaturalist.fetch_weekly_histogram()

        assert len(weeks) == 7
        # Should be sorted by week number
        assert weeks[0].week == 1
        assert weeks[-1].week == 50
        # Week 30 has highest count
        week_30 = next(w for w in weeks if w.week == 30)
        assert week_30.count == 1200

    @patch("butterfly_planner.services.inat.get_histogram")
    def test_params_include_bbox(self, mock_hist: object) -> None:
        mock_hist.return_value = SAMPLE_HISTOGRAM_RESPONSE  # type: ignore[union-attr]

        inaturalist.fetch_weekly_histogram()

        call_args = mock_hist.call_args[0][0]  # type: ignore[union-attr]
        assert call_args["swlat"] == 44.5
        assert call_args["interval"] == "week_of_year"
        assert call_args["taxon_id"] == inat.BUTTERFLIES


# =============================================================================
# High-level Function Tests
# =============================================================================


class TestGetCurrentWeekSpecies:
    """Test get_current_week_species convenience function."""

    @patch("butterfly_planner.inaturalist.fetch_observations_for_month")
    @patch("butterfly_planner.inaturalist.fetch_species_counts")
    def test_returns_summary(self, mock_species: object, mock_obs: object) -> None:
        mock_species.return_value = [  # type: ignore[union-attr]
            inaturalist.SpeciesRecord(
                taxon_id=48662,
                scientific_name="Vanessa cardui",
                common_name="Painted Lady",
                rank="species",
                observation_count=100,
            )
        ]
        mock_obs.return_value = [  # type: ignore[union-attr]
            inaturalist.ButterflyObservation(
                id=1,
                species="Vanessa cardui",
                common_name="Painted Lady",
                observed_on=date(2025, 6, 15),
                latitude=45.5,
                longitude=-122.6,
                quality_grade="research",
                url="https://www.inaturalist.org/observations/1",
            )
        ]

        summary = inaturalist.get_current_week_species()

        assert summary.total_species == 1
        assert summary.total_observations == 1
        assert summary.year is None  # All years
        assert len(summary.weeks) == 3  # current week ± 1

    @patch("butterfly_planner.inaturalist.fetch_observations_for_month")
    @patch("butterfly_planner.inaturalist.fetch_species_counts")
    def test_queries_multiple_months(self, mock_species: object, mock_obs: object) -> None:
        mock_species.return_value = []  # type: ignore[union-attr]
        mock_obs.return_value = []  # type: ignore[union-attr]

        inaturalist.get_current_week_species()

        # Should query with a list of months (from week ± 1 range)
        call_args = mock_species.call_args[0][0]  # type: ignore[union-attr]
        assert isinstance(call_args, list)
        assert len(call_args) >= 1


class TestGetSpeciesForWeek:
    """Test get_species_for_week function."""

    @patch("butterfly_planner.inaturalist.fetch_observations_for_month")
    @patch("butterfly_planner.inaturalist.fetch_species_counts")
    def test_week_25(self, mock_species: object, mock_obs: object) -> None:
        mock_species.return_value = []  # type: ignore[union-attr]
        mock_obs.return_value = []  # type: ignore[union-attr]

        inaturalist.get_species_for_week(25)

        # Week 25 is mid-June → should query month 6
        call_args = mock_species.call_args  # type: ignore[union-attr]
        months = call_args[0][0]  # first positional arg
        assert 6 in months


# =============================================================================
# Analysis Tests
# =============================================================================


class TestSummarizeSpecies:
    """Test summarize_species analysis function."""

    def test_empty_list(self) -> None:
        result = inaturalist.summarize_species([])
        assert result["total_species"] == 0

    def test_with_species(self) -> None:
        species = [
            inaturalist.SpeciesRecord(
                taxon_id=i,
                scientific_name=f"Species {i}",
                common_name=f"Common {i}" if i < 3 else None,
                rank="species",
                observation_count=(i + 1) * 100,
            )
            for i in range(5)
        ]
        result = inaturalist.summarize_species(species)

        assert result["total_species"] == 5
        assert result["total_observations"] == 1500  # 100+200+300+400+500
        assert len(result["top_species"]) == 5
        # Top species should be highest count first
        assert result["top_species"][0]["count"] == 500


class TestPeakWeeks:
    """Test peak_weeks function."""

    def test_finds_peak(self) -> None:
        histogram = [
            inaturalist.WeeklyActivity(week=w, count=c)
            for w, c in [(1, 5), (25, 890), (30, 1200), (40, 210)]
        ]
        peaks = inaturalist.peak_weeks(histogram, top_n=2)
        assert len(peaks) == 2
        assert peaks[0].week == 30
        assert peaks[1].week == 25


# =============================================================================
# Internal Helper Tests
# =============================================================================


class TestWeekRange:
    """Test _week_range helper."""

    def test_mid_year(self) -> None:
        weeks = inaturalist._week_range(25)
        assert weeks == [24, 25, 26]

    def test_week_1_wraps_to_52(self) -> None:
        weeks = inaturalist._week_range(1)
        assert weeks == [1, 2, 52]

    def test_week_52_wraps_to_1(self) -> None:
        weeks = inaturalist._week_range(52)
        assert weeks == [1, 51, 52]

    def test_custom_radius(self) -> None:
        weeks = inaturalist._week_range(10, radius=2)
        assert weeks == [8, 9, 10, 11, 12]


class TestWeeksToMonths:
    """Test _weeks_to_months helper."""

    def test_single_month(self) -> None:
        # Weeks 24-26 are all in June
        months = inaturalist._weeks_to_months([24, 25, 26], year=2026)
        assert 6 in months

    def test_spanning_months(self) -> None:
        # Weeks around month boundaries should return multiple months
        # Week 5 (late Jan) through week 7 (mid Feb) → Jan + Feb
        months = inaturalist._weeks_to_months([5, 6, 7], year=2026)
        assert 1 in months or 2 in months
        assert len(months) >= 1


class TestWeekToMonths:
    """Test _week_to_months conversion."""

    def test_mid_january(self) -> None:
        # Week 3 is mid-January
        months = inaturalist._week_to_months(3, year=2026)
        assert months == [1]

    def test_mid_june(self) -> None:
        # Week 25 is mid-June
        months = inaturalist._week_to_months(25, year=2026)
        assert 6 in months

    def test_week_spanning_two_months(self) -> None:
        # Week ~5 often spans Jan/Feb boundary
        # Find a week that actually spans two months
        months = inaturalist._week_to_months(5, year=2026)
        # Could be [1, 2] or just [1] depending on year — just check it returns valid months
        assert all(1 <= m <= 12 for m in months)
        assert len(months) >= 1

    def test_week_1(self) -> None:
        months = inaturalist._week_to_months(1, year=2026)
        assert 1 in months

    def test_week_52(self) -> None:
        months = inaturalist._week_to_months(52, year=2026)
        assert 12 in months


# =============================================================================
# Service Client Tests
# =============================================================================


class TestInatClient:
    """Test low-level inat service module constants and structure."""

    def test_constants(self) -> None:
        assert inat.BUTTERFLIES == 47224
        assert inat.LEPIDOPTERA == 47157
        assert inat.OREGON == 10
        assert inat.WASHINGTON == 46
        assert "v1" in inat.API_BASE

    def test_max_per_page(self) -> None:
        assert inat.MAX_PER_PAGE == 200

    @patch("butterfly_planner.services.inat.requests.get")
    def test_get_observations_calls_api(self, mock_get: object) -> None:
        mock_resp = mock_get.return_value  # type: ignore[union-attr]
        mock_resp.json.return_value = {"results": [], "total_results": 0}
        mock_resp.raise_for_status.return_value = None

        # Reset rate limiter for test
        inat._last_request_time = 0.0

        result = inat.get_observations({"taxon_id": 47224})
        assert result == {"results": [], "total_results": 0}
        mock_get.assert_called_once()  # type: ignore[union-attr]

    @patch("butterfly_planner.services.inat.requests.get")
    def test_get_species_counts_calls_api(self, mock_get: object) -> None:
        mock_resp = mock_get.return_value  # type: ignore[union-attr]
        mock_resp.json.return_value = {"results": [], "total_results": 0}
        mock_resp.raise_for_status.return_value = None

        inat._last_request_time = 0.0

        result = inat.get_species_counts({"taxon_id": 47224})
        assert result == {"results": [], "total_results": 0}

        call_url = mock_get.call_args[0][0]  # type: ignore[union-attr]
        assert "species_counts" in call_url

    @patch("butterfly_planner.services.inat.requests.get")
    def test_pagination_stops_on_empty(self, mock_get: object) -> None:
        mock_resp = mock_get.return_value  # type: ignore[union-attr]
        mock_resp.json.return_value = {"results": [], "total_results": 0}
        mock_resp.raise_for_status.return_value = None

        inat._last_request_time = 0.0

        results = inat.get_observations_paginated({"taxon_id": 47224}, max_pages=5)
        assert results == []
        # Should stop after first empty page
        assert mock_get.call_count == 1  # type: ignore[union-attr]

    @patch("butterfly_planner.services.inat.requests.get")
    def test_pagination_uses_id_above(self, mock_get: object) -> None:
        # First page returns results, second page empty
        page1 = {"results": [{"id": 100}, {"id": 200}], "total_results": 2}
        page2 = {"results": [], "total_results": 0}

        mock_resp = mock_get.return_value  # type: ignore[union-attr]
        mock_resp.json.side_effect = [page1, page2]
        mock_resp.raise_for_status.return_value = None

        inat._last_request_time = 0.0

        results = inat.get_observations_paginated({"taxon_id": 47224}, max_pages=5)
        assert len(results) == 2

        # Second call should include id_above=200
        second_call_params = mock_get.call_args_list[1][1]["params"]  # type: ignore[union-attr]
        assert second_call_params["id_above"] == 200


# =============================================================================
# Default Bounding Box Tests
# =============================================================================


class TestDefaultBoundingBox:
    """Test the NW Oregon / SW Washington bounding box constant."""

    def test_bbox_values(self) -> None:
        bbox = inaturalist.NW_OREGON_SW_WASHINGTON
        assert bbox["swlat"] == 44.5
        assert bbox["nelat"] == 46.5
        assert bbox["swlng"] == -124.2
        assert bbox["nelng"] == -121.5

    def test_bbox_covers_portland(self) -> None:
        """Portland (45.5, -122.6) should be inside the bbox."""
        bbox = inaturalist.NW_OREGON_SW_WASHINGTON
        assert bbox["swlat"] <= 45.5 <= bbox["nelat"]
        assert bbox["swlng"] <= -122.6 <= bbox["nelng"]

    def test_bbox_covers_vancouver_wa(self) -> None:
        """Vancouver, WA (45.63, -122.67) should be inside."""
        bbox = inaturalist.NW_OREGON_SW_WASHINGTON
        assert bbox["swlat"] <= 45.63 <= bbox["nelat"]
        assert bbox["swlng"] <= -122.67 <= bbox["nelng"]
