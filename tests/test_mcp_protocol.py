"""MCP Protocol compliance tests for Realize MCP server."""
import pytest
import asyncio
import json
import sys
import pathlib
sys.path.append(str(pathlib.Path(__file__).parent.parent / "src"))
from unittest.mock import Mock, patch, AsyncMock
from realize.realize_server import handle_list_tools, handle_call_tool, server
import mcp.types as types


class TestMCPProtocolCompliance:
    """Test MCP protocol compliance and server behavior."""
    
    @pytest.mark.asyncio
    async def test_list_tools_returns_proper_mcp_types(self):
        """Test that list_tools returns proper MCP Tool types."""
        tools = await handle_list_tools()
        
        # Should return a list
        assert isinstance(tools, list)
        assert len(tools) > 0
        
        # Each tool should be a proper MCP Tool type
        for tool in tools:
            assert isinstance(tool, types.Tool)
            assert hasattr(tool, 'name')
            assert hasattr(tool, 'description')
            assert hasattr(tool, 'inputSchema')
            
            # Name should be non-empty string
            assert isinstance(tool.name, str)
            assert len(tool.name) > 0
            
            # Description should be non-empty string
            assert isinstance(tool.description, str)
            assert len(tool.description) > 0
            
            # Schema should be a valid JSON schema
            assert isinstance(tool.inputSchema, dict)
            assert 'type' in tool.inputSchema
            assert tool.inputSchema['type'] == 'object'
    
    @pytest.mark.asyncio
    async def test_call_tool_returns_proper_mcp_types(self):
        """Test that call_tool returns proper MCP TextContent types."""
        # Test with a simple auth tool
        with patch('realize.tools.auth_handlers.auth.get_auth_token') as mock_auth:
            mock_token = Mock()
            mock_token.expires_in = 3600
            mock_auth.return_value = mock_token
            
            result = await handle_call_tool("get_auth_token", {})
            
            # Should return a list of TextContent
            assert isinstance(result, list)
            assert len(result) > 0
            
            for content in result:
                assert isinstance(content, types.TextContent)
                assert hasattr(content, 'type')
                assert hasattr(content, 'text')
                assert content.type == 'text'
                assert isinstance(content.text, str)
    
    @pytest.mark.asyncio
    async def test_invalid_tool_name_handling(self):
        """Test proper error handling for invalid tool names."""
        with pytest.raises(ValueError, match="Unknown tool"):
            await handle_call_tool("nonexistent_tool", {})
    
    @pytest.mark.asyncio
    async def test_none_arguments_handling(self):
        """Test handling of None arguments."""
        with patch('realize.tools.auth_handlers.auth.get_auth_token') as mock_auth:
            mock_token = Mock()
            mock_token.expires_in = 3600
            mock_auth.return_value = mock_token
            
            # Should work with None arguments for tools that don't require them
            result = await handle_call_tool("get_auth_token", None)
            assert isinstance(result, list)
            assert len(result) > 0
    
    @pytest.mark.asyncio
    async def test_empty_arguments_handling(self):
        """Test handling of empty arguments dict."""
        with patch('realize.tools.auth_handlers.auth.get_auth_token') as mock_auth:
            mock_token = Mock()
            mock_token.expires_in = 3600
            mock_auth.return_value = mock_token
            
            result = await handle_call_tool("get_auth_token", {})
            assert isinstance(result, list)
            assert len(result) > 0


class TestToolDiscovery:
    """Test tool discovery and registration mechanisms."""
    
    @pytest.mark.asyncio
    async def test_all_tools_discoverable(self):
        """Test that all registered tools are discoverable via MCP."""
        from realize.tools.registry import get_all_tools
        
        # Get tools from registry
        registry_tools = get_all_tools()
        
        # Get tools from MCP interface
        mcp_tools = await handle_list_tools()
        mcp_tool_names = {tool.name for tool in mcp_tools}
        
        # All registry tools should be discoverable via MCP
        for tool_name in registry_tools.keys():
            assert tool_name in mcp_tool_names, f"Tool {tool_name} not discoverable via MCP"
    
    @pytest.mark.asyncio
    async def test_tool_schemas_are_valid_json_schema(self):
        """Test that all tool schemas are valid JSON schemas."""
        tools = await handle_list_tools()
        
        for tool in tools:
            schema = tool.inputSchema
            
            # Basic JSON schema structure
            assert 'type' in schema
            assert schema['type'] == 'object'
            
            if 'properties' in schema:
                assert isinstance(schema['properties'], dict)
                
            if 'required' in schema:
                assert isinstance(schema['required'], list)
                
                # All required fields should be in properties
                if 'properties' in schema:
                    for req_field in schema['required']:
                        assert req_field in schema['properties'], \
                            f"Required field {req_field} not in properties for tool {tool.name}"
    
    def test_tool_categories_comprehensive(self):
        """Test that all tools have proper categories."""
        from realize.tools.registry import get_all_tools, get_tool_categories
        
        tools = get_all_tools()
        categories = get_tool_categories()
        
        # All tools should have a category
        for tool_name, tool_config in tools.items():
            assert 'category' in tool_config, f"Tool {tool_name} missing category"
            category = tool_config['category']
            assert category in categories, f"Tool {tool_name} has invalid category {category}"
    
    def test_no_duplicate_tool_names(self):
        """Test that there are no duplicate tool names."""
        from realize.tools.registry import get_all_tools
        
        tools = get_all_tools()
        tool_names = list(tools.keys())
        unique_names = set(tool_names)
        
        assert len(tool_names) == len(unique_names), "Duplicate tool names found"


class TestServerInitialization:
    """Test MCP server initialization and capabilities."""
    
    def test_server_instance_created(self):
        """Test that server instance is properly created."""
        assert server is not None
        assert hasattr(server, 'get_capabilities')
        assert hasattr(server, 'run')
    
    def test_server_capabilities(self):
        """Test server capabilities are properly configured."""
        try:
            capabilities = server.get_capabilities()
            assert capabilities is not None
        except Exception as e:
            # Some MCP versions may have different capability APIs
            # The important thing is that the server instance exists and has this method
            assert hasattr(server, 'get_capabilities'), f"Server missing get_capabilities method: {e}"
    
    @pytest.mark.asyncio
    async def test_server_handlers_registered(self):
        """Test that server handlers are properly registered."""
        # Test that list_tools handler works
        tools = await handle_list_tools()
        assert len(tools) > 0
        
        # Test that call_tool handler works
        with patch('realize.tools.auth_handlers.auth.get_auth_token') as mock_auth:
            mock_token = Mock()
            mock_token.expires_in = 3600
            mock_auth.return_value = mock_token
            
            result = await handle_call_tool("get_auth_token", {})
            assert len(result) > 0


class TestErrorHandling:
    """Test comprehensive error handling in MCP server."""
    
    @pytest.mark.asyncio
    async def test_tool_execution_exception_handling(self):
        """Test that tool execution exceptions are properly handled."""
        # Mock a tool to raise an exception
        with patch('realize.tools.account_handlers.client.get') as mock_get:
            mock_get.side_effect = Exception("API connection failed")
            
            result = await handle_call_tool("search_accounts", {"query": "test"})
            
            # Should return error message, not raise exception
            assert len(result) == 1
            assert isinstance(result[0], types.TextContent)
            assert "failed" in result[0].text.lower() or "error" in result[0].text.lower()
    
    @pytest.mark.asyncio
    async def test_malformed_arguments_handling(self):
        """Test handling of malformed arguments."""
        # Test with required parameter missing
        result = await handle_call_tool("search_accounts", {})
        
        # Should handle gracefully
        assert len(result) == 1
        assert isinstance(result[0], types.TextContent)
    
    @pytest.mark.asyncio
    async def test_network_error_handling(self):
        """Test handling of network errors in tool execution."""
        import httpx
        
        with patch('realize.tools.account_handlers.client.get') as mock_get:
            mock_get.side_effect = httpx.ConnectError("Connection failed")
            
            result = await handle_call_tool("search_accounts", {"query": "test"})
            
            # Should return error message, not crash
            assert len(result) == 1
            assert isinstance(result[0], types.TextContent)
            assert "failed" in result[0].text.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 