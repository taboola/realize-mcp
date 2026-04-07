"""Tests for OAuth 2.1 Dynamic Client Registration (RFC 7591)."""
import logging
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

    def test_returns_client_id_from_env(self):
        """Verify client_id comes from environment."""
        with patch("realize.oauth.dcr.config") as mock_config:
            mock_config.oauth_dcr_client_id = "test-client-id"

            response = handle_client_registration({})

            assert response["client_id"] == "test-client-id"
            assert "client_secret" not in response

    def test_raises_error_when_not_configured(self):
        """Verify DCRError raised when env vars not set."""
        with patch("realize.oauth.dcr.config") as mock_config:
            mock_config.oauth_dcr_client_id = None

            with pytest.raises(DCRError) as exc_info:
                handle_client_registration({})

            assert "not configured" in str(exc_info.value)

    def test_includes_issued_at_timestamp(self):
        """Verify client_id_issued_at is included."""
        with patch("realize.oauth.dcr.config") as mock_config:
            mock_config.oauth_dcr_client_id = "test-client-id"

            response = handle_client_registration({})

            assert "client_id_issued_at" in response
            assert isinstance(response["client_id_issued_at"], int)
            assert response["client_id_issued_at"] > 0

    def test_echoes_redirect_uris(self):
        """Verify redirect_uris from request are echoed back."""
        with patch("realize.oauth.dcr.config") as mock_config:
            mock_config.oauth_dcr_client_id = "test-client-id"

            request_data = {
                "redirect_uris": ["http://localhost:8080/callback", "http://localhost:3000/auth"]
            }
            response = handle_client_registration(request_data)

            assert response["redirect_uris"] == request_data["redirect_uris"]

    def test_echoes_client_name(self):
        """Verify client_name from request is echoed back."""
        with patch("realize.oauth.dcr.config") as mock_config:
            mock_config.oauth_dcr_client_id = "test-client-id"

            request_data = {"client_name": "My MCP Client"}
            response = handle_client_registration(request_data)

            assert response["client_name"] == "My MCP Client"

    def test_default_grant_types(self):
        """Verify default grant_types when not specified."""
        with patch("realize.oauth.dcr.config") as mock_config:
            mock_config.oauth_dcr_client_id = "test-client-id"

            response = handle_client_registration({})

            assert response["grant_types"] == ["authorization_code"]

    def test_default_response_types(self):
        """Verify default response_types when not specified."""
        with patch("realize.oauth.dcr.config") as mock_config:
            mock_config.oauth_dcr_client_id = "test-client-id"

            response = handle_client_registration({})

            assert response["response_types"] == ["code"]

    def test_default_token_endpoint_auth_method(self):
        """Verify default token_endpoint_auth_method is 'none' (PKCE public client)."""
        with patch("realize.oauth.dcr.config") as mock_config:
            mock_config.oauth_dcr_client_id = "test-client-id"

            response = handle_client_registration({})

            assert response["token_endpoint_auth_method"] == "none"

    def test_override_grant_types(self):
        """Verify grant_types can be overridden by request."""
        with patch("realize.oauth.dcr.config") as mock_config:
            mock_config.oauth_dcr_client_id = "test-client-id"

            request_data = {"grant_types": ["authorization_code", "refresh_token"]}
            response = handle_client_registration(request_data)

            assert response["grant_types"] == ["authorization_code", "refresh_token"]


class TestDCRValidation:
    """Tests for DCR input validation."""

    def _register(self, request_data):
        with patch("realize.oauth.dcr.config") as mock_config:
            mock_config.oauth_dcr_client_id = "test-client-id"
            return handle_client_registration(request_data)

    # --- redirect_uris ---

    def test_allows_https_redirect(self):
        response = self._register({"redirect_uris": ["https://example.com/callback"]})
        assert response["redirect_uris"] == ["https://example.com/callback"]

    def test_allows_localhost_redirect(self):
        response = self._register({"redirect_uris": ["http://localhost:3000/callback"]})
        assert response["redirect_uris"] == ["http://localhost:3000/callback"]

    def test_allows_127_redirect(self):
        response = self._register({"redirect_uris": ["http://127.0.0.1:8080/callback"]})
        assert response["redirect_uris"] == ["http://127.0.0.1:8080/callback"]

    def test_allows_custom_scheme_redirect(self):
        response = self._register({"redirect_uris": ["myapp://callback"]})
        assert response["redirect_uris"] == ["myapp://callback"]

    def test_rejects_http_non_loopback_redirect(self):
        with pytest.raises(DCRError) as exc_info:
            self._register({"redirect_uris": ["http://evil.com/callback"]})
        assert exc_info.value.error_code == "invalid_redirect_uri"

    def test_rejects_mixed_valid_and_invalid_redirects(self):
        with pytest.raises(DCRError) as exc_info:
            self._register({"redirect_uris": [
                "http://localhost:3000/cb",
                "http://attacker.com/steal",
            ]})
        assert exc_info.value.error_code == "invalid_redirect_uri"

    # --- grant_types ---

    def test_allows_authorization_code(self):
        response = self._register({"grant_types": ["authorization_code"]})
        assert response["grant_types"] == ["authorization_code"]

    def test_allows_authorization_code_with_refresh_token(self):
        response = self._register({"grant_types": ["authorization_code", "refresh_token"]})
        assert response["grant_types"] == ["authorization_code", "refresh_token"]

    def test_rejects_implicit_grant(self):
        with pytest.raises(DCRError) as exc_info:
            self._register({"grant_types": ["implicit"]})
        assert exc_info.value.error_code == "invalid_client_metadata"

    def test_rejects_client_credentials_grant(self):
        with pytest.raises(DCRError) as exc_info:
            self._register({"grant_types": ["client_credentials"]})
        assert exc_info.value.error_code == "invalid_client_metadata"

    def test_rejects_password_grant(self):
        with pytest.raises(DCRError) as exc_info:
            self._register({"grant_types": ["password"]})
        assert exc_info.value.error_code == "invalid_client_metadata"

    # --- response_types ---

    def test_allows_code_response_type(self):
        response = self._register({"response_types": ["code"]})
        assert response["response_types"] == ["code"]

    def test_rejects_token_response_type(self):
        with pytest.raises(DCRError) as exc_info:
            self._register({"response_types": ["token"]})
        assert exc_info.value.error_code == "invalid_client_metadata"

    # --- token_endpoint_auth_method ---

    def test_allows_none_auth_method(self):
        response = self._register({"token_endpoint_auth_method": "none"})
        assert response["token_endpoint_auth_method"] == "none"

    def test_rejects_client_secret_post(self):
        with pytest.raises(DCRError) as exc_info:
            self._register({"token_endpoint_auth_method": "client_secret_post"})
        assert exc_info.value.error_code == "invalid_client_metadata"

    def test_rejects_client_secret_basic(self):
        with pytest.raises(DCRError) as exc_info:
            self._register({"token_endpoint_auth_method": "client_secret_basic"})
        assert exc_info.value.error_code == "invalid_client_metadata"

    # --- jwks_uri / jwks ---

    def test_rejects_jwks_uri(self):
        with pytest.raises(DCRError) as exc_info:
            self._register({"jwks_uri": "https://example.com/.well-known/jwks.json"})
        assert exc_info.value.error_code == "invalid_client_metadata"

    def test_rejects_jwks(self):
        with pytest.raises(DCRError) as exc_info:
            self._register({"jwks": {"keys": []}})
        assert exc_info.value.error_code == "invalid_client_metadata"

    # --- type checks (RFC 7591 requires arrays) ---

    def test_rejects_redirect_uris_as_string(self):
        with pytest.raises(DCRError) as exc_info:
            self._register({"redirect_uris": "http://localhost:3000/cb"})
        assert exc_info.value.error_code == "invalid_redirect_uri"

    def test_rejects_grant_types_as_string(self):
        with pytest.raises(DCRError) as exc_info:
            self._register({"grant_types": "authorization_code"})
        assert exc_info.value.error_code == "invalid_client_metadata"

    def test_rejects_response_types_as_string(self):
        with pytest.raises(DCRError) as exc_info:
            self._register({"response_types": "code"})
        assert exc_info.value.error_code == "invalid_client_metadata"

    # --- omitted fields still work ---

    def test_empty_body_still_succeeds(self):
        response = self._register({})
        assert response["client_id"] == "test-client-id"
        assert response["grant_types"] == ["authorization_code"]
        assert response["response_types"] == ["code"]
        assert response["token_endpoint_auth_method"] == "none"


class TestRegisterRouteHandler:
    """Tests for /register HTTP endpoint."""

    def test_returns_201_on_success(self):
        """Verify POST /register returns 201 Created."""
        app = Starlette(routes=[
            Route("/register", register_handler, methods=["POST"]),
        ])

        with patch("realize.oauth.dcr.config") as mock_config:
            mock_config.oauth_dcr_client_id = "test-client-id"

            client = TestClient(app)
            response = client.post("/register", json={"client_name": "Test"})

            assert response.status_code == 201
            assert response.headers["content-type"] == "application/json"

    def test_returns_400_with_correct_error_code_on_validation_failure(self):
        """Verify validation errors return RFC 7591 error codes."""
        app = Starlette(routes=[
            Route("/register", register_handler, methods=["POST"]),
        ])

        with patch("realize.oauth.dcr.config") as mock_config:
            mock_config.oauth_dcr_client_id = "test-client-id"

            client = TestClient(app)
            response = client.post("/register", json={"grant_types": ["implicit"]})

            assert response.status_code == 400
            data = response.json()
            assert data["error"] == "invalid_client_metadata"

    def test_returns_400_with_redirect_error_code(self):
        """Verify redirect URI errors use invalid_redirect_uri error code."""
        app = Starlette(routes=[
            Route("/register", register_handler, methods=["POST"]),
        ])

        with patch("realize.oauth.dcr.config") as mock_config:
            mock_config.oauth_dcr_client_id = "test-client-id"

            client = TestClient(app)
            response = client.post("/register", json={"redirect_uris": ["http://evil.com"]})

            assert response.status_code == 400
            data = response.json()
            assert data["error"] == "invalid_redirect_uri"

    def test_returns_400_when_not_configured(self):
        """Verify POST /register returns 400 when DCR not configured."""
        app = Starlette(routes=[
            Route("/register", register_handler, methods=["POST"]),
        ])

        with patch("realize.oauth.dcr.config") as mock_config:
            mock_config.oauth_dcr_client_id = None

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

            client = TestClient(app)
            response = client.post("/register", content="", headers={"content-type": "application/json"})

            # Should handle gracefully and return defaults
            assert response.status_code == 201

    def test_logs_info_on_successful_registration(self, caplog):
        """Verify info log emitted on 201."""
        app = Starlette(routes=[
            Route("/register", register_handler, methods=["POST"]),
        ])

        with patch("realize.oauth.dcr.config") as mock_config:
            mock_config.oauth_dcr_client_id = "test-client-id"

            client = TestClient(app)
            with caplog.at_level(logging.INFO, logger="realize.oauth.routes"):
                response = client.post("/register", json={
                    "client_name": "Claude Desktop",
                    "software_id": "claude-desktop",
                    "redirect_uris": ["http://localhost:3000/cb"],
                })

            assert response.status_code == 201
            assert any("dcr_register" in r.message for r in caplog.records)
            log_record = next(r for r in caplog.records if "dcr_register" in r.message)
            assert log_record.client_name == "Claude Desktop"
            assert log_record.software_id == "claude-desktop"
            assert log_record.status == 201

    def test_logs_info_on_validation_failure(self, caplog):
        """Verify info log emitted on 400 with error_code."""
        app = Starlette(routes=[
            Route("/register", register_handler, methods=["POST"]),
        ])

        with patch("realize.oauth.dcr.config") as mock_config:
            mock_config.oauth_dcr_client_id = "test-client-id"

            client = TestClient(app)
            with caplog.at_level(logging.INFO, logger="realize.oauth.routes"):
                response = client.post("/register", json={
                    "client_name": "Bad Client",
                    "grant_types": ["implicit"],
                })

            assert response.status_code == 400
            assert any("dcr_register" in r.message for r in caplog.records)
            log_record = next(r for r in caplog.records if "dcr_register" in r.message)
            assert log_record.client_name == "Bad Client"
            assert log_record.status == 400
            assert log_record.error_code == "invalid_client_metadata"

    def test_response_contains_required_fields(self):
        """Verify response contains required RFC 7591 fields."""
        app = Starlette(routes=[
            Route("/register", register_handler, methods=["POST"]),
        ])

        with patch("realize.oauth.dcr.config") as mock_config:
            mock_config.oauth_dcr_client_id = "test-client-id"

            client = TestClient(app)
            response = client.post("/register", json={"redirect_uris": ["http://localhost/cb"]})

            data = response.json()
            assert "client_id" in data
            assert "client_id_issued_at" in data
            assert "client_secret" not in data
