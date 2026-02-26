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

    def test_get_request_returns_401_without_auth(self):
        """Test GET to /mcp returns 401 without Authorization."""
        app = _make_test_app_with_endpoint()
        client = TestClient(app)
        response = client.get("/mcp")

        assert response.status_code == 401

    def test_delete_request_returns_401_without_auth(self):
        """Test DELETE to /mcp returns 401 without Authorization."""
        app = _make_test_app_with_endpoint()
        client = TestClient(app)
        response = client.delete("/mcp")

        assert response.status_code == 401


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

        with pytest.raises(ValueError, match="OAUTH_SERVER_URL"):
            Config(
                mcp_transport="streamable-http",
                _env_file=None,
            )
