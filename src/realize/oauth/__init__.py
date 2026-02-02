"""OAuth 2.1 support for realize-mcp."""
from .session import SessionManager, InMemorySessionManager, get_session_id_from_request
from .metadata import get_protected_resource_metadata, proxy_authorization_server_metadata
from .dcr import handle_client_registration, DCRError
from .token import TokenProxy, TokenProxyError
from .refresh import TokenRefresher
from .oauth21_auth import OAuth21Auth
from .context import set_session_token, get_session_token, clear_session_token
from .routes import (
    protected_resource_metadata_handler,
    authorization_server_metadata_handler,
    register_handler,
    create_token_handler,
)

__all__ = [
    # Session management
    "SessionManager",
    "InMemorySessionManager",
    "get_session_id_from_request",
    # Metadata
    "get_protected_resource_metadata",
    "proxy_authorization_server_metadata",
    # DCR
    "handle_client_registration",
    "DCRError",
    # Token proxy
    "TokenProxy",
    "TokenProxyError",
    # Token refresh and auth
    "TokenRefresher",
    "OAuth21Auth",
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
