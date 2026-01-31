"""OAuth 2.1 session-aware authentication provider."""
import logging
from typing import Optional, Dict

from ..auth import AuthProvider
from ..models import OAuth21Token
from .session import SessionManager
from .refresh import TokenRefresher

logger = logging.getLogger(__name__)


class OAuth21Auth(AuthProvider):
    """Session-aware OAuth 2.1 authentication provider.

    Manages per-session tokens with automatic refresh support.
    Used for SSE transport where each client has their own token.
    """

    def __init__(self, session_manager: SessionManager, token_refresher: TokenRefresher):
        """Initialize OAuth21Auth.

        Args:
            session_manager: SessionManager for token storage
            token_refresher: TokenRefresher for proactive token refresh
        """
        self.session_manager = session_manager
        self.token_refresher = token_refresher

    async def get_auth_header(self, session_id: Optional[str] = None) -> Optional[Dict[str, str]]:
        """Get authorization header for a session.

        Automatically refreshes token if expired or about to expire.

        Args:
            session_id: Session ID to get auth header for. Required for this provider.

        Returns:
            Dict with Authorization header, or None if no valid token

        Raises:
            ValueError: If session_id is not provided
        """
        if session_id is None:
            raise ValueError("session_id is required for OAuth21Auth")

        token = await self.token_refresher.ensure_valid_token(session_id)
        if token is None:
            logger.debug(f"No valid token for session {session_id}")
            return None
        return {"Authorization": f"Bearer {token.access_token}"}

    async def get_token(self, session_id: str) -> Optional[OAuth21Token]:
        """Get current token for a session.

        Does not refresh - returns token as-is from session storage.

        Args:
            session_id: Session ID to get token for

        Returns:
            OAuth21Token if exists, None otherwise
        """
        return await self.session_manager.get_token(session_id)

    async def is_authenticated(self, session_id: str) -> bool:
        """Check if session has a valid token.

        Automatically refreshes token if expired or about to expire.

        Args:
            session_id: Session ID to check

        Returns:
            True if session has valid (possibly refreshed) token
        """
        token = await self.token_refresher.ensure_valid_token(session_id)
        return token is not None

    async def invalidate_session(self, session_id: str) -> None:
        """Invalidate/logout a session.

        Removes the session's token from storage.

        Args:
            session_id: Session ID to invalidate
        """
        logger.info(f"Invalidating session {session_id}")
        await self.session_manager.delete_session(session_id)
