"""Browser authentication tool handlers."""
import logging
import webbrowser
import asyncio
import secrets
import urllib.parse
from typing import List, Optional
from aiohttp import web
import mcp.types as types
from realize.auth import auth

logger = logging.getLogger(__name__)

# Hardcoded OAuth2 configuration
CLIENT_ID = "5d76124a06234466bb65ee7680afc082"
REDIRECT_URI = "http://localhost:3456/oauth/callback"
AUTH_URL = "https://authentication.taboola.com/authentication/oauth/authorize"
PORT = 3456

# Global state storage for OAuth flow
oauth_state = None
auth_result = None
auth_event = None


async def browser_authenticate() -> List[types.TextContent]:
    """Initiate browser-based OAuth2 authentication flow."""
    global oauth_state, auth_result, auth_event
    
    # Reset global state
    oauth_state = None
    auth_result = None
    auth_event = asyncio.Event()
    
    try:
        # Generate random state for security
        state = secrets.token_urlsafe(32)
        oauth_state = state
        
        # Build authorization URL
        params = {
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "response_type": "token",
            "state": state,
            "appName": "Realize MCP"
        }
        auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"
        
        # Create aiohttp app for callback
        app = web.Application()
        app.router.add_get('/oauth/callback', handle_callback)
        
        # Start server
        runner = web.AppRunner(app)
        await runner.setup()
        
        try:
            site = web.TCPSite(runner, 'localhost', PORT)
            await site.start()
        except OSError as e:
            if "Address already in use" in str(e):
                return [
                    types.TextContent(
                        type="text",
                        text="Authentication server port is already in use. Please try again in a moment."
                    )
                ]
            raise
        
        logger.info(f"Started OAuth callback server on port {PORT}")
        
        # Open browser
        if not webbrowser.open(auth_url):
            logger.warning("Failed to open browser automatically")
            return [
                types.TextContent(
                    type="text",
                    text=f"Please open this URL in your browser to authenticate:\n{auth_url}"
                )
            ]
        
        logger.info("Opened browser for authentication")
        
        # Wait for callback (with timeout)
        try:
            await asyncio.wait_for(auth_event.wait(), timeout=300)  # 5 minute timeout
        except asyncio.TimeoutError:
            await runner.cleanup()
            return [
                types.TextContent(
                    type="text",
                    text="Authentication timed out. Please try again."
                )
            ]
        
        # Cleanup server
        await runner.cleanup()
        
        # Process result
        if auth_result and auth_result.get("success"):
            # Update the existing global auth instance
            from realize.auth import auth, BrowserAuth
            
            # Verify we have a BrowserAuth instance
            if isinstance(auth, BrowserAuth):
                # Update the existing instance's token
                auth.set_token(auth_result["access_token"], auth_result["expires_in"])
                logger.info("Updated browser auth token successfully")
            else:
                # This shouldn't happen if config is correct
                logger.error(f"Expected BrowserAuth instance but got {type(auth).__name__}")
                return [
                    types.TextContent(
                        type="text",
                        text="Error: Authentication system is not configured for browser auth. Please check configuration."
                    )
                ]
            
            return [
                types.TextContent(
                    type="text",
                    text=f"Successfully authenticated via browser. Token expires in {auth_result['expires_in']} seconds."
                )
            ]
        else:
            error_msg = auth_result.get("error", "Unknown error") if auth_result else "No response received"
            return [
                types.TextContent(
                    type="text",
                    text=f"Authentication failed: {error_msg}"
                )
            ]
            
    except Exception as e:
        logger.error(f"Browser authentication failed: {e}")
        return [
            types.TextContent(
                type="text",
                text=f"Browser authentication failed: {str(e)}"
            )
        ]


async def handle_callback(request):
    """Handle OAuth callback from browser."""
    global oauth_state, auth_result, auth_event
    
    # Extract fragment from URL (for implicit flow, token comes in fragment)
    # Since fragments aren't sent to server, we use JavaScript to extract and send as query params
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Realize MCP - Authentication</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                background-color: #f5f5f5;
            }
            .container {
                text-align: center;
                padding: 40px;
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                max-width: 400px;
            }
            .success {
                color: #4CAF50;
                font-size: 48px;
                margin-bottom: 20px;
            }
            .error {
                color: #f44336;
                font-size: 48px;
                margin-bottom: 20px;
            }
            h1 {
                margin: 0 0 10px 0;
                font-size: 24px;
            }
            p {
                color: #666;
                margin: 10px 0;
            }
        </style>
    </head>
    <body>
        <div class="container" id="container">
            <div id="content">
                <p>Processing authentication...</p>
            </div>
        </div>
        <script>
            // Extract token from fragment
            const hash = window.location.hash.substring(1);
            const params = new URLSearchParams(hash);
            const queryParams = new URLSearchParams(window.location.search);
            
            // Get state from query params (if error) or from hash params
            const state = queryParams.get('state') || params.get('state');
            const error = queryParams.get('error');
            
            if (error) {
                // Error case - redirect was to query params
                window.location.href = `/oauth/callback?processed=true&error=${encodeURIComponent(error)}&state=${encodeURIComponent(state)}`;
            } else if (params.get('access_token')) {
                // Success case - token in fragment
                const token = params.get('access_token');
                const expiresIn = params.get('expires_in');
                window.location.href = `/oauth/callback?processed=true&access_token=${encodeURIComponent(token)}&expires_in=${encodeURIComponent(expiresIn)}&state=${encodeURIComponent(state)}`;
            } else if (!queryParams.get('processed')) {
                // No token or error found
                window.location.href = '/oauth/callback?processed=true&error=no_token_received';
            }
            
            // If we're already processed, show the result
            if (queryParams.get('processed')) {
                const content = document.getElementById('content');
                if (queryParams.get('access_token')) {
                    content.innerHTML = `
                        <div class="success">✓</div>
                        <h1>Authentication Successful!</h1>
                        <p>You can now close this browser window and return to your terminal.</p>
                    `;
                    // Try to close window after 2 seconds
                    setTimeout(() => {
                        window.close();
                    }, 2000);
                } else {
                    const errorMsg = queryParams.get('error') || 'Unknown error';
                    content.innerHTML = `
                        <div class="error">✗</div>
                        <h1>Authentication Failed</h1>
                        <p>Error: ${errorMsg}</p>
                        <p>Please close this window and try again.</p>
                    `;
                }
            }
        </script>
    </body>
    </html>
    """
    
    # Check if this is the processed callback with params
    if request.query.get('processed'):
        # Validate state
        state = request.query.get('state')
        if state != oauth_state:
            auth_result = {"success": False, "error": "Invalid state parameter"}
        elif request.query.get('access_token'):
            # Success
            auth_result = {
                "success": True,
                "access_token": request.query.get('access_token'),
                "expires_in": int(request.query.get('expires_in', 3600))
            }
        else:
            # Error
            auth_result = {
                "success": False,
                "error": request.query.get('error', 'Unknown error')
            }
        
        # Signal completion
        auth_event.set()
    
    return web.Response(text=html_content, content_type='text/html')