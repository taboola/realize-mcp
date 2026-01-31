"""Tests for OAuth 2.1 per-session token storage and authentication."""
import pathlib
import sys
sys.path.append(str(pathlib.Path(__file__).parent.parent / "src"))

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timedelta

from realize.oauth.session import InMemorySessionManager
from realize.oauth.token import TokenProxy
from realize.oauth.refresh import TokenRefresher
from realize.oauth.oauth21_auth import OAuth21Auth
from realize.models import OAuth21Token


class TestTokenRefresher:
    """Tests for TokenRefresher class."""

    @pytest.fixture
    def session_manager(self):
        return InMemorySessionManager()

    @pytest.fixture
    def token_proxy(self, session_manager):
        return TokenProxy(session_manager)

    @pytest.fixture
    def token_refresher(self, session_manager, token_proxy):
        with patch("realize.oauth.refresh.config") as mock_config:
            mock_config.oauth_refresh_buffer_seconds = 60
            return TokenRefresher(session_manager, token_proxy)

    @pytest.mark.asyncio
    async def test_returns_valid_token(self, token_refresher, session_manager):
        """Test that valid token is returned without refresh."""
        # Store a valid token
        token = OAuth21Token(
            access_token="valid-token",
            token_type="Bearer",
            expires_in=3600,
            created_at=datetime.now(),
        )
        await session_manager.set_token("test-session", token)

        result = await token_refresher.ensure_valid_token("test-session")

        assert result is not None
        assert result.access_token == "valid-token"

    @pytest.mark.asyncio
    async def test_returns_none_for_missing_session(self, token_refresher):
        """Test that None is returned for non-existent session."""
        result = await token_refresher.ensure_valid_token("nonexistent-session")
        assert result is None

    @pytest.mark.asyncio
    async def test_refreshes_expired_token(self, session_manager, token_proxy):
        """Test that expired token is refreshed."""
        # Store an expired token with refresh_token
        expired_token = OAuth21Token(
            access_token="expired-token",
            token_type="Bearer",
            expires_in=3600,
            refresh_token="refresh-token-123",
            created_at=datetime.now() - timedelta(hours=2),  # Expired
        )
        await session_manager.set_token("test-session", expired_token)

        # Mock the token proxy exchange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new-access-token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": "new-refresh-token",
        }

        with patch("realize.oauth.refresh.config") as mock_config:
            mock_config.oauth_refresh_buffer_seconds = 60

            with patch("realize.oauth.token.config") as mock_token_config:
                mock_token_config.oauth_server_url = "https://auth.example.com"
                mock_token_config.oauth_dcr_client_id = "test-client"
                mock_token_config.oauth_dcr_client_secret = "test-secret"

                with patch("realize.oauth.token.httpx.AsyncClient") as mock_client:
                    mock_instance = AsyncMock()
                    mock_instance.post.return_value = mock_response
                    mock_instance.__aenter__.return_value = mock_instance
                    mock_instance.__aexit__.return_value = None
                    mock_client.return_value = mock_instance

                    refresher = TokenRefresher(session_manager, token_proxy)
                    result = await refresher.ensure_valid_token("test-session")

                    assert result is not None
                    assert result.access_token == "new-access-token"

    @pytest.mark.asyncio
    async def test_deletes_session_on_refresh_failure(self, session_manager, token_proxy):
        """Test that session is deleted when refresh fails."""
        # Store an expired token with refresh_token
        expired_token = OAuth21Token(
            access_token="expired-token",
            token_type="Bearer",
            expires_in=3600,
            refresh_token="invalid-refresh-token",
            created_at=datetime.now() - timedelta(hours=2),
        )
        await session_manager.set_token("test-session", expired_token)

        # Mock the token proxy to fail
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "error": "invalid_grant",
            "error_description": "Refresh token expired",
        }

        with patch("realize.oauth.refresh.config") as mock_config:
            mock_config.oauth_refresh_buffer_seconds = 60

            with patch("realize.oauth.token.config") as mock_token_config:
                mock_token_config.oauth_server_url = "https://auth.example.com"
                mock_token_config.oauth_dcr_client_id = "test-client"
                mock_token_config.oauth_dcr_client_secret = "test-secret"

                with patch("realize.oauth.token.httpx.AsyncClient") as mock_client:
                    mock_instance = AsyncMock()
                    mock_instance.post.return_value = mock_response
                    mock_instance.__aenter__.return_value = mock_instance
                    mock_instance.__aexit__.return_value = None
                    mock_client.return_value = mock_instance

                    refresher = TokenRefresher(session_manager, token_proxy)
                    result = await refresher.ensure_valid_token("test-session")

                    assert result is None
                    # Session should be deleted
                    stored = await session_manager.get_token("test-session")
                    assert stored is None

    @pytest.mark.asyncio
    async def test_deletes_session_when_no_refresh_token(self, session_manager, token_proxy):
        """Test that session is deleted when token expired and no refresh_token."""
        # Store an expired token without refresh_token
        expired_token = OAuth21Token(
            access_token="expired-token",
            token_type="Bearer",
            expires_in=3600,
            refresh_token=None,  # No refresh token
            created_at=datetime.now() - timedelta(hours=2),
        )
        await session_manager.set_token("test-session", expired_token)

        with patch("realize.oauth.refresh.config") as mock_config:
            mock_config.oauth_refresh_buffer_seconds = 60

            refresher = TokenRefresher(session_manager, token_proxy)
            result = await refresher.ensure_valid_token("test-session")

            assert result is None
            stored = await session_manager.get_token("test-session")
            assert stored is None


class TestOAuth21Auth:
    """Tests for OAuth21Auth class."""

    @pytest.fixture
    def session_manager(self):
        return InMemorySessionManager()

    @pytest.fixture
    def token_proxy(self, session_manager):
        return TokenProxy(session_manager)

    @pytest.fixture
    def token_refresher(self, session_manager, token_proxy):
        with patch("realize.oauth.refresh.config") as mock_config:
            mock_config.oauth_refresh_buffer_seconds = 60
            return TokenRefresher(session_manager, token_proxy)

    @pytest.fixture
    def oauth21_auth(self, session_manager, token_refresher):
        return OAuth21Auth(session_manager, token_refresher)

    @pytest.mark.asyncio
    async def test_get_auth_header_returns_bearer_token(self, oauth21_auth, session_manager):
        """Test that get_auth_header returns proper Authorization header."""
        token = OAuth21Token(
            access_token="test-access-token",
            token_type="Bearer",
            expires_in=3600,
            created_at=datetime.now(),
        )
        await session_manager.set_token("test-session", token)

        header = await oauth21_auth.get_auth_header("test-session")

        assert header == {"Authorization": "Bearer test-access-token"}

    @pytest.mark.asyncio
    async def test_get_auth_header_returns_none_for_missing_session(self, oauth21_auth):
        """Test that get_auth_header returns None for non-existent session."""
        header = await oauth21_auth.get_auth_header("nonexistent-session")
        assert header is None

    @pytest.mark.asyncio
    async def test_get_token_returns_stored_token(self, oauth21_auth, session_manager):
        """Test that get_token returns token from session."""
        token = OAuth21Token(
            access_token="stored-token",
            token_type="Bearer",
            expires_in=3600,
            created_at=datetime.now(),
        )
        await session_manager.set_token("test-session", token)

        result = await oauth21_auth.get_token("test-session")

        assert result is not None
        assert result.access_token == "stored-token"

    @pytest.mark.asyncio
    async def test_is_authenticated_returns_true_for_valid_session(self, oauth21_auth, session_manager):
        """Test that is_authenticated returns True for valid token."""
        token = OAuth21Token(
            access_token="valid-token",
            token_type="Bearer",
            expires_in=3600,
            created_at=datetime.now(),
        )
        await session_manager.set_token("test-session", token)

        result = await oauth21_auth.is_authenticated("test-session")
        assert result is True

    @pytest.mark.asyncio
    async def test_is_authenticated_returns_false_for_missing_session(self, oauth21_auth):
        """Test that is_authenticated returns False for non-existent session."""
        result = await oauth21_auth.is_authenticated("nonexistent-session")
        assert result is False

    @pytest.mark.asyncio
    async def test_invalidate_session_removes_token(self, oauth21_auth, session_manager):
        """Test that invalidate_session removes token from storage."""
        token = OAuth21Token(
            access_token="to-be-removed",
            token_type="Bearer",
            expires_in=3600,
            created_at=datetime.now(),
        )
        await session_manager.set_token("test-session", token)

        await oauth21_auth.invalidate_session("test-session")

        stored = await session_manager.get_token("test-session")
        assert stored is None

    @pytest.mark.asyncio
    async def test_multiple_sessions_independent(self, oauth21_auth, session_manager):
        """Test that multiple sessions maintain independent tokens."""
        token1 = OAuth21Token(
            access_token="token-for-session-1",
            token_type="Bearer",
            expires_in=3600,
            created_at=datetime.now(),
        )
        token2 = OAuth21Token(
            access_token="token-for-session-2",
            token_type="Bearer",
            expires_in=3600,
            created_at=datetime.now(),
        )
        await session_manager.set_token("session-1", token1)
        await session_manager.set_token("session-2", token2)

        header1 = await oauth21_auth.get_auth_header("session-1")
        header2 = await oauth21_auth.get_auth_header("session-2")

        assert header1 == {"Authorization": "Bearer token-for-session-1"}
        assert header2 == {"Authorization": "Bearer token-for-session-2"}

        # Invalidate one session, other should be unaffected
        await oauth21_auth.invalidate_session("session-1")

        assert await oauth21_auth.is_authenticated("session-1") is False
        assert await oauth21_auth.is_authenticated("session-2") is True
