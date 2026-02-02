"""Tests for OAuth 2.1 Dynamic Client Registration (RFC 7591)."""
import pathlib
import sys
sys.path.append(str(pathlib.Path(__file__).parent.parent / "src"))

import pytest
from unittest.mock import patch
from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.routing import Route

from realize.oauth.dcr import handle_client_registration, DCRError
from realize.oauth.routes import register_handler


class TestHandleClientRegistration:
    """Tests for handle_client_registration function."""

    def test_returns_credentials_from_env(self):
        """Verify client_id and client_secret come from environment."""
        with patch("realize.oauth.dcr.config") as mock_config:
            mock_config.oauth_dcr_client_id = "test-client-id"
            mock_config.oauth_dcr_client_secret = "test-client-secret"

            response = handle_client_registration({})

            assert response["client_id"] == "test-client-id"
            assert response["client_secret"] == "test-client-secret"

    def test_raises_error_when_credentials_not_configured(self):
        """Verify DCRError raised when env vars not set."""
        with patch("realize.oauth.dcr.config") as mock_config:
            mock_config.oauth_dcr_client_id = None
            mock_config.oauth_dcr_client_secret = None

            with pytest.raises(DCRError) as exc_info:
                handle_client_registration({})

            assert "not configured" in str(exc_info.value)

    def test_raises_error_when_only_client_id_configured(self):
        """Verify DCRError raised when only client_id is set."""
        with patch("realize.oauth.dcr.config") as mock_config:
            mock_config.oauth_dcr_client_id = "test-client-id"
            mock_config.oauth_dcr_client_secret = None

            with pytest.raises(DCRError):
                handle_client_registration({})

    def test_includes_issued_at_timestamp(self):
        """Verify client_id_issued_at is included."""
        with patch("realize.oauth.dcr.config") as mock_config:
            mock_config.oauth_dcr_client_id = "test-client-id"
            mock_config.oauth_dcr_client_secret = "test-client-secret"

            response = handle_client_registration({})

            assert "client_id_issued_at" in response
            assert isinstance(response["client_id_issued_at"], int)
            assert response["client_id_issued_at"] > 0

    def test_secret_does_not_expire(self):
        """Verify client_secret_expires_at is 0 (no expiry)."""
        with patch("realize.oauth.dcr.config") as mock_config:
            mock_config.oauth_dcr_client_id = "test-client-id"
            mock_config.oauth_dcr_client_secret = "test-client-secret"

            response = handle_client_registration({})

            assert response["client_secret_expires_at"] == 0

    def test_echoes_redirect_uris(self):
        """Verify redirect_uris from request are echoed back."""
        with patch("realize.oauth.dcr.config") as mock_config:
            mock_config.oauth_dcr_client_id = "test-client-id"
            mock_config.oauth_dcr_client_secret = "test-client-secret"

            request_data = {
                "redirect_uris": ["http://localhost:8080/callback", "http://localhost:3000/auth"]
            }
            response = handle_client_registration(request_data)

            assert response["redirect_uris"] == request_data["redirect_uris"]

    def test_echoes_client_name(self):
        """Verify client_name from request is echoed back."""
        with patch("realize.oauth.dcr.config") as mock_config:
            mock_config.oauth_dcr_client_id = "test-client-id"
            mock_config.oauth_dcr_client_secret = "test-client-secret"

            request_data = {"client_name": "My MCP Client"}
            response = handle_client_registration(request_data)

            assert response["client_name"] == "My MCP Client"

    def test_default_grant_types(self):
        """Verify default grant_types when not specified."""
        with patch("realize.oauth.dcr.config") as mock_config:
            mock_config.oauth_dcr_client_id = "test-client-id"
            mock_config.oauth_dcr_client_secret = "test-client-secret"

            response = handle_client_registration({})

            assert response["grant_types"] == ["authorization_code"]

    def test_default_response_types(self):
        """Verify default response_types when not specified."""
        with patch("realize.oauth.dcr.config") as mock_config:
            mock_config.oauth_dcr_client_id = "test-client-id"
            mock_config.oauth_dcr_client_secret = "test-client-secret"

            response = handle_client_registration({})

            assert response["response_types"] == ["code"]

    def test_default_token_endpoint_auth_method(self):
        """Verify default token_endpoint_auth_method when not specified."""
        with patch("realize.oauth.dcr.config") as mock_config:
            mock_config.oauth_dcr_client_id = "test-client-id"
            mock_config.oauth_dcr_client_secret = "test-client-secret"

            response = handle_client_registration({})

            assert response["token_endpoint_auth_method"] == "client_secret_post"

    def test_override_grant_types(self):
        """Verify grant_types can be overridden by request."""
        with patch("realize.oauth.dcr.config") as mock_config:
            mock_config.oauth_dcr_client_id = "test-client-id"
            mock_config.oauth_dcr_client_secret = "test-client-secret"

            request_data = {"grant_types": ["authorization_code", "refresh_token"]}
            response = handle_client_registration(request_data)

            assert response["grant_types"] == ["authorization_code", "refresh_token"]


class TestRegisterRouteHandler:
    """Tests for /register HTTP endpoint."""

    def test_returns_201_on_success(self):
        """Verify POST /register returns 201 Created."""
        app = Starlette(routes=[
            Route("/register", register_handler, methods=["POST"]),
        ])

        with patch("realize.oauth.dcr.config") as mock_config:
            mock_config.oauth_dcr_client_id = "test-client-id"
            mock_config.oauth_dcr_client_secret = "test-client-secret"

            client = TestClient(app)
            response = client.post("/register", json={"client_name": "Test"})

            assert response.status_code == 201
            assert response.headers["content-type"] == "application/json"

    def test_returns_400_when_not_configured(self):
        """Verify POST /register returns 400 when DCR not configured."""
        app = Starlette(routes=[
            Route("/register", register_handler, methods=["POST"]),
        ])

        with patch("realize.oauth.dcr.config") as mock_config:
            mock_config.oauth_dcr_client_id = None
            mock_config.oauth_dcr_client_secret = None

            client = TestClient(app)
            response = client.post("/register", json={})

            assert response.status_code == 400
            data = response.json()
            assert data["error"] == "invalid_request"
            assert "not configured" in data["error_description"]

    def test_handles_empty_body(self):
        """Verify POST /register handles empty request body."""
        app = Starlette(routes=[
            Route("/register", register_handler, methods=["POST"]),
        ])

        with patch("realize.oauth.dcr.config") as mock_config:
            mock_config.oauth_dcr_client_id = "test-client-id"
            mock_config.oauth_dcr_client_secret = "test-client-secret"

            client = TestClient(app)
            response = client.post("/register", content="", headers={"content-type": "application/json"})

            # Should handle gracefully and return defaults
            assert response.status_code == 201

    def test_response_contains_required_fields(self):
        """Verify response contains all RFC 7591 required fields."""
        app = Starlette(routes=[
            Route("/register", register_handler, methods=["POST"]),
        ])

        with patch("realize.oauth.dcr.config") as mock_config:
            mock_config.oauth_dcr_client_id = "test-client-id"
            mock_config.oauth_dcr_client_secret = "test-client-secret"

            client = TestClient(app)
            response = client.post("/register", json={"redirect_uris": ["http://localhost/cb"]})

            data = response.json()
            assert "client_id" in data
            assert "client_secret" in data
            assert "client_id_issued_at" in data
            assert "client_secret_expires_at" in data
