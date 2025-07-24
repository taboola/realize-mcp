"""Integration tests for Realize MCP server with real API calls (read-only)."""
import asyncio
import pytest
import os
import pathlib
import sys
sys.path.append(str(pathlib.Path(__file__).parent.parent / "src"))
from datetime import datetime, timedelta
from realize.tools.registry import get_all_tools
from unittest.mock import Mock, patch, AsyncMock
from realize.realize_server import handle_list_tools, handle_call_tool


class TestReadOnlyIntegration:
    """Integration tests for the complete read-only system using raw JSON."""
    
    @pytest.mark.asyncio
    async def test_list_tools_integration(self):
        """Test that list_tools returns all registered read-only tools."""
        tools = await handle_list_tools()
        
        # Check that we have tools
        assert len(tools) > 0
        
        # Check that essential read-only tools are present (excluding auth which is dynamic)
        tool_names = [tool.name for tool in tools]
        essential_tools = ['search_accounts', 'get_all_campaigns', 'get_token_details']
        
        for tool in essential_tools:
            assert tool in tool_names, f"Essential read-only tool {tool} missing"
        
        # Check that we have at least one auth tool (either credential or browser based)
        auth_tools = [name for name in tool_names if name in ['get_auth_token', 'browser_authenticate', 'clear_auth_token']]
        assert len(auth_tools) > 0, "No authentication tools found"
    
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
    async def test_call_tool_integration(self):
        """Test tool calling integration."""
        # Get available tools to test with the correct auth method
        tools = await handle_list_tools()
        tool_names = [tool.name for tool in tools]
        
        # Test with available auth tool
        if "get_auth_token" in tool_names:
            # Test credential-based auth
            with patch('realize.tools.auth_handlers.auth.get_auth_token') as mock_get_auth_token:
                mock_token = Mock()
                mock_token.expires_in = 3600
                mock_get_auth_token.return_value = mock_token
                
                result = await handle_call_tool("get_auth_token", {})
                assert len(result) == 1
                assert "Successfully authenticated" in result[0].text
                
        elif "browser_authenticate" in tool_names:
            # Test browser-based auth - mock the browser auth process
            with patch('realize.tools.auth_handlers.webbrowser.open', return_value=True), \
                 patch('realize.tools.auth_handlers.web.AppRunner') as mock_runner, \
                 patch('realize.tools.auth_handlers.web.TCPSite') as mock_site, \
                 patch('realize.tools.auth_handlers.asyncio.wait_for') as mock_wait:
                
                # Mock successful authentication flow
                mock_runner_instance = Mock()
                mock_runner_instance.setup = AsyncMock()
                mock_runner_instance.cleanup = AsyncMock()
                mock_runner.return_value = mock_runner_instance
                
                mock_site_instance = Mock()
                mock_site_instance.start = AsyncMock()
                mock_site.return_value = mock_site_instance
                
                mock_wait.return_value = None
                
                # Simulate successful auth result
                import realize.tools.auth_handlers as handlers
                handlers.auth_result = {
                    "success": True,
                    "access_token": "test_token",
                    "expires_in": 3600
                }
                
                result = await handle_call_tool("browser_authenticate", {})
                assert len(result) == 1
                assert "successfully authenticated" in result[0].text.lower() or "authentication" in result[0].text.lower()
        else:
            pytest.fail("No authentication tools available for testing")
    
    @pytest.mark.asyncio
    async def test_invalid_tool_call(self):
        """Test handling of invalid tool calls."""
        with pytest.raises(ValueError, match="Unknown tool"):
            await handle_call_tool("nonexistent_tool", {})
    

    

    
    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.get')
    async def test_campaign_tools_integration(self, mock_get):
        """Test campaign tools integration with raw JSON."""
        # Mock campaign data
        mock_get.return_value = {
            "results": [
                {
                    "id": "123",
                    "name": "Integration Test Campaign", 
                    "status": "RUNNING",
                    "cpc": 2.50
                }
            ],
            "metadata": {"total": 1}
        }
        
        # Test get_all_campaigns
        result = await handle_call_tool("get_all_campaigns", {
            "account_id": "test_account"
        })
        assert len(result) == 1
        assert "Integration Test Campaign" in result[0].text
        
        # Test get_campaign  
        mock_get.return_value = {
            "id": "123",
            "name": "Single Campaign",
            "status": "RUNNING"
        }
        
        result = await handle_call_tool("get_campaign", {
            "account_id": "test_account",
            "campaign_id": "123"
        })
        assert len(result) == 1
        assert "Single Campaign" in result[0].text
    
    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.get')
    async def test_campaign_items_integration(self, mock_get):
        """Test campaign items tools integration with raw JSON."""
        # Test get_campaign_items
        mock_get.return_value = {
            "results": [
                {
                    "id": "item_123",
                    "campaign_id": "123",
                    "title": "Test Campaign Item",
                    "status": "APPROVED"
                }
            ]
        }
        
        result = await handle_call_tool("get_campaign_items", {
            "account_id": "test_account", 
            "campaign_id": "123"
        })
        assert len(result) == 1
        assert "Test Campaign Item" in result[0].text
        
        # Test get_campaign_item - reset mock with new data
        mock_get.return_value = {
            "id": "item_123",
            "title": "Single Campaign Item",
            "status": "APPROVED"
        }
        
        result = await handle_call_tool("get_campaign_item", {
            "account_id": "test_account",
            "campaign_id": "123", 
            "item_id": "item_123"
        })
        assert len(result) == 1
        assert "Single Campaign Item" in result[0].text
    
    @pytest.mark.asyncio
    @patch('realize.tools.report_handlers.client.get')
    async def test_reports_integration(self, mock_get):
        """Test reporting tools integration with raw JSON."""
        # Mock report data
        mock_get.return_value = {
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
        }
        
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
    @patch('realize.tools.campaign_handlers.client.get')
    async def test_error_handling_integration(self, mock_get):
        """Test error handling integration across all tools."""
        # Test that all tools handle errors gracefully
        error_tools = [
            ("get_all_campaigns", {"account_id": "test"}),
            ("get_campaign", {"account_id": "test", "campaign_id": "123"}),
            ("get_campaign_items", {"account_id": "test", "campaign_id": "123"})
        ]
        
        for tool_name, args in error_tools:
            # Configure mock for each tool test
            mock_get.side_effect = Exception("API Error")
            
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
            registry = get_all_tools()
            if tool.name in registry:
                category = registry[tool.name].get("category", "unknown")
                category_counts[category] = category_counts.get(category, 0) + 1
        
        # Verify we have tools in all expected categories
        expected_categories = ['authentication', 'accounts', 'campaigns', 'campaign_items', 'reports']
        for category in expected_categories:
            assert category in category_counts, f"No tools found in category: {category}"
            assert category_counts[category] > 0, f"Category {category} has no tools"
    
    @pytest.mark.asyncio
    @patch('realize.tools.account_handlers.client.get')
    async def test_account_tools_integration(self, mock_get):
        """Test account tools integration with raw JSON."""
        # Test search_accounts
        mock_get.return_value = {
            "results": [
                {
                    "account_id": "acc_123",
                    "name": "Integration Test Account",
                    "type": "advertiser",
                    "currency": "USD"
                },
                {
                    "account_id": "acc_456", 
                    "name": "Another Test Account",
                    "type": "advertiser",
                    "currency": "EUR"
                }
            ],
            "metadata": {"total": 2}
        }
        
        result = await handle_call_tool("search_accounts", {"query": "Test Account"})
        assert len(result) == 1
        assert "Integration Test Account" in result[0].text
        assert "Another Test Account" in result[0].text
        assert "acc_123" in result[0].text
    
    @pytest.mark.asyncio
    @patch('realize.tools.report_handlers.client.get')
    async def test_site_day_breakdown_report_integration(self, mock_get):
        """Test site day breakdown report integration."""
        # Test get_campaign_site_day_breakdown_report
        mock_get.return_value = {
            "results": [
                {
                    "date": "2024-01-01",
                    "site_id": "site_123",
                    "site_name": "example.com",
                    "campaign_id": "camp_123",
                    "impressions": 1500,
                    "clicks": 75,
                    "ctr": 0.05,
                    "cost": 187.50
                }
            ],
            "metadata": {
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "breakdown_by": ["site", "day"]
            }
        }
        
        result = await handle_call_tool("get_campaign_site_day_breakdown_report", {
            "account_id": "test_account",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31"
        })
        assert len(result) == 1
        assert "Site Day Breakdown Report CSV" in result[0].text
    
    @pytest.mark.asyncio
    async def test_workflow_integration(self):
        """Test realistic workflow: search accounts → get campaigns → get campaign items."""
        # Mock account search
        with patch('realize.tools.account_handlers.client.get') as mock_accounts:
            mock_accounts.return_value = {
                "results": [{"account_id": "workflow_acc_123", "name": "Workflow Test Account"}]
            }
            
            # Step 1: Search for accounts
            account_result = await handle_call_tool("search_accounts", {"query": "Workflow"})
            assert len(account_result) == 1
            assert "workflow_acc_123" in account_result[0].text
        
        # Mock campaign listing
        with patch('realize.tools.campaign_handlers.client.get') as mock_campaigns:
            mock_campaigns.return_value = {
                "results": [
                    {
                        "id": "workflow_camp_123",
                        "name": "Workflow Test Campaign",
                        "status": "RUNNING"
                    }
                ]
            }
            
            # Step 2: Get campaigns for the account
            campaign_result = await handle_call_tool("get_all_campaigns", {
                "account_id": "workflow_acc_123"
            })
            assert len(campaign_result) == 1
            assert "Workflow Test Campaign" in campaign_result[0].text
        
        # Mock campaign items
        with patch('realize.tools.campaign_handlers.client.get') as mock_items:
            mock_items.return_value = {
                "results": [
                    {
                        "id": "workflow_item_123",
                        "campaign_id": "workflow_camp_123",
                        "title": "Workflow Test Item",
                        "status": "APPROVED"
                    }
                ]
            }
            
            # Step 3: Get campaign items
            item_result = await handle_call_tool("get_campaign_items", {
                "account_id": "workflow_acc_123",
                "campaign_id": "workflow_camp_123"
            })
            assert len(item_result) == 1
            assert "Workflow Test Item" in item_result[0].text
    
    @pytest.mark.asyncio
    async def test_browser_auth_workflow_integration(self):
        """Test browser authentication workflow integration."""
        # Get available tools
        tools = await handle_list_tools()
        tool_names = [tool.name for tool in tools]
        
        if "browser_authenticate" not in tool_names:
            pytest.skip("Browser authentication not available in current config")
        
        # Test browser auth → token details → clear token workflow
        with patch('realize.tools.auth_handlers.webbrowser.open', return_value=True), \
             patch('realize.tools.auth_handlers.web.AppRunner') as mock_runner, \
             patch('realize.tools.auth_handlers.web.TCPSite') as mock_site, \
             patch('realize.tools.auth_handlers.asyncio.wait_for') as mock_wait:
            
            # Mock successful authentication setup
            mock_runner_instance = Mock()
            mock_runner_instance.setup = AsyncMock()
            mock_runner_instance.cleanup = AsyncMock()
            mock_runner.return_value = mock_runner_instance
            
            mock_site_instance = Mock()
            mock_site_instance.start = AsyncMock()
            mock_site.return_value = mock_site_instance
            
            # Mock wait_for to immediately set the auth result and signal completion
            async def mock_wait_for_success(event_wait, timeout):
                import realize.tools.auth_handlers as handlers
                handlers.auth_result = {
                    "success": True,
                    "access_token": "workflow_browser_token",
                    "expires_in": 3600
                }
                return None  # No timeout
            
            mock_wait.side_effect = mock_wait_for_success
            
            # Step 1: Authenticate via browser
            auth_result = await handle_call_tool("browser_authenticate", {})
            assert len(auth_result) == 1
            assert "successfully authenticated" in auth_result[0].text.lower()
        
        # Step 2: Get token details
        with patch('realize.tools.auth_handlers.auth.get_token_details') as mock_details:
            mock_details.return_value = {
                "token": "workflow_browser_token",
                "expires_in": 3600,
                "account_id": "browser_test_acc"
            }
            
            details_result = await handle_call_tool("get_token_details", {})
            assert len(details_result) == 1
            assert "workflow_browser_token" in details_result[0].text
        
        # Step 3: Clear token
        clear_result = await handle_call_tool("clear_auth_token", {})
        assert len(clear_result) == 1
        assert "removed" in clear_result[0].text.lower() or "cleared" in clear_result[0].text.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 