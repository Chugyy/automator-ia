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
    logger.info("✅ Platform ready")
    
    yield
    
    # Shutdown
    logger.info("🛑 Workflow Platform shutting down")
    workflow_scheduler.stop()

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
    return RedirectResponse(url="/dashboard")

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