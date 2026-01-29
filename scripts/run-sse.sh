#!/bin/bash
# Startup script for Realize MCP Server in SSE mode with OAuth 2.1

set -e

# =============================================================================
# OAuth 2.1 / SSE Transport Configuration
#
# Note: REALIZE_CLIENT_ID/SECRET are NOT needed for SSE mode.
# The client's OAuth 2.1 access token is passed through to Taboola API.
# =============================================================================

# Transport mode
export MCP_TRANSPORT="sse"

# Public URL of this MCP server (ngrok URL)
export MCP_SERVER_URL="https://luciana-unangular-geminally.ngrok-free.dev"

# Taboola Backstage API (where MCP tools make API calls)
export REALIZE_BASE_URL="http://qa-chris-hall-pr-94305-1961-backstage.on-demand.svc.kube.la.taboolasyndication.com/backstage"

# Upstream OAuth authorization server
export OAUTH_SERVER_URL="http://qa-chris-hall-pr-94305-1961-authentication.on-demand.svc.kube.la.taboolasyndication.com:10290/authentication"

# Port for SSE server
export OAUTH_SERVER_PORT="8000"

# Dynamic Client Registration credentials (required - set in environment)
if [ -z "$OAUTH_DCR_CLIENT_ID" ] || [ -z "$OAUTH_DCR_CLIENT_SECRET" ]; then
    echo "ERROR: OAUTH_DCR_CLIENT_ID and OAUTH_DCR_CLIENT_SECRET must be set"
    exit 1
fi

# OAuth scopes
export OAUTH_SCOPES="all"

# Token refresh buffer (seconds before expiry to refresh)
export OAUTH_REFRESH_BUFFER_SECONDS="60"

# =============================================================================
# Logging
# =============================================================================
export LOG_LEVEL="DEBUG"

# =============================================================================
# Print configuration (mask secrets)
# =============================================================================
echo "========================================"
echo "Realize MCP Server - SSE Mode"
echo "========================================"
echo "MCP_TRANSPORT:        $MCP_TRANSPORT"
echo "MCP_SERVER_URL:       $MCP_SERVER_URL"
echo "OAUTH_SERVER_URL:  $OAUTH_SERVER_URL"
echo "OAUTH_SERVER_PORT:      $OAUTH_SERVER_PORT"
echo "OAUTH_DCR_CLIENT_ID:    $OAUTH_DCR_CLIENT_ID"
echo "OAUTH_SCOPES:           $OAUTH_SCOPES"
echo "LOG_LEVEL:              $LOG_LEVEL"
echo "========================================"
echo ""
echo "Endpoints:"
echo "  GET  /.well-known/oauth-protected-resource"
echo "  GET  /.well-known/oauth-authorization-server (proxied)"
echo "  GET  /authorize (redirects to upstream auth server)"
echo "  POST /register"
echo "  POST /oauth/token"
echo "  GET  /sse"
echo "========================================"
echo ""

# =============================================================================
# Start server
# =============================================================================
echo "Starting server..."
cd "$(dirname "$0")/.."
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
python3 -m realize.realize_server
