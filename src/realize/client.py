"""HTTP client for Realize API."""
import logging
from typing import Any, Dict, List, Optional
import httpx
from realize.auth import auth 

logger = logging.getLogger(__name__)


class RealizeClient:
    """HTTP client for Realize API operations."""
    
    def __init__(self):
        self.base_url = f"{auth.base_url}/api/1.0"
        self.timeout = 30.0
    
    async def request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to API and return raw JSON response."""
        url = f"{self.base_url}{endpoint}"
        headers = await auth.get_auth_header()
        headers["Content-Type"] = "application/json"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                params=params
            )
            
            response.raise_for_status()
            return response.json()
    
    # Convenience methods for common HTTP verbs
    async def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make GET request."""
        return await self.request("GET", endpoint, params=params)
    
    async def post(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make POST request."""
        return await self.request("POST", endpoint, data=data)
    
    async def put(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make PUT request."""
        return await self.request("PUT", endpoint, data=data)
    
    async def patch(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make PATCH request."""
        return await self.request("PATCH", endpoint, data=data)
    
    async def delete(self, endpoint: str) -> Dict[str, Any]:
        """Make DELETE request."""
        return await self.request("DELETE", endpoint)


# Global client instance
client = RealizeClient() 