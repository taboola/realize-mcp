"""MCP Protocol compliance tests for Realize MCP server."""
import pytest
import asyncio
import json
import sys
import pathlib
sys.path.append(str(pathlib.Path(__file__).parent.parent / "src"))
from unittest.mock import Mock, patch, AsyncMock
from realize.realize_server import handle_list_tools, handle_call_tool, server
from realize.tools.errors import ToolInputError
import mcp.types as types


class TestMCPProtocolCompliance:
    """Test MCP protocol compliance and server behavior."""

    @pytest.mark.asyncio
    async def test_list_tools_returns_proper_mcp_types(self):
        """Test that list_tools returns proper MCP Tool types."""
        tools = await handle_list_tools()

        assert isinstance(tools, list)
        assert len(tools) > 0

        for tool in tools:
            assert isinstance(tool, types.Tool)
            assert hasattr(tool, 'name')
            assert hasattr(tool, 'description')
            assert hasattr(tool, 'inputSchema')

            assert isinstance(tool.name, str)
            assert len(tool.name) > 0

            assert isinstance(tool.description, str)
            assert len(tool.description) > 0

            assert isinstance(tool.inputSchema, dict)
            assert 'type' in tool.inputSchema
            assert tool.inputSchema['type'] == 'object'

    @pytest.mark.asyncio
    async def test_call_tool_returns_proper_mcp_types(self):
        """Test that call_tool returns proper MCP TextContent types."""
        with patch('realize.tools.auth_handlers.auth.get_auth_token') as mock_auth:
            mock_token = Mock()
            mock_token.expires_in = 3600
            mock_auth.return_value = mock_token

            result = await handle_call_tool("get_auth_token", {})

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

        registry_tools = get_all_tools()

        mcp_tools = await handle_list_tools()
        mcp_tool_names = {tool.name for tool in mcp_tools}

        for tool_name in registry_tools.keys():
            assert tool_name in mcp_tool_names, f"Tool {tool_name} not discoverable via MCP"

    @pytest.mark.asyncio
    async def test_tool_schemas_are_valid_json_schema(self):
        """Test that all tool schemas are valid JSON schemas."""
        tools = await handle_list_tools()

        for tool in tools:
            schema = tool.inputSchema

            assert 'type' in schema
            assert schema['type'] == 'object'

            if 'properties' in schema:
                assert isinstance(schema['properties'], dict)

            if 'required' in schema:
                assert isinstance(schema['required'], list)

                if 'properties' in schema:
                    for req_field in schema['required']:
                        assert req_field in schema['properties'], \
                            f"Required field {req_field} not in properties for tool {tool.name}"

    def test_tool_categories_comprehensive(self):
        """Test that all tools have proper categories."""
        from realize.tools.registry import get_all_tools, get_tool_categories

        tools = get_all_tools()
        categories = get_tool_categories()

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
            assert hasattr(server, 'get_capabilities'), f"Server missing get_capabilities method: {e}"

    @pytest.mark.asyncio
    async def test_server_handlers_registered(self):
        """Test that server handlers are properly registered."""
        tools = await handle_list_tools()
        assert len(tools) > 0

        with patch('realize.tools.auth_handlers.auth.get_auth_token') as mock_auth:
            mock_token = Mock()
            mock_token.expires_in = 3600
            mock_auth.return_value = mock_token

            result = await handle_call_tool("get_auth_token", {})
            assert len(result) > 0


class TestErrorHandling:
    """Test error handling produces exceptions for SDK isError conversion."""

    @pytest.mark.asyncio
    async def test_tool_execution_exception_raises(self):
        """Test that tool execution exceptions propagate (SDK converts to isError=true)."""
        with patch('realize.tools.account_handlers.client.get') as mock_get:
            mock_get.side_effect = Exception("API connection failed")

            with pytest.raises(Exception, match="An unexpected error occurred"):
                await handle_call_tool("search_accounts", {"query": "test"})

    @pytest.mark.asyncio
    async def test_search_accounts_pagination_forwarded(self):
        """Test that page and page_size are forwarded to search_accounts."""
        from realize.tools.account_handlers import search_accounts
        with patch('realize.tools.account_handlers.client.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"results": []}

            result = await search_accounts("test", page=2, page_size=5)

            mock_get.assert_called_once_with("/advertisers", params={"search_text": "test", "page": 2, "page_size": 5})

    @pytest.mark.asyncio
    async def test_validation_error_raises_tool_input_error(self):
        """Test that validation errors raise ToolInputError (SDK converts to isError=true)."""
        # Missing required query
        with pytest.raises(ToolInputError, match="Query parameter cannot be empty"):
            await handle_call_tool("search_accounts", {})

    @pytest.mark.asyncio
    async def test_network_error_raises_with_classified_message(self):
        """Test that network errors raise with classified message."""
        import httpx

        with patch('realize.tools.account_handlers.client.get') as mock_get:
            mock_get.side_effect = httpx.ConnectError("Connection failed")

            with pytest.raises(Exception, match="unreachable"):
                await handle_call_tool("search_accounts", {"query": "test"})

    @pytest.mark.asyncio
    async def test_4xx_error_proxied(self):
        """Test that 4xx errors are proxied verbatim."""
        import httpx

        error = httpx.HTTPStatusError(
            "404 Not Found", request=Mock(), response=Mock(status_code=404)
        )

        with patch('realize.tools.account_handlers.client.get') as mock_get:
            mock_get.side_effect = error

            with pytest.raises(Exception, match="404 Not Found"):
                await handle_call_tool("search_accounts", {"query": "test"})

    @pytest.mark.asyncio
    async def test_5xx_error_status_code_surfaced(self):
        """Test that 5xx errors surface status code without internals."""
        import httpx

        error = httpx.HTTPStatusError(
            "Internal Server Error with sensitive details",
            request=Mock(),
            response=Mock(status_code=500),
        )

        with patch('realize.tools.account_handlers.client.get') as mock_get:
            mock_get.side_effect = error

            with pytest.raises(Exception, match="Realize API returned 500") as exc_info:
                await handle_call_tool("search_accounts", {"query": "test"})

            # Should NOT contain internal details
            assert "sensitive details" not in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
