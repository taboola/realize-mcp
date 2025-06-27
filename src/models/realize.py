"""Data models for Realize API responses."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class Token(BaseModel):
    """OAuth token model - only model we need for token management."""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    created_at: Optional[datetime] = None


# All other API responses will be handled as raw JSON dictionaries for flexibility
# No need for explicit models - this allows the API to evolve without breaking changes 