"""Error classification utilities for MCP tool handlers."""
import httpx


class ToolInputError(Exception):
    """Raised for local validation failures (missing/invalid params).

    Message is surfaced directly to the client — it never came from upstream.
    """
    pass


def classify_api_error(exc: Exception) -> str:
    """Return client-facing message for upstream/unexpected errors.

    - 4xx from Realize API: proxied back (actionable for the caller)
    - 5xx from Realize API: status code surfaced so client can decide retry strategy,
      but no internal details (error bodies, stack traces) leaked
    - Network/timeout: descriptive category message
    - Unexpected: generic message

    ToolInputError is NOT handled here — it is a local validation error,
    not an API error, and should be re-raised directly.
    """
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if 400 <= status < 500:
            return str(exc)  # 4xx: actionable, proxy it
        return f"Realize API returned {status}. Please try again later."
    # TimeoutException must be checked before ConnectError because
    # ConnectTimeout is a subclass of both.
    if isinstance(exc, httpx.TimeoutException):
        return "Request to the Realize API timed out. Please try again later."
    if isinstance(exc, httpx.ConnectError):
        return "The Realize API is currently unreachable. Please try again later."
    return "An unexpected error occurred. Please try again later."
