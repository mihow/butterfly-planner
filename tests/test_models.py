"""
Tests for data models.

These tests verify the Pydantic models work correctly.
"""

from datetime import datetime

import pytest

from butterfly_planner.models import Example, Result, Status


class TestStatus:
    """Tests for the Status enum."""

    def test_status_values(self) -> None:
        """Verify all expected status values exist."""
        assert Status.PENDING.value == "pending"
        assert Status.IN_PROGRESS.value == "in_progress"
        assert Status.COMPLETED.value == "completed"
        assert Status.FAILED.value == "failed"

    def test_status_from_string(self) -> None:
        """Status can be created from string value."""
        assert Status("pending") == Status.PENDING


class TestExample:
    """Tests for the Example model."""

    def test_create_minimal(self) -> None:
        """Example can be created with just required fields."""
        example = Example(id="123", name="Test")

        assert example.id == "123"
        assert example.name == "Test"
        assert example.status == Status.PENDING  # default
        assert isinstance(example.created_at, datetime)
        assert example.metadata == {}

    def test_create_full(self, sample_example: Example) -> None:
        """Example can be created with all fields."""
        assert sample_example.id == "test-123"
        assert sample_example.name == "Test Example"
        assert sample_example.status == Status.PENDING
        assert sample_example.metadata == {"key": "value"}

    def test_status_change(self, sample_example: Example) -> None:
        """Example status can be updated."""
        sample_example.status = Status.COMPLETED
        assert sample_example.status == Status.COMPLETED

    def test_metadata_update(self, sample_example: Example) -> None:
        """Example metadata can be updated."""
        sample_example.metadata["new_key"] = "new_value"
        assert "new_key" in sample_example.metadata

    def test_name_whitespace_stripped(self) -> None:
        """Name whitespace is stripped."""
        example = Example(id="123", name="  spaced name  ")
        assert example.name == "spaced name"

    def test_invalid_id_raises(self) -> None:
        """Missing required fields raise validation error."""
        with pytest.raises(ValueError):
            Example(name="No ID")


class TestResult:
    """Tests for the Result model."""

    def test_success_result(self) -> None:
        """Create a success result."""
        result = Result(
            success=True,
            message="Operation completed",
            data={"key": "value"},
        )

        assert result.success is True
        assert result.message == "Operation completed"
        assert result.data == {"key": "value"}
        assert result.error is None

    def test_failure_result(self) -> None:
        """Create a failure result."""
        result = Result(
            success=False,
            message="Operation failed",
            error="Something went wrong",
        )

        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.data is None

    def test_minimal_result(self) -> None:
        """Result only requires success and message."""
        result = Result(success=True, message="OK")
        assert result.success is True
        assert result.message == "OK"
