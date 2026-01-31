"""Context variable support for per-connection token isolation.

Uses Python's contextvars module to isolate tokens per async context.
Each SSE connection runs in its own async task, so contextvars provide
natural isolation between concurrent connections.
"""
from contextvars import ContextVar
from typing import Optional

# Token for current SSE connection (isolated per async context)
current_session_token: ContextVar[Optional[str]] = ContextVar(
    'current_session_token',
    default=None
)


def set_session_token(token: str) -> None:
    """Set token for current async context."""
    current_session_token.set(token)


def get_session_token() -> Optional[str]:
    """Get token for current async context."""
    return current_session_token.get()


def clear_session_token() -> None:
    """Clear token for current async context."""
    current_session_token.set(None)
