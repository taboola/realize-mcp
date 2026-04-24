"""Tests for Streamable HTTP transport with OAuth 2.1 (stateless)."""
import pathlib
import sys
sys.path.append(str(pathlib.Path(__file__).parent.parent / "src"))

import os
from unittest.mock import patch, MagicMock

import pytest
from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.routing import Route

from realize.transports.streamable_http_server import StreamableHTTPEndpoint


def _make_test_app_with_endpoint():
    """Create a minimal test app with just the streamable HTTP endpoint.

    Uses a mock session manager to avoid needing the full MCP server.
    """
    mock_session_manager = MagicMock()

    async def mock_handle_request(scope, receive, send):
        from starlette.responses import JSONResponse
        response = JSONResponse({"status": "ok"})
        await response(scope, receive, send)

    mock_session_manager.handle_request = mock_handle_request

    endpoint = StreamableHTTPEndpoint(mock_session_manager)
    app = Starlette(routes=[Route("/mcp", endpoint)])
    return app


class TestStreamableHTTPEndpoint:
    """Tests for Streamable HTTP endpoint (stateless)."""

    def test_returns_401_without_authorization_header(self):
        """Test POST to /mcp returns 401 when no Authorization header present."""
        app = _make_test_app_with_endpoint()
        client = TestClient(app)
        response = client.post("/mcp")

        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers
        assert "Bearer" in response.headers["WWW-Authenticate"]

    def test_returns_401_with_non_bearer_auth(self):
        """Test POST to /mcp returns 401 when Authorization is not Bearer."""
        app = _make_test_app_with_endpoint()
        client = TestClient(app)
        response = client.post(
            "/mcp", headers={"Authorization": "Basic dXNlcjpwYXNz"}
        )

        assert response.status_code == 401

    def test_returns_401_with_empty_bearer_token(self):
        """Test POST to /mcp returns 401 when Bearer token is empty."""
        app = _make_test_app_with_endpoint()
        client = TestClient(app)
        response = client.post(
            "/mcp", headers={"Authorization": "Bearer "}
        )

        assert response.status_code == 401

    def test_delegates_to_session_manager_with_valid_token(self):
        """Test that valid Bearer token delegates to session manager."""
        app = _make_test_app_with_endpoint()
        client = TestClient(app)
        response = client.post(
            "/mcp",
            headers={"Authorization": "Bearer valid-test-token"},
            json={"jsonrpc": "2.0", "id": 1, "method": "test"},
        )

        assert response.status_code == 200

    def test_sets_and_clears_context_token(self):
        """Test that Bearer token is set in context and cleared after request."""
        from realize.oauth.context import get_session_token

        captured_tokens = []
        mock_session_manager = MagicMock()

        async def mock_handle_request(scope, receive, send):
            captured_tokens.append(get_session_token())
            from starlette.responses import JSONResponse
            response = JSONResponse({"status": "ok"})
            await response(scope, receive, send)

        mock_session_manager.handle_request = mock_handle_request

        endpoint = StreamableHTTPEndpoint(mock_session_manager)
        app = Starlette(routes=[Route("/mcp", endpoint)])
        client = TestClient(app)

        client.post(
            "/mcp",
            headers={"Authorization": "Bearer my-test-token"},
            json={},
        )

        assert len(captured_tokens) == 1
        assert captured_tokens[0] == "my-test-token"

        # Token should be cleared after request
        assert get_session_token() is None

    def test_get_request_returns_405(self):
        """GET /mcp returns 405 - stateless mode rejects server-initiated streams."""
        app = _make_test_app_with_endpoint()
        client = TestClient(app)
        response = client.get("/mcp")

        assert response.status_code == 405
        assert response.headers.get("Allow") == "POST, DELETE"

    def test_get_with_bearer_returns_405(self):
        """Authorized GET /mcp also returns 405 (method-level rejection)."""
        app = _make_test_app_with_endpoint()
        client = TestClient(app)
        response = client.get("/mcp", headers={"Authorization": "Bearer valid-token"})

        assert response.status_code == 405
        assert response.headers.get("Allow") == "POST, DELETE"

    def test_head_request_returns_405(self):
        """HEAD /mcp returns 405 - same server-initiated-stream bug surface as GET."""
        app = _make_test_app_with_endpoint()
        client = TestClient(app)
        response = client.head("/mcp")

        assert response.status_code == 405
        assert response.headers.get("Allow") == "POST, DELETE"

    def test_put_request_returns_405(self):
        """PUT /mcp returns 405 - only POST and DELETE allowed."""
        app = _make_test_app_with_endpoint()
        client = TestClient(app)
        response = client.put("/mcp", headers={"Authorization": "Bearer x"})

        assert response.status_code == 405

    def test_get_does_not_delegate_to_session_manager(self):
        """GET /mcp must not reach the SDK session manager (stateless GET is broken)."""
        call_count = {"n": 0}
        mock_session_manager = MagicMock()

        async def mock_handle_request(scope, receive, send):
            call_count["n"] += 1
            from starlette.responses import JSONResponse
            response = JSONResponse({"status": "ok"})
            await response(scope, receive, send)

        mock_session_manager.handle_request = mock_handle_request
        endpoint = StreamableHTTPEndpoint(mock_session_manager)
        app = Starlette(routes=[Route("/mcp", endpoint)])
        client = TestClient(app)

        client.get("/mcp", headers={"Authorization": "Bearer x"})

        assert call_count["n"] == 0

    def test_delete_request_returns_401_without_auth(self):
        """Test DELETE to /mcp returns 401 without Authorization."""
        app = _make_test_app_with_endpoint()
        client = TestClient(app)
        response = client.delete("/mcp")

        assert response.status_code == 401


class TestPassthroughHeaders:
    """Tests for CDN pass-through headers (Fastly SSE re-framing fix).

    The three headers instruct Fastly/Cloudflare/nginx to stream the response
    body through without buffering, caching, or transformation — the bug
    being worked around is Fastly's HTTP/2 re-framer corrupting SSE bodies.
    """

    EXPECTED = {
        "cache-control": "no-store, no-transform",
        "surrogate-control": "no-store",
        "x-accel-buffering": "no",
    }

    def _assert_passthrough_headers(self, response):
        for name, value in self.EXPECTED.items():
            assert response.headers.get(name) == value, (
                f"expected {name}={value!r}, got {response.headers.get(name)!r}"
            )

    def test_headers_on_401_missing_bearer(self):
        app = _make_test_app_with_endpoint()
        client = TestClient(app)
        response = client.post("/mcp")
        assert response.status_code == 401
        self._assert_passthrough_headers(response)
        assert "WWW-Authenticate" in response.headers

    def test_headers_on_401_empty_bearer(self):
        app = _make_test_app_with_endpoint()
        client = TestClient(app)
        response = client.post("/mcp", headers={"Authorization": "Bearer "})
        assert response.status_code == 401
        self._assert_passthrough_headers(response)
        assert "WWW-Authenticate" in response.headers

    def test_headers_on_405(self):
        app = _make_test_app_with_endpoint()
        client = TestClient(app)
        response = client.get("/mcp")
        assert response.status_code == 405
        self._assert_passthrough_headers(response)
        assert response.headers.get("Allow") == "POST, DELETE"

    def test_headers_on_delete_401(self):
        """DELETE path 401 also gets the three pass-through headers."""
        app = _make_test_app_with_endpoint()
        client = TestClient(app)
        response = client.delete("/mcp")
        assert response.status_code == 401
        self._assert_passthrough_headers(response)
        assert "WWW-Authenticate" in response.headers

    def test_headers_on_200_success_path(self):
        app = _make_test_app_with_endpoint()
        client = TestClient(app)
        response = client.post(
            "/mcp",
            headers={"Authorization": "Bearer valid-token"},
            json={"jsonrpc": "2.0", "id": 1, "method": "test"},
        )
        assert response.status_code == 200
        self._assert_passthrough_headers(response)

    def test_sdk_duplicate_headers_replaced_not_appended(self):
        """If downstream sets its own Cache-Control, wrapper must replace it."""
        mock_session_manager = MagicMock()

        async def mock_handle_request(scope, receive, send):
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": [
                    (b"content-type", b"text/event-stream"),
                    (b"cache-control", b"max-age=3600"),
                ],
            })
            await send({"type": "http.response.body", "body": b"data: ok\n\n"})

        mock_session_manager.handle_request = mock_handle_request
        endpoint = StreamableHTTPEndpoint(mock_session_manager)
        app = Starlette(routes=[Route("/mcp", endpoint)])
        client = TestClient(app)

        response = client.post(
            "/mcp",
            headers={"Authorization": "Bearer x"},
            json={},
        )
        assert response.status_code == 200
        # SDK's Cache-Control must be replaced, not duplicated
        assert response.headers.get("cache-control") == "no-store, no-transform"
        # Content-Type must be preserved
        assert response.headers.get("content-type") == "text/event-stream"

    def test_body_messages_pass_through_unchanged(self):
        """Wrapper must only touch http.response.start — body bytes must be byte-identical."""
        captured = []
        payload = b"data: {\"jsonrpc\":\"2.0\",\"id\":1,\"result\":{}}\n\n"

        async def mock_handle_request(scope, receive, send):
            async def recording_send(message):
                captured.append(message)
                await send(message)
            await recording_send({
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"text/event-stream")],
            })
            await recording_send({
                "type": "http.response.body",
                "body": payload,
                "more_body": False,
            })

        mock_session_manager = MagicMock()
        mock_session_manager.handle_request = mock_handle_request
        endpoint = StreamableHTTPEndpoint(mock_session_manager)
        app = Starlette(routes=[Route("/mcp", endpoint)])
        client = TestClient(app)

        response = client.post(
            "/mcp",
            headers={"Authorization": "Bearer x"},
            json={},
        )
        assert response.status_code == 200
        assert response.content == payload
        body_messages = [m for m in captured if m["type"] == "http.response.body"]
        assert len(body_messages) == 1
        assert body_messages[0]["body"] == payload


class TestCreateApp:
    """Tests for create_app factory function."""

    def test_creates_starlette_app(self):
        """Test that create_app returns a Starlette application."""
        from realize.transports.app import create_app

        app = create_app()

        assert app is not None
        assert len(app.routes) > 0

    def test_app_has_metadata_endpoints(self):
        """Test that app has OAuth metadata endpoints."""
        from realize.transports.app import create_app

        with patch("realize.oauth.metadata.config") as mock_meta_config:
            mock_meta_config.oauth_scopes = "all"

            app = create_app()
            client = TestClient(app, raise_server_exceptions=False)

            response = client.get("/.well-known/oauth-protected-resource")
            assert response.status_code == 200

    def test_app_has_register_endpoint(self):
        """Test that app has /register endpoint."""
        from realize.transports.app import create_app

        with patch("realize.oauth.dcr.config") as mock_dcr_config:
            mock_dcr_config.oauth_dcr_client_id = "test-client"
            mock_dcr_config.oauth_dcr_client_secret = "test-secret"

            app = create_app()
            client = TestClient(app, raise_server_exceptions=False)

            response = client.post("/register", json={"client_name": "Test"})
            assert response.status_code == 201

    def test_app_has_mcp_endpoint(self):
        """Test that app has /mcp endpoint."""
        from realize.transports.app import create_app

        app = create_app()
        client = TestClient(app, raise_server_exceptions=False)

        # Without auth, should get 401
        response = client.post("/mcp")
        assert response.status_code == 401

    def test_app_has_health_endpoint(self):
        """Test that app has /health endpoint."""
        from realize.transports.app import create_app

        app = create_app()
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestTransportSelection:
    """Tests for transport selection with streamable-http."""

    def test_stdio_is_default(self):
        """Test that stdio is the default transport."""
        from realize.config import Config

        with patch.dict("os.environ", {}, clear=True):
            with patch("realize.config.Config") as MockConfig:
                mock_instance = MagicMock()
                mock_instance.mcp_transport = "stdio"
                MockConfig.return_value = mock_instance

                assert mock_instance.mcp_transport == "stdio"

    def test_streamable_http_transport_via_env(self):
        """Test that streamable-http transport can be selected via environment."""
        env = {
            "MCP_TRANSPORT": "streamable-http",
            "OAUTH_SERVER_URL": "https://auth.example.com",
            "OAUTH_DCR_CLIENT_ID": "test_client_id",
            "OAUTH_DCR_CLIENT_SECRET": "test_client_secret",
        }
        with patch.dict(os.environ, env):
            from realize.config import Config
            test_config = Config()
            assert test_config.mcp_transport == "streamable-http"
            assert test_config.oauth_server_url == "https://auth.example.com"

    def test_streamable_http_requires_oauth_config(self):
        """Test that streamable-http transport requires OAuth configuration."""
        from realize.config import Config

        with pytest.raises(ValueError, match="OAUTH_DCR_CLIENT_ID"):
            Config(
                mcp_transport="streamable-http",
                _env_file=None,
            )
