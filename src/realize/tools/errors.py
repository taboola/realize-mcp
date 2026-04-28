"""Error classification utilities for MCP tool handlers."""
import json
import httpx

_MAX_BODY_CHARS = 1000


class ToolInputError(Exception):
    """Raised for local validation failures (missing/invalid params).

    Message is surfaced directly to the client — it never came from upstream.
    """
    pass


def _extract_error_body(response: httpx.Response) -> str:
    """Compact, LLM-friendly summary of a 4xx response body.

    Prefers JSON error fields (message, error, details) when present; falls
    back to raw text. Output is truncated to keep client context bounded.
    """
    try:
        data = response.json()
    except Exception:
        data = None

    if isinstance(data, dict):
        parts = []
        for key in ("message", "error", "details"):
            if key in data and data[key] not in (None, "", [], {}):
                value = data[key]
                if not isinstance(value, str):
                    try:
                        value = json.dumps(value, separators=(",", ":"))
                    except (TypeError, ValueError):
                        value = str(value)
                parts.append(f"{key}={value}")
        if parts:
            return "; ".join(parts)[:_MAX_BODY_CHARS]

    if data is not None:
        try:
            return json.dumps(data, separators=(",", ":"))[:_MAX_BODY_CHARS]
        except (TypeError, ValueError):
            pass

    try:
        raw = response.text
        text = raw.strip() if isinstance(raw, str) else ""
    except Exception:
        text = ""
    return text[:_MAX_BODY_CHARS] if text else "no response body"


def classify_api_error(exc: Exception) -> str:
    """Return client-facing message for upstream/unexpected errors.

    - 4xx from Realize API: proxied back with response body for LLM self-correction
    - 5xx from Realize API: status code only (no internal body/stack leakage)
    - Network/timeout: descriptive category message
    - Unexpected: generic message

    ToolInputError is NOT handled here — it is a local validation error,
    not an API error, and should be re-raised directly.
    """
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if 400 <= status < 500:
            body = _extract_error_body(exc.response)
            return f"Realize API returned {status}: {body}"
        return f"Realize API returned {status}. Please try again later."
    # TimeoutException must be checked before ConnectError because
    # ConnectTimeout is a subclass of both.
    if isinstance(exc, httpx.TimeoutException):
        return "Request to the Realize API timed out. Please try again later."
    if isinstance(exc, httpx.ConnectError):
        return "The Realize API is currently unreachable. Please try again later."
    return "An unexpected error occurred. Please try again later."
