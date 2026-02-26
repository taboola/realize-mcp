"""Authentication handler for Realize API."""
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from datetime import timedelta
import httpx
from realize.config import config
from realize.models import Token, utc_now

logger = logging.getLogger(__name__)


class AuthProvider(ABC):
    """Abstract base class for authentication providers.

    Implementations provide authorization headers for API requests.
    """

    @abstractmethod
    async def get_auth_header(self) -> Optional[Dict[str, str]]:
        """Get authorization header for API requests.

        Returns:
            Dict with Authorization header, or None if no valid auth available.
        """
        pass


class ClientCredentialsAuth(AuthProvider):
    """OAuth 2.0 Client Credentials authentication provider.

    Uses server credentials to obtain tokens for machine-to-machine API calls.
    This is used for stdio transport where the server authenticates with its own credentials.
    Thread-safe with asyncio lock to prevent concurrent refresh attempts.
    """

    def __init__(self):
        self.token: Optional[Token] = None
        self.base_url = config.realize_base_url
        self._refresh_lock = asyncio.Lock()

    async def get_auth_token(self) -> Token:
        """Get OAuth token using client credentials."""
        url = f"{self.base_url}/oauth/token"

        data = {
            "client_id": config.realize_client_id,
            "client_secret": config.realize_client_secret,
            "grant_type": "client_credentials"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=data)
            response.raise_for_status()

            token_data = response.json()
            self.token = Token(**token_data, created_at=utc_now())

            logger.debug("Successfully obtained auth token")
            return self.token

    async def get_token_details(self) -> Dict[str, Any]:
        """Get details about current token - returns raw JSON response."""
        async with self._refresh_lock:
            if not self.token:
                await self.get_auth_token()
            access_token = self.token.access_token

        url = f"{self.base_url}/api/1.0/token-details"
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            return response.json()

    async def get_auth_header(self) -> Dict[str, str]:
        """Get authorization header for API requests.

        Returns:
            Dict with Authorization header.
        """
        # Use lock to prevent concurrent refresh attempts
        async with self._refresh_lock:
            if not self.token or self._is_token_expired():
                await self.get_auth_token()
            return {"Authorization": f"Bearer {self.token.access_token}"}

    def _is_token_expired(self) -> bool:
        """Check if current token is expired."""
        if not self.token or not self.token.created_at:
            return True

        expiry_time = self.token.created_at + timedelta(seconds=self.token.expires_in)
        return utc_now() >= expiry_time


# Backward compatibility alias
RealizeAuth = ClientCredentialsAuth


class BearerTokenAuth(AuthProvider):
    """Auth provider for HTTP transports using Bearer token from OAuth flow.

    Retrieves the Bearer token from the current async context via get_session_token().
    Each HTTP request sets its token in the context, providing per-request isolation.
    """

    async def get_auth_header(self) -> Optional[Dict[str, str]]:
        """Get authorization header using Bearer token from current context.

        Returns:
            Dict with Authorization header, or None if no token in context.
        """
        from realize.oauth.context import get_session_token

        token = get_session_token()
        if not token:
            logger.warning("No Bearer token in current context")
            return None

        return {"Authorization": f"Bearer {token}"}


# Backward compatibility alias
SSETokenAuth = BearerTokenAuth


# Global auth instances
_client_credentials_auth = ClientCredentialsAuth()
_bearer_token_auth = BearerTokenAuth()


def get_auth_provider() -> AuthProvider:
    """Get the appropriate auth provider based on transport mode."""
    if config.mcp_transport == "streamable-http":
        return _bearer_token_auth
    return _client_credentials_auth


# Global auth instance (defaults to client credentials for backward compatibility)
auth = _client_credentials_auth
 