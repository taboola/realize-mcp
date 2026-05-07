"""Lower sse_starlette ping interval for proxy compatibility.

Intermediate proxies and CDNs commonly enforce a between-bytes timeout
on response streams (often around 10s). The upstream sse_starlette
default ping interval is 15s, so the first keepalive can arrive after
such a proxy has already cut the SSE stream on a slow tool call.

Default here is 5s. Override with the MCP_SSE_PING_INTERVAL env var
(positive integer, seconds).

Applied at import time. Must be imported before any EventSourceResponse
is instantiated — the class attribute is read in __init__, per instance.
"""
import os

import sse_starlette.sse

_DEFAULT_PING_INTERVAL_SECONDS = 5
_ENV_VAR_NAME = "MCP_SSE_PING_INTERVAL"


def _resolve_interval() -> int:
    raw = os.getenv(_ENV_VAR_NAME)
    if raw is None or raw == "":
        return _DEFAULT_PING_INTERVAL_SECONDS
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(
            f"{_ENV_VAR_NAME} must be a positive integer (seconds); got {raw!r}"
        ) from exc
    if value <= 0:
        raise ValueError(
            f"{_ENV_VAR_NAME} must be a positive integer (seconds); got {value}"
        )
    return value


sse_starlette.sse.EventSourceResponse.DEFAULT_PING_INTERVAL = _resolve_interval()
