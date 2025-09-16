from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
import asyncio
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, Any
import os

from app.private.workflows.registry import workflow_registry
from app.common.engine import workflow_engine
from app.common.services.tool import ToolsService

DISPLAY_NAME = "Dashboard Principal"
DESCRIPTION = "Interface centrale pour gérer tous les workflows"
ROUTE = "/dashboard"
ICON = "🏠"

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/")
def get_dashboard():
    """Sert le fichier HTML du dashboard"""
    return FileResponse(os.path.join(os.path.dirname(__file__), "src", "index.html"))

@router.get("/style.css")
def get_css():
    """Sert le fichier CSS"""
    return FileResponse(os.path.join(os.path.dirname(__file__), "src", "style.css"), media_type="text/css")

@router.get("/script.js")
def get_js():
    """Sert le fichier JavaScript"""
    return FileResponse(os.path.join(os.path.dirname(__file__), "src", "script.js"), media_type="application/javascript")

@router.get("/api/stats")
def get_dashboard_stats():
    """API pour récupérer les statistiques du dashboard"""
    from app.private.interfaces.registry import interface_registry
    return {
        "workflows": workflow_registry.get_workflow_summary(),
        "interfaces": interface_registry.get_interface_cards(),
        "tools": ToolsService.get_available_tools(),
        "stats": workflow_engine.get_workflow_stats(),
        "history": workflow_engine.get_execution_history(limit=10)
    }

@router.get("/api/env")
def get_env_variables():
    """API pour récupérer les variables d'environnement depuis config/.env"""
    env_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "config", ".env")
    if not os.path.exists(env_path):
        raise HTTPException(status_code=404, detail="config/.env not found")
    try:
        from dotenv import dotenv_values
        env_vars = dotenv_values(env_path)
        return {"variables": env_vars, "count": len(env_vars), "path": env_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading config/.env: {str(e)}")

@router.post("/api/workflows/{workflow_name}/toggle")
def toggle_workflow(workflow_name: str):
    """Active/désactive un workflow"""
    return workflow_registry.toggle_workflow(workflow_name)

@router.get("/api/workflows/{workflow_name}/logs")
def get_workflow_logs(workflow_name: str, limit: int = 50):
    """Récupère les logs d'un workflow"""
    return {
        "logs": workflow_registry.get_workflow_logs(workflow_name, limit),
        "workflow_name": workflow_name
    }

class ProfileData(BaseModel):
    config: Dict[str, str]

@router.get("/api/tools")
def get_tools():
    """Récupère la liste des outils disponibles"""
    return ToolsService.get_available_tools()

@router.get("/api/tools/{tool_name}/profiles")
def get_tool_profiles(tool_name: str):
    """Récupère les profils d'un outil depuis .env et database"""
    profiles = ToolsService.get_tool_profiles(tool_name)
    return {
        "tool_name": tool_name,
        "profiles": profiles,
        "count": len(profiles),
        "sources": {
            "env_files": len([p for p in profiles if p.get("source") == "env_file"]),
            "database": len([p for p in profiles if p.get("source") == "database"])
        }
    }

@router.get("/api/tools/{tool_name}/config-schema")
def get_tool_config_schema(tool_name: str):
    """Récupère le schéma de configuration d'un outil"""
    return ToolsService.get_tool_config_schema(tool_name)

@router.get("/api/workflows/{workflow_name}/config")
def get_workflow_config(workflow_name: str):
    """Récupère la configuration complète d'un workflow avec ses outils"""
    return workflow_registry.get_workflow_config_with_tools(workflow_name)

class WorkflowToolProfileUpdate(BaseModel):
    tool_profiles: Dict[str, str]

@router.put("/api/workflows/{workflow_name}/tool-profiles")
def update_workflow_tool_profiles(workflow_name: str, update_data: WorkflowToolProfileUpdate):
    """Met à jour les profils d'outils d'un workflow"""
    from app.common.database.crud import list_workflows, update_workflow
    
    db_workflow = next((w for w in list_workflows(active_only=False) if w.name == workflow_name), None)
    if not db_workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    success = update_workflow(db_workflow.id, {"tool_profiles": update_data.tool_profiles})
    if success:
        # Recharger les workflows pour prendre en compte les changements
        workflow_registry.reload_workflows()
        return {"status": "success", "message": "Tool profiles updated"}
    else:
        raise HTTPException(status_code=500, detail="Failed to update tool profiles")

class CreateProfileData(BaseModel):
    config: Dict[str, str]
    save_to_env: bool = True  # Par défaut, sauvegarder dans .env

@router.post("/api/tools/{tool_name}/profiles/{profile_name}")
def create_profile(tool_name: str, profile_name: str, data: CreateProfileData):
    """Crée un nouveau profil"""
    if ToolsService.create_profile(tool_name, profile_name, data.config, data.save_to_env):
        save_type = "env file" if data.save_to_env else "database"
        return {"status": "success", "message": f"Profile {profile_name} created in {save_type}"}
    raise HTTPException(status_code=400, detail="Failed to create profile")

class FreeConfigData(BaseModel):
    config: Dict[str, str]
    
@router.post("/api/tools/{tool_name}/free-mode/validate")
def validate_free_config(tool_name: str, data: FreeConfigData):
    """Valide une configuration en mode libre"""
    try:
        from app.private.tools import registry
        tool_class = registry.get_tool_class(tool_name)
        tool_instance = tool_class(free_mode=True)
        tool_instance.set_free_config(data.config)
        
        is_valid = tool_instance.validate_config(data.config)
        schema = tool_instance.get_config_schema()
        
        missing_required = []
        for param in schema.get('required_params', []):
            if param not in data.config or not data.config[param]:
                missing_required.append(param)
        
        return {
            "valid": is_valid,
            "missing_required": missing_required,
            "schema": schema
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")

@router.put("/api/tools/{tool_name}/profiles/{profile_name}")
def update_profile(tool_name: str, profile_name: str, data: ProfileData):
    """Met à jour un profil"""
    if ToolsService.update_profile(tool_name, profile_name, data.config):
        return {"status": "success", "message": f"Profile {profile_name} updated"}
    raise HTTPException(status_code=400, detail="Failed to update profile")

@router.delete("/api/tools/{tool_name}/profiles/{profile_name}")
def delete_profile(tool_name: str, profile_name: str):
    """Supprime un profil"""
    if ToolsService.delete_profile(tool_name, profile_name):
        return {"status": "success", "message": f"Profile {profile_name} deleted"}
    raise HTTPException(status_code=400, detail="Failed to delete profile")

@router.post("/api/tools/{tool_name}/toggle")
def toggle_tool(tool_name: str):
    """Active/désactive un outil"""
    return ToolsService.toggle_tool(tool_name)

@router.get("/api/tools/{tool_name}/logo")
def get_tool_logo(tool_name: str):
    """Sert le logo d'un outil"""
    logo_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "private", "tools", tool_name, "logo.png")
    if os.path.exists(logo_path):
        return FileResponse(logo_path, media_type="image/png")
    raise HTTPException(status_code=404, detail="Logo not found")

@router.get("/api/profiles/all")
def get_all_profiles_with_status():
    """Récupère tous les profils de tous les outils avec leur statut OAuth"""
    try:
        from app.common.services.oauth_service import OAuthService
        
        # Récupérer tous les outils OAuth
        oauth_tools = OAuthService.discover_oauth_tools()
        
        # Récupérer tous les outils depuis ToolsService
        all_tools = ToolsService.get_available_tools()
        
        profiles_by_tool = {}
        oauth_status_by_profile = {}
        
        for tool in all_tools:
            tool_name = tool['name']
            profiles = tool.get('profiles', [])
            
            if profiles:
                profiles_by_tool[tool_name] = []
                
                for profile in profiles:
                    profile_name = profile.get('name')
                    if not profile_name:
                        continue
                        
                    profile_data = {
                        "name": profile_name,
                        "source": profile.get('source', 'unknown'),
                        "has_oauth": tool_name in oauth_tools,
                        "oauth_status": None
                    }
                    
                    # Marquer si l'outil supporte OAuth (sans vérifier le statut pour éviter les lenteurs)
                    if tool_name in oauth_tools:
                        profile_data['oauth_status'] = {
                            "authenticated": None,  # Non vérifié ici pour éviter les lenteurs
                            "provider": "google" if tool_name.startswith('google_') else "unknown",
                            "check_required": True
                        }
                    
                    profiles_by_tool[tool_name].append(profile_data)
        
        return {
            "profiles_by_tool": profiles_by_tool,
            "oauth_tools": list(oauth_tools.keys())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get all profiles: {str(e)}")

@router.get("/api/oauth/status/{tool_name}/{profile_name}")
def check_tool_profile_oauth_status(tool_name: str, profile_name: str):
    """Vérifie le statut OAuth d'un profil spécifique pour un outil donné"""
    try:
        from app.common.services.oauth_service import OAuthService
        
        oauth_tools = OAuthService.discover_oauth_tools()
        
        if tool_name not in oauth_tools:
            return {"error": f"Tool {tool_name} does not support OAuth", "authenticated": False}
        
        if tool_name.startswith('google_'):
            # Vérification directe sans requête HTTP
            service = tool_name.replace('google_', '')
            try:
                from app.private.tools.oauth import GoogleOAuthTool
                google_tool = GoogleOAuthTool(service=service, profile=profile_name)
                status = google_tool.get_oauth_status()
                return {
                    "authenticated": status.get('authenticated', False),
                    "provider": "google",
                    "service": service,
                    "profile": profile_name,
                    "tool": tool_name,
                    "auth_url": f"/oauth/google/auth?service={service}&profile={profile_name}",
                    "scopes": status.get('scopes', [])
                }
            except Exception as e:
                return {
                    "error": str(e), 
                    "authenticated": False, 
                    "tool": tool_name, 
                    "profile": profile_name,
                    "service": service
                }
        else:
            # Autres outils OAuth
            import requests
            import os
            host = os.getenv('HOST', 'localhost')
            port = os.getenv('PORT', '10000')
            base_url = f"http://{host}:{port}"
            response = requests.get(f"{base_url}/oauth/{tool_name}/status?profile={profile_name}", timeout=5)
            if response.status_code == 200:
                status_data = response.json()
                status_data.update({
                    "profile": profile_name,
                    "tool": tool_name
                })
                return status_data
            else:
                return {"error": f"Failed to check OAuth status: {response.status_code}", "authenticated": False}
                
    except Exception as e:
        return {"error": str(e), "authenticated": False, "tool": tool_name, "profile": profile_name}

@router.get("/api/google/profiles")
def get_google_profiles():
    """Récupère tous les profils disponibles pour les outils Google"""
    try:
        from app.common.services.oauth_service import OAuthService
        
        oauth_tools = OAuthService.discover_oauth_tools()
        google_tools = {name: info for name, info in oauth_tools.items() if info.get('unified_google')}
        
        all_profiles = set()
        for tool_name in google_tools.keys():
            try:
                profiles = ToolsService.get_tool_profiles(tool_name)
                for p in profiles:
                    if p.get('name'):
                        all_profiles.add(p.get('name'))
            except Exception:
                continue
        
        return {
            "profiles": sorted(list(all_profiles)),
            "count": len(all_profiles),
            "google_tools": list(google_tools.keys())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Google profiles: {str(e)}")

@router.get("/api/workflows/{workflow_name}/inputs")
async def get_workflow_inputs(workflow_name: str):
    """Récupère les inputs requis pour un workflow"""
    try:
        workflow_data = workflow_registry.get_workflow(workflow_name)
        if workflow_data and 'module' in workflow_data:
            workflow_module = workflow_data['module']
            if hasattr(workflow_module, 'get_required_inputs'):
                inputs = workflow_module.get_required_inputs()
                return {"inputs": inputs}
        return {"inputs": []}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/api/workflows/{workflow_name}/execute-stream")
async def execute_workflow_stream(workflow_name: str, inputs: Dict[str, Any]):
    """Exécute workflow avec inputs manuels et streaming logs"""
    import time
    import asyncio
    
    try:
        execution_id = f"{workflow_name}_{int(time.time())}"
        
        from app.common.engine import execute_workflow_with_logs
        
        asyncio.create_task(
            execute_workflow_with_logs(workflow_name, inputs, execution_id)
        )
        
        return {"execution_id": execution_id, "status": "started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/ws/workflows/{workflow_name}/logs/{execution_id}")
async def workflow_logs_websocket(websocket: WebSocket, workflow_name: str, execution_id: str):
    """WebSocket pour logs temps réel"""
    await websocket.accept()
    
    try:
        from app.common.engine import logs_buffer, websocket_connections
        
        # Ajouter à la liste des connexions
        if execution_id not in websocket_connections:
            websocket_connections[execution_id] = []
        websocket_connections[execution_id].append(websocket)
        
        # Envoyer les logs existants
        if execution_id in logs_buffer:
            for log_entry in logs_buffer[execution_id]:
                await websocket.send_json(log_entry)
        
        # Écouter pour nouveaux logs
        while True:
            try:
                await asyncio.sleep(0.5)  # Polling toutes les 500ms
                if execution_id in logs_buffer:
                    # Vérifier nouveaux logs (simple pour cette implémentation)
                    await websocket.ping()
            except Exception:
                break
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass
    finally:
        # Nettoyer la connexion
        from app.common.engine import websocket_connections
        if execution_id in websocket_connections and websocket in websocket_connections[execution_id]:
            websocket_connections[execution_id].remove(websocket)
        try:
            await websocket.close()
        except:
            pass

@router.get("/api/oauth/google/status")
def check_google_oauth_status(profile: str = "DEFAULT"):
    """Vérifie l'état des comptes Google OAuth pour les services détectés"""
    try:
        from app.common.services.oauth_service import OAuthService
        import requests
        import os
        from dotenv import load_dotenv
        
        # Charger la configuration depuis .env
        env_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..", "config", ".env")
        if os.path.exists(env_path):
            load_dotenv(env_path)
        
        host = os.getenv('HOST', 'localhost')
        port = os.getenv('PORT', '10000')
        base_url = f"http://{host}:{port}"
        
        oauth_tools = OAuthService.discover_oauth_tools()
        google_tools = {name: info for name, info in oauth_tools.items() if info.get('unified_google')}
        
        if not google_tools:
            return {"error": "No Google services detected", "services": []}
        
        # Récupérer les profils disponibles de manière dynamique
        available_profiles = []
        for tool_name in google_tools.keys():
            try:
                profiles = ToolsService.get_tool_profiles(tool_name)
                for p in profiles:
                    if p.get('name') not in available_profiles:
                        available_profiles.append(p.get('name'))
            except:
                continue
        
        # Si le profil demandé n'existe pas, utiliser le premier disponible
        if not available_profiles:
            available_profiles = ['DEFAULT']
        
        if profile not in available_profiles:
            profile = available_profiles[0]
        
        # Effectuer la requête vers l'endpoint OAuth
        try:
            import urllib.parse
            url = f"{base_url}/oauth/google/status?profile={urllib.parse.quote(profile)}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "success",
                    "profile": profile,
                    "available_profiles": available_profiles,
                    "google_services": data.get('google_services', {}),
                    "detected_services": list(google_tools.keys())
                }
            else:
                return {
                    "status": "error", 
                    "message": f"OAuth service returned {response.status_code}",
                    "profile": profile,
                    "available_profiles": available_profiles,
                    "detected_services": list(google_tools.keys())
                }
        except requests.RequestException as e:
            return {
                "status": "error",
                "message": f"Cannot reach OAuth service: {str(e)}",
                "profile": profile,
                "available_profiles": available_profiles,
                "detected_services": list(google_tools.keys())
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check Google OAuth status: {str(e)}")

def get_router():
    """Retourne le router FastAPI pour cette interface"""
    return router

if __name__ == "__main__":
    # Test de génération du dashboard
    workflows = workflow_registry.get_workflow_summary()
    stats = workflow_engine.get_workflow_stats()
    
    print(f"Dashboard prêt avec {len(workflows)} workflows")
    print(f"Statistiques: {stats['total']} exécutions, {stats['success_rate']}% de succès")
