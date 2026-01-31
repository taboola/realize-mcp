"""Configuration management for Realize MCP server."""
from typing import Literal, Optional
from pydantic import ConfigDict, model_validator
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Configuration settings for Realize MCP server."""

    # === Transport selection ===
    mcp_transport: Literal["stdio", "sse"] = "stdio"

    # === Shared settings ===
    realize_base_url: str = "https://backstage.taboola.com/backstage"
    log_level: str = "INFO"

    # === Stdio mode (required when mcp_transport="stdio") ===
    realize_client_id: Optional[str] = None
    realize_client_secret: Optional[str] = None

    # === SSE mode (required when mcp_transport="sse") ===
    mcp_server_url: Optional[str] = None
    mcp_server_port: int = 8000
    oauth_server_url: Optional[str] = None
    oauth_dcr_client_id: Optional[str] = None
    oauth_dcr_client_secret: Optional[str] = None
    oauth_scopes: str = "all"
    oauth_refresh_buffer_seconds: int = 60

    @model_validator(mode='after')
    def validate_transport_requirements(self):
        """Validate required fields based on transport mode."""
        if self.mcp_transport == "stdio":
            # stdio requires Realize credentials for Client Credentials flow
            if not self.realize_client_id or not self.realize_client_secret:
                raise ValueError(
                    "REALIZE_CLIENT_ID and REALIZE_CLIENT_SECRET are required for stdio transport"
                )
        elif self.mcp_transport == "sse":
            # SSE requires OAuth 2.1 configuration
            if not self.mcp_server_url:
                raise ValueError("MCP_SERVER_URL is required for SSE transport")
            if not self.oauth_server_url:
                raise ValueError("OAUTH_SERVER_URL is required for SSE transport")
            if not self.oauth_dcr_client_id or not self.oauth_dcr_client_secret:
                raise ValueError(
                    "OAUTH_DCR_CLIENT_ID and OAUTH_DCR_CLIENT_SECRET are required for SSE transport"
                )
        return self

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


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