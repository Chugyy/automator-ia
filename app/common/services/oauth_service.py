import os
import json
import glob
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from config.common.logger import logger

class OAuthService:
    """Service for auto-discovery and registration of OAuth routes"""
    
    TOOLS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "private", "tools")
    
    @classmethod
    def discover_oauth_tools(cls) -> Dict[str, Dict[str, Any]]:
        """Discover all tools that support OAuth authentication"""
        oauth_tools = {}
        
        # Scan all tool directories
        for tool_dir in glob.glob(os.path.join(cls.TOOLS_DIR, "*/")):
            tool_name = os.path.basename(tool_dir.rstrip('/'))
            config_file = os.path.join(tool_dir, "config.json")
            main_file = os.path.join(tool_dir, "main.py")
            
            # Skip if not a valid tool
            if not (os.path.exists(config_file) and os.path.exists(main_file)):
                continue
                
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                oauth_config = config.get('oauth_config')
                if oauth_config:
                    oauth_tools[tool_name] = {
                        'config': oauth_config,
                        'display_name': config.get('display_name', tool_name),
                        'tool_path': tool_dir,
                        'class_name': f"{tool_name.title()}Tool"
                    }
                    logger.debug(f"Discovered OAuth tool: {tool_name}")
                    
            except Exception as e:
                logger.warning(f"Failed to load OAuth config for {tool_name}: {e}")
        
        return oauth_tools
    
    @classmethod
    def register_oauth_routes(cls, app) -> None:
        """Register OAuth routes for all discovered tools"""
        oauth_tools = cls.discover_oauth_tools()
        
        if not oauth_tools:
            logger.info("No OAuth tools discovered")
            return
        
        # Create main OAuth router
        oauth_router = APIRouter(prefix="/oauth", tags=["oauth"])
        
        # Register routes for each OAuth tool
        for tool_name, tool_info in oauth_tools.items():
            cls._register_tool_routes(oauth_router, tool_name, tool_info)
        
        # Include the OAuth router in the main app
        app.include_router(oauth_router)
        
        logger.info(f"Registered OAuth routes for {len(oauth_tools)} tools: {list(oauth_tools.keys())}")
    
    @classmethod
    def _register_tool_routes(cls, router: APIRouter, tool_name: str, tool_info: Dict[str, Any]) -> None:
        """Register OAuth routes for a specific tool"""
        
        @router.get(f"/{tool_name}/auth")
        async def auth_endpoint():
            """Initiate OAuth authentication"""
            try:
                tool_instance = cls._get_tool_instance(tool_name, tool_info)
                auth_url = tool_instance.get_auth_url()
                return RedirectResponse(url=auth_url)
            except Exception as e:
                logger.error(f"OAuth auth error for {tool_name}: {e}")
                raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")
        
        @router.get(f"/{tool_name}/callback")
        async def callback_endpoint(request: Request):
            """Handle OAuth callback"""
            try:
                tool_instance = cls._get_tool_instance(tool_name, tool_info)
                
                # Get state from query parameters
                state = request.query_params.get('state')
                
                # Handle the callback
                success = tool_instance.handle_oauth_callback(str(request.url), state)
                
                if success:
                    return {
                        "status": "success",
                        "message": f"{tool_info['display_name']} authentication successful",
                        "tool": tool_name
                    }
                else:
                    raise HTTPException(status_code=400, detail="Authentication failed")
                    
            except Exception as e:
                logger.error(f"OAuth callback error for {tool_name}: {e}")
                raise HTTPException(status_code=500, detail=f"Callback processing failed: {str(e)}")
        
        @router.get(f"/{tool_name}/status")
        async def status_endpoint():
            """Get OAuth authentication status"""
            try:
                tool_instance = cls._get_tool_instance(tool_name, tool_info)
                return tool_instance.get_oauth_status()
            except Exception as e:
                logger.error(f"OAuth status error for {tool_name}: {e}")
                raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")
        
        @router.post(f"/{tool_name}/revoke")
        async def revoke_endpoint():
            """Revoke OAuth authentication"""
            try:
                tool_instance = cls._get_tool_instance(tool_name, tool_info)
                # Remove token file
                token_path = os.path.join(tool_instance.base_dir, tool_instance.config['token_file'])
                if os.path.exists(token_path):
                    os.remove(token_path)
                    logger.info(f"OAuth token revoked for {tool_name}")
                    return {
                        "status": "success", 
                        "message": f"{tool_info['display_name']} authentication revoked"
                    }
                else:
                    return {
                        "status": "info", 
                        "message": f"No active authentication found for {tool_info['display_name']}"
                    }
            except Exception as e:
                logger.error(f"OAuth revoke error for {tool_name}: {e}")
                raise HTTPException(status_code=500, detail=f"Revoke failed: {str(e)}")
    
    @classmethod
    def _get_tool_instance(cls, tool_name: str, tool_info: Dict[str, Any]):
        """Get tool instance for OAuth operations"""
        try:
            # Dynamic import of the tool class
            module_path = f"app.private.tools.{tool_name}.main"
            module = __import__(module_path, fromlist=[tool_info['class_name']])
            tool_class = getattr(module, tool_info['class_name'])
            
            # Create instance with default profile
            return tool_class(profile="DEFAULT")
            
        except ImportError as e:
            raise ImportError(f"Could not import {tool_name} tool: {e}")
        except AttributeError as e:
            raise AttributeError(f"Tool class {tool_info['class_name']} not found in {tool_name}: {e}")
    
    @classmethod
    def get_oauth_tools_info(cls) -> Dict[str, Any]:
        """Get information about all OAuth tools"""
        oauth_tools = cls.discover_oauth_tools()
        
        return {
            "count": len(oauth_tools),
            "tools": {
                name: {
                    "display_name": info["display_name"],
                    "provider": info["config"].get("provider"),
                    "endpoints": {
                        "auth": f"/oauth/{name}/auth",
                        "callback": f"/oauth/{name}/callback", 
                        "status": f"/oauth/{name}/status",
                        "revoke": f"/oauth/{name}/revoke"
                    }
                }
                for name, info in oauth_tools.items()
            }
        }