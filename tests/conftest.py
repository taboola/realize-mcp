"""Pytest configuration and fixtures for realize-mcp tests."""
import os
import pathlib
import sys

# Ensure local src/ takes precedence over any installed realize-mcp package
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

# Set default environment variables for tests BEFORE any imports
# These are required for config validation
# Use values that don't trigger placeholder detection in tests
os.environ.setdefault("REALIZE_CLIENT_ID", "realize_mcp_ci_client")
os.environ.setdefault("REALIZE_CLIENT_SECRET", "realize_mcp_ci_secret")
os.environ.setdefault("MCP_TRANSPORT", "stdio")
os.environ.setdefault("METRICS_ENABLED", "true")
