"""Authentication handler for Realize API."""
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import httpx
from realize.config import config
from realize.models import Token

logger = logging.getLogger(__name__)


class RealizeAuth:
    """Handles authentication with Realize API."""
    
    def __init__(self):
        self.token: Optional[Token] = None
        self.base_url = config.realize_base_url
    
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


# Global auth instance
auth = RealizeAuth() 