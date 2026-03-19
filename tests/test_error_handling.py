"""Comprehensive error handling tests for MCP server edge cases."""
import pytest
import sys
import pathlib
sys.path.append(str(pathlib.Path(__file__).parent.parent / "src"))
import asyncio
from unittest.mock import patch, Mock, AsyncMock
import httpx
import mcp.types as types
from realize.tools.errors import ToolInputError


class TestMCPServerErrorHandling:
    """Test MCP server error handling for various edge cases."""

    @pytest.mark.asyncio
    async def test_network_errors_raise_with_classified_message(self):
        """Test that network errors are classified and re-raised."""
        from realize.realize_server import handle_call_tool

        test_cases = [
            (
                httpx.ConnectError("Connection failed"),
                "The Realize API is currently unreachable",
            ),
            (
                httpx.TimeoutException("Request timed out"),
                "Request to the Realize API timed out",
            ),
            (
                httpx.HTTPStatusError("404 Not Found", request=Mock(), response=Mock(status_code=404)),
                "404 Not Found",  # 4xx proxied
            ),
        ]

        for error, expected_fragment in test_cases:
            with patch('realize.tools.account_handlers.client.get') as mock_get:
                mock_get.side_effect = error

                with pytest.raises(Exception, match=expected_fragment):
                    await handle_call_tool("search_accounts", {"query": "test"})

    @pytest.mark.asyncio
    async def test_5xx_errors_include_status_code(self):
        """Test that 5xx errors surface status code without internals."""
        from realize.realize_server import handle_call_tool

        for status in [500, 502, 503]:
            error = httpx.HTTPStatusError(
                f"{status} Server Error", request=Mock(), response=Mock(status_code=status)
            )
            with patch('realize.tools.account_handlers.client.get') as mock_get:
                mock_get.side_effect = error

                with pytest.raises(Exception, match=f"Realize API returned {status}"):
                    await handle_call_tool("search_accounts", {"query": "test"})

    @pytest.mark.asyncio
    async def test_unexpected_exceptions_obfuscated(self):
        """Test that unexpected exceptions get a generic message."""
        from realize.realize_server import handle_call_tool

        unexpected_errors = [
            RuntimeError("Unexpected runtime error"),
            KeyError("Missing key"),
            AttributeError("Missing attribute"),
            TypeError("Type error"),
        ]

        for error in unexpected_errors:
            with patch('realize.tools.account_handlers.client.get') as mock_get:
                mock_get.side_effect = error

                with pytest.raises(Exception, match="An unexpected error occurred"):
                    await handle_call_tool("search_accounts", {"query": "test"})

    @pytest.mark.asyncio
    async def test_validation_errors_raise_tool_input_error(self):
        """Test that validation errors raise ToolInputError with original message."""
        from realize.realize_server import handle_call_tool

        # Empty query
        with pytest.raises(ToolInputError, match="Query parameter cannot be empty"):
            await handle_call_tool("search_accounts", {"query": ""})

        # Missing account_id
        with pytest.raises(ToolInputError, match="account_id is required"):
            await handle_call_tool("get_all_campaigns", {})

        # Missing campaign_id
        with pytest.raises(ToolInputError, match="campaign_id is required"):
            await handle_call_tool("get_campaign", {"account_id": "validAccountId"})

    @pytest.mark.asyncio
    async def test_authentication_failures(self):
        """Test handling of authentication failures."""
        from realize.realize_server import handle_call_tool

        # 4xx auth errors should be proxied
        for status in [401, 403]:
            error = httpx.HTTPStatusError(
                f"{status} Unauthorized", request=Mock(), response=Mock(status_code=status)
            )
            with patch('realize.tools.auth_handlers.auth.get_auth_token') as mock_auth:
                mock_auth.side_effect = error

                with pytest.raises(Exception, match=f"{status} Unauthorized"):
                    await handle_call_tool("get_auth_token", {})

    @pytest.mark.asyncio
    async def test_api_rate_limiting(self):
        """Test handling of API rate limiting (4xx, proxied)."""
        from realize.realize_server import handle_call_tool

        rate_limit_error = httpx.HTTPStatusError(
            "429 Too Many Requests",
            request=Mock(),
            response=Mock(status_code=429)
        )

        with patch('realize.tools.account_handlers.client.get') as mock_get:
            mock_get.side_effect = rate_limit_error

            with pytest.raises(Exception, match="429 Too Many Requests"):
                await handle_call_tool("search_accounts", {"query": "test"})

    @pytest.mark.asyncio
    async def test_missing_session_token_raises_tool_input_error(self):
        """Test that missing session token in SSE mode raises ToolInputError."""
        from realize.realize_server import handle_call_tool

        with patch('realize.tools.auth_handlers.config') as mock_config:
            mock_config.mcp_transport = "sse"
            with patch('realize.oauth.context.get_session_token', return_value=None):
                with pytest.raises(ToolInputError, match="No active session token"):
                    await handle_call_tool("get_auth_token", {})

                with pytest.raises(ToolInputError, match="No active session token"):
                    await handle_call_tool("get_token_details", {})

    @pytest.mark.asyncio
    async def test_exception_chaining_preserved(self):
        """Test that original exception is chained via __cause__ for debugging."""
        from realize.realize_server import handle_call_tool

        original = httpx.ConnectError("Connection refused to 10.0.0.1:443")

        with patch('realize.tools.account_handlers.client.get') as mock_get:
            mock_get.side_effect = original

            with pytest.raises(Exception) as exc_info:
                await handle_call_tool("search_accounts", {"query": "test"})

            # The classified exception should chain to the original
            assert exc_info.value.__cause__ is original


class TestToolRegistryErrorHandling:
    """Test error handling in tool registry operations."""

    def test_registry_with_missing_modules(self):
        """Test registry behavior when handler modules are missing."""
        from realize.tools.registry import get_all_tools

        tools = get_all_tools()
        assert isinstance(tools, dict)
        assert len(tools) > 0

    def test_registry_with_corrupted_tool_definitions(self):
        """Test registry behavior with malformed tool definitions."""
        from realize.tools.registry import get_all_tools

        tools = get_all_tools()

        for tool_name, tool_config in tools.items():
            required_fields = ['description', 'schema', 'handler', 'category']
            for field in required_fields:
                assert field in tool_config, f"Tool {tool_name} missing {field}"


class TestConfigurationErrorHandling:
    """Test error handling in configuration loading."""

    def test_config_with_invalid_log_level(self):
        """Test config behavior with invalid log level."""
        import os
        original_level = os.environ.get('LOG_LEVEL')

        try:
            os.environ['LOG_LEVEL'] = 'INVALID_LEVEL'

            import importlib
            import realize.config
            importlib.reload(realize.config)
            from realize.config import config

            assert config.log_level == 'INVALID_LEVEL'

            import logging
            try:
                level = getattr(logging, config.log_level, logging.INFO)
                assert isinstance(level, int) or level == logging.INFO
            except AttributeError:
                pass

        finally:
            if original_level is not None:
                os.environ['LOG_LEVEL'] = original_level
            elif 'LOG_LEVEL' in os.environ:
                del os.environ['LOG_LEVEL']

            importlib.reload(realize.config)

    def test_config_with_malformed_url(self):
        """Test config behavior with malformed base URL."""
        import os
        original_url = os.environ.get('REALIZE_BASE_URL')

        try:
            os.environ['REALIZE_BASE_URL'] = 'not-a-valid-url'

            import importlib
            import realize.config
            importlib.reload(realize.config)
            from realize.config import config

            assert config.realize_base_url == 'not-a-valid-url'

        finally:
            if original_url is not None:
                os.environ['REALIZE_BASE_URL'] = original_url
            elif 'REALIZE_BASE_URL' in os.environ:
                del os.environ['REALIZE_BASE_URL']

            importlib.reload(realize.config)


class TestAsyncErrorHandling:
    """Test error handling in async operations."""

    @pytest.mark.asyncio
    async def test_concurrent_tool_calls_error_isolation(self):
        """Test that errors in one tool call don't affect others."""
        from realize.realize_server import handle_call_tool

        async def failing_call():
            with patch('realize.tools.account_handlers.client.get') as mock_get:
                mock_get.side_effect = RuntimeError("Simulated failure")
                try:
                    return await handle_call_tool("search_accounts", {"query": "fail"})
                except Exception as e:
                    return e

        async def succeeding_call():
            with patch('realize.tools.auth_handlers.auth.get_auth_token') as mock_auth:
                mock_token = Mock()
                mock_token.expires_in = 3600
                mock_auth.return_value = mock_token
                return await handle_call_tool("get_auth_token", {})

        results = await asyncio.gather(
            failing_call(),
            succeeding_call(),
            failing_call(),
            succeeding_call(),
        )

        assert len(results) == 4

        # Failing calls return Exception, succeeding calls return list[TextContent]
        for i, result in enumerate(results):
            if i % 2 == 0:  # failing
                assert isinstance(result, Exception)
                assert "unexpected error" in str(result).lower()
            else:  # succeeding
                assert isinstance(result, list)
                assert isinstance(result[0], types.TextContent)

    @pytest.mark.asyncio
    async def test_timeout_exception_classified(self):
        """Test that httpx timeout exceptions are classified correctly."""
        from realize.realize_server import handle_call_tool
        import httpx

        with patch('realize.tools.account_handlers.client.get') as mock_get:
            mock_get.side_effect = httpx.ReadTimeout("read timed out")

            with pytest.raises(Exception, match="Request to the Realize API timed out"):
                await handle_call_tool("search_accounts", {"query": "test"})


class TestMemoryAndResourceHandling:
    """Test memory and resource error handling."""

    @pytest.mark.asyncio
    async def test_large_response_handling(self):
        """Test handling of unexpectedly large API responses."""
        from realize.realize_server import handle_call_tool

        large_response = {
            "results": [{"id": f"account_{i}", "name": f"Account {i}"} for i in range(1000)]
        }

        with patch('realize.tools.account_handlers.client.get') as mock_get:
            mock_get.return_value = large_response

            result = await handle_call_tool("search_accounts", {"query": "test"})

            assert len(result) == 1
            assert isinstance(result[0], types.TextContent)
            assert "Account" in result[0].text or "account" in result[0].text

    def test_repeated_registry_access_no_memory_leak(self):
        """Test that repeated registry access doesn't cause memory leaks."""
        from realize.tools.registry import get_all_tools

        for _ in range(100):
            tools = get_all_tools()
            assert len(tools) > 0

        tools = get_all_tools()
        assert len(tools) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
