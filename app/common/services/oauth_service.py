import os
import json
import glob
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from config.logger import logger

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
                    # Check if this is a Google service tool
                    if cls._is_google_tool(tool_name):
                        service_name = cls._get_google_service_name(tool_name)
                        oauth_tools[tool_name] = {
                            'config': oauth_config,
                            'display_name': config.get('display_name', tool_name),
                            'tool_path': tool_dir,
                            'class_name': 'GoogleOAuthTool',  # Use unified Google OAuth class
                            'google_service': service_name,   # calendar, drive, etc.
                            'unified_google': True            # Flag for special handling
                        }
                        logger.debug(f"Discovered Google OAuth tool: {tool_name} (service: {service_name})")
                    else:
                        # Regular OAuth tool
                        tool_class_name = cls._discover_tool_class(tool_dir, tool_name)
                        if tool_class_name:
                            oauth_tools[tool_name] = {
                                'config': oauth_config,
                                'display_name': config.get('display_name', tool_name),
                                'tool_path': tool_dir,
                                'class_name': tool_class_name
                            }
                            logger.debug(f"Discovered OAuth tool: {tool_name} with class {tool_class_name}")
                        else:
                            logger.warning(f"Could not find Tool class in {tool_name}")
                    
            except Exception as e:
                logger.warning(f"Failed to load OAuth config for {tool_name}: {e}")
        
        return oauth_tools
    
    @classmethod
    def _is_google_tool(cls, tool_name: str) -> bool:
        """Check if tool follows google_* pattern"""
        return tool_name.startswith('google_')
    
    @classmethod
    def _get_google_service_name(cls, tool_name: str) -> str:
        """Extract service name from google_service pattern"""
        return tool_name.replace('google_', '')
    
    @classmethod
    def _discover_tool_class(cls, tool_dir: str, tool_name: str) -> str:
        """Dynamically discover the actual Tool class name in main.py"""
        main_file = os.path.join(tool_dir, "main.py")
        if not os.path.exists(main_file):
            return None
        
        try:
            with open(main_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for class definitions that inherit from BaseOAuthTool
            import re
            pattern = r'class\s+(\w*Tool)\s*\([^)]*BaseOAuthTool[^)]*\)'
            matches = re.findall(pattern, content)
            
            if matches:
                return matches[0]  # Return first matching class
            
            # Fallback: look for any class ending with 'Tool'
            pattern = r'class\s+(\w*Tool)\s*\('
            matches = re.findall(pattern, content)
            
            if matches:
                return matches[0]
                
        except Exception as e:
            logger.warning(f"Error parsing {main_file}: {e}")
        
        return None
    
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
        
        # Register unified Google routes if Google tools are present
        google_tools = {name: info for name, info in oauth_tools.items() if info.get('unified_google')}
        if google_tools:
            cls._register_google_unified_routes(oauth_router, google_tools)
        
        # Include the OAuth router in the main app
        app.include_router(oauth_router)
        
        logger.info(f"Registered OAuth routes for {len(oauth_tools)} tools: {list(oauth_tools.keys())}")
    
    @classmethod
    def _register_google_unified_routes(cls, router: APIRouter, google_tools: Dict[str, Dict[str, Any]]) -> None:
        """Register unified Google OAuth routes"""
        
        @router.get("/google/auth")
        async def google_auth_endpoint(request: Request):
            """Unified Google OAuth initiation"""
            try:
                service = request.query_params.get('service')
                profile = request.query_params.get('profile', 'DEFAULT')
                
                if not service:
                    raise HTTPException(status_code=400, detail="Service parameter required")
                
                # Find the Google tool for this service
                google_tool_name = f"google_{service}"
                if google_tool_name not in google_tools:
                    raise HTTPException(status_code=404, detail=f"Google service '{service}' not found")
                
                tool_info = google_tools[google_tool_name]
                tool_instance = cls._get_google_tool_instance(service, profile, tool_info)
                auth_url = tool_instance.get_auth_url()
                return RedirectResponse(url=auth_url)
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Google OAuth auth error: {e}")
                raise HTTPException(status_code=500, detail=f"Google authentication failed: {str(e)}")
        
        @router.get("/google/callback") 
        async def google_callback_endpoint(request: Request):
            """Unified Google OAuth callback"""
            try:
                # Extract service and profile from OAuth state
                state = request.query_params.get('state')
                if not state:
                    raise HTTPException(status_code=400, detail="Missing state parameter")
                
                # Create a temporary GoogleOAuthTool to validate state and extract service info
                from app.private.tools.oauth import GoogleOAuthTool
                temp_tool = GoogleOAuthTool('calendar')  # Temporary service for validation
                
                if not temp_tool._validate_oauth_state(state):
                    raise HTTPException(status_code=400, detail="Invalid or expired state")
                
                # Extract service and profile from stored state
                import json, os
                state_file = os.path.join(temp_tool.base_dir, ".oauth_state_google")
                with open(state_file, 'r') as f:
                    stored_data = json.load(f)
                
                state_entry = None
                for entry in stored_data.get('entries', []):
                    if entry.get('state') == state:
                        state_entry = entry
                        break
                
                if not state_entry:
                    raise HTTPException(status_code=400, detail="State not found")
                
                service = state_entry.get('service')
                profile = state_entry.get('profile', 'DEFAULT')
                
                # Get the correct tool info
                google_tool_name = f"google_{service}"
                if google_tool_name not in google_tools:
                    raise HTTPException(status_code=404, detail=f"Service '{service}' not found")
                
                tool_info = google_tools[google_tool_name]
                tool_instance = cls._get_google_tool_instance(service, profile, tool_info)
                
                # Handle the callback
                success = tool_instance.handle_oauth_callback(str(request.url), state)
                
                if success:
                    return {
                        "status": "success",
                        "message": f"Google {service.title()} authentication successful",
                        "service": service,
                        "profile": profile
                    }
                else:
                    raise HTTPException(status_code=400, detail="Authentication failed")
                    
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Google OAuth callback error: {e}")
                raise HTTPException(status_code=500, detail=f"Callback processing failed: {str(e)}")
        
        @router.get("/google/status")
        async def google_status_endpoint(request: Request):
            """Get Google OAuth status for all services or specific service"""
            try:
                service = request.query_params.get('service')
                profile = request.query_params.get('profile', 'DEFAULT')
                
                if service:
                    # Status for specific service
                    google_tool_name = f"google_{service}"
                    if google_tool_name not in google_tools:
                        raise HTTPException(status_code=404, detail=f"Service '{service}' not found")
                    
                    tool_info = google_tools[google_tool_name]
                    tool_instance = cls._get_google_tool_instance(service, profile, tool_info)
                    return tool_instance.get_oauth_status()
                else:
                    # Status for all Google services
                    services_status = {}
                    for tool_name, tool_info in google_tools.items():
                        service_name = tool_info['google_service']
                        try:
                            tool_instance = cls._get_google_tool_instance(service_name, profile, tool_info)
                            services_status[service_name] = tool_instance.get_oauth_status()
                        except Exception as e:
                            services_status[service_name] = {"error": str(e), "authenticated": False}
                    
                    return {
                        "google_services": services_status,
                        "profile": profile
                    }
                    
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Google OAuth status error: {e}")
                raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")
        
        logger.info(f"Registered unified Google OAuth routes for {len(google_tools)} services")
    
    @classmethod
    def _register_tool_routes(cls, router: APIRouter, tool_name: str, tool_info: Dict[str, Any]) -> None:
        """Register OAuth routes for a specific tool"""
        
        @router.get(f"/{tool_name}/auth")
        async def auth_endpoint(request: Request):
            """Initiate OAuth authentication"""
            try:
                # Optional profile selection via query param
                requested_profile = request.query_params.get('profile')
                tool_instance = cls._get_tool_instance(tool_name, tool_info, requested_profile)
                auth_url = tool_instance.get_auth_url()
                return RedirectResponse(url=auth_url)
            except Exception as e:
                logger.error(f"OAuth auth error for {tool_name}: {e}")
                raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")
        
        @router.get(f"/{tool_name}/callback")
        async def callback_endpoint(request: Request):
            """Handle OAuth callback"""
            try:
                requested_profile = request.query_params.get('profile')
                tool_instance = cls._get_tool_instance(tool_name, tool_info, requested_profile)
                
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
        async def status_endpoint(request: Request):
            """Get OAuth authentication status"""
            try:
                requested_profile = request.query_params.get('profile')
                tool_instance = cls._get_tool_instance(tool_name, tool_info, requested_profile)
                return tool_instance.get_oauth_status()
            except Exception as e:
                logger.error(f"OAuth status error for {tool_name}: {e}")
                raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")
        
        @router.post(f"/{tool_name}/revoke")
        async def revoke_endpoint(request: Request):
            """Revoke OAuth authentication"""
            try:
                requested_profile = request.query_params.get('profile')
                tool_instance = cls._get_tool_instance(tool_name, tool_info, requested_profile)
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
    def _get_google_tool_instance(cls, service: str, profile: str, tool_info: Dict[str, Any]):
        """Get GoogleOAuthTool instance for specific service"""
        from app.private.tools.oauth import GoogleOAuthTool
        return GoogleOAuthTool(service=service, profile=profile, config=tool_info.get('config', {}))
    
    @classmethod 
    def _get_tool_instance(cls, tool_name: str, tool_info: Dict[str, Any], requested_profile: str = None):
        """Get tool instance for OAuth operations, picking the proper profile"""
        try:
            # Check if this is a unified Google tool
            if tool_info.get('unified_google'):
                service = tool_info['google_service']
                profile = requested_profile or 'DEFAULT'
                return cls._get_google_tool_instance(service, profile, tool_info)
            
            # Regular tool handling
            # Dynamic import of the tool class
            module_path = f"app.private.tools.{tool_name}.main"
            module = __import__(module_path, fromlist=[tool_info['class_name']])
            tool_class = getattr(module, tool_info['class_name'])
            
            # Determine best profile
            profile = requested_profile
            if not profile:
                # Try discover profiles via ToolsService
                try:
                    from app.common.services.tool import ToolsService
                    profiles = ToolsService.get_tool_profiles(tool_name)
                    profile_names = [p.get('name') for p in profiles if p.get('name')]
                    if 'DEFAULT' in profile_names:
                        profile = 'DEFAULT'
                    elif 'TEST' in profile_names:
                        profile = 'TEST'
                    elif profile_names:
                        profile = profile_names[0]
                except Exception:
                    profile = 'DEFAULT'
            
            return tool_class(profile=profile or 'DEFAULT')
            
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
