"""Test browser-based authentication functionality."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from realize.auth import BrowserAuth
from realize.models import Token


class TestBrowserAuthentication:
    """Test browser-based authentication functionality."""
    
    def test_browser_auth_initialization(self):
        """Test that BrowserAuth initializes correctly."""
        auth = BrowserAuth()
        assert auth.token is None
        assert auth.base_url is not None
    
    def test_browser_auth_token_storage(self):
        """Test that browser auth can store and retrieve tokens."""
        auth = BrowserAuth()
        
        test_token = Token(
            access_token='test_browser_token',
            token_type='Bearer',
            expires_in=3600
        )
        
        # Set token
        auth.token = test_token
        assert auth.token.access_token == 'test_browser_token'
        assert auth.token.expires_in == 3600
    
    @pytest.mark.asyncio
    async def test_browser_auth_without_token_raises_error(self):
        """Test that get_auth_token raises error when no token is set."""
        auth = BrowserAuth()
        
        with pytest.raises(Exception) as exc_info:
            await auth.get_auth_token()
        
        assert "No browser auth token available" in str(exc_info.value)
        assert "browser_authenticate tool" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_browser_auth_with_valid_token(self):
        """Test that get_auth_token returns token when set."""
        auth = BrowserAuth()
        
        test_token = Token(
            access_token='valid_browser_token',
            token_type='Bearer',
            expires_in=3600
        )
        auth.token = test_token
        
        retrieved_token = await auth.get_auth_token()
        assert retrieved_token.access_token == 'valid_browser_token'
        assert retrieved_token.expires_in == 3600
    
    @pytest.mark.asyncio
    async def test_browser_auth_header_generation(self):
        """Test that auth header is generated correctly."""
        auth = BrowserAuth()
        
        test_token = Token(
            access_token='header_test_token',
            token_type='Bearer',
            expires_in=3600
        )
        auth.token = test_token
        
        # Mock _is_token_expired to return False
        with patch.object(auth, '_is_token_expired', return_value=False):
            header = await auth.get_auth_header()
            assert header == {"Authorization": "Bearer header_test_token"}
    
    @pytest.mark.asyncio
    async def test_browser_auth_expired_token_handling(self):
        """Test handling of expired tokens."""
        auth = BrowserAuth()
        
        # Clear any existing token first
        auth.token = None
        
        # Mock _is_token_expired to return True (indicating no token or expired token)
        with patch.object(auth, '_is_token_expired', return_value=True):
            # When no token exists and expired check returns True, 
            # get_auth_header should fail
            with pytest.raises(Exception) as exc_info:
                await auth.get_auth_header()
            
            assert "No browser auth token available" in str(exc_info.value)
    
    def test_browser_auth_token_clearing(self):
        """Test that tokens can be cleared."""
        auth = BrowserAuth()
        
        # Set a token
        test_token = Token(
            access_token='to_be_cleared',
            token_type='Bearer',
            expires_in=3600
        )
        auth.token = test_token
        assert auth.token is not None
        
        # Clear the token
        auth.token = None
        assert auth.token is None


class TestBrowserAuthHandlers:
    """Test browser authentication tool handlers."""
    
    @pytest.mark.asyncio
    async def test_browser_authenticate_tool_handler(self):
        """Test browser authenticate tool handler."""
        from realize.tools.auth_handlers import browser_authenticate
        
        # Mock the browser authentication process components
        with patch('realize.tools.auth_handlers.webbrowser.open', return_value=True) as mock_browser, \
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
            
            # Mock successful wait (no timeout)
            mock_wait.return_value = None
            
            # Simulate successful auth result
            import realize.tools.auth_handlers as handlers
            handlers.auth_result = {
                "success": True,
                "access_token": "test_token",
                "expires_in": 3600
            }
            
            result = await browser_authenticate()
            
            # Should return list of TextContent
            assert isinstance(result, list)
            assert len(result) == 1
            assert hasattr(result[0], 'text')
            
            # Should contain success message
            result_text = result[0].text.lower()
            assert "successfully authenticated" in result_text or "authentication" in result_text
    
    @pytest.mark.asyncio
    async def test_clear_auth_token_handler(self):
        """Test clear auth token handler."""
        from realize.tools.auth_handlers import clear_auth_token
        from realize.auth import auth
        
        # Set a token first
        test_token = Token(
            access_token='to_be_cleared',
            token_type='Bearer',
            expires_in=3600
        )
        auth.token = test_token
        
        # Clear the token
        result = await clear_auth_token()
        
        # Should return list of TextContent
        assert isinstance(result, list)
        assert len(result) == 1
        
        # Should confirm clearing
        result_text = result[0].text.lower()
        assert "removed" in result_text or "cleared" in result_text
        assert auth.token is None
    
    @pytest.mark.asyncio
    async def test_browser_authenticate_error_handling(self):
        """Test browser authenticate error handling."""
        from realize.tools.auth_handlers import browser_authenticate
        
        # Mock browser authentication to fail during server setup
        with patch('realize.tools.auth_handlers.web.AppRunner') as mock_runner:
            mock_runner.side_effect = Exception("Authentication server failed")
            
            result = await browser_authenticate()
            
            # Should handle error gracefully
            assert isinstance(result, list)
            assert len(result) == 1
            result_text = result[0].text.lower()
            assert "failed" in result_text or "error" in result_text


class TestBrowserAuthIntegration:
    """Test browser auth integration with the overall system."""
    
    def test_browser_auth_selected_when_no_credentials(self):
        """Test that browser auth is selected when no credentials are configured."""
        from realize.auth import auth
        from realize.config import config
        
        # In test environment, credentials should be placeholder values
        assert config.realize_client_id == "your_client_id"
        assert config.realize_client_secret == "your_client_secret"
        
        # So auth should be BrowserAuth
        assert isinstance(auth, BrowserAuth)
    
    @pytest.mark.asyncio
    async def test_browser_auth_tool_availability(self):
        """Test that browser auth tools are available when using browser auth."""
        from realize.tools.registry import get_all_tools
        
        tools = get_all_tools()
        
        # Should have browser auth tools
        assert "browser_authenticate" in tools
        assert "clear_auth_token" in tools
        assert "get_token_details" in tools
        
        # Should NOT have credential-based auth tool
        assert "get_auth_token" not in tools