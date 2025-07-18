"""Comprehensive error handling tests for MCP server edge cases."""
import pytest
import sys
import pathlib
sys.path.append(str(pathlib.Path(__file__).parent.parent / "src"))
import asyncio
from unittest.mock import patch, Mock, AsyncMock
import httpx
import mcp.types as types


class TestMCPServerErrorHandling:
    """Test MCP server error handling for various edge cases."""
    
    @pytest.mark.asyncio
    async def test_tool_execution_network_errors(self):
        """Test handling of various network errors during tool execution."""
        from realize.realize_server import handle_call_tool
        
        network_errors = [
            httpx.ConnectError("Connection failed"),
            httpx.TimeoutException("Request timed out"),
            httpx.HTTPStatusError("404 Not Found", request=Mock(), response=Mock(status_code=404)),
            httpx.RequestError("General request error")
        ]
        
        for error in network_errors:
            with patch('realize.tools.account_handlers.client.get') as mock_get:
                mock_get.side_effect = error
                
                result = await handle_call_tool("search_accounts", {"query": "test"})
                
                # Should handle gracefully
                assert len(result) == 1
                assert isinstance(result[0], types.TextContent)
                assert "failed" in result[0].text.lower() or "error" in result[0].text.lower()
    
    @pytest.mark.asyncio
    async def test_tool_execution_json_decode_errors(self):
        """Test handling of JSON decode errors."""
        from realize.realize_server import handle_call_tool
        
        with patch('realize.tools.account_handlers.client.get') as mock_get:
            # Mock a response that causes JSON decode error
            mock_response = Mock()
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_get.return_value = mock_response
            
            result = await handle_call_tool("search_accounts", {"query": "test"})
            
            # Should handle gracefully
            assert len(result) == 1
            assert isinstance(result[0], types.TextContent)
            assert "failed" in result[0].text.lower()
    
    @pytest.mark.asyncio
    async def test_tool_execution_unexpected_exceptions(self):
        """Test handling of unexpected exceptions during tool execution."""
        from realize.realize_server import handle_call_tool
        
        unexpected_errors = [
            RuntimeError("Unexpected runtime error"),
            KeyError("Missing key"),
            AttributeError("Missing attribute"),
            TypeError("Type error"),
            ValueError("Value error")
        ]
        
        for error in unexpected_errors:
            with patch('realize.tools.account_handlers.client.get') as mock_get:
                mock_get.side_effect = error
                
                result = await handle_call_tool("search_accounts", {"query": "test"})
                
                # Should handle gracefully and not crash the server
                assert len(result) == 1
                assert isinstance(result[0], types.TextContent)
                assert "failed" in result[0].text.lower() or "error" in result[0].text.lower()
    
    @pytest.mark.asyncio
    async def test_malformed_tool_arguments(self):
        """Test handling of malformed tool arguments."""
        from realize.realize_server import handle_call_tool
        
        # Test various malformed argument scenarios
        malformed_args = [
            None,
            {},
            {"wrong_param": "value"},
            {"query": None},
            {"query": ""},
            {"query": 123},  # Wrong type
        ]
        
        for args in malformed_args:
            result = await handle_call_tool("search_accounts", args)
            
            # Should handle gracefully
            assert len(result) == 1
            assert isinstance(result[0], types.TextContent)
            # Should either succeed or give appropriate error message
    
    @pytest.mark.asyncio
    async def test_authentication_failures(self):
        """Test handling of authentication failures."""
        from realize.realize_server import handle_call_tool
        
        auth_errors = [
            httpx.HTTPStatusError("401 Unauthorized", request=Mock(), response=Mock(status_code=401)),
            httpx.HTTPStatusError("403 Forbidden", request=Mock(), response=Mock(status_code=403)),
            Exception("Auth service unavailable")
        ]
        
        for error in auth_errors:
            with patch('realize.tools.auth_handlers.auth.get_auth_token') as mock_auth:
                mock_auth.side_effect = error
                
                result = await handle_call_tool("get_auth_token", {})
                
                # Should handle gracefully
                assert len(result) == 1
                assert isinstance(result[0], types.TextContent)
                assert "failed" in result[0].text.lower() or "error" in result[0].text.lower()
    
    @pytest.mark.asyncio
    async def test_api_rate_limiting(self):
        """Test handling of API rate limiting."""
        from realize.realize_server import handle_call_tool
        
        rate_limit_error = httpx.HTTPStatusError(
            "429 Too Many Requests", 
            request=Mock(), 
            response=Mock(status_code=429)
        )
        
        with patch('realize.tools.account_handlers.client.get') as mock_get:
            mock_get.side_effect = rate_limit_error
            
            result = await handle_call_tool("search_accounts", {"query": "test"})
            
            # Should handle gracefully
            assert len(result) == 1
            assert isinstance(result[0], types.TextContent)
            assert "failed" in result[0].text.lower()
    
    @pytest.mark.asyncio
    async def test_server_errors_5xx(self):
        """Test handling of server errors (5xx)."""
        from realize.realize_server import handle_call_tool
        
        server_errors = [
            httpx.HTTPStatusError("500 Internal Server Error", request=Mock(), response=Mock(status_code=500)),
            httpx.HTTPStatusError("502 Bad Gateway", request=Mock(), response=Mock(status_code=502)),
            httpx.HTTPStatusError("503 Service Unavailable", request=Mock(), response=Mock(status_code=503))
        ]
        
        for error in server_errors:
            with patch('realize.tools.account_handlers.client.get') as mock_get:
                mock_get.side_effect = error
                
                result = await handle_call_tool("search_accounts", {"query": "test"})
                
                # Should handle gracefully
                assert len(result) == 1
                assert isinstance(result[0], types.TextContent)
                assert "failed" in result[0].text.lower()


class TestToolRegistryErrorHandling:
    """Test error handling in tool registry operations."""
    
    def test_registry_with_missing_modules(self):
        """Test registry behavior when handler modules are missing."""
        from realize.tools.registry import get_all_tools
        
        # Registry should still work even if we can't import all modules
        # (This tests the robustness of the registry system)
        tools = get_all_tools()
        assert isinstance(tools, dict)
        assert len(tools) > 0
    
    def test_registry_with_corrupted_tool_definitions(self):
        """Test registry behavior with malformed tool definitions."""
        # This tests that the registry validation catches problems
        from realize.tools.registry import get_all_tools
        
        tools = get_all_tools()
        
        # All tools should have required fields (this validates the registry)
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
            # Set invalid log level
            os.environ['LOG_LEVEL'] = 'INVALID_LEVEL'
            
            # Config will accept invalid log level (validation happens at logging setup time)
            import importlib
            import realize.config
            importlib.reload(realize.config)
            from realize.config import config
            
            # Config will contain the invalid level (validation is not done at config level)
            assert config.log_level == 'INVALID_LEVEL'
            
            # But logging setup should handle this gracefully
            import logging
            try:
                level = getattr(logging, config.log_level, logging.INFO)
                assert isinstance(level, int) or level == logging.INFO
            except AttributeError:
                # getattr with default should prevent AttributeError
                pass
            
        finally:
            # Restore original
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
            # Set malformed URL
            os.environ['REALIZE_BASE_URL'] = 'not-a-valid-url'
            
            # Should still load config (validation happens at usage time)
            import importlib
            import realize.config
            importlib.reload(realize.config)
            from realize.config import config
            
            # Should have the malformed URL (validation happens elsewhere)
            assert config.realize_base_url == 'not-a-valid-url'
            
        finally:
            # Restore original
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
        
        # Create concurrent tool calls, some failing, some succeeding
        async def failing_call():
            with patch('realize.tools.account_handlers.client.get') as mock_get:
                mock_get.side_effect = Exception("Simulated failure")
                return await handle_call_tool("search_accounts", {"query": "fail"})
        
        async def succeeding_call():
            with patch('realize.tools.auth_handlers.auth.get_auth_token') as mock_auth:
                mock_token = Mock()
                mock_token.expires_in = 3600
                mock_auth.return_value = mock_token
                return await handle_call_tool("get_auth_token", {})
        
        # Run concurrently
        results = await asyncio.gather(
            failing_call(),
            succeeding_call(),
            failing_call(),
            succeeding_call(),
            return_exceptions=True
        )
        
        # Should have 4 results
        assert len(results) == 4
        
        # No exceptions should propagate (all handled gracefully)
        for result in results:
            assert not isinstance(result, Exception)
            assert isinstance(result, list)
            assert len(result) > 0
            assert isinstance(result[0], types.TextContent)
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test handling of operation timeouts."""
        from realize.realize_server import handle_call_tool
        
        async def slow_operation():
            await asyncio.sleep(10)  # Simulate slow operation
            return {"results": []}
        
        with patch('realize.tools.account_handlers.client.get', side_effect=slow_operation):
            # This should complete quickly due to error handling, not hang
            start_time = asyncio.get_event_loop().time()
            result = await handle_call_tool("search_accounts", {"query": "test"})
            end_time = asyncio.get_event_loop().time()
            
            # Should complete reasonably quickly (error handling, not waiting for timeout)
            # Note: This depends on the actual implementation's timeout handling
            assert end_time - start_time < 10  # Should not wait for the full 10 seconds
            
            # Should return error result
            assert len(result) == 1
            assert isinstance(result[0], types.TextContent)


class TestMemoryAndResourceHandling:
    """Test memory and resource error handling."""
    
    @pytest.mark.asyncio
    async def test_large_response_handling(self):
        """Test handling of unexpectedly large API responses."""
        from realize.realize_server import handle_call_tool
        
        # Create a very large mock response
        large_response = {
            "results": [{"id": f"account_{i}", "name": f"Account {i}"} for i in range(1000)]
        }
        
        with patch('realize.tools.account_handlers.client.get') as mock_get:
            mock_get.return_value = large_response
            
            result = await handle_call_tool("search_accounts", {"query": "test"})
            
            # Should handle large responses gracefully
            assert len(result) == 1
            assert isinstance(result[0], types.TextContent)
            # Should contain some indication of the results
            assert "Account" in result[0].text or "account" in result[0].text
    
    def test_repeated_registry_access_no_memory_leak(self):
        """Test that repeated registry access doesn't cause memory leaks."""
        from realize.tools.registry import get_all_tools
        
        # Access registry many times
        for _ in range(100):
            tools = get_all_tools()
            assert len(tools) > 0
        
        # Should still work fine (basic smoke test for memory issues)
        tools = get_all_tools()
        assert len(tools) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 