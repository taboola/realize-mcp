"""Token refresh logic for OAuth 2.1."""
import logging
from typing import Optional

from ..config import config
from ..models import OAuth21Token
from .session import SessionManager
from .token import TokenProxy, TokenProxyError

logger = logging.getLogger(__name__)


class TokenRefresher:
    """Handles proactive token refresh before expiry."""

    def __init__(self, session_manager: SessionManager, token_proxy: TokenProxy):
        """Initialize TokenRefresher.

        Args:
            session_manager: SessionManager for token storage
            token_proxy: TokenProxy for refresh token exchange
        """
        self.session_manager = session_manager
        self.token_proxy = token_proxy
        self.buffer_seconds = config.oauth_refresh_buffer_seconds

    async def ensure_valid_token(self, session_id: str) -> Optional[OAuth21Token]:
        """Ensure session has a valid (non-expired) token.

        If token is expired or about to expire within buffer_seconds,
        attempts to refresh using the refresh_token grant.

        Args:
            session_id: Session ID to check/refresh token for

        Returns:
            Valid OAuth21Token if available, None if no token or refresh failed
        """
        token = await self.session_manager.get_token(session_id)
        if token is None:
            logger.debug(f"No token found for session {session_id}")
            return None

        # Check if token needs refresh
        if not token.is_expired(buffer_seconds=self.buffer_seconds):
            logger.debug(f"Token for session {session_id} is still valid")
            return token

        logger.info(f"Token for session {session_id} needs refresh")

        # Attempt refresh if we have a refresh token
        if token.refresh_token:
            try:
                new_token = await self.token_proxy.exchange_token(
                    grant_type="refresh_token",
                    session_id=session_id,
                    refresh_token=token.refresh_token,
                )
                logger.info(f"Token refreshed successfully for session {session_id}")
                return new_token
            except (TokenProxyError, ValueError) as e:
                logger.warning(f"Token refresh failed for session {session_id}: {e}")
                # Refresh failed, token is invalid
                await self.session_manager.delete_session(session_id)
                return None

        # No refresh token and access token expired
        logger.info(f"No refresh token available for session {session_id}, deleting session")
        await self.session_manager.delete_session(session_id)
        return None
