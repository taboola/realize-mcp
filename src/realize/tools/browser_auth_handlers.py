"""Browser authentication tool handlers."""
import logging
import webbrowser
import asyncio
import secrets
import urllib.parse
import os
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
        app.router.add_post('/oauth/process', handle_process)
        
        # Start server
        runner = web.AppRunner(app)
        await runner.setup()
        
        try:
            site = web.TCPSite(runner, 'localhost', PORT)
            await site.start()
        except OSError as e:
            await runner.cleanup()  # Cleanup runner if site start fails
            if "Address already in use" in str(e):
                return [
                    types.TextContent(
                        type="text",
                        text="Authentication server port is already in use. Please try again in a moment."
                    )
                ]
            raise
        
        logger.info(f"Started OAuth callback server on port {PORT}")
        
        try:
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
                return [
                    types.TextContent(
                        type="text",
                        text="Authentication timed out. Please try again."
                    )
                ]
        finally:
            # Always cleanup server, even if there's an error
            await runner.cleanup()
            logger.info("Cleaned up OAuth callback server")
        
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
    """Handle OAuth callback from browser - serves the HTML page."""
    # Load HTML content from external file
    html_file_path = os.path.join(os.path.dirname(__file__), 'assets', 'oauth_callback.html')
    try:
        with open(html_file_path, 'r') as f:
            html_content = f.read()
    except Exception as e:
        logger.error(f"Failed to load OAuth callback HTML: {e}")
        html_content = """
        <!DOCTYPE html>
        <html>
        <body>
            <h1>Error</h1>
            <p>Failed to load authentication page. Please try again.</p>
        </body>
        </html>
        """
    
    return web.Response(text=html_content, content_type='text/html')


async def handle_process(request):
    """Handle OAuth token processing via POST."""
    global oauth_state, auth_result, auth_event
    
    try:
        # Get JSON data from request body
        data = await request.json()
        
        # Validate state
        state = data.get('state')
        if state != oauth_state:
            auth_result = {"success": False, "error": "Invalid state parameter"}
            auth_event.set()
            return web.json_response({"status": "error", "message": "Invalid state parameter"}, status=400)
        
        # Check for access token
        if data.get('access_token'):
            # Success
            auth_result = {
                "success": True,
                "access_token": data.get('access_token'),
                "expires_in": int(data.get('expires_in', 3600))
            }
            # Signal completion
            auth_event.set()
            return web.json_response({"status": "success", "message": "Authentication successful"})
        else:
            # Error
            error_msg = data.get('error', 'No access token received')
            auth_result = {
                "success": False,
                "error": error_msg
            }
            # Signal completion
            auth_event.set()
            return web.json_response({"status": "error", "message": error_msg}, status=400)
            
    except Exception as e:
        logger.error(f"Error processing OAuth callback: {e}")
        auth_result = {"success": False, "error": str(e)}
        auth_event.set()
        return web.json_response({"status": "error", "message": "Failed to process authentication"}, status=500)