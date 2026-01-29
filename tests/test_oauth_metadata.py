"""Tests for OAuth 2.1 metadata endpoints (RFC 8414 and RFC 9728)."""
import pathlib
import sys
sys.path.append(str(pathlib.Path(__file__).parent.parent / "src"))

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.routing import Route

from realize.oauth.metadata import (
    get_protected_resource_metadata,
    proxy_authorization_server_metadata,
)
from realize.oauth.routes import (
    protected_resource_metadata_handler,
    authorization_server_metadata_handler,
)


class TestProtectedResourceMetadata:
    """Tests for RFC 9728 Protected Resource Metadata."""

    def test_returns_correct_structure(self):
        """Verify metadata has all required RFC 9728 fields."""
        with patch("realize.oauth.metadata.config") as mock_config:
            mock_config.mcp_server_url = "https://mcp.example.com"
            mock_config.oauth_server_url = "https://auth.example.com"
            mock_config.oauth_scopes = "read write admin"

            metadata = get_protected_resource_metadata()

            assert metadata["resource"] == "https://mcp.example.com"
            # authorization_servers points to MCP server so clients fetch
            # modified AS metadata (with proxied endpoints) from us
            assert metadata["authorization_servers"] == ["https://mcp.example.com"]
            assert metadata["bearer_methods_supported"] == ["header"]
            assert metadata["scopes_supported"] == ["read", "write", "admin"]
            assert "resource_documentation" in metadata

    def test_scopes_split_correctly(self):
        """Verify space-separated scopes are split into list."""
        with patch("realize.oauth.metadata.config") as mock_config:
            mock_config.mcp_server_url = "https://mcp.example.com"
            mock_config.oauth_server_url = "https://auth.example.com"
            mock_config.oauth_scopes = "all"

            metadata = get_protected_resource_metadata()

            assert metadata["scopes_supported"] == ["all"]

    def test_single_authorization_server(self):
        """Verify authorization_servers is a list with single entry."""
        with patch("realize.oauth.metadata.config") as mock_config:
            mock_config.mcp_server_url = "https://mcp.example.com"
            mock_config.oauth_server_url = "https://auth.example.com"
            mock_config.oauth_scopes = "all"

            metadata = get_protected_resource_metadata()

            assert isinstance(metadata["authorization_servers"], list)
            assert len(metadata["authorization_servers"]) == 1


class TestAuthorizationServerMetadataProxy:
    """Tests for RFC 8414 Authorization Server Metadata proxy."""

    @pytest.mark.asyncio
    async def test_proxies_required_fields(self):
        """Verify required RFC 8414 fields are included and endpoints are proxied."""
        upstream_metadata = {
            "issuer": "https://auth.example.com",
            "authorization_endpoint": "https://auth.example.com/authorize",
            "token_endpoint": "https://auth.example.com/token",
            "response_types_supported": ["code"],
            "extra_field": "should_be_preserved",
        }

        mock_response = MagicMock()
        mock_response.json.return_value = upstream_metadata
        mock_response.raise_for_status = MagicMock()

        with patch("realize.oauth.metadata.config") as mock_config:
            mock_config.oauth_server_url = "https://auth.example.com"
            mock_config.mcp_server_url = "https://mcp.example.com"

            with patch("realize.oauth.metadata.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                metadata = await proxy_authorization_server_metadata()

                # Required fields preserved
                assert metadata["issuer"] == "https://auth.example.com"
                assert metadata["response_types_supported"] == ["code"]
                # All OAuth endpoints proxied through MCP server's HTTPS URL
                # (authorization_endpoint is proxied because some clients refuse HTTP URLs)
                assert metadata["authorization_endpoint"] == "https://mcp.example.com/authorize"
                assert metadata["token_endpoint"] == "https://mcp.example.com/oauth/token"
                assert metadata["registration_endpoint"] == "https://mcp.example.com/register"
                # Extra fields are preserved (not filtered)
                assert metadata["extra_field"] == "should_be_preserved"

    @pytest.mark.asyncio
    async def test_includes_optional_fields_when_present(self):
        """Verify optional fields are included and auth methods are filtered."""
        upstream_metadata = {
            "issuer": "https://auth.example.com",
            "authorization_endpoint": "https://auth.example.com/authorize",
            "token_endpoint": "https://auth.example.com/token",
            "response_types_supported": ["code"],
            "registration_endpoint": "https://auth.example.com/register",
            "scopes_supported": ["openid", "profile"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "code_challenge_methods_supported": ["S256"],
            "token_endpoint_auth_methods_supported": ["client_secret_post", "none"],
        }

        mock_response = MagicMock()
        mock_response.json.return_value = upstream_metadata
        mock_response.raise_for_status = MagicMock()

        with patch("realize.oauth.metadata.config") as mock_config:
            mock_config.oauth_server_url = "https://auth.example.com"
            mock_config.mcp_server_url = "https://mcp.example.com"

            with patch("realize.oauth.metadata.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                metadata = await proxy_authorization_server_metadata()

                # Registration endpoint is overridden to MCP server
                assert metadata["registration_endpoint"] == "https://mcp.example.com/register"
                # Other optional fields preserved
                assert metadata["scopes_supported"] == ["openid", "profile"]
                assert metadata["grant_types_supported"] == ["authorization_code", "refresh_token"]
                assert metadata["code_challenge_methods_supported"] == ["S256"]
                # "none" is filtered out from auth methods
                assert metadata["token_endpoint_auth_methods_supported"] == ["client_secret_post"]

    @pytest.mark.asyncio
    async def test_fetches_from_correct_url(self):
        """Verify the correct well-known URL is called."""
        upstream_metadata = {
            "issuer": "https://auth.example.com",
            "authorization_endpoint": "https://auth.example.com/authorize",
            "token_endpoint": "https://auth.example.com/token",
            "response_types_supported": ["code"],
        }

        mock_response = MagicMock()
        mock_response.json.return_value = upstream_metadata
        mock_response.raise_for_status = MagicMock()

        with patch("realize.oauth.metadata.config") as mock_config:
            mock_config.oauth_server_url = "https://auth.example.com"
            mock_config.mcp_server_url = "https://mcp.example.com"

            with patch("realize.oauth.metadata.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                await proxy_authorization_server_metadata()

                mock_instance.get.assert_called_once_with(
                    "https://auth.example.com/.well-known/oauth-authorization-server",
                    timeout=10.0,
                )


class TestMetadataRouteHandlers:
    """Tests for OAuth metadata HTTP route handlers."""

    def test_protected_resource_endpoint_returns_200(self):
        """Verify /.well-known/oauth-protected-resource returns 200."""
        app = Starlette(routes=[
            Route("/.well-known/oauth-protected-resource", protected_resource_metadata_handler),
        ])

        with patch("realize.oauth.metadata.config") as mock_config:
            mock_config.mcp_server_url = "https://mcp.example.com"
            mock_config.oauth_server_url = "https://auth.example.com"
            mock_config.oauth_scopes = "all"

            client = TestClient(app)
            response = client.get("/.well-known/oauth-protected-resource")

            assert response.status_code == 200
            assert response.headers["content-type"] == "application/json"
            data = response.json()
            assert "resource" in data
            assert "authorization_servers" in data

    def test_authorization_server_endpoint_returns_200_on_success(self):
        """Verify /.well-known/oauth-authorization-server returns 200 on success."""
        app = Starlette(routes=[
            Route("/.well-known/oauth-authorization-server", authorization_server_metadata_handler),
        ])

        upstream_metadata = {
            "issuer": "https://auth.example.com",
            "authorization_endpoint": "https://auth.example.com/authorize",
            "token_endpoint": "https://auth.example.com/token",
            "response_types_supported": ["code"],
        }

        mock_response = MagicMock()
        mock_response.json.return_value = upstream_metadata
        mock_response.raise_for_status = MagicMock()

        with patch("realize.oauth.metadata.config") as mock_config:
            mock_config.oauth_server_url = "https://auth.example.com"
            mock_config.mcp_server_url = "https://mcp.example.com"

            with patch("realize.oauth.metadata.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                client = TestClient(app)
                response = client.get("/.well-known/oauth-authorization-server")

                assert response.status_code == 200
                assert response.headers["content-type"] == "application/json"

    def test_authorization_server_endpoint_returns_502_on_upstream_error(self):
        """Verify /.well-known/oauth-authorization-server returns 502 on upstream error."""
        app = Starlette(routes=[
            Route("/.well-known/oauth-authorization-server", authorization_server_metadata_handler),
        ])

        with patch("realize.oauth.metadata.config") as mock_config:
            mock_config.oauth_server_url = "https://auth.example.com"

            with patch("realize.oauth.metadata.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.side_effect = Exception("Connection refused")
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                client = TestClient(app)
                response = client.get("/.well-known/oauth-authorization-server")

                assert response.status_code == 502
                data = response.json()
                assert data["error"] == "upstream_error"
                assert "Connection refused" in data["error_description"]
