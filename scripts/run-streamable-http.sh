#!/bin/bash
# Startup script for Realize MCP Server in Streamable HTTP mode with OAuth 2.1

set -e

# =============================================================================
# Configuration is loaded from .env file by pydantic-settings.
# Copy .env.example to .env and fill in your credentials.
# Environment variables set here act as overridable defaults.
# =============================================================================

cd "$(dirname "$0")/.."

# Use http scheme for local development (no TLS)
export MCP_SERVER_SCHEME="${MCP_SERVER_SCHEME:-http}"

# Transport mode
export MCP_TRANSPORT="${MCP_TRANSPORT:-streamable-http}"

# =============================================================================
# Start server
# =============================================================================
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

echo "========================================"
echo "Realize MCP Server - Streamable HTTP (local)"
echo "========================================"
echo "MCP_SERVER_SCHEME: $MCP_SERVER_SCHEME"
echo "Listening on:      http://localhost:8000"
echo ""
echo "Endpoints:"
echo "  POST|GET|DELETE /mcp  (Streamable HTTP)"
echo "  GET  /.well-known/oauth-protected-resource"
echo "  GET  /.well-known/oauth-authorization-server"
echo "  POST /register"
echo "  GET  /health"
echo "========================================"
echo ""

python3 -m realize.realize_server
