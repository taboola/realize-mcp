"""Dynamic Client Registration (RFC 7591) for OAuth 2.1."""
import time
from typing import Any

from ..config import config


class DCRError(Exception):
    """Error during Dynamic Client Registration."""
    pass


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
    if not config.oauth_dcr_client_id or not config.oauth_dcr_client_secret:
        raise DCRError("DCR credentials not configured. Set OAUTH_DCR_CLIENT_ID and OAUTH_DCR_CLIENT_SECRET environment variables.")

    # Default values per RFC 7591
    defaults = {
        "grant_types": ["authorization_code"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "client_secret_post",
    }

    response = {
        "client_id": config.oauth_dcr_client_id,
        "client_secret": config.oauth_dcr_client_secret,
        "client_id_issued_at": int(time.time()),
        "client_secret_expires_at": 0,  # Does not expire
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
