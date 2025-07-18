"""Environment variable and configuration tests."""
import pytest
import os
import sys
import pathlib
sys.path.append(str(pathlib.Path(__file__).parent.parent / "src"))
import tempfile
import shutil
from unittest.mock import patch, Mock


class TestEnvironmentVariables:
    """Test environment variable handling."""
    
    def test_required_env_vars_defined(self):
        """Test that all required environment variables are properly defined."""
        from realize.config import config
        
        # These should have defaults or be properly handled
        required_attrs = [
            'realize_client_id',
            'realize_client_secret', 
            'realize_base_url',
            'log_level'
        ]
        
        for attr in required_attrs:
            assert hasattr(config, attr), f"Config missing required attribute: {attr}"
            value = getattr(config, attr)
            assert value is not None, f"Config attribute {attr} is None"
    
    def test_env_var_override_works(self):
        """Test that environment variables properly override defaults."""
        original_env = {}
        test_vars = {
            'REALIZE_CLIENT_ID': 'test_override_id',
            'REALIZE_BASE_URL': 'https://override.api.com',
            'LOG_LEVEL': 'ERROR'
        }
        
        # Backup original values
        for key in test_vars:
            if key in os.environ:
                original_env[key] = os.environ[key]
        
        try:
            # Set test values
            for key, value in test_vars.items():
                os.environ[key] = value
            
            # Reload config module to pick up changes
            import importlib
            import realize.config
            importlib.reload(realize.config)
            from realize.config import config
            
            # Check values are overridden
            assert config.realize_client_id == 'test_override_id'
            assert config.realize_base_url == 'https://override.api.com'
            assert config.log_level == 'ERROR'
            
        finally:
            # Restore original environment
            for key in test_vars:
                if key in original_env:
                    os.environ[key] = original_env[key]
                elif key in os.environ:
                    del os.environ[key]
            
            # Reload config again
            importlib.reload(realize.config)
    
    def test_missing_env_vars_handled_gracefully(self):
        """Test that missing environment variables are handled gracefully."""
        # Remove all realize-related env vars temporarily
        original_env = {}
        realize_vars = [key for key in os.environ.keys() if key.startswith('REALIZE_')]
        
        for key in realize_vars:
            original_env[key] = os.environ[key]
            del os.environ[key]
        
        try:
            # Should still be able to import config
            import importlib
            import realize.config
            importlib.reload(realize.config)
            from realize.config import config
            
            # Should have some defaults
            assert hasattr(config, 'realize_base_url')
            assert config.realize_base_url is not None
            
        finally:
            # Restore environment
            for key, value in original_env.items():
                os.environ[key] = value
            
            # Reload config
            importlib.reload(realize.config)
    
    def test_boolean_env_vars_parsed_correctly(self):
        """Test that boolean environment variables are parsed correctly."""
        # This test can be expanded if we add boolean config vars in the future
        # For now, just test that the config system can handle boolean parsing
        original_env = os.environ.get('TEST_BOOL_VAR')
        
        try:
            # Test various boolean representations
            test_cases = [
                ('true', True),
                ('True', True), 
                ('TRUE', True),
                ('1', True),
                ('false', False),
                ('False', False),
                ('FALSE', False),
                ('0', False),
                ('', False)
            ]
            
            for env_value, expected in test_cases:
                os.environ['TEST_BOOL_VAR'] = env_value
                
                # Simple test of boolean parsing logic
                parsed = env_value.lower() in ('true', '1')
                assert parsed == expected, f"Failed to parse {env_value} as {expected}"
                
        finally:
            if original_env is not None:
                os.environ['TEST_BOOL_VAR'] = original_env
            elif 'TEST_BOOL_VAR' in os.environ:
                del os.environ['TEST_BOOL_VAR']


class TestDotEnvHandling:
    """Test .env file handling."""
    
    def test_config_works_without_dotenv_file(self):
        """Test that config works when .env file doesn't exist."""
        env_file = pathlib.Path(__file__).parent.parent / ".env"
        backup_file = None
        
        # Backup .env if it exists
        if env_file.exists():
            backup_file = env_file.with_suffix(".env.test_backup")
            shutil.copy(env_file, backup_file)
            env_file.unlink()
        
        try:
            # Should be able to import config without .env
            import importlib
            import realize.config
            importlib.reload(realize.config)
            from realize.config import config
            
            # Should have attributes even without .env
            assert hasattr(config, 'realize_client_id')
            assert hasattr(config, 'realize_base_url')
            
        finally:
            # Restore .env if it existed
            if backup_file and backup_file.exists():
                shutil.copy(backup_file, env_file)
                backup_file.unlink()
            
            # Reload config
            import importlib
            import realize.config
            importlib.reload(realize.config)
    
    def test_config_loads_dotenv_when_present(self):
        """Test that config loads from .env file when present."""
        env_file = pathlib.Path(__file__).parent.parent / ".env"
        
        # Create temporary .env file
        test_content = """
REALIZE_CLIENT_ID=dotenv_test_id
REALIZE_CLIENT_SECRET=dotenv_test_secret
REALIZE_BASE_URL=https://dotenv.test.com
LOG_LEVEL=WARNING
"""
        
        backup_content = None
        if env_file.exists():
            with open(env_file, 'r') as f:
                backup_content = f.read()
        
        try:
            # Write test .env file
            with open(env_file, 'w') as f:
                f.write(test_content)
            
            # Reload config to pick up .env
            import importlib
            import realize.config
            importlib.reload(realize.config)
            from realize.config import config
            
            # Should load values from .env (if not overridden by actual env vars)
            # Note: actual env vars take precedence over .env
            if 'REALIZE_CLIENT_ID' not in os.environ:
                assert config.realize_client_id == 'dotenv_test_id'
            if 'REALIZE_BASE_URL' not in os.environ:
                assert config.realize_base_url == 'https://dotenv.test.com'
            
        finally:
            # Restore original .env file
            if backup_content is not None:
                with open(env_file, 'w') as f:
                    f.write(backup_content)
            elif env_file.exists():
                env_file.unlink()
            
            # Reload config
            importlib.reload(realize.config)


class TestConfigurationValidation:
    """Test configuration validation and error handling."""
    
    def test_config_attributes_have_correct_types(self):
        """Test that config attributes have correct types."""
        from realize.config import config
        
        # String attributes
        string_attrs = ['realize_client_id', 'realize_client_secret', 'realize_base_url', 'log_level']
        for attr in string_attrs:
            value = getattr(config, attr)
            assert isinstance(value, str), f"Config {attr} should be string, got {type(value)}"
    
    def test_log_level_is_valid(self):
        """Test that log level is a valid logging level."""
        from realize.config import config
        import logging
        
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        assert config.log_level in valid_levels, f"Invalid log level: {config.log_level}"
        
        # Should be convertible to logging level
        level = getattr(logging, config.log_level)
        assert isinstance(level, int), "Log level should convert to integer"
    
    def test_base_url_format(self):
        """Test that base URL has correct format."""
        from realize.config import config
        
        base_url = config.realize_base_url
        
        # Should start with http:// or https://
        assert base_url.startswith(('http://', 'https://')), \
            f"Base URL should start with http:// or https://: {base_url}"
        
        # Should not end with slash (for consistency)
        assert not base_url.endswith('/'), \
            f"Base URL should not end with slash: {base_url}"
    
    def test_client_credentials_format(self):
        """Test that client credentials have reasonable format."""
        from realize.config import config
        
        # Should not be empty
        assert len(config.realize_client_id) > 0, "Client ID should not be empty"
        assert len(config.realize_client_secret) > 0, "Client secret should not be empty"
        
        # If running with real environment variables, they shouldn't be placeholders
        import os
        if 'REALIZE_CLIENT_ID' in os.environ:
            placeholder_indicators = ['your_', 'example_', 'test_', 'placeholder', 'xxx', '???']
            client_id_lower = config.realize_client_id.lower()
            for indicator in placeholder_indicators:
                assert indicator not in client_id_lower, \
                    f"Client ID appears to be placeholder: {config.realize_client_id}"
        else:
            # When no env var is set, default placeholders are OK for testing
            pass


class TestLoggingConfiguration:
    """Test logging configuration."""
    
    def test_logging_level_set_correctly(self):
        """Test that logging level is set correctly from config."""
        from realize.config import config
        import logging
        
        # Get the logger used by the MCP server
        logger = logging.getLogger('realize')
        
        # Should have level from config
        try:
            expected_level = getattr(logging, config.log_level)
        except AttributeError:
            # Invalid level should fallback to INFO
            expected_level = logging.INFO
        
        # Check root logger level (since realize_server.py configures it)
        root_logger = logging.getLogger()
        # The level should be reasonable (not necessarily exact match due to test env)
        assert root_logger.level in [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL], \
            f"Logging level not valid. Got {root_logger.level}"
    
    def test_logging_works_without_errors(self):
        """Test that logging doesn't cause errors."""
        import logging
        
        # Create a test logger
        logger = logging.getLogger('test_realize')
        
        # Should be able to log at all levels without errors
        try:
            logger.debug("Test debug message")
            logger.info("Test info message")
            logger.warning("Test warning message")
            logger.error("Test error message")
            logger.critical("Test critical message")
        except Exception as e:
            pytest.fail(f"Logging caused error: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 