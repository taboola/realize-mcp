"""Token proxy for OAuth 2.1 token endpoint."""
import logging
import httpx
from typing import Optional, Tuple

from ..config import config
from ..models import OAuth21Token, utc_now
from .session import SessionManager

logger = logging.getLogger(__name__)


class TokenProxyError(Exception):
    """Error during token proxy operation."""
    pass


class TokenProxy:
    """Proxies token requests to upstream auth server."""

    UPSTREAM_TOKEN_PATH = "/oauth2.1/token"
    REQUEST_TIMEOUT = 30.0

    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager

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

    def _create_token(self, token_data: dict, default_expires_in: int = 3600) -> OAuth21Token:
        """Create OAuth21Token from response data."""
        return OAuth21Token(
            access_token=token_data["access_token"],
            token_type=token_data.get("token_type", "Bearer"),
            expires_in=token_data.get("expires_in", default_expires_in),
            refresh_token=token_data.get("refresh_token"),
            scope=token_data.get("scope"),
            created_at=utc_now(),
        )

    async def exchange_token(
        self,
        grant_type: str,
        session_id: str,
        code: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        code_verifier: Optional[str] = None,
        refresh_token: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        scope: Optional[str] = None,
    ) -> OAuth21Token:
        """Exchange authorization code or refresh token for access token.

        Args:
            grant_type: "authorization_code" or "refresh_token"
            session_id: Session ID for token storage
            code: Authorization code (for authorization_code grant)
            redirect_uri: Redirect URI (for authorization_code grant)
            code_verifier: PKCE code verifier (for authorization_code grant)
            refresh_token: Refresh token (for refresh_token grant)
            client_id: Client ID (defaults to DCR client_id from config)
            client_secret: Client secret (defaults to DCR client_secret from config)
            scope: Requested scope

        Returns:
            OAuth21Token with access token and optional refresh token

        Raises:
            TokenProxyError: If token exchange fails
            ValueError: If required parameters missing for grant type
        """
        # Build request data
        data = {
            "grant_type": grant_type,
            "client_id": client_id or config.oauth_dcr_client_id,
            "client_secret": client_secret or config.oauth_dcr_client_secret,
        }

        if grant_type == "authorization_code":
            if not code:
                raise ValueError("code required for authorization_code grant")
            if not redirect_uri:
                raise ValueError("redirect_uri required for authorization_code grant")
            data["code"] = code
            data["redirect_uri"] = redirect_uri
            if code_verifier:
                data["code_verifier"] = code_verifier

        elif grant_type == "refresh_token":
            if not refresh_token:
                raise ValueError("refresh_token required for refresh_token grant")
            data["refresh_token"] = refresh_token

        else:
            raise ValueError(f"Unsupported grant_type: {grant_type}")

        if scope:
            data["scope"] = scope

        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}

        try:
            response = await self._post_token_request(data)

            if response.status_code != 200:
                error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                error_msg = error_data.get("error_description", error_data.get("error", response.text))
                raise TokenProxyError(f"Token exchange failed: {error_msg}")

            token_data = response.json()

        except httpx.RequestError as e:
            raise TokenProxyError(f"Failed to connect to auth server: {str(e)}")

        token = self._create_token(token_data)
        await self.session_manager.set_token(session_id, token)
        return token

    async def proxy_token_request(
        self,
        form_data: dict,
        session_id: str,
    ) -> Tuple[dict, int]:
        """Proxy a raw token request to upstream and return response.

        This method proxies the request as-is without parsing into OAuth21Token.
        Used by the route handler to return the raw upstream response.

        Args:
            form_data: Form data from the incoming request
            session_id: Session ID for token storage

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
            elif "access_token" in token_data:
                logger.debug("Token exchange successful")
                token = self._create_token(token_data)
                await self.session_manager.set_token(session_id, token)

            return token_data, response.status_code

        except httpx.RequestError as e:
            logger.error(f"Token proxy error: {e}")
            return {"error": "server_error", "error_description": str(e)}, 502
