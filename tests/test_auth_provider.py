"""Tests for AuthProvider interface and implementations."""
import pathlib
import sys
sys.path.append(str(pathlib.Path(__file__).parent.parent / "src"))

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime

from realize.auth import AuthProvider, ClientCredentialsAuth, RealizeAuth
from realize.client import RealizeClient, create_client
from realize.oauth.session import InMemorySessionManager
from realize.oauth.token import TokenProxy
from realize.oauth.refresh import TokenRefresher
from realize.oauth.oauth21_auth import OAuth21Auth
from realize.models import OAuth21Token


class TestAuthProviderInterface:
    """Tests for AuthProvider ABC."""

    def test_client_credentials_auth_is_auth_provider(self):
        """Test that ClientCredentialsAuth implements AuthProvider."""
        auth = ClientCredentialsAuth()
        assert isinstance(auth, AuthProvider)

    def test_realize_auth_alias(self):
        """Test that RealizeAuth is alias for ClientCredentialsAuth."""
        assert RealizeAuth is ClientCredentialsAuth

    def test_oauth21_auth_is_auth_provider(self):
        """Test that OAuth21Auth implements AuthProvider."""
        session_manager = InMemorySessionManager()
        token_proxy = TokenProxy(session_manager)

        with patch("realize.oauth.refresh.config") as mock_config:
            mock_config.oauth_refresh_buffer_seconds = 60
            token_refresher = TokenRefresher(session_manager, token_proxy)
            oauth_auth = OAuth21Auth(session_manager, token_refresher)

            assert isinstance(oauth_auth, AuthProvider)


class TestClientCredentialsAuth:
    """Tests for ClientCredentialsAuth."""

    @pytest.mark.asyncio
    async def test_get_auth_header_ignores_session_id(self):
        """Test that session_id is ignored by ClientCredentialsAuth."""
        auth = ClientCredentialsAuth()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "test-token",
            "token_type": "Bearer",
            "expires_in": 3600,
        }
        mock_response.raise_for_status = MagicMock()

        with patch("realize.auth.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            # With session_id
            header1 = await auth.get_auth_header(session_id="session-123")
            # Without session_id
            header2 = await auth.get_auth_header()

            assert header1 == {"Authorization": "Bearer test-token"}
            assert header2 == {"Authorization": "Bearer test-token"}


class TestOAuth21AuthProvider:
    """Tests for OAuth21Auth as AuthProvider."""

    @pytest.fixture
    def session_manager(self):
        return InMemorySessionManager()

    @pytest.fixture
    def oauth_auth(self, session_manager):
        token_proxy = TokenProxy(session_manager)
        with patch("realize.oauth.refresh.config") as mock_config:
            mock_config.oauth_refresh_buffer_seconds = 60
            token_refresher = TokenRefresher(session_manager, token_proxy)
            return OAuth21Auth(session_manager, token_refresher)

    @pytest.mark.asyncio
    async def test_requires_session_id(self, oauth_auth):
        """Test that OAuth21Auth raises error without session_id."""
        with pytest.raises(ValueError) as exc_info:
            await oauth_auth.get_auth_header()

        assert "session_id is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_returns_header_with_session_id(self, oauth_auth, session_manager):
        """Test that OAuth21Auth returns header when session has token."""
        token = OAuth21Token(
            access_token="session-token",
            token_type="Bearer",
            expires_in=3600,
            created_at=datetime.now(),
        )
        await session_manager.set_token("test-session", token)

        header = await oauth_auth.get_auth_header(session_id="test-session")

        assert header == {"Authorization": "Bearer session-token"}


class TestRealizeClientWithAuthProvider:
    """Tests for RealizeClient with different auth providers."""

    def test_default_uses_global_auth(self):
        """Test that RealizeClient uses global auth by default."""
        client = RealizeClient()
        assert client.auth_provider is not None

    def test_accepts_custom_auth_provider(self):
        """Test that RealizeClient accepts custom auth provider."""
        session_manager = InMemorySessionManager()
        token_proxy = TokenProxy(session_manager)

        with patch("realize.oauth.refresh.config") as mock_config:
            mock_config.oauth_refresh_buffer_seconds = 60
            token_refresher = TokenRefresher(session_manager, token_proxy)
            oauth_auth = OAuth21Auth(session_manager, token_refresher)

            client = RealizeClient(auth_provider=oauth_auth)

            assert client.auth_provider is oauth_auth

    def test_create_client_factory(self):
        """Test create_client factory function."""
        auth = ClientCredentialsAuth()
        client = create_client(auth)

        assert isinstance(client, RealizeClient)
        assert client.auth_provider is auth

    @pytest.mark.asyncio
    async def test_request_passes_session_id_to_auth(self):
        """Test that request passes session_id to auth provider."""
        mock_auth = AsyncMock(spec=AuthProvider)
        mock_auth.get_auth_header.return_value = {"Authorization": "Bearer test"}

        client = RealizeClient(auth_provider=mock_auth)

        mock_response = MagicMock()
        mock_response.json.return_value = {"result": "ok"}
        mock_response.raise_for_status = MagicMock()

        with patch("realize.client.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.request.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            await client.get("/test", session_id="my-session")

            mock_auth.get_auth_header.assert_called_once_with("my-session")

    @pytest.mark.asyncio
    async def test_request_raises_on_no_auth(self):
        """Test that request raises error when auth returns None."""
        mock_auth = AsyncMock(spec=AuthProvider)
        mock_auth.get_auth_header.return_value = None

        client = RealizeClient(auth_provider=mock_auth)

        with pytest.raises(ValueError) as exc_info:
            await client.get("/test", session_id="invalid-session")

        assert "No valid authentication" in str(exc_info.value)
