"""Shared HTTP client factory with standard defaults."""
import httpx

USER_AGENT = "realize-mcp"


def create_http_client(**kwargs) -> httpx.AsyncClient:
    """Create an httpx.AsyncClient with standard defaults."""
    headers = kwargs.pop("headers", {})
    headers.setdefault("User-Agent", USER_AGENT)
    return httpx.AsyncClient(headers=headers, **kwargs)
