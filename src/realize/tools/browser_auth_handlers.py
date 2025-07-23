"""Browser authentication tool handlers."""
import logging
import webbrowser
import asyncio
import secrets
import urllib.parse
import os
import signal
import atexit
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
current_runner = None  # Track active server for cleanup


def cleanup_server():
    """Cleanup function for signal handlers and atexit."""
    global current_runner
    if current_runner:
        try:
            # Create a new event loop if needed (for signal handlers)
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            if not loop.is_running():
                loop.run_until_complete(current_runner.cleanup())
            else:
                # If loop is running, schedule cleanup
                loop.create_task(current_runner.cleanup())
            
            logger.info("Cleaned up OAuth server on process exit")
            current_runner = None
        except Exception as e:
            logger.error(f"Error during server cleanup: {e}")


def setup_cleanup_handlers():
    """Setup signal handlers and atexit callback for cleanup."""
    # Register cleanup for normal exit
    atexit.register(cleanup_server)
    
    # Register signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, cleaning up OAuth server")
        cleanup_server()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def browser_authenticate() -> List[types.TextContent]:
    """Initiate browser-based OAuth2 authentication flow."""
    global oauth_state, auth_result, auth_event, current_runner
    
    # Setup cleanup handlers
    setup_cleanup_handlers()
    
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
        current_runner = runner  # Track for cleanup
        await runner.setup()
        
        try:
            site = web.TCPSite(runner, 'localhost', PORT)
            await site.start()
        except OSError as e:
            await runner.cleanup()  # Cleanup runner if site start fails
            current_runner = None  # Clear tracking
            if "Address already in use" in str(e):
                return [
                    types.TextContent(
                        type="text",
                        text="Authentication server port 3456 is already in use. This might be from a previous authentication session. Please wait 30 seconds and try again, or restart your terminal to force cleanup."
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
                        text=f"Could not open browser automatically. Please copy and paste this URL into your browser to authenticate:\n\n{auth_url}\n\nYou have 15 minutes to complete the authentication."
                    )
                ]
            
            logger.info("Opened browser for authentication")
            
            # Wait for callback (with timeout)
            try:
                await asyncio.wait_for(auth_event.wait(), timeout=900)  # 15 minute timeout
            except asyncio.TimeoutError:
                return [
                    types.TextContent(
                        type="text",
                        text="Authentication timed out after 15 minutes. Please try again."
                    )
                ]
        finally:
            # Always cleanup server, even if there's an error
            await runner.cleanup()
            current_runner = None  # Clear tracking
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
                    text=f"Authentication failed: {error_msg}. Please try running the authentication command again."
                )
            ]
            
    except Exception as e:
        logger.error(f"Browser authentication failed: {e}")
        return [
            types.TextContent(
                type="text",
                text=f"Browser authentication failed due to an unexpected error: {str(e)}. Please try again or check your network connection."
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


async def clear_auth_token() -> List[types.TextContent]:
    """Remove stored authentication token, forcing user to reauthenticate."""
    try:
        from realize.auth import auth, BrowserAuth
        
        if isinstance(auth, BrowserAuth):
            # Clear the token from the auth instance
            auth.clear_token()
            logger.info("Successfully cleared browser authentication token")
            
            return [
                types.TextContent(
                    type="text",
                    text="Authentication token has been removed from memory. You will need to authenticate again for future API requests."
                )
            ]
        else:
            return [
                types.TextContent(
                    type="text",
                    text="No browser authentication token found to remove."
                )
            ]
            
    except Exception as e:
        logger.error(f"Failed to clear authentication token: {e}")
        return [
            types.TextContent(
                type="text",
                text=f"Failed to remove authentication token: {str(e)}"
            )
        ]