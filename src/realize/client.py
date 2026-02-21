"""HTTP client for Realize API."""
import logging
from typing import Any, Dict, Optional
import httpx
from realize.auth import AuthProvider, get_auth_provider
from realize.config import config

logger = logging.getLogger(__name__)


class RealizeClient:
    """HTTP client for Realize API operations.

    Supports both global auth (for stdio transport) and context-based auth (for SSE).
    """

    def __init__(self, auth_provider: Optional[AuthProvider] = None):
        """Initialize client.

        Args:
            auth_provider: Optional auth provider. Defaults to transport-appropriate auth.
        """
        self.base_url = f"{config.realize_base_url}/api/1.0"
        self.timeout = 30.0
        # Use provided auth or get appropriate one based on transport mode
        self._auth_provider = auth_provider

    @property
    def auth_provider(self) -> AuthProvider:
        """Get auth provider, resolving transport mode at call time."""
        if self._auth_provider:
            return self._auth_provider
        # Resolve at call time to pick up SSE token if set
        return get_auth_provider()

    async def request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make authenticated request to API and return raw JSON response.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Optional request body
            params: Optional query parameters

        Returns:
            JSON response as dict

        Raises:
            httpx.HTTPStatusError: If request fails
            ValueError: If no valid auth available
        """
        url = f"{self.base_url}{endpoint}"
        auth_header = await self.auth_provider.get_auth_header()

        if auth_header is None:
            raise ValueError("No valid authentication available")

        headers = {**auth_header, "Content-Type": "application/json"}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                params=params
            )

            if response.status_code == 401:
                raise httpx.HTTPStatusError(
                    "Authentication token expired or invalid. "
                    "Please reconnect with a valid token.",
                    request=response.request,
                    response=response,
                )

            response.raise_for_status()
            return response.json()

    # Convenience methods for common HTTP verbs
    async def get(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make GET request."""
        return await self.request("GET", endpoint, params=params)

    async def post(
        self,
        endpoint: str,
        data: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make POST request."""
        return await self.request("POST", endpoint, data=data)

    async def put(
        self,
        endpoint: str,
        data: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make PUT request."""
        return await self.request("PUT", endpoint, data=data)

    async def patch(
        self,
        endpoint: str,
        data: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make PATCH request."""
        return await self.request("PATCH", endpoint, data=data)

    async def delete(
        self,
        endpoint: str,
    ) -> Dict[str, Any]:
        """Make DELETE request."""
        return await self.request("DELETE", endpoint)


def create_client(auth_provider: AuthProvider) -> RealizeClient:
    """Factory function to create client with specific auth provider.

    Args:
        auth_provider: Auth provider to use for this client

    Returns:
        Configured RealizeClient
    """
    return RealizeClient(auth_provider=auth_provider)


# Global client instance (for stdio transport - backward compatibility)
client = RealizeClient()
 