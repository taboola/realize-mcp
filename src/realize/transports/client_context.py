"""Context variable support for per-request client info propagation.

Bridges client identity from MCP session handlers to the ASGI metrics
middleware using Python's contextvars module.
"""
from contextvars import ContextVar
from typing import Optional

_client_name: ContextVar[Optional[str]] = ContextVar("client_name", default=None)
_client_version: ContextVar[Optional[str]] = ContextVar("client_version", default=None)


def set_client_info(name: str, version: str) -> None:
    """Set client info for current async context."""
    _client_name.set(name)
    _client_version.set(version)


def get_client_info() -> tuple[str, str]:
    """Get client info, falling back to ("unknown", "?") if unset."""
    return (
        _client_name.get() or "unknown",
        _client_version.get() or "?",
    )


def clear_client_info() -> None:
    """Clear client info for current async context."""
    _client_name.set(None)
    _client_version.set(None)