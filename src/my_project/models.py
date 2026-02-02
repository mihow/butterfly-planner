"""
Data models for the application.

This module contains Pydantic models that define the core data structures.
Add your domain models here.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Status(str, Enum):
    """Status enum for tracking item state."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Example(BaseModel):
    """
    Example model demonstrating Pydantic usage.

    This is a placeholder model. Replace with your domain models.
    """

    id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="Display name")
    status: Status = Field(default=Status.PENDING, description="Current status")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    metadata: dict[str, str] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        """Pydantic model configuration."""

        frozen = False
        str_strip_whitespace = True


class Result(BaseModel):
    """Generic result wrapper for operations."""

    success: bool
    message: str
    data: dict[str, Any] | None = None
    error: str | None = None
