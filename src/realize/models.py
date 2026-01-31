"""Data models for Realize API responses."""
from datetime import datetime, timedelta, timezone
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


class OAuth21Token(BaseModel):
    """OAuth 2.1 token with refresh support and session tracking."""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    scope: Optional[str] = None
    session_id: Optional[str] = None
    created_at: Optional[datetime] = None

    @field_validator("expires_in")
    @classmethod
    def validate_expires_in(cls, v: int) -> int:
        """Ensure expires_in is positive."""
        if v <= 0:
            raise ValueError("expires_in must be positive")
        return v

    def is_expired(self, buffer_seconds: int = 0) -> bool:
        """Check if token is expired or will expire within buffer_seconds."""
        if self.created_at is None:
            return True

        # Compare using same datetime type as created_at to avoid timezone issues
        if self.created_at.tzinfo is None:
            now = datetime.now()
        else:
            now = utc_now()

        expiry = self.created_at + timedelta(seconds=self.expires_in)
        return now >= (expiry - timedelta(seconds=buffer_seconds))


# All other API responses will be handled as raw JSON dictionaries for flexibility
# No need for explicit models - this allows the API to evolve without breaking changes
 