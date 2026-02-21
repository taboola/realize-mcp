"""OAuth 2.1 support for realize-mcp."""
from .metadata import get_protected_resource_metadata, proxy_authorization_server_metadata
from .dcr import handle_client_registration, DCRError
from .token import TokenProxy, TokenProxyError
from .context import set_session_token, get_session_token, clear_session_token
from .routes import (
    protected_resource_metadata_handler,
    authorization_server_metadata_handler,
    register_handler,
    create_token_handler,
)

__all__ = [
    # Metadata
    "get_protected_resource_metadata",
    "proxy_authorization_server_metadata",
    # DCR
    "handle_client_registration",
    "DCRError",
    # Token proxy
    "TokenProxy",
    "TokenProxyError",
    # Context (per-connection token isolation)
    "set_session_token",
    "get_session_token",
    "clear_session_token",
    # Route handlers
    "protected_resource_metadata_handler",
    "authorization_server_metadata_handler",
    "register_handler",
    "create_token_handler",
]
