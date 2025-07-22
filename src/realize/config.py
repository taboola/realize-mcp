"""Configuration management for Realize MCP server."""
import os
from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Configuration settings for Realize MCP server."""
    
    realize_client_id: str = "your_client_id"
    realize_client_secret: str = "your_client_secret"
    realize_base_url: str = "https://backstage.taboola.com/backstage"
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra environment variables not defined in model


# Pagination configuration
PAGINATION_DEFAULTS = {
    "default_page": 1,
    "default_page_size": 100,
    "max_page_size": 1000
}

# Sort configuration
SORT_CONFIG = {
    "valid_directions": ["ASC", "DESC"],
    "default_direction": "DESC",
    "default_sort_field": "spent",
    "report_sort_fields": ["clicks", "spent", "impressions"]
}

# Global config instance
config = Config() 