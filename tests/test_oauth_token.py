"""Tests for OAuth 2.1 token proxy."""
import pathlib
import sys
sys.path.append(str(pathlib.Path(__file__).parent.parent / "src"))

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime

from realize.oauth.token import TokenProxy, TokenProxyError
from realize.oauth.session import InMemorySessionManager
from realize.models import OAuth21Token


class TestTokenProxyExchangeToken:
    """Tests for TokenProxy.exchange_token method."""

    @pytest.fixture
    def session_manager(self):
        return InMemorySessionManager()

    @pytest.fixture
    def token_proxy(self, session_manager):
        return TokenProxy(session_manager)

    @pytest.mark.asyncio
    async def test_authorization_code_grant_success(self, token_proxy, session_manager):
        """Test successful authorization_code grant."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test-access-token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": "test-refresh-token",
            "scope": "all",
        }

        with patch("realize.oauth.token.config") as mock_config:
            mock_config.oauth_server_url = "https://auth.example.com"
            mock_config.oauth_dcr_client_id = "test-client"
            mock_config.oauth_dcr_client_secret = "test-secret"

            with patch("realize.oauth.token.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                token = await token_proxy.exchange_token(
                    grant_type="authorization_code",
                    session_id="test-session",
                    code="auth-code-123",
                    redirect_uri="http://localhost/callback",
                )

                assert token.access_token == "test-access-token"
                assert token.refresh_token == "test-refresh-token"
                assert token.expires_in == 3600

                # Verify token stored in session
                stored_token = await session_manager.get_token("test-session")
                assert stored_token is not None
                assert stored_token.access_token == "test-access-token"

    @pytest.mark.asyncio
    async def test_authorization_code_grant_with_pkce(self, token_proxy):
        """Test authorization_code grant with PKCE code_verifier."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test-access-token",
            "token_type": "Bearer",
            "expires_in": 3600,
        }

        with patch("realize.oauth.token.config") as mock_config:
            mock_config.oauth_server_url = "https://auth.example.com"
            mock_config.oauth_dcr_client_id = "test-client"
            mock_config.oauth_dcr_client_secret = "test-secret"

            with patch("realize.oauth.token.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                await token_proxy.exchange_token(
                    grant_type="authorization_code",
                    session_id="test-session",
                    code="auth-code-123",
                    redirect_uri="http://localhost/callback",
                    code_verifier="pkce-verifier-123",
                )

                # Verify code_verifier was included in request
                call_args = mock_instance.post.call_args
                assert call_args[1]["data"]["code_verifier"] == "pkce-verifier-123"

    @pytest.mark.asyncio
    async def test_refresh_token_grant_success(self, token_proxy, session_manager):
        """Test successful refresh_token grant."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new-access-token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": "new-refresh-token",
        }

        with patch("realize.oauth.token.config") as mock_config:
            mock_config.oauth_server_url = "https://auth.example.com"
            mock_config.oauth_dcr_client_id = "test-client"
            mock_config.oauth_dcr_client_secret = "test-secret"

            with patch("realize.oauth.token.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                token = await token_proxy.exchange_token(
                    grant_type="refresh_token",
                    session_id="test-session",
                    refresh_token="old-refresh-token",
                )

                assert token.access_token == "new-access-token"
                assert token.refresh_token == "new-refresh-token"

    @pytest.mark.asyncio
    async def test_missing_code_for_authorization_code_grant(self, token_proxy):
        """Test error when code missing for authorization_code grant."""
        with pytest.raises(ValueError) as exc_info:
            await token_proxy.exchange_token(
                grant_type="authorization_code",
                session_id="test-session",
                redirect_uri="http://localhost/callback",
            )
        assert "code required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_missing_redirect_uri_for_authorization_code_grant(self, token_proxy):
        """Test error when redirect_uri missing for authorization_code grant."""
        with pytest.raises(ValueError) as exc_info:
            await token_proxy.exchange_token(
                grant_type="authorization_code",
                session_id="test-session",
                code="auth-code-123",
            )
        assert "redirect_uri required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_missing_refresh_token_for_refresh_token_grant(self, token_proxy):
        """Test error when refresh_token missing for refresh_token grant."""
        with pytest.raises(ValueError) as exc_info:
            await token_proxy.exchange_token(
                grant_type="refresh_token",
                session_id="test-session",
            )
        assert "refresh_token required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_unsupported_grant_type(self, token_proxy):
        """Test error for unsupported grant_type."""
        with pytest.raises(ValueError) as exc_info:
            await token_proxy.exchange_token(
                grant_type="client_credentials",
                session_id="test-session",
            )
        assert "Unsupported grant_type" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_upstream_error_response(self, token_proxy):
        """Test handling of error response from upstream."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "error": "invalid_grant",
            "error_description": "Authorization code expired",
        }

        with patch("realize.oauth.token.config") as mock_config:
            mock_config.oauth_server_url = "https://auth.example.com"
            mock_config.oauth_dcr_client_id = "test-client"
            mock_config.oauth_dcr_client_secret = "test-secret"

            with patch("realize.oauth.token.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                with pytest.raises(TokenProxyError) as exc_info:
                    await token_proxy.exchange_token(
                        grant_type="authorization_code",
                        session_id="test-session",
                        code="expired-code",
                        redirect_uri="http://localhost/callback",
                    )
                assert "Authorization code expired" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_uses_correct_upstream_url(self, token_proxy):
        """Test that correct upstream URL is used."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test-token",
            "token_type": "Bearer",
            "expires_in": 3600,
        }

        with patch("realize.oauth.token.config") as mock_config:
            mock_config.oauth_server_url = "https://auth.example.com"
            mock_config.oauth_dcr_client_id = "test-client"
            mock_config.oauth_dcr_client_secret = "test-secret"

            with patch("realize.oauth.token.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                await token_proxy.exchange_token(
                    grant_type="authorization_code",
                    session_id="test-session",
                    code="auth-code",
                    redirect_uri="http://localhost/callback",
                )

                # Verify correct URL with /oauth2.1/token path
                call_args = mock_instance.post.call_args
                assert call_args[0][0] == "https://auth.example.com/oauth2.1/token"


class TestTokenProxyProxyRequest:
    """Tests for TokenProxy.proxy_token_request method."""

    @pytest.fixture
    def session_manager(self):
        return InMemorySessionManager()

    @pytest.fixture
    def token_proxy(self, session_manager):
        return TokenProxy(session_manager)

    @pytest.mark.asyncio
    async def test_proxy_returns_raw_response(self, token_proxy):
        """Test that proxy returns raw upstream response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test-token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "custom_field": "custom_value",
        }

        with patch("realize.oauth.token.config") as mock_config:
            mock_config.oauth_server_url = "https://auth.example.com"

            with patch("realize.oauth.token.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                response_data, status_code = await token_proxy.proxy_token_request(
                    form_data={"grant_type": "authorization_code", "code": "test"},
                    session_id="test-session",
                )

                assert status_code == 200
                assert response_data["access_token"] == "test-token"
                assert response_data["custom_field"] == "custom_value"

    @pytest.mark.asyncio
    async def test_proxy_stores_token_on_success(self, token_proxy, session_manager):
        """Test that successful proxy stores token in session."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test-token",
            "token_type": "Bearer",
            "expires_in": 3600,
        }

        with patch("realize.oauth.token.config") as mock_config:
            mock_config.oauth_server_url = "https://auth.example.com"

            with patch("realize.oauth.token.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                await token_proxy.proxy_token_request(
                    form_data={"grant_type": "authorization_code"},
                    session_id="test-session",
                )

                stored_token = await session_manager.get_token("test-session")
                assert stored_token is not None
                assert stored_token.access_token == "test-token"

    @pytest.mark.asyncio
    async def test_proxy_returns_error_response(self, token_proxy):
        """Test that proxy returns error response from upstream."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": "invalid_request",
            "error_description": "Missing required parameter",
        }

        with patch("realize.oauth.token.config") as mock_config:
            mock_config.oauth_server_url = "https://auth.example.com"

            with patch("realize.oauth.token.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                response_data, status_code = await token_proxy.proxy_token_request(
                    form_data={},
                    session_id="test-session",
                )

                assert status_code == 400
                assert response_data["error"] == "invalid_request"
