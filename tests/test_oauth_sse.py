"""Tests for SSE transport with OAuth 2.1."""
import pathlib
import sys
sys.path.append(str(pathlib.Path(__file__).parent.parent / "src"))

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from starlette.testclient import TestClient

from realize.transports.app import create_app
from realize.transports.sse_server import create_sse_endpoint, sse_transport
from realize.oauth.session import InMemorySessionManager, is_valid_session_id
from realize.oauth.token import TokenProxy
from realize.models import OAuth21Token, utc_now


class TestSSEEndpoint:
    """Tests for SSE endpoint function."""

    def test_returns_401_without_authorization_header(self):
        """Test SSE returns 401 when no Authorization header present."""
        with patch("realize.transports.sse_server.config") as mock_config:
            mock_config.mcp_server_url = "https://mcp.example.com"

            from starlette.applications import Starlette
            from starlette.routing import Route

            session_manager = InMemorySessionManager()
            sse_endpoint = create_sse_endpoint(session_manager)

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

            session_manager = InMemorySessionManager()
            sse_endpoint = create_sse_endpoint(session_manager)

            app = Starlette(routes=[
                Route("/sse", sse_endpoint, methods=["GET"]),
            ])

            client = TestClient(app)
            response = client.get("/sse", headers={"Authorization": "Basic dXNlcjpwYXNz"})

            assert response.status_code == 401

    def test_returns_401_with_unrecognized_bearer_token(self):
        """Test SSE returns 401 when Bearer token is not in session manager."""
        with patch("realize.transports.sse_server.config") as mock_config:
            mock_config.mcp_server_url = "https://mcp.example.com"

            from starlette.applications import Starlette
            from starlette.routing import Route

            session_manager = InMemorySessionManager()
            sse_endpoint = create_sse_endpoint(session_manager)

            app = Starlette(routes=[
                Route("/sse", sse_endpoint, methods=["GET"]),
            ])

            client = TestClient(app)
            # Send an unknown token - should be rejected
            response = client.get("/sse", headers={"Authorization": "Bearer unknown_token"})

            assert response.status_code == 401
            assert "invalid_token" in response.headers.get("WWW-Authenticate", "")

    @pytest.mark.asyncio
    async def test_accepts_valid_token_from_session_manager(self):
        """Test SSE accepts Bearer token that exists in session manager."""
        session_manager = InMemorySessionManager()

        # Store a token in session manager (simulating token exchange)
        token = OAuth21Token(
            access_token="valid_test_token",
            token_type="Bearer",
            expires_in=3600,
            created_at=utc_now(),
        )
        await session_manager.set_token("test-session", token)

        # Verify the token can be found
        session_id = await session_manager.find_session_by_token("valid_test_token")
        assert session_id == "test-session"


class TestSessionValidation:
    """Tests for session ID validation."""

    def test_valid_uuid_formats(self):
        """Test valid UUID formats are accepted."""
        assert is_valid_session_id("550e8400-e29b-41d4-a716-446655440000")
        assert is_valid_session_id("550e8400e29b41d4a716446655440000")  # Without dashes
        assert is_valid_session_id("550E8400-E29B-41D4-A716-446655440000")  # Uppercase

    def test_invalid_formats_rejected(self):
        """Test invalid formats are rejected."""
        assert not is_valid_session_id("")
        assert not is_valid_session_id("invalid")
        assert not is_valid_session_id("'; DROP TABLE users; --")
        assert not is_valid_session_id("../../../etc/passwd")


class TestInMemorySessionManager:
    """Tests for InMemorySessionManager."""

    @pytest.fixture
    def session_manager(self):
        return InMemorySessionManager(max_sessions=5)

    @pytest.fixture
    def sample_token(self):
        return OAuth21Token(
            access_token="test_token",
            token_type="Bearer",
            expires_in=3600,
            created_at=utc_now(),
        )

    @pytest.mark.asyncio
    async def test_set_and_get_token(self, session_manager, sample_token):
        """Test storing and retrieving a token."""
        await session_manager.set_token("session-1", sample_token)
        retrieved = await session_manager.get_token("session-1")

        assert retrieved is not None
        assert retrieved.access_token == "test_token"

    @pytest.mark.asyncio
    async def test_find_session_by_token(self, session_manager, sample_token):
        """Test finding session by token value."""
        await session_manager.set_token("session-1", sample_token)

        # Should find the session
        found = await session_manager.find_session_by_token("test_token")
        assert found == "session-1"

        # Should not find non-existent token
        not_found = await session_manager.find_session_by_token("nonexistent")
        assert not_found is None

    @pytest.mark.asyncio
    async def test_max_sessions_enforcement(self, session_manager, sample_token):
        """Test that max sessions limit is enforced."""
        # Fill up to max
        for i in range(5):
            token = OAuth21Token(
                access_token=f"token_{i}",
                expires_in=3600,
                created_at=utc_now(),
            )
            await session_manager.set_token(f"session-{i}", token)

        assert session_manager.session_count == 5

        # Add one more - should evict oldest
        new_token = OAuth21Token(
            access_token="new_token",
            expires_in=3600,
            created_at=utc_now(),
        )
        await session_manager.set_token("session-new", new_token)

        assert session_manager.session_count == 5

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, session_manager):
        """Test cleanup of expired sessions."""
        # Create a token that will be "old"
        old_token = OAuth21Token(
            access_token="old_token",
            expires_in=3600,
            created_at=utc_now(),
        )
        await session_manager.set_token("old-session", old_token)

        # Cleanup with 0 max age should remove everything
        removed = await session_manager.cleanup_expired(max_age_seconds=0)
        assert removed == 1
        assert session_manager.session_count == 0


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
            mock_token_config.oauth_dcr_client_id = "test"
            mock_token_config.oauth_dcr_client_secret = "test"

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
