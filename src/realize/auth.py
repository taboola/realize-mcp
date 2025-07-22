"""Authentication handler for Realize API."""
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import httpx
from realize.config import config
from realize.models import Token

logger = logging.getLogger(__name__)


class AuthBase:
    """Base class for authentication handlers."""
    
    def __init__(self):
        self.token: Optional[Token] = None
        self.base_url = config.realize_base_url
    
    async def get_auth_header(self) -> dict:
        """Get authorization header for API requests."""
        if not self.token or self._is_token_expired():
            await self.get_auth_token()
        
        return {"Authorization": f"Bearer {self.token.access_token}"}
    
    def _is_token_expired(self) -> bool:
        """Check if current token is expired."""
        if not self.token or not self.token.created_at:
            return True
        
        expiry_time = self.token.created_at + timedelta(seconds=self.token.expires_in)
        return datetime.now() >= expiry_time
    
    async def get_auth_token(self) -> Token:
        """Get OAuth token - must be implemented by subclasses."""
        raise NotImplementedError
    
    async def get_token_details(self) -> Dict[str, Any]:
        """Get details about current token - returns raw JSON response."""
        if not self.token:
            await self.get_auth_token()
        
        url = f"{self.base_url}/api/1.0/token-details"
        headers = {"Authorization": f"Bearer {self.token.access_token}"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            return response.json()


class RealizeAuth(AuthBase):
    """Handles authentication with Realize API using client credentials."""
    
    def __init__(self):
        super().__init__()
    
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
            self.token = Token(**token_data, created_at=datetime.now())
            
            logger.info("Successfully obtained auth token")
            return self.token


class BrowserAuth(AuthBase):
    """Handles authentication with Realize API using browser flow."""
    
    def __init__(self):
        super().__init__()
    
    def set_token(self, access_token: str, expires_in: int):
        """Set token from browser authentication."""
        self.token = Token(
            access_token=access_token,
            token_type="Bearer",
            expires_in=expires_in,
            created_at=datetime.now()
        )
        logger.info("Browser auth token set successfully")
    
    async def get_auth_token(self) -> Token:
        """Get OAuth token - for browser auth, this raises an error as token must be set via browser flow."""
        if not self.token:
            raise Exception("No browser auth token available. Please authenticate using browser_authenticate tool first.")
        return self.token


# Global auth instance - default to client credentials if available
if (config.realize_client_id and config.realize_client_id != "your_client_id" and 
    config.realize_client_secret and config.realize_client_secret != "your_client_secret"):
    auth = RealizeAuth()
else:
    # No client credentials configured, will need browser auth
    auth = BrowserAuth() 