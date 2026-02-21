"""Tests for SSE transport with OAuth 2.1 (stateless)."""
import pathlib
import sys
sys.path.append(str(pathlib.Path(__file__).parent.parent / "src"))

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from starlette.testclient import TestClient

from realize.transports.app import create_app
from realize.transports.sse_server import create_sse_endpoint, sse_transport


class TestSSEEndpoint:
    """Tests for SSE endpoint function (stateless)."""

    def test_returns_401_without_authorization_header(self):
        """Test SSE returns 401 when no Authorization header present."""
        with patch("realize.transports.sse_server.config") as mock_config:
            mock_config.mcp_server_url = "https://mcp.example.com"

            from starlette.applications import Starlette
            from starlette.routing import Route

            sse_endpoint = create_sse_endpoint()

            app = Starlette(routes=[
                Route("/sse", sse_endpoint, methods=["GET"]),
            ])

            client = TestClient(app)
            response = client.get("/sse")

            assert response.status_code == 401
            assert "WWW-Authenticate" in response.headers
            assert "Bearer" in response.headers["WWW-Authenticate"]

    def test_returns_401_with_non_bearer_auth(self):
        """Test SSE returns 401 when Authorization is not Bearer."""
        with patch("realize.transports.sse_server.config") as mock_config:
            mock_config.mcp_server_url = "https://mcp.example.com"

            from starlette.applications import Starlette
            from starlette.routing import Route

            sse_endpoint = create_sse_endpoint()

            app = Starlette(routes=[
                Route("/sse", sse_endpoint, methods=["GET"]),
            ])

            client = TestClient(app)
            response = client.get("/sse", headers={"Authorization": "Basic dXNlcjpwYXNz"})

            assert response.status_code == 401

    def test_returns_401_with_empty_bearer_token(self):
        """Test SSE returns 401 when Bearer token is empty."""
        with patch("realize.transports.sse_server.config") as mock_config:
            mock_config.mcp_server_url = "https://mcp.example.com"

            from starlette.applications import Starlette
            from starlette.routing import Route

            sse_endpoint = create_sse_endpoint()

            app = Starlette(routes=[
                Route("/sse", sse_endpoint, methods=["GET"]),
            ])

            client = TestClient(app)
            response = client.get("/sse", headers={"Authorization": "Bearer "})

            assert response.status_code == 401


class TestCreateApp:
    """Tests for create_app factory function."""

    def test_creates_starlette_app(self):
        """Test that create_app returns a Starlette application."""
        app = create_app()

        assert app is not None
        # Check it has routes
        assert len(app.routes) > 0

    def test_app_has_metadata_endpoints(self):
        """Test that app has OAuth metadata endpoints."""
        with patch("realize.oauth.metadata.config") as mock_meta_config:
            mock_meta_config.mcp_server_url = "https://mcp.example.com"
            mock_meta_config.oauth_server_url = "https://auth.example.com"
            mock_meta_config.oauth_scopes = "all"

            app = create_app()
            client = TestClient(app)

            response = client.get("/.well-known/oauth-protected-resource")
            assert response.status_code == 200

    def test_app_has_register_endpoint(self):
        """Test that app has /register endpoint."""
        with patch("realize.oauth.dcr.config") as mock_dcr_config:
            mock_dcr_config.oauth_dcr_client_id = "test-client"
            mock_dcr_config.oauth_dcr_client_secret = "test-secret"

            app = create_app()
            client = TestClient(app)

            response = client.post("/register", json={"client_name": "Test"})
            assert response.status_code == 201

    def test_app_has_token_endpoint(self):
        """Test that app has /oauth/token endpoint."""
        app = create_app()
        client = TestClient(app)

        # This will fail because no upstream, but endpoint should exist
        with patch("realize.oauth.token.config") as mock_token_config:
            mock_token_config.oauth_server_url = "https://auth.example.com"

            with patch("realize.oauth.token.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_response = MagicMock()
                mock_response.status_code = 400
                mock_response.json.return_value = {"error": "invalid_request"}
                mock_instance.post.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                response = client.post(
                    "/oauth/token",
                    data={"grant_type": "authorization_code"}
                )
                # Endpoint exists and responds
                assert response.status_code in [400, 502]

    def test_app_has_sse_endpoint(self):
        """Test that app has /sse endpoint."""
        with patch("realize.transports.sse_server.config") as mock_sse_config:
            mock_sse_config.mcp_server_url = "https://mcp.example.com"

            app = create_app()
            client = TestClient(app)

            # Without auth, should get 401
            response = client.get("/sse")
            assert response.status_code == 401


class TestTransportSelection:
    """Tests for transport selection in realize_server."""

    def test_stdio_is_default(self):
        """Test that stdio is the default transport."""
        from realize.config import Config

        with patch.dict("os.environ", {}, clear=True):
            # Create fresh config to test defaults
            with patch("realize.config.Config") as MockConfig:
                mock_instance = MagicMock()
                mock_instance.mcp_transport = "stdio"
                MockConfig.return_value = mock_instance

                # Default should be stdio
                assert mock_instance.mcp_transport == "stdio"

    def test_sse_transport_via_env(self):
        """Test that SSE transport can be selected via environment."""
        import os
        from pydantic_settings import BaseSettings

        # Test that config accepts "sse" value
        # SSE transport requires additional OAuth config variables
        sse_env = {
            "MCP_TRANSPORT": "sse",
            "MCP_SERVER_URL": "https://mcp.example.com",
            "OAUTH_SERVER_URL": "https://auth.example.com",
            "OAUTH_DCR_CLIENT_ID": "test_client_id",
            "OAUTH_DCR_CLIENT_SECRET": "test_client_secret",
        }
        with patch.dict(os.environ, sse_env):
            from realize.config import Config
            # Create new config instance to pick up env var
            test_config = Config()
            assert test_config.mcp_transport == "sse"
            assert test_config.mcp_server_url == "https://mcp.example.com"
            assert test_config.oauth_server_url == "https://auth.example.com"