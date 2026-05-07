"""Tests for the sse_starlette ping-interval override.

The override lowers sse_starlette's default ping interval so SSE streams
survive intermediate-proxy between-bytes timeouts on slow tool calls.
"""
import importlib

import pytest
import sse_starlette.sse


@pytest.fixture
def reload_keepalive(monkeypatch):
    """Re-import realize.sse_keepalive so module-level env reads are re-run."""
    def _reload():
        import realize.sse_keepalive
        return importlib.reload(realize.sse_keepalive)
    return _reload


def test_class_default_lowered_to_five(reload_keepalive, monkeypatch):
    """With no env var, the class-level DEFAULT_PING_INTERVAL is 5s."""
    monkeypatch.delenv("MCP_SSE_PING_INTERVAL", raising=False)
    reload_keepalive()

    assert sse_starlette.sse.EventSourceResponse.DEFAULT_PING_INTERVAL == 5


def test_instance_inherits_lowered_default(reload_keepalive, monkeypatch):
    """A response constructed without ping= inherits the lowered default.

    Catches a future sse_starlette change that bypasses the class attribute.
    """
    monkeypatch.delenv("MCP_SSE_PING_INTERVAL", raising=False)
    reload_keepalive()

    async def _empty_stream():
        return
        yield  # pragma: no cover -- unreachable, marks as async generator

    response = sse_starlette.sse.EventSourceResponse(content=_empty_stream())

    assert response.ping_interval == 5


def test_env_var_overrides_default(reload_keepalive, monkeypatch):
    """MCP_SSE_PING_INTERVAL env var overrides the built-in default."""
    monkeypatch.setenv("MCP_SSE_PING_INTERVAL", "3")
    reload_keepalive()

    assert sse_starlette.sse.EventSourceResponse.DEFAULT_PING_INTERVAL == 3


def test_env_var_non_integer_rejected(reload_keepalive, monkeypatch):
    """Garbage values fail fast at import."""
    monkeypatch.setenv("MCP_SSE_PING_INTERVAL", "not-a-number")
    with pytest.raises(ValueError, match="MCP_SSE_PING_INTERVAL"):
        reload_keepalive()


def test_env_var_zero_rejected(reload_keepalive, monkeypatch):
    """0 would silently disable keepalive — reject."""
    monkeypatch.setenv("MCP_SSE_PING_INTERVAL", "0")
    with pytest.raises(ValueError, match="positive integer"):
        reload_keepalive()


def test_env_var_negative_rejected(reload_keepalive, monkeypatch):
    """Negative values rejected."""
    monkeypatch.setenv("MCP_SSE_PING_INTERVAL", "-1")
    with pytest.raises(ValueError, match="positive integer"):
        reload_keepalive()
