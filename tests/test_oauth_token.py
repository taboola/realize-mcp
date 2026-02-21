"""Tests for OAuth 2.1 token proxy (stateless)."""
import pathlib
import sys
sys.path.append(str(pathlib.Path(__file__).parent.parent / "src"))

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from realize.oauth.token import TokenProxy, TokenProxyError


class TestTokenProxyProxyRequest:
    """Tests for TokenProxy.proxy_token_request method (stateless)."""

    @pytest.fixture
    def token_proxy(self):
        return TokenProxy()

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
                )

                assert status_code == 200
                assert response_data["access_token"] == "test-token"
                assert response_data["custom_field"] == "custom_value"

    @pytest.mark.asyncio
    async def test_proxy_does_not_store_token(self, token_proxy):
        """Test that proxy does NOT store token server-side (stateless)."""
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

                response_data, status_code = await token_proxy.proxy_token_request(
                    form_data={"grant_type": "authorization_code"},
                )

                assert status_code == 200
                # Token is returned to client but not stored anywhere
                assert response_data["access_token"] == "test-token"
                # No session_manager attribute on TokenProxy
                assert not hasattr(token_proxy, 'session_manager')

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
                )

                assert status_code == 400
                assert response_data["error"] == "invalid_request"

    @pytest.mark.asyncio
    async def test_proxy_handles_connection_error(self, token_proxy):
        """Test that proxy handles upstream connection errors."""
        import httpx

        with patch("realize.oauth.token.config") as mock_config:
            mock_config.oauth_server_url = "https://auth.example.com"

            with patch("realize.oauth.token.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post.side_effect = httpx.RequestError("Connection refused")
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                response_data, status_code = await token_proxy.proxy_token_request(
                    form_data={"grant_type": "authorization_code"},
                )

                assert status_code == 502
                assert response_data["error"] == "server_error"

    @pytest.mark.asyncio
    async def test_proxy_handles_non_json_response(self, token_proxy):
        """Test that proxy handles non-JSON upstream response."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.side_effect = Exception("Not JSON")

        with patch("realize.oauth.token.config") as mock_config:
            mock_config.oauth_server_url = "https://auth.example.com"

            with patch("realize.oauth.token.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                response_data, status_code = await token_proxy.proxy_token_request(
                    form_data={"grant_type": "authorization_code"},
                )

                assert status_code == 502
                assert response_data["error"] == "server_error"

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

            with patch("realize.oauth.token.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                await token_proxy.proxy_token_request(
                    form_data={"grant_type": "authorization_code", "code": "test"},
                )

                # Verify correct URL with /oauth2.1/token path
                call_args = mock_instance.post.call_args
                assert call_args[0][0] == "https://auth.example.com/oauth2.1/token"

    @pytest.mark.asyncio
    async def test_proxy_forwards_all_form_data(self, token_proxy):
        """Test that proxy forwards all form data to upstream."""
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

                form_data = {
                    "grant_type": "authorization_code",
                    "code": "auth-code-123",
                    "redirect_uri": "http://localhost/callback",
                    "code_verifier": "pkce-verifier-123",
                    "client_id": "test-client",
                    "client_secret": "test-secret",
                }

                await token_proxy.proxy_token_request(form_data=form_data)

                # Verify all form data was forwarded
                call_args = mock_instance.post.call_args
                assert call_args[1]["data"] == form_data