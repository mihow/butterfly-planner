"""
Core business logic for the application.

This module contains the main functionality. Add your business logic here.
"""

from __future__ import annotations

import uuid

from butterfly_planner.models import Example, Result, Status


def create_example(name: str, metadata: dict[str, str] | None = None) -> Example:
    """
    Create a new Example instance.

    Args:
        name: Display name for the example
        metadata: Optional metadata dictionary

    Returns:
        New Example instance with generated ID
    """
    return Example(
        id=str(uuid.uuid4()),
        name=name,
        status=Status.PENDING,
        metadata=metadata or {},
    )


def process_example(name: str) -> Result:
    """
    Process an example item.

    This is a placeholder function demonstrating the pattern for
    business logic that returns a Result.

    Args:
        name: Name to process

    Returns:
        Result indicating success or failure
    """
    try:
        example = create_example(name)
        example.status = Status.COMPLETED

        return Result(
            success=True,
            message=f"Successfully processed '{name}'",
            data={"id": example.id, "name": example.name},
        )
    except Exception as e:
        return Result(
            success=False,
            message="Processing failed",
            error=str(e),
        )


def validate_input(value: str, max_length: int = 100) -> tuple[bool, str | None]:
    """
    Validate user input.

    Args:
        value: Input string to validate
        max_length: Maximum allowed length

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not value:
        return False, "Value cannot be empty"

    if len(value) > max_length:
        return False, f"Value exceeds maximum length of {max_length}"

    return True, None
