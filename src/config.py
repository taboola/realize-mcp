"""Configuration management for Realize MCP server."""
import os
from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Configuration settings for Realize MCP server."""
    
    realize_client_id: str
    realize_client_secret: str
    realize_base_url: str = "https://backstage.taboola.com/backstage"
    log_level: str = "INFO"
    
    @field_validator('realize_client_id')
    @classmethod
    def validate_client_id(cls, v):
        if not v:
            raise ValueError("REALIZE_CLIENT_ID is required")
        return v
    
    @field_validator('realize_client_secret')
    @classmethod
    def validate_client_secret(cls, v):
        if not v:
            raise ValueError("REALIZE_CLIENT_SECRET is required")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global config instance
config = Config() 