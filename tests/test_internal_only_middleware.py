"""Tests for InternalOnlyMiddleware."""
import json
import pytest

from realize.transports.middleware import InternalOnlyMiddleware


DEFAULT_CIDRS = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "127.0.0.0/8", "::1/128"]


def _make_scope(path="/metrics", client_ip="93.184.216.34", method="GET"):
    """Build a minimal ASGI HTTP scope."""
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": [],
    }
    if client_ip is not None:
        scope["client"] = (client_ip, 0)
    return scope


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
    """Dummy app that returns 200."""
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b"ok"})


async def _noop_receive():
    return {"type": "http.disconnect"}


@pytest.mark.asyncio
class TestInternalOnlyMiddleware:

    async def test_blocks_public_ip(self):
        """Public IP accessing /metrics gets 403."""
        middleware = InternalOnlyMiddleware(_passthrough_app, allowed_cidrs=DEFAULT_CIDRS)
        send = _ResponseCapture()

        await middleware(_make_scope(client_ip="93.184.216.34"), _noop_receive, send)

        assert send.status == 403
        assert send.body["error"] == "forbidden"

    async def test_allows_10_network(self):
        """/metrics from 10.x.x.x passes through."""
        middleware = InternalOnlyMiddleware(_passthrough_app, allowed_cidrs=DEFAULT_CIDRS)
        send = _ResponseCapture()

        await middleware(_make_scope(client_ip="10.0.1.50"), _noop_receive, send)

        assert send.status == 200

    async def test_allows_172_16_network(self):
        """/metrics from 172.16.x.x passes through."""
        middleware = InternalOnlyMiddleware(_passthrough_app, allowed_cidrs=DEFAULT_CIDRS)
        send = _ResponseCapture()

        await middleware(_make_scope(client_ip="172.16.0.1"), _noop_receive, send)

        assert send.status == 200

    async def test_allows_192_168_network(self):
        """/metrics from 192.168.x.x passes through."""
        middleware = InternalOnlyMiddleware(_passthrough_app, allowed_cidrs=DEFAULT_CIDRS)
        send = _ResponseCapture()

        await middleware(_make_scope(client_ip="192.168.1.1"), _noop_receive, send)

        assert send.status == 200

    async def test_allows_loopback(self):
        """/metrics from 127.0.0.1 passes through."""
        middleware = InternalOnlyMiddleware(_passthrough_app, allowed_cidrs=DEFAULT_CIDRS)
        send = _ResponseCapture()

        await middleware(_make_scope(client_ip="127.0.0.1"), _noop_receive, send)

        assert send.status == 200

    async def test_allows_ipv6_loopback(self):
        """/metrics from ::1 passes through."""
        middleware = InternalOnlyMiddleware(_passthrough_app, allowed_cidrs=DEFAULT_CIDRS)
        send = _ResponseCapture()

        await middleware(_make_scope(client_ip="::1"), _noop_receive, send)

        assert send.status == 200

    async def test_non_restricted_path_allows_any_ip(self):
        """Non-restricted paths pass through regardless of IP."""
        middleware = InternalOnlyMiddleware(_passthrough_app, allowed_cidrs=DEFAULT_CIDRS)
        send = _ResponseCapture()

        await middleware(_make_scope(path="/health", client_ip="93.184.216.34"), _noop_receive, send)

        assert send.status == 200

    async def test_mcp_path_allows_any_ip(self):
        """/mcp passes through regardless of IP."""
        middleware = InternalOnlyMiddleware(_passthrough_app, allowed_cidrs=DEFAULT_CIDRS)
        send = _ResponseCapture()

        await middleware(_make_scope(path="/mcp", client_ip="93.184.216.34"), _noop_receive, send)

        assert send.status == 200

    async def test_missing_client_blocked(self):
        """No client in scope fails closed with 403."""
        middleware = InternalOnlyMiddleware(_passthrough_app, allowed_cidrs=DEFAULT_CIDRS)
        scope = {"type": "http", "method": "GET", "path": "/metrics", "headers": []}
        send = _ResponseCapture()

        await middleware(scope, _noop_receive, send)

        assert send.status == 403

    async def test_non_http_scope_passes_through(self):
        """Non-HTTP scopes (e.g. lifespan) are not checked."""
        called = False

        async def app(scope, receive, send):
            nonlocal called
            called = True

        middleware = InternalOnlyMiddleware(app, allowed_cidrs=DEFAULT_CIDRS)
        await middleware({"type": "lifespan"}, None, None)

        assert called is True

    async def test_403_response_format(self):
        """403 response has correct JSON structure and headers."""
        middleware = InternalOnlyMiddleware(_passthrough_app, allowed_cidrs=DEFAULT_CIDRS)
        send = _ResponseCapture()

        await middleware(_make_scope(client_ip="8.8.8.8"), _noop_receive, send)

        assert send.body == {
            "error": "forbidden",
            "error_description": "Access denied",
        }
        headers = dict(send.messages[0]["headers"])
        assert headers[b"content-type"] == b"application/json"

    async def test_blocks_172_outside_range(self):
        """172.32.x.x is outside 172.16.0.0/12 and should be blocked."""
        middleware = InternalOnlyMiddleware(_passthrough_app, allowed_cidrs=DEFAULT_CIDRS)
        send = _ResponseCapture()

        await middleware(_make_scope(client_ip="172.32.0.1"), _noop_receive, send)

        assert send.status == 403

    async def test_invalid_client_ip_blocked(self):
        """Unparseable IP fails closed with 403."""
        middleware = InternalOnlyMiddleware(_passthrough_app, allowed_cidrs=DEFAULT_CIDRS)
        send = _ResponseCapture()
        await middleware(_make_scope(client_ip="not-an-ip"), _noop_receive, send)
        assert send.status == 403

    async def test_custom_cidrs(self):
        """Custom CIDR configuration is respected."""
        middleware = InternalOnlyMiddleware(_passthrough_app, allowed_cidrs=["203.0.113.0/24"])
        send = _ResponseCapture()

        await middleware(_make_scope(client_ip="203.0.113.50"), _noop_receive, send)
        assert send.status == 200

        send2 = _ResponseCapture()
        await middleware(_make_scope(client_ip="10.0.0.1"), _noop_receive, send2)
        assert send2.status == 403