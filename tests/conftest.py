"""Pytest configuration and fixtures for realize-mcp tests."""
import os

# Set default environment variables for tests BEFORE any imports
# These are required for config validation
# Use values that don't trigger placeholder detection in tests
os.environ.setdefault("REALIZE_CLIENT_ID", "realize_mcp_ci_client")
os.environ.setdefault("REALIZE_CLIENT_SECRET", "realize_mcp_ci_secret")
os.environ.setdefault("MCP_TRANSPORT", "stdio")
