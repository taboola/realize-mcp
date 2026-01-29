"""Session management for OAuth 2.1 per-session token storage."""
import asyncio
import logging
import re
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from starlette.requests import Request

from ..models import OAuth21Token, utc_now

logger = logging.getLogger(__name__)

# Valid session ID pattern (UUID format)
SESSION_ID_PATTERN = re.compile(r"^[a-f0-9]{8}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{12}$", re.IGNORECASE)


def is_valid_session_id(session_id: str) -> bool:
    """Validate session ID format to prevent injection."""
    return bool(SESSION_ID_PATTERN.match(session_id))


@dataclass
class SessionData:
    """Container for session data with metadata."""
    token: OAuth21Token
    created_at: float = field(default_factory=lambda: utc_now().timestamp())
    last_accessed: float = field(default_factory=lambda: utc_now().timestamp())


class SessionManager(ABC):
    """Abstract interface for session-based token storage."""

    @abstractmethod
    async def get_token(self, session_id: str) -> Optional[OAuth21Token]:
        """Retrieve token for a session."""
        pass

    @abstractmethod
    async def set_token(self, session_id: str, token: OAuth21Token) -> None:
        """Store token for a session."""
        pass

    @abstractmethod
    async def delete_session(self, session_id: str) -> None:
        """Remove session and its token."""
        pass

    @abstractmethod
    async def get_all_sessions(self) -> list[str]:
        """List all active session IDs."""
        pass

    @abstractmethod
    async def cleanup_expired(self, max_age_seconds: int = 86400) -> int:
        """Remove sessions older than max_age_seconds. Returns count removed."""
        pass

    @abstractmethod
    async def find_session_by_token(self, access_token: str) -> Optional[str]:
        """Find session ID by access token value.

        Args:
            access_token: The access token to search for

        Returns:
            Session ID if token found, None otherwise
        """
        pass


class InMemorySessionManager(SessionManager):
    """In-memory implementation of SessionManager with cleanup support."""

    DEFAULT_MAX_SESSIONS = 1000
    DEFAULT_SESSION_TTL = 86400  # 24 hours

    def __init__(self, max_sessions: int = DEFAULT_MAX_SESSIONS):
        self._sessions: dict[str, SessionData] = {}
        self._lock = asyncio.Lock()
        self._max_sessions = max_sessions

    async def get_token(self, session_id: str) -> Optional[OAuth21Token]:
        """Retrieve token for a session, updating last access time."""
        async with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.last_accessed = utc_now().timestamp()
                return session.token
            return None

    async def set_token(self, session_id: str, token: OAuth21Token) -> None:
        """Store token for a session, enforcing max session limit."""
        async with self._lock:
            # Enforce max sessions - remove oldest if at limit
            if session_id not in self._sessions and len(self._sessions) >= self._max_sessions:
                oldest_id = min(self._sessions, key=lambda k: self._sessions[k].last_accessed)
                del self._sessions[oldest_id]
                logger.warning(f"Session limit reached, removed oldest session")

            token.session_id = session_id
            self._sessions[session_id] = SessionData(token=token)

    async def delete_session(self, session_id: str) -> None:
        """Remove session and its token."""
        async with self._lock:
            self._sessions.pop(session_id, None)

    async def get_all_sessions(self) -> list[str]:
        """List all active session IDs."""
        async with self._lock:
            return list(self._sessions.keys())

    async def cleanup_expired(self, max_age_seconds: int = DEFAULT_SESSION_TTL) -> int:
        """Remove sessions older than max_age_seconds. Returns count removed."""
        async with self._lock:
            now = utc_now().timestamp()
            expired = [
                sid for sid, data in self._sessions.items()
                if (now - data.last_accessed) > max_age_seconds
            ]
            for sid in expired:
                del self._sessions[sid]
            if expired:
                logger.debug(f"Cleaned up {len(expired)} expired sessions")
            return len(expired)

    @property
    def session_count(self) -> int:
        """Current number of active sessions."""
        return len(self._sessions)

    async def find_session_by_token(self, access_token: str) -> Optional[str]:
        """Find session ID by access token value.

        Args:
            access_token: The access token to search for

        Returns:
            Session ID if token found, None otherwise
        """
        async with self._lock:
            for session_id, session_data in self._sessions.items():
                if session_data.token.access_token == access_token:
                    session_data.last_accessed = utc_now().timestamp()
                    return session_id
            return None


def get_session_id_from_request(request: Request) -> str:
    """Extract and validate session ID from request.

    Priority:
    1. X-Session-ID header (if valid format)
    2. session_id query parameter (if valid format)
    3. Generate new UUID

    Invalid session IDs are rejected to prevent injection attacks.
    """
    session_id = request.headers.get("X-Session-ID")
    if session_id and is_valid_session_id(session_id):
        return session_id

    session_id = request.query_params.get("session_id")
    if session_id and is_valid_session_id(session_id):
        return session_id

    return str(uuid.uuid4())
