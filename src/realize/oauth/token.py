"""Token proxy for OAuth 2.1 token endpoint."""
import logging
import httpx
from typing import Tuple

from ..config import config

logger = logging.getLogger(__name__)


class TokenProxyError(Exception):
    """Error during token proxy operation."""
    pass


class TokenProxy:
    """Proxies token requests to upstream auth server.

    Stateless: proxies requests and returns responses without storing tokens.
    Token storage is the client's responsibility.
    """

    UPSTREAM_TOKEN_PATH = "/oauth2.1/token"
    REQUEST_TIMEOUT = 30.0

    @property
    def _token_url(self) -> str:
        """Get upstream token URL (computed at call time for testability)."""
        return f"{config.oauth_server_url}{self.UPSTREAM_TOKEN_PATH}"

    async def _post_token_request(self, data: dict) -> httpx.Response:
        """Send POST request to upstream token endpoint."""
        async with httpx.AsyncClient() as client:
            return await client.post(
                self._token_url,
                data=data,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                },
                timeout=self.REQUEST_TIMEOUT,
            )

    async def proxy_token_request(self, form_data: dict) -> Tuple[dict, int]:
        """Proxy a raw token request to upstream and return response.

        Stateless: does not store the token. The client receives the token
        directly and is responsible for using it in subsequent requests.

        Args:
            form_data: Form data from the incoming request

        Returns:
            Tuple of (response_data, status_code)
        """
        logger.debug(f"Proxying token request: grant_type={form_data.get('grant_type')}")

        try:
            response = await self._post_token_request(form_data)

            try:
                token_data = response.json()
            except Exception:
                logger.error(f"Token endpoint returned non-JSON response: {response.status_code}")
                return {"error": "server_error", "error_description": "Invalid response from auth server"}, 502

            if response.status_code != 200:
                logger.warning(f"Token request failed: {response.status_code}")
            else:
                logger.debug("Token exchange successful")

            return token_data, response.status_code

        except httpx.RequestError as e:
            logger.error(f"Token proxy error: {e}")
            return {"error": "server_error", "error_description": str(e)}, 502
