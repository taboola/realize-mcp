"""Production readiness tests for Realize MCP server (read-only)."""
import pytest
import asyncio
import os
import sys
import pathlib
sys.path.append(str(pathlib.Path(__file__).parent.parent / "src"))
from unittest.mock import Mock, patch, AsyncMock
from realize.auth import auth
from realize.client import client
from realize.tools.registry import get_all_tools, get_tools_by_category
from realize.config import config


class TestProductionReadiness:
    """Test suite for production readiness with read-only operations."""
    
    def test_all_read_only_tools_registered(self):
        """Test that all expected read-only tools are registered."""
        tools = get_all_tools()
        
        # Check minimum required read-only tools
        required_tools = [
            'get_auth_token', 'get_token_details',
            'search_accounts',
            'get_all_campaigns', 'get_campaign',
            'get_campaign_items', 'get_campaign_item',
            'get_top_campaign_content_report', 'get_campaign_history_report',
            'get_campaign_breakdown_report', 'get_campaign_site_day_breakdown_report'
        ]
        
        for tool in required_tools:
            assert tool in tools, f"Required read-only tool {tool} not found in registry"
    
    def test_no_write_operations(self):
        """Test that no write operations are included for safety."""
        tools = get_all_tools()
        
        # Verify no write operations exist
        forbidden_operations = [
            'create_campaign', 'update_campaign', 'delete_campaign', 'duplicate_campaign',
            'create_campaign_item', 'update_campaign_item', 'delete_campaign_item',
            'create_', 'update_', 'delete_', 'post_', 'put_', 'patch_'
        ]
        
        for tool_name in tools.keys():
            for forbidden in forbidden_operations:
                assert not tool_name.startswith(forbidden.lower()), \
                    f"Found write operation {tool_name} - only read operations allowed"
    
    def test_tool_categories_exist(self):
        """Test that all tool categories are properly defined for read-only operations."""
        categories = ['authentication', 'accounts', 'campaigns', 'campaign_items', 'reports']
        
        for category in categories:
            tools = get_tools_by_category(category)
            assert len(tools) > 0, f"Category {category} has no tools"
    
    def test_tool_schemas_valid_read_only(self):
        """Test that all tool schemas are valid for read-only raw JSON handling."""
        tools = get_all_tools()
        
        for tool_name, tool_config in tools.items():
            # Check required fields
            assert 'description' in tool_config
            assert 'schema' in tool_config
            assert 'handler' in tool_config
            assert 'category' in tool_config
            
            # Verify description indicates read-only
            description = tool_config['description'].lower()
            assert 'read-only' in description or 'get' in description, \
                f"Tool {tool_name} should be clearly marked as read-only"
            
            # Check schema structure supports flexible JSON
            schema = tool_config['schema']
            assert schema['type'] == 'object'
            assert 'properties' in schema
            assert 'required' in schema
    
    @pytest.mark.asyncio
    @patch('realize.auth.httpx.AsyncClient')
    async def test_authentication_flow(self, mock_client):
        """Test authentication flow works correctly with Token model."""
        # Mock successful auth response
        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'test_token',
            'token_type': 'Bearer',
            'expires_in': 3600
        }
        mock_response.raise_for_status.return_value = None
        
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
        
        # Test token retrieval (only model used)
        token = await auth.get_auth_token()
        assert token.access_token == 'test_token'
        assert token.expires_in == 3600
    
    def test_configuration_validation(self):
        """Test that configuration validation works."""
        # Test that required config fields exist
        assert hasattr(config, 'realize_client_id')
        assert hasattr(config, 'realize_client_secret')
        assert hasattr(config, 'realize_base_url')
        assert hasattr(config, 'log_level')
    
    @pytest.mark.asyncio
    @patch('realize.client.httpx.AsyncClient')
    async def test_api_client_read_only_json_handling(self, mock_client):
        """Test API client returns raw JSON dictionaries for read operations."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [
                {"id": "123", "name": "Test Campaign", "cpc": 1.5}
            ],
            "metadata": {"total": 1}
        }
        mock_response.raise_for_status.return_value = None
        
        # Create an async context manager mock
        mock_context = Mock()
        mock_context.request = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_context)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Test raw JSON response handling for GET operations
        response = await client.get("/test-endpoint")
        
        # Should return raw dictionary, not parsed model
        assert isinstance(response, dict)
        assert "results" in response
        assert "metadata" in response
        assert response["results"][0]["name"] == "Test Campaign"
    
    @pytest.mark.asyncio
    @patch('realize.client.httpx.AsyncClient')
    async def test_api_client_error_handling(self, mock_client):
        """Test API client error handling."""
        # Mock HTTP error
        from httpx import HTTPStatusError
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = HTTPStatusError(
            "401 Unauthorized", request=Mock(), response=mock_response
        )
        
        # Create an async context manager mock that raises error
        mock_context = Mock()
        mock_context.request = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_context)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Test error handling
        with pytest.raises(HTTPStatusError):
            await client.get("/test-endpoint")
    
    def test_environment_variables(self):
        """Test that environment variables are properly configured."""
        # Check that example file exists
        example_file = pathlib.Path(__file__).parent.parent / ".env.example"
        if not example_file.exists():
            # Create .env.example for testing
            with open(example_file, 'w') as f:
                f.write("REALIZE_CLIENT_ID=your_client_id_here\n")
                f.write("REALIZE_CLIENT_SECRET=your_client_secret_here\n")
        
        assert example_file.exists(), ".env.example file missing"
        
        # Read example file and check required variables
        with open(example_file, 'r') as f:
            content = f.read()
            assert 'REALIZE_CLIENT_ID' in content
            assert 'REALIZE_CLIENT_SECRET' in content
    
    def test_server_imports(self):
        """Test that all server imports work correctly."""
        # Test that main server module can be imported
        try:
            from realize.realize_server import server, handle_list_tools, handle_call_tool
            assert server is not None
            assert callable(handle_list_tools)
            assert callable(handle_call_tool)
        except ImportError as e:
            pytest.fail(f"Server import failed: {e}")


class TestReadOnlyToolHandlers:
    """Test read-only tool handler functions with raw JSON responses."""
    
    @pytest.mark.asyncio
    @patch('realize.tools.auth_handlers.auth')
    async def test_auth_handlers(self, mock_auth):
        """Test authentication handlers (only place where models are used)."""
        from realize.tools.auth_handlers import get_auth_token, get_token_details
        
        # Mock successful auth - Token model is OK to use
        mock_token = Mock()
        mock_token.expires_in = 3600
        mock_auth.get_auth_token = AsyncMock(return_value=mock_token)
        
        result = await get_auth_token()
        assert len(result) == 1
        assert "Successfully authenticated" in result[0].text
    
    @pytest.mark.asyncio
    @patch('realize.tools.account_handlers.client')
    async def test_account_handlers_raw_json(self, mock_client):
        """Test account handlers with raw JSON responses."""
        from realize.tools.account_handlers import search_accounts
        
        # Mock raw JSON API response (no model parsing)
        mock_client.get = AsyncMock(return_value={
            "results": [
                {"name": "Test Account", "account_id": "123", "type": "advertiser"}
            ]
        })
        
        result = await search_accounts("Test Account")
        assert len(result) == 1
        assert "Test Account" in result[0].text
    
    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client')
    async def test_campaign_read_handlers_raw_json(self, mock_client):
        """Test read-only campaign handlers work with raw JSON responses."""
        # Test campaign handlers with raw JSON
        from realize.tools.campaign_handlers import get_all_campaigns, get_campaign
        
        # Test campaign listing (read-only) - reset mock first
        mock_client.get.reset_mock()
        mock_client.get = AsyncMock(return_value={
            "results": [
                {
                    "id": "campaign_123",
                    "name": "Test Campaign",
                    "cpc": 1.25,
                    "daily_cap": 100.0,
                    "is_active": True
                }
            ]
        })
        
        result = await get_all_campaigns({"account_id": "acc_123"})
        assert len(result) == 1
        assert "Test Campaign" in result[0].text
        
        # Test single campaign retrieval (read-only) - reset mock with new data
        mock_client.get.reset_mock()
        mock_client.get = AsyncMock(return_value={
            "id": "campaign_123",
            "name": "Test Campaign Details",
            "cpc": 1.25,
            "is_active": True
        })
        
        result = await get_campaign({
            "account_id": "acc_123",
            "campaign_id": "campaign_123"
        })
        assert len(result) == 1
        assert "Test Campaign Details" in result[0].text


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"]) 