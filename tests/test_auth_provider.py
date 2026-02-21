"""Tests for AuthProvider interface and implementations."""
import pathlib
import sys
sys.path.append(str(pathlib.Path(__file__).parent.parent / "src"))

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from realize.auth import AuthProvider, ClientCredentialsAuth, RealizeAuth, SSETokenAuth
from realize.client import RealizeClient, create_client


class TestAuthProviderInterface:
    """Tests for AuthProvider ABC."""

    def test_client_credentials_auth_is_auth_provider(self):
        """Test that ClientCredentialsAuth implements AuthProvider."""
        auth = ClientCredentialsAuth()
        assert isinstance(auth, AuthProvider)

    def test_realize_auth_alias(self):
        """Test that RealizeAuth is alias for ClientCredentialsAuth."""
        assert RealizeAuth is ClientCredentialsAuth

    def test_sse_token_auth_is_auth_provider(self):
        """Test that SSETokenAuth implements AuthProvider."""
        auth = SSETokenAuth()
        assert isinstance(auth, AuthProvider)


class TestClientCredentialsAuth:
    """Tests for ClientCredentialsAuth."""

    @pytest.mark.asyncio
    async def test_get_auth_header(self):
        """Test that ClientCredentialsAuth returns valid auth header."""
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

            header = await auth.get_auth_header()
            assert header == {"Authorization": "Bearer test-token"}


class TestSSETokenAuth:
    """Tests for SSETokenAuth (stateless context-based auth)."""

    @pytest.mark.asyncio
    async def test_returns_none_without_context_token(self):
        """Test that SSETokenAuth returns None when no token in context."""
        auth = SSETokenAuth()
        header = await auth.get_auth_header()
        assert header is None

    @pytest.mark.asyncio
    async def test_returns_bearer_header_with_context_token(self):
        """Test that SSETokenAuth returns Bearer header when token is in context."""
        from realize.oauth.context import set_session_token, clear_session_token

        auth = SSETokenAuth()

        set_session_token("test-context-token")
        try:
            header = await auth.get_auth_header()
            assert header == {"Authorization": "Bearer test-context-token"}
        finally:
            clear_session_token()


class TestRealizeClientWithAuthProvider:
    """Tests for RealizeClient with different auth providers."""

    def test_default_uses_global_auth(self):
        """Test that RealizeClient uses global auth by default."""
        client = RealizeClient()
        assert client.auth_provider is not None

    def test_accepts_custom_auth_provider(self):
        """Test that RealizeClient accepts custom auth provider."""
        auth = SSETokenAuth()
        client = RealizeClient(auth_provider=auth)
        assert client.auth_provider is auth

    def test_create_client_factory(self):
        """Test create_client factory function."""
        auth = ClientCredentialsAuth()
        client = create_client(auth)

        assert isinstance(client, RealizeClient)
        assert client.auth_provider is auth

    @pytest.mark.asyncio
    async def test_request_calls_auth_provider(self):
        """Test that request calls auth provider for header."""
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

            await client.get("/test")

            mock_auth.get_auth_header.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_raises_on_no_auth(self):
        """Test that request raises error when auth returns None."""
        mock_auth = AsyncMock(spec=AuthProvider)
        mock_auth.get_auth_header.return_value = None

        client = RealizeClient(auth_provider=mock_auth)

        with pytest.raises(ValueError) as exc_info:
            await client.get("/test")

        assert "No valid authentication" in str(exc_info.value)