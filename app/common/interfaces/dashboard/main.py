from fastapi import APIRouter, HTTPException
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

def get_router():
    """Retourne le router FastAPI pour cette interface"""
    return router

if __name__ == "__main__":
    # Test de génération du dashboard
    workflows = workflow_registry.get_workflow_summary()
    stats = workflow_engine.get_workflow_stats()
    
    print(f"Dashboard prêt avec {len(workflows)} workflows")
    print(f"Statistiques: {stats['total']} exécutions, {stats['success_rate']}% de succès")
