"""
Tests for core business logic.

These tests verify the main application functionality.
"""

from unittest.mock import patch

from my_project.core import create_example, process_example, validate_input
from my_project.models import Status


class TestCreateExample:
    """Tests for create_example function."""

    def test_creates_with_name(self) -> None:
        """Creates example with given name."""
        example = create_example("Test Name")

        assert example.name == "Test Name"
        assert example.status == Status.PENDING
        assert example.id  # UUID is generated

    def test_creates_with_metadata(self) -> None:
        """Creates example with metadata."""
        metadata = {"env": "test", "version": "1.0"}
        example = create_example("Test", metadata=metadata)

        assert example.metadata == metadata

    def test_generates_unique_ids(self) -> None:
        """Each example gets a unique ID."""
        ex1 = create_example("First")
        ex2 = create_example("Second")

        assert ex1.id != ex2.id

    def test_empty_metadata_default(self) -> None:
        """Metadata defaults to empty dict if None."""
        example = create_example("Test", metadata=None)
        assert example.metadata == {}


class TestProcessExample:
    """Tests for process_example function."""

    def test_success(self) -> None:
        """Successful processing returns success result."""
        result = process_example("test-item")

        assert result.success is True
        assert "test-item" in result.message
        assert result.data is not None
        assert result.data["name"] == "test-item"

    def test_returns_id(self) -> None:
        """Result data includes generated ID."""
        result = process_example("test")

        assert result.data is not None
        assert "id" in result.data
        assert len(result.data["id"]) > 0

    def test_handles_exception(self) -> None:
        """Exception during processing returns error result."""
        with patch("my_project.core.create_example") as mock_create:
            mock_create.side_effect = ValueError("Test error")
            result = process_example("test")

            assert result.success is False
            assert result.error == "Test error"
            assert "failed" in result.message.lower()


class TestValidateInput:
    """Tests for validate_input function."""

    def test_valid_input(self) -> None:
        """Valid input passes validation."""
        is_valid, error = validate_input("valid string")

        assert is_valid is True
        assert error is None

    def test_empty_input_invalid(self) -> None:
        """Empty input fails validation."""
        is_valid, error = validate_input("")

        assert is_valid is False
        assert error is not None
        assert "empty" in error.lower()

    def test_exceeds_max_length(self) -> None:
        """Input exceeding max length fails."""
        long_input = "x" * 101
        is_valid, error = validate_input(long_input, max_length=100)

        assert is_valid is False
        assert error is not None
        assert "100" in error

    def test_custom_max_length(self) -> None:
        """Custom max length is respected."""
        is_valid, _ = validate_input("12345", max_length=5)
        assert is_valid is True

        is_valid, _ = validate_input("123456", max_length=5)
        assert is_valid is False

    def test_boundary_length(self) -> None:
        """Input at exactly max length passes."""
        is_valid, _ = validate_input("12345", max_length=5)
        assert is_valid is True
