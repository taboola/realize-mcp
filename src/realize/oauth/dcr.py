"""Dynamic Client Registration (RFC 7591) for OAuth 2.1."""
import ipaddress
import re
import time
from typing import Any
from urllib.parse import urlparse

from ..config import config

ALLOWED_GRANT_TYPES = {"authorization_code", "refresh_token"}
MAX_REDIRECT_URI_LEN = 2048
# Schemes known to execute script or otherwise unsafe as redirect targets.
DANGEROUS_SCHEMES = frozenset({
    "javascript", "data", "file", "vbscript", "blob", "about", "view-source",
})
_WHITESPACE_RE = re.compile(r"\s")
# RFC 3986 §3.1: scheme = ALPHA *( ALPHA / DIGIT / "+" / "-" / "." )
_SCHEME_RE = re.compile(r"^[a-z][a-z0-9+\-.]*$")


class DCRError(Exception):
    """Error during Dynamic Client Registration."""

    def __init__(self, message: str, error_code: str = "invalid_client_metadata"):
        super().__init__(message)
        self.error_code = error_code


def _is_loopback_host(host: str | None) -> bool:
    """True if host is a loopback IP literal or the string "localhost".

    Accepts 127.0.0.0/8, ::1 (any canonical form), ::ffff:127.x.x.x
    (IPv4-mapped IPv6 loopback), and the literal "localhost". RFC 8252
    §8.3 discourages "localhost" in favor of IP literals, but real
    clients ship it, so we keep it.
    """
    if not host:
        return False
    if host == "localhost":
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    if ip.is_loopback:
        return True
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        return ip.ipv4_mapped.is_loopback
    return False


def _validate_redirect_uri(uri: Any) -> None:
    """Validate a single redirect_uri per RFC 7591 + RFC 8252 with defense-in-depth checks."""
    if not isinstance(uri, str):
        raise DCRError(
            "redirect_uris must contain strings",
            error_code="invalid_redirect_uri",
        )
    if len(uri) > MAX_REDIRECT_URI_LEN:
        raise DCRError(
            "Invalid redirect URI: exceeds maximum length",
            error_code="invalid_redirect_uri",
        )
    if _WHITESPACE_RE.search(uri):
        raise DCRError(
            "Invalid redirect URI: contains whitespace",
            error_code="invalid_redirect_uri",
        )
    parsed = urlparse(uri)
    scheme = parsed.scheme.lower()
    if not scheme:
        raise DCRError(
            "Invalid redirect URI: missing scheme",
            error_code="invalid_redirect_uri",
        )
    if parsed.fragment:
        raise DCRError(
            "Invalid redirect URI: must not contain fragment",
            error_code="invalid_redirect_uri",
        )
    if scheme == "https":
        if not parsed.hostname:
            raise DCRError(
                "Invalid redirect URI: missing host",
                error_code="invalid_redirect_uri",
            )
        return
    if scheme == "http":
        if not _is_loopback_host(parsed.hostname):
            raise DCRError(
                "Invalid redirect URI: HTTP scheme requires loopback host "
                "(localhost, 127.0.0.0/8, or ::1)",
                error_code="invalid_redirect_uri",
            )
        return
    if scheme in DANGEROUS_SCHEMES:
        raise DCRError(
            "Invalid redirect URI: disallowed scheme",
            error_code="invalid_redirect_uri",
        )
    if not _SCHEME_RE.match(scheme):
        raise DCRError(
            "Invalid redirect URI: malformed scheme",
            error_code="invalid_redirect_uri",
        )


def _validate_request(request_data: dict[str, Any]) -> None:
    """Validate DCR request fields per RFC 7591. Only checks fields that are present."""
    # redirect_uris: must be HTTPS, loopback HTTP, or safe custom scheme
    if "redirect_uris" in request_data:
        if not isinstance(request_data["redirect_uris"], list):
            raise DCRError("redirect_uris must be an array", error_code="invalid_redirect_uri")
        for uri in request_data["redirect_uris"]:
            _validate_redirect_uri(uri)

    # grant_types: only authorization_code and refresh_token
    if "grant_types" in request_data:
        if not isinstance(request_data["grant_types"], list):
            raise DCRError("grant_types must be an array")
        invalid = set(request_data["grant_types"]) - ALLOWED_GRANT_TYPES
        if invalid:
            raise DCRError(
                f"Unsupported grant_types. Allowed: {', '.join(sorted(ALLOWED_GRANT_TYPES))}",
            )

    # response_types: only code
    if "response_types" in request_data:
        if not isinstance(request_data["response_types"], list):
            raise DCRError("response_types must be an array")
        if request_data["response_types"] != ["code"]:
            raise DCRError("response_types must be [\"code\"]")

    # token_endpoint_auth_method: must be none (public PKCE client)
    if "token_endpoint_auth_method" in request_data:
        if request_data["token_endpoint_auth_method"] != "none":
            raise DCRError(
                "token_endpoint_auth_method must be \"none\" for public PKCE clients",
            )

    # jwks_uri / jwks: not applicable for public clients
    if "jwks_uri" in request_data:
        raise DCRError("jwks_uri is not supported for public PKCE clients")
    if "jwks" in request_data:
        raise DCRError("jwks is not supported for public PKCE clients")


def handle_client_registration(request_data: dict[str, Any]) -> dict[str, Any]:
    """Handle RFC 7591 Dynamic Client Registration.

    Returns credentials from environment variables rather than
    actually registering with an upstream server.

    Args:
        request_data: Client metadata from registration request

    Returns:
        dict: Client registration response per RFC 7591

    Raises:
        DCRError: If DCR credentials not configured in environment
    """
    if not config.oauth_dcr_client_id:
        raise DCRError("DCR credentials not configured. Set OAUTH_DCR_CLIENT_ID environment variable.",
                        error_code="invalid_request")

    _validate_request(request_data)

    # Default values per RFC 7591
    defaults = {
        "grant_types": ["authorization_code"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",
    }

    response = {
        "client_id": config.oauth_dcr_client_id,
        "client_id_issued_at": int(time.time()),
    }

    # Echo back client metadata with defaults
    echoed_fields = [
        "redirect_uris",
        "client_name",
        "client_uri",
        "logo_uri",
        "scope",
        "contacts",
        "tos_uri",
        "policy_uri",
        "jwks_uri",
        "jwks",
        "software_id",
        "software_version",
        "grant_types",
        "response_types",
        "token_endpoint_auth_method",
    ]

    for field in echoed_fields:
        if field in request_data:
            response[field] = request_data[field]
        elif field in defaults:
            response[field] = defaults[field]

    return response
