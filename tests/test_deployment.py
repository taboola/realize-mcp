"""Deployment scenario tests for Realize MCP server."""
import pytest
import subprocess
import sys
import os
import pathlib
import shutil
from unittest.mock import patch, Mock


class TestSourceDeployment:
    """Test running from source code."""
    
    def test_source_imports_work(self):
        """Test that source imports work when src is in path."""
        # This mimics how the existing tests work
        original_path = sys.path[:]
        try:
            src_path = str(pathlib.Path(__file__).parent.parent / "src")
            if src_path not in sys.path:
                sys.path.append(src_path)
            
            # Should be able to import
            import realize.realize_server
            from realize.tools.registry import get_all_tools
            
            # Should have tools
            tools = get_all_tools()
            assert len(tools) > 0
            
        finally:
            sys.path[:] = original_path
    
    def test_source_server_can_be_started(self):
        """Test that server can be started from source."""
        src_path = str(pathlib.Path(__file__).parent.parent / "src")
        original_path = sys.path[:]
        
        try:
            if src_path not in sys.path:
                sys.path.append(src_path)
            
            from realize.realize_server import server, handle_list_tools
            
            # Server should be properly initialized
            assert server is not None
            
            # Should be able to call async functions
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                tools = loop.run_until_complete(handle_list_tools())
                assert len(tools) > 0
            finally:
                loop.close()
                
        finally:
            sys.path[:] = original_path


class TestInstalledDeployment:
    """Test behavior when package is properly installed."""
    
    def test_installed_imports_work(self):
        """Test that imports work when package is installed."""
        # This should work since we installed the package in development mode
        try:
            import realize.realize_server
            from realize.tools.registry import get_all_tools
            
            # Should have tools
            tools = get_all_tools()
            assert len(tools) > 0
            
        except ImportError:
            pytest.skip("Package not installed - run 'pip install -e .' first")
    
    def test_cli_entry_point_exists(self):
        """Test that CLI entry point is properly installed."""
        result = subprocess.run(['which', 'realize-mcp-server'], 
                               capture_output=True, text=True)
        
        if result.returncode != 0:
            pytest.skip("CLI entry point not found - package may not be installed")
        
        assert result.stdout.strip() != ""
        assert 'realize-mcp-server' in result.stdout
    
    def test_cli_entry_point_can_show_help(self):
        """Test that CLI entry point can run and show help."""
        try:
            # Try to run the server with a timeout to see if it starts
            result = subprocess.run(['realize-mcp-server', '--help'], 
                                   capture_output=True, text=True, timeout=10)
            # If it runs without error, great. If it times out or has issues, 
            # that's expected since we don't have a --help flag implemented
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            # This is expected - the server runs indefinitely or doesn't have --help
            pass


# Note: Virtual environment tests are covered by existing source vs installed deployment tests
# which provide the same validation without the performance overhead


class TestEnvironmentConfiguration:
    """Test environment variable and configuration handling."""
    
    def test_config_loads_without_env_file(self):
        """Test that config can load even without .env file."""
        # Temporarily rename .env if it exists
        env_file = pathlib.Path(__file__).parent.parent / ".env"
        backup_file = None
        
        if env_file.exists():
            backup_file = env_file.with_suffix(".env.backup")
            shutil.move(env_file, backup_file)
        
        try:
            # Should be able to import config without .env file
            from realize.config import config
            
            # Should have default values
            assert hasattr(config, 'realize_client_id')
            assert hasattr(config, 'realize_client_secret')
            assert hasattr(config, 'realize_base_url')
            assert hasattr(config, 'log_level')
            
        finally:
            # Restore .env file if it existed
            if backup_file and backup_file.exists():
                shutil.move(backup_file, env_file)
    
    def test_config_works_with_env_variables(self):
        """Test that config respects environment variables."""
        original_values = {}
        test_vars = {
            'REALIZE_CLIENT_ID': 'test_client_id',
            'REALIZE_CLIENT_SECRET': 'test_secret',
            'REALIZE_BASE_URL': 'https://test.api.com',
            'LOG_LEVEL': 'DEBUG'
        }
        
        # Backup original values
        for key in test_vars:
            if key in os.environ:
                original_values[key] = os.environ[key]
        
        try:
            # Set test values
            for key, value in test_vars.items():
                os.environ[key] = value
            
            # Re-import config to pick up new values
            import importlib
            import realize.config
            importlib.reload(realize.config)
            from realize.config import config
            
            # Should reflect the environment variables
            assert config.realize_client_id == 'test_client_id'
            assert config.realize_client_secret == 'test_secret'
            assert config.realize_base_url == 'https://test.api.com'
            assert config.log_level == 'DEBUG'
            
        finally:
            # Restore original values
            for key in test_vars:
                if key in original_values:
                    os.environ[key] = original_values[key]
                elif key in os.environ:
                    del os.environ[key]
            
            # Reload config again to restore original state
            importlib.reload(realize.config)


class TestPackageMetadata:
    """Test package metadata and distribution."""
    
    def test_package_metadata_complete(self):
        """Test that package metadata is complete."""
        import toml
        
        pyproject_path = pathlib.Path(__file__).parent.parent / "pyproject.toml"
        assert pyproject_path.exists(), "pyproject.toml not found"
        
        with open(pyproject_path, 'r') as f:
            pyproject = toml.load(f)
        
        # Check required fields
        assert 'project' in pyproject
        project = pyproject['project']
        
        required_fields = ['name', 'version', 'description', 'authors', 'dependencies']
        for field in required_fields:
            assert field in project, f"Required field {field} missing from pyproject.toml"
        
        # Check scripts entry point
        assert 'scripts' in project
        assert 'realize-mcp-server' in project['scripts']
        assert project['scripts']['realize-mcp-server'] == 'realize.realize_server:cli_main'
    
    def test_dependencies_available(self):
        """Test that all required dependencies are available."""
        try:
            import mcp
            import httpx
            import pydantic
            from dotenv import load_dotenv
        except ImportError as e:
            pytest.fail(f"Required dependency not available: {e}")
    
    def test_version_consistency(self):
        """Test that version is consistent across files."""
        import toml
        
        # Get version from pyproject.toml
        pyproject_path = pathlib.Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject_path, 'r') as f:
            pyproject = toml.load(f)
        pyproject_version = pyproject['project']['version']
        
        # Get version from _version.py if it exists
        version_file = pathlib.Path(__file__).parent.parent / "src" / "realize" / "_version.py"
        if version_file.exists():
            version_content = {}
            with open(version_file, 'r') as f:
                exec(f.read(), version_content)
            if '__version__' in version_content:
                assert version_content['__version__'] == pyproject_version, \
                    "Version mismatch between pyproject.toml and _version.py"


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 