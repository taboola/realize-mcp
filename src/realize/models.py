"""Data models for Realize API responses."""
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, field_validator


def utc_now() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class Token(BaseModel):
    """OAuth token model - only model we need for token management."""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    created_at: Optional[datetime] = None

    @field_validator("expires_in")
    @classmethod
    def validate_expires_in(cls, v: int) -> int:
        """Ensure expires_in is positive."""
        if v <= 0:
            raise ValueError("expires_in must be positive")
        return v


# All other API responses will be handled as raw JSON dictionaries for flexibility
# No need for explicit models - this allows the API to evolve without breaking changes
 