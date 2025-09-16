#!/usr/bin/env python3
# app/main.py

import uvicorn
import sys
import os
import subprocess
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Dict, Any
from contextlib import asynccontextmanager

from config.config import settings
from config.logger import logger
from config.get_version import get_version

def run_build_system():
    """Lance le système de build avant de démarrer le serveur"""
    logger.info("🏗️  Running build system...")
    try:
        result = subprocess.run(
            [sys.executable, "build.py"], 
            cwd="app",
            capture_output=True, 
            text=True
        )
        
        if result.returncode == 0:
            logger.info("✅ Build system completed successfully")
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    logger.info(f"Build: {line}")
        else:
            logger.error("❌ Build system failed:")
            if result.stderr:
                for line in result.stderr.strip().split('\n'):
                    logger.error(f"Build Error: {line}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Build system error: {e}")
        sys.exit(1)

from .private.workflows.registry import workflow_registry
from .common.engine import workflow_engine
from .private.interfaces.registry import interface_registry
from .common.services.scheduler import workflow_scheduler
from .common.services.oauth_service import OAuthService

def setup_interface_routes():
    """Configure automatiquement les routes des interfaces"""
    # Register OAuth routes first
    OAuthService.register_oauth_routes(app)
    
    # Then register interface routes
    for name, interface in interface_registry.get_all_interfaces().items():
        if hasattr(interface['module'], 'get_router'):
            try:
                router = interface['module'].get_router()
                app.include_router(router)
                logger.info(f"Interface '{name}' loaded at {interface['route']}")
            except Exception as e:
                logger.error(f"Failed to load interface '{name}': {e}")

# --- Événements startup/shutdown ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    run_build_system()  # Lance le build avant tout
    logger.info("🚀 Workflow Platform starting up")
    logger.info(f"Workflows loaded: {len(workflow_registry.get_all_workflows())}")
    logger.info(f"Interfaces loaded: {len(interface_registry.get_all_interfaces())}")
    setup_interface_routes()
    workflow_scheduler.start()
    logger.info("⏰ Workflow scheduler started")
    
    # Vérification des statuts OAuth au démarrage
    await check_oauth_status_on_startup()
    
    logger.info("✅ Platform ready")
    
    yield
    
    # Shutdown
    logger.info("🛑 Workflow Platform shutting down")
    workflow_scheduler.stop()

async def check_oauth_status_on_startup():
    """Vérifie l'état des comptes OAuth au démarrage"""
    try:
        oauth_tools = OAuthService.discover_oauth_tools()
        if oauth_tools:
            logger.info(f"🔐 Checking OAuth status for {len(oauth_tools)} tools")
            
            # Import ToolsService pour récupérer les profils
            from app.common.services.tool import ToolsService
            
            for tool_name, tool_info in oauth_tools.items():
                try:
                    # Récupérer le premier profil disponible pour cet outil
                    profiles = ToolsService.get_tool_profiles(tool_name)
                    if not profiles:
                        logger.warning(f"❌ {tool_name}: No profiles found")
                        continue
                        
                    first_profile = profiles[0].get('name', 'DEFAULT')
                    
                    if tool_info.get('unified_google'):
                        service = tool_info['google_service']
                        tool_instance = OAuthService._get_google_tool_instance(service, first_profile, tool_info)
                    else:
                        tool_instance = OAuthService._get_tool_instance(tool_name, tool_info, first_profile)
                    
                    status = tool_instance.get_oauth_status()
                    auth_status = "✅" if status.get('authenticated') else "❌"
                    logger.info(f"{auth_status} {tool_name} ({first_profile}): {'Connected' if status.get('authenticated') else 'Disconnected'}")
                except Exception as e:
                    logger.warning(f"❌ {tool_name}: Error checking status - {e}")
        else:
            logger.info("🔐 No OAuth tools found")
    except Exception as e:
        logger.error(f"❌ OAuth status check failed: {e}")

# --- Création de l'app ---
app = FastAPI(
    title="Workflow Automation Platform", 
    description="Plateforme d'automatisation avec workflows et interfaces modulaires",
    version="1.0.0",
    debug=settings.debug,
    lifespan=lifespan
)

# --- Modèles de données ---
class WorkflowExecutionRequest(BaseModel):
    data: Dict[str, Any] = {}

class WebhookRequest(BaseModel):
    workflow_name: str
    data: Dict[str, Any] = {}

# --- Route racine ---
@app.get("/")
def root():
    """Redirection vers le dashboard principal"""
    return RedirectResponse(url="/dashboard/")

# --- Endpoints de santé ---
@app.get("/health", tags=["health"])
def health_check():
    return {
        "status": "ok", 
        "app": "Workflow Platform",
        "workflows_loaded": len(workflow_registry.get_all_workflows()),
        "interfaces_loaded": len(interface_registry.get_all_interfaces())
    }

# --- API Workflows ---
@app.get("/api/workflows", tags=["workflows"])
def list_workflows():
    """Liste tous les workflows disponibles"""
    return workflow_registry.get_workflow_summary()

@app.get("/api/workflows/{workflow_name}", tags=["workflows"])
def get_workflow_info(workflow_name: str):
    """Récupère les informations d'un workflow spécifique"""
    workflow = workflow_registry.get_workflow(workflow_name)
    if not workflow:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_name}' not found")
    return {
        "name": workflow_name,
        "config": workflow['config'],
        "path": workflow['path']
    }

@app.post("/api/workflows/execute/{workflow_name}", tags=["workflows"])
def execute_workflow_endpoint(workflow_name: str, request: WorkflowExecutionRequest = None):
    """Exécute un workflow avec des données optionnelles"""
    data = request.data if request else {}
    result = workflow_engine.execute_workflow(workflow_name, data, trigger_type="api")
    return result

@app.get("/api/workflows/trigger/{workflow_name}", tags=["workflows"])
def trigger_workflow_manually(workflow_name: str, request: Request):
    """Déclenche manuellement un workflow avec les paramètres d'URL"""
    query_params = dict(request.query_params)
    result = workflow_engine.execute_workflow(workflow_name, query_params, trigger_type="manual")
    return result

@app.post("/api/workflows/toggle/{workflow_name}", tags=["workflows"])
def toggle_workflow_endpoint(workflow_name: str):
    """Active/désactive un workflow"""
    return workflow_registry.toggle_workflow(workflow_name)

@app.post("/api/webhooks/{workflow_name}", tags=["webhooks"])  
def process_webhook(workflow_name: str, request: Request, data: Dict[str, Any] = None):
    """Traite un webhook pour déclencher un workflow"""
    # Merge query parameters with JSON body data
    query_params = dict(request.query_params)
    webhook_data = {**(data or {}), **query_params}
    result = workflow_engine.process_webhook(workflow_name, webhook_data)
    return result

@app.get("/api/workflows/logs/{workflow_name}", tags=["workflows"])
def get_workflow_logs(workflow_name: str, limit: int = 20):
    """Récupère les logs d'exécution d'un workflow"""
    history = workflow_engine.get_execution_history(limit=100)
    workflow_logs = [log for log in history if log.get('workflow_name') == workflow_name]
    return workflow_logs[:limit]

@app.get("/api/workflows/stats", tags=["workflows"])
def get_workflows_stats():
    """Récupère les statistiques globales des workflows"""
    return workflow_engine.get_workflow_stats()

@app.get("/api/workflows/stats/{workflow_name}", tags=["workflows"])
def get_workflow_stats(workflow_name: str):
    """Récupère les statistiques d'un workflow spécifique"""
    return workflow_engine.get_workflow_stats(workflow_name)

@app.get("/api/scheduler/jobs", tags=["scheduler"])
def get_scheduled_jobs():
    """Liste tous les jobs programmés avec leurs statuts"""
    return workflow_scheduler.get_scheduled_jobs_info()

# --- API Interfaces ---
@app.get("/api/interfaces", tags=["interfaces"])
def list_interfaces():
    """Liste toutes les interfaces disponibles"""
    return interface_registry.get_interface_cards()

# --- API OAuth Status ---
@app.get("/api/oauth/status", tags=["oauth"])
def get_oauth_status():
    """Récupère l'état de tous les outils OAuth"""
    try:
        oauth_tools = OAuthService.discover_oauth_tools()
        status_data = {}
        
        for tool_name, tool_info in oauth_tools.items():
            try:
                if tool_info.get('unified_google'):
                    service = tool_info['google_service']
                    tool_instance = OAuthService._get_google_tool_instance(service, 'DEFAULT', tool_info)
                else:
                    tool_instance = OAuthService._get_tool_instance(tool_name, tool_info)
                
                status = tool_instance.get_oauth_status()
                
                # Génération des liens d'auth par profil dynamiques
                auth_links = {}
                from app.common.services.tool import ToolsService
                tool_profiles = ToolsService.get_tool_profiles(tool_name)
                profiles = [p.get('name') for p in tool_profiles if p.get('name')]
                if not profiles:
                    profiles = ['DEFAULT']  # Fallback seulement si aucun profil trouvé
                
                for profile in profiles:
                    if tool_info.get('unified_google'):
                        auth_links[profile] = f"/oauth/google/auth?service={service}&profile={profile}"
                    else:
                        auth_links[profile] = f"/oauth/{tool_name}/auth?profile={profile}"
                
                status_data[tool_name] = {
                    **status,
                    'display_name': tool_info.get('display_name', tool_name),
                    'service_type': tool_info.get('google_service') if tool_info.get('unified_google') else 'oauth',
                    'auth_links': auth_links
                }
                
            except Exception as e:
                status_data[tool_name] = {
                    'authenticated': False,
                    'error': str(e),
                    'display_name': tool_info.get('display_name', tool_name),
                    'service_type': tool_info.get('google_service') if tool_info.get('unified_google') else 'oauth',
                    'auth_links': {}
                }
        
        return {
            'tools': status_data,
            'total_tools': len(oauth_tools),
            'connected_tools': len([t for t in status_data.values() if t.get('authenticated')])
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get OAuth status: {str(e)}")

@app.get("/api/oauth/status/{tool_name}", tags=["oauth"])
def get_tool_oauth_status(tool_name: str, profile: str = "DEFAULT"):
    """Récupère l'état OAuth d'un outil spécifique"""
    try:
        oauth_tools = OAuthService.discover_oauth_tools()
        
        if tool_name not in oauth_tools:
            raise HTTPException(status_code=404, detail=f"OAuth tool '{tool_name}' not found")
        
        tool_info = oauth_tools[tool_name]
        
        if tool_info.get('unified_google'):
            service = tool_info['google_service']
            tool_instance = OAuthService._get_google_tool_instance(service, profile, tool_info)
        else:
            tool_instance = OAuthService._get_tool_instance(tool_name, tool_info, profile)
        
        return tool_instance.get_oauth_status()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status for {tool_name}: {str(e)}")

# --- Hot Reload ---
@app.post("/api/reload", tags=["admin"])
def reload_system():
    """Recharge tous les workflows et interfaces (hot-reload)"""
    try:
        workflow_registry.reload_workflows()
        interface_registry.reload_interfaces()
        workflow_scheduler.reload_schedules()
        return {
            "status": "success",
            "message": "System reloaded successfully",
            "workflows_loaded": len(workflow_registry.get_all_workflows()),
            "interfaces_loaded": len(interface_registry.get_all_interfaces())
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Reload failed: {str(e)}"
        }

# --- Lancement en mode script ---
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )