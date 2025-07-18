"""Integration tests for Realize MCP server with read-only raw JSON handling."""
import pytest
import asyncio
import json
import sys
import pathlib
sys.path.append(str(pathlib.Path(__file__).parent.parent / "src"))
from unittest.mock import Mock, patch, AsyncMock
from realize_server import handle_list_tools, handle_call_tool


class TestReadOnlyIntegration:
    """Integration tests for the complete read-only system using raw JSON."""
    
    @pytest.mark.asyncio
    async def test_list_tools_integration(self):
        """Test that list_tools returns all registered read-only tools."""
        tools = await handle_list_tools()
        
        # Check that we have tools
        assert len(tools) > 0
        
        # Check that essential read-only tools are present
        tool_names = [tool.name for tool in tools]
        essential_tools = ['get_auth_token', 'search_accounts', 'get_all_campaigns']
        
        for tool in essential_tools:
            assert tool in tool_names, f"Essential read-only tool {tool} missing"
    
    @pytest.mark.asyncio
    async def test_no_write_tools_available(self):
        """Test that no write operations are available."""
        tools = await handle_list_tools()
        tool_names = [tool.name for tool in tools]
        
        # Verify no write operations
        forbidden_patterns = ['create_', 'update_', 'delete_', 'post_', 'put_', 'patch_']
        for tool_name in tool_names:
            for pattern in forbidden_patterns:
                assert not tool_name.startswith(pattern), \
                    f"Found write operation {tool_name} - only read operations should be available"
    
    @pytest.mark.asyncio
    @patch('tools.auth_handlers.auth')
    async def test_call_tool_integration(self, mock_auth):
        """Test tool calling integration."""
        # Mock auth token (only model used)
        mock_token = Mock()
        mock_token.expires_in = 3600
        mock_auth.get_auth_token = AsyncMock(return_value=mock_token)
        
        # Test auth tool call
        result = await handle_call_tool("get_auth_token", {})
        assert len(result) == 1
        assert "Successfully authenticated" in result[0].text
    
    @pytest.mark.asyncio
    async def test_invalid_tool_call(self):
        """Test handling of invalid tool calls."""
        with pytest.raises(ValueError, match="Unknown tool"):
            await handle_call_tool("nonexistent_tool", {})
    

    

    
    @pytest.mark.asyncio
    @patch('realize.client.client')
    async def test_campaign_tools_integration(self, mock_client):
        """Test campaign tools integration with raw JSON."""
        # Mock campaign data
        mock_client.get = AsyncMock(return_value={
            "results": [
                {
                    "id": "123",
                    "name": "Integration Test Campaign",
                    "status": "RUNNING",
                    "cpc": 2.50
                }
            ],
            "metadata": {"total": 1}
        })
        
        # Test get_all_campaigns
        result = await handle_call_tool("get_all_campaigns", {
            "account_id": "test_account"
        })
        assert len(result) == 1
        assert "Integration Test Campaign" in result[0].text
        
        # Test get_campaign  
        mock_client.get = AsyncMock(return_value={
            "id": "123",
            "name": "Single Campaign",
            "status": "RUNNING"
        })
        
        result = await handle_call_tool("get_campaign", {
            "account_id": "test_account",
            "campaign_id": "123"
        })
        assert len(result) == 1
        assert "Single Campaign" in result[0].text
    
    @pytest.mark.asyncio
    @patch('tools.campaign_handlers.client')
    async def test_campaign_items_integration(self, mock_client):
        """Test campaign items tools integration with raw JSON."""
        # Test get_campaign_items
        mock_client.get = AsyncMock(return_value={
            "results": [
                {
                    "id": "item_123",
                    "campaign_id": "123",
                    "title": "Test Campaign Item",
                    "status": "APPROVED"
                }
            ]
        })
        
        result = await handle_call_tool("get_campaign_items", {
            "account_id": "test_account", 
            "campaign_id": "123"
        })
        assert len(result) == 1
        assert "Test Campaign Item" in result[0].text
        
        # Test get_campaign_item - reset mock with new data
        mock_client.get.reset_mock()
        mock_client.get = AsyncMock(return_value={
            "id": "item_123",
            "title": "Single Campaign Item",
            "status": "APPROVED"
        })
        
        result = await handle_call_tool("get_campaign_item", {
            "account_id": "test_account",
            "campaign_id": "123", 
            "item_id": "item_123"
        })
        assert len(result) == 1
        assert "Single Campaign Item" in result[0].text
    
    @pytest.mark.asyncio
    @patch('realize.client.client')
    async def test_reports_integration(self, mock_client):
        """Test reporting tools integration with raw JSON."""
        # Mock report data
        mock_client.get.return_value = asyncio.Future()
        mock_client.get.return_value.set_result({
            "results": [
                {
                    "campaign_id": "123",
                    "impressions": 1000,
                    "clicks": 50,
                    "ctr": 0.05,
                    "cost": 125.00
                }
            ],
            "metadata": {
                "start_date": "2024-01-01",
                "end_date": "2024-01-31"
            }
        })
        
        # Test get_campaign_breakdown_report
        result = await handle_call_tool("get_campaign_breakdown_report", {
            "account_id": "test_account",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31"
        })
        assert len(result) == 1
        assert "1000" in result[0].text  # Should contain impressions data
        
        # Test get_top_campaign_content_report (now returns CSV format)
        result = await handle_call_tool("get_top_campaign_content_report", {
            "account_id": "test_account",
            "start_date": "2024-01-01", 
            "end_date": "2024-01-31"
        })
        assert len(result) == 1
        assert "Top Campaign Content Report CSV" in result[0].text
        
        # Test get_campaign_history_report (now returns CSV format)
        result = await handle_call_tool("get_campaign_history_report", {
            "account_id": "test_account",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31"
        })
        assert len(result) == 1
        assert "Campaign History Report CSV" in result[0].text
    
    @pytest.mark.asyncio  
    @patch('tools.campaign_handlers.client')
    async def test_error_handling_integration(self, mock_client):
        """Test error handling integration across all tools."""
        # Test that all tools handle errors gracefully
        error_tools = [
            ("get_all_campaigns", {"account_id": "test"}),
            ("get_campaign", {"account_id": "test", "campaign_id": "123"}),
            ("get_campaign_items", {"account_id": "test", "campaign_id": "123"})
        ]
        
        for tool_name, args in error_tools:
            # Reset and configure mock for each tool test
            mock_client.get.reset_mock()
            mock_client.get = AsyncMock(side_effect=Exception("API Error"))
            
            result = await handle_call_tool(tool_name, args)
            assert len(result) == 1
            assert "failed" in result[0].text.lower() or "error" in result[0].text.lower()
    
    @pytest.mark.asyncio
    async def test_parameter_validation_integration(self):
        """Test parameter validation across all tools."""
        # Test tools with missing required parameters
        validation_tests = [
            ("get_all_campaigns", {}, "account_id is required"),
            ("get_campaign", {"account_id": "test"}, "campaign_id"),
            ("get_campaign_items", {"account_id": "test"}, "campaign_id"),
            ("get_campaign_item", {"account_id": "test", "campaign_id": "123"}, "item_id"),
            ("get_campaign_breakdown_report", {"account_id": "test"}, "start_date"),
            ("get_top_campaign_content_report", {"account_id": "test"}, "start_date"),
            ("get_campaign_history_report", {"account_id": "test"}, "start_date")
        ]
        
        for tool_name, args, expected_error in validation_tests:
            result = await handle_call_tool(tool_name, args)
            assert len(result) == 1
            assert expected_error in result[0].text
    
    @pytest.mark.asyncio
    async def test_tool_categories_integration(self):
        """Test that tools are properly categorized."""
        tools = await handle_list_tools()
        
        # Count tools by expected categories
        category_counts = {}
        for tool in tools:
            # Get category from tool registry
            from tools.registry import get_all_tools
            registry = get_all_tools()
            if tool.name in registry:
                category = registry[tool.name].get("category", "unknown")
                category_counts[category] = category_counts.get(category, 0) + 1
        
        # Verify we have tools in all expected categories
        expected_categories = ['authentication', 'accounts', 'campaigns', 'campaign_items', 'reports']
        for category in expected_categories:
            assert category in category_counts, f"No tools found in category: {category}"
            assert category_counts[category] > 0, f"Category {category} has no tools"


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 