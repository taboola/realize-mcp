"""Tests for RequestSizeLimitMiddleware."""
import json
import pytest

from realize.transports.middleware import RequestSizeLimitMiddleware, MAX_REQUEST_BYTES


def _make_scope(method="POST", content_length=None):
    """Build a minimal ASGI HTTP scope."""
    headers = []
    if content_length is not None:
        headers.append([b"content-length", str(content_length).encode()])
    return {
        "type": "http",
        "method": method,
        "path": "/register",
        "headers": headers,
    }


def _make_receive(body: bytes):
    """Return an ASGI receive callable that yields the body in one chunk."""
    called = False

    async def receive():
        nonlocal called
        if not called:
            called = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    return receive


def _make_chunked_receive(body: bytes, chunk_size: int):
    """Return an ASGI receive callable that yields the body in chunks."""
    offset = 0

    async def receive():
        nonlocal offset
        if offset < len(body):
            chunk = body[offset : offset + chunk_size]
            offset += chunk_size
            return {
                "type": "http.request",
                "body": chunk,
                "more_body": offset < len(body),
            }
        return {"type": "http.disconnect"}

    return receive


class _ResponseCapture:
    """Captures ASGI send messages."""

    def __init__(self):
        self.messages = []

    async def __call__(self, message):
        self.messages.append(message)

    @property
    def status(self):
        return self.messages[0]["status"]

    @property
    def body(self):
        return json.loads(self.messages[1]["body"])


async def _passthrough_app(scope, receive, send):
    """Dummy app that reads the full body and returns 200."""
    while True:
        message = await receive()
        if message.get("type") == "http.disconnect" or not message.get("more_body", False):
            break
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b"ok"})


@pytest.mark.asyncio
class TestRequestSizeLimitMiddleware:

    async def test_rejects_large_content_length(self):
        """Fast path: Content-Length header exceeds limit."""
        middleware = RequestSizeLimitMiddleware(_passthrough_app)
        scope = _make_scope(content_length=MAX_REQUEST_BYTES + 1)
        receive = _make_receive(b"")
        send = _ResponseCapture()

        await middleware(scope, receive, send)

        assert send.status == 413
        assert send.body["error"] == "request_too_large"

    async def test_rejects_large_body_with_spoofed_content_length(self):
        """Streaming guard: Content-Length is small but actual body exceeds limit."""
        middleware = RequestSizeLimitMiddleware(_passthrough_app)
        big_body = b"x" * (MAX_REQUEST_BYTES + 1)
        scope = _make_scope(content_length=100)
        receive = _make_receive(big_body)
        send = _ResponseCapture()

        await middleware(scope, receive, send)

        assert send.status == 413
        assert send.body["error"] == "request_too_large"

    async def test_rejects_large_chunked_body(self):
        """Streaming guard: no Content-Length, body arrives in chunks exceeding limit."""
        middleware = RequestSizeLimitMiddleware(_passthrough_app)
        big_body = b"x" * (MAX_REQUEST_BYTES + 1)
        scope = _make_scope(content_length=None)
        receive = _make_chunked_receive(big_body, chunk_size=32768)
        send = _ResponseCapture()

        await middleware(scope, receive, send)

        assert send.status == 413
        assert send.body["error"] == "request_too_large"

    async def test_allows_small_request(self):
        """Request under limit passes through to the app."""
        middleware = RequestSizeLimitMiddleware(_passthrough_app)
        scope = _make_scope(content_length=100)
        receive = _make_receive(b'{"query": "test"}')
        send = _ResponseCapture()

        await middleware(scope, receive, send)

        assert send.status == 200

    async def test_allows_get_request(self):
        """GET requests (no body) pass through."""
        middleware = RequestSizeLimitMiddleware(_passthrough_app)
        scope = _make_scope(method="GET", content_length=None)
        receive = _make_receive(b"")
        send = _ResponseCapture()

        await middleware(scope, receive, send)

        assert send.status == 200

    async def test_allows_request_at_exact_limit(self):
        """Request exactly at 128KB passes through."""
        middleware = RequestSizeLimitMiddleware(_passthrough_app)
        body = b"x" * MAX_REQUEST_BYTES
        scope = _make_scope(content_length=MAX_REQUEST_BYTES)
        receive = _make_receive(body)
        send = _ResponseCapture()

        await middleware(scope, receive, send)

        assert send.status == 200

    async def test_error_response_format(self):
        """413 response has correct JSON structure."""
        middleware = RequestSizeLimitMiddleware(_passthrough_app)
        scope = _make_scope(content_length=MAX_REQUEST_BYTES + 1)
        receive = _make_receive(b"")
        send = _ResponseCapture()

        await middleware(scope, receive, send)

        assert send.body == {
            "error": "request_too_large",
            "error_description": "Request body exceeds 128KB limit",
        }
        # Check content-type header
        headers = dict(send.messages[0]["headers"])
        assert headers[b"content-type"] == b"application/json"

    async def test_non_http_scope_passes_through(self):
        """Non-HTTP scopes (e.g. lifespan) are not checked."""
        called = False

        async def app(scope, receive, send):
            nonlocal called
            called = True

        middleware = RequestSizeLimitMiddleware(app)
        await middleware({"type": "lifespan"}, None, None)

        assert called is True
