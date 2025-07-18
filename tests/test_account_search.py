"""Tests for account search functionality."""
import pytest
import json
import sys
import pathlib
sys.path.append(str(pathlib.Path(__file__).parent.parent / "src"))
from unittest.mock import patch, AsyncMock
from realize.tools.account_handlers import search_accounts
from realize.client import RealizeClient


class TestAccountSearch:
    """Test cases for search_accounts tool."""
    
    @pytest.mark.asyncio
    async def test_search_accounts_numeric_query(self):
        """Test searching with numeric ID."""
        mock_response = {
            "results": [
                {
                    "account_id": "12345",
                    "name": "Test Account",
                    "type": "advertiser"
                }
            ]
        }
        
        with patch.object(RealizeClient, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            result = await search_accounts("12345")
            
            assert len(result) == 1
            assert hasattr(result[0], 'type')
            assert hasattr(result[0], 'text')
            # Check for formatted response elements
            assert "🎯 ACCOUNT SEARCH RESULTS" in result[0].text
            assert "📋 ACCOUNT_ID VALUES FOR OTHER TOOLS:" in result[0].text
            assert "account_id: '12345'" in result[0].text
            assert "Test Account" in result[0].text
            assert "📊 FULL DETAILS:" in result[0].text
            mock_get.assert_called_once_with("/advertisers", params={"id": "12345", "page": 1, "page_size": 10})
    
    @pytest.mark.asyncio
    async def test_search_accounts_text_query(self):
        """Test searching with text query."""
        mock_response = {
            "results": [
                {
                    "account_id": "67890",
                    "name": "Marketing Corp",
                    "type": "advertiser"
                }
            ]
        }
        
        with patch.object(RealizeClient, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            result = await search_accounts("Marketing")
            
            assert len(result) == 1
            assert hasattr(result[0], 'type')
            assert hasattr(result[0], 'text')
            # Check for formatted response elements
            assert "🎯 ACCOUNT SEARCH RESULTS" in result[0].text
            assert "📋 ACCOUNT_ID VALUES FOR OTHER TOOLS:" in result[0].text
            assert "account_id: '67890'" in result[0].text
            assert "Marketing Corp" in result[0].text
            assert "📊 FULL DETAILS:" in result[0].text
            mock_get.assert_called_once_with("/advertisers", params={"search_text": "Marketing", "page": 1, "page_size": 10})
    
    @pytest.mark.asyncio
    async def test_search_accounts_empty_query(self):
        """Test with empty query string."""
        result = await search_accounts("")
        
        assert len(result) == 1
        assert hasattr(result[0], 'text')
        assert "Error: Query parameter cannot be empty" in result[0].text
    
    @pytest.mark.asyncio
    async def test_search_accounts_whitespace_query(self):
        """Test with whitespace-only query."""
        result = await search_accounts("   ")
        
        assert len(result) == 1
        assert hasattr(result[0], 'text')
        assert "Error: Query parameter cannot be empty" in result[0].text
    
    @pytest.mark.asyncio
    async def test_search_accounts_none_query(self):
        """Test with None query."""
        result = await search_accounts(None)
        
        assert len(result) == 1
        assert hasattr(result[0], 'text')
        assert "Error: Query parameter cannot be empty" in result[0].text
    
    @pytest.mark.asyncio
    async def test_search_accounts_api_error(self):
        """Test error handling when API call fails."""
        with patch.object(RealizeClient, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("API Error")
            
            result = await search_accounts("test")
            
            assert len(result) == 1
            assert hasattr(result[0], 'text')
            assert "Failed to search accounts: API Error" in result[0].text
    
    @pytest.mark.asyncio
    async def test_search_accounts_mixed_alphanumeric(self):
        """Test mixed alphanumeric query (should be treated as text)."""
        mock_response = {"results": []}
        
        with patch.object(RealizeClient, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            result = await search_accounts("ABC123")
            
            assert len(result) == 1
            assert "No accounts found for query: 'ABC123'" in result[0].text
            mock_get.assert_called_once_with("/advertisers", params={"search_text": "ABC123", "page": 1, "page_size": 10})
    
    @pytest.mark.asyncio
    async def test_search_accounts_leading_zeros(self):
        """Test numeric query with leading zeros."""
        mock_response = {"results": []}
        
        with patch.object(RealizeClient, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            result = await search_accounts("00123")
            
            assert len(result) == 1
            assert "No accounts found for query: '00123'" in result[0].text
            mock_get.assert_called_once_with("/advertisers", params={"id": "00123", "page": 1, "page_size": 10})
    
    @pytest.mark.asyncio
    async def test_search_accounts_special_characters(self):
        """Test query with special characters."""
        mock_response = {"results": []}
        
        with patch.object(RealizeClient, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            result = await search_accounts("Test & Co.")
            
            assert len(result) == 1
            assert "No accounts found for query: 'Test & Co.'" in result[0].text
            mock_get.assert_called_once_with("/advertisers", params={"search_text": "Test & Co.", "page": 1, "page_size": 10})


# The get_advertisers method was moved to search_accounts handler
# These tests are now covered by the TestAccountSearch class above


# Note: Integration tests would require real API credentials and are not needed
# since we have comprehensive mocking tests that cover all scenarios


if __name__ == "__main__":
    pytest.main([__file__]) 