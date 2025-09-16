from typing import Dict, Any, List
from datetime import datetime
import asyncio
import time
from collections import defaultdict
from app.private.workflows.registry import workflow_registry
from app.common.database.crud import get_workflow_executions, get_logs
from app.common.database.models import LogModel

logs_buffer = defaultdict(list)
websocket_connections = defaultdict(list)

class WorkflowEngine:
    def __init__(self):
        pass
    
    def execute_workflow(self, workflow_name: str, data: Dict[str, Any] = None, trigger_type: str = "manual") -> Dict[str, Any]:
        return workflow_registry.execute_workflow(workflow_name, data)
    
    async def execute_workflow_async(self, workflow_name: str, data: Dict[str, Any] = None, trigger_type: str = "manual") -> Dict[str, Any]:
        return await asyncio.get_event_loop().run_in_executor(
            None, self.execute_workflow, workflow_name, data, trigger_type
        )
    
    def process_webhook(self, workflow_name: str, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        workflow = workflow_registry.get_workflow(workflow_name)
        if not workflow:
            return {"status": "error", "message": f"Workflow '{workflow_name}' not found"}
        
        triggers = workflow['config'].get('triggers', [])
        if 'webhook' not in triggers:
            return {"status": "error", "message": f"Workflow '{workflow_name}' doesn't support webhooks"}
        
        return self.execute_workflow(workflow_name, webhook_data, trigger_type="webhook")
    
    def get_execution_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        executions = get_workflow_executions(limit=limit)
        return [{
            "workflow_name": e.workflow_id,
            "trigger_type": e.trigger_type,
            "start_time": e.start_time.isoformat(),
            "end_time": e.end_time.isoformat() if e.end_time else None,
            "duration": e.duration,
            "status": e.status,
            "success": e.status == "success",
            "input_data": e.input_data,
            "result": e.result
        } for e in executions]
    
    def get_workflow_stats(self, workflow_name: str = None) -> Dict[str, Any]:
        executions = get_workflow_executions(workflow_name if workflow_name else None)
        
        if not executions:
            return {"total": 0, "success": 0, "error": 0, "success_rate": 0}
        
        total = len(executions)
        success = sum(1 for e in executions if e.status == "success")
        error = total - success
        success_rate = (success / total) * 100 if total > 0 else 0
        
        avg_duration = sum(e.duration for e in executions if e.duration) / total if total > 0 else 0
        
        return {
            "total": total,
            "success": success,
            "error": error,
            "success_rate": round(success_rate, 2),
            "average_duration": round(avg_duration, 2)
        }
    
    def validate_workflow_data(self, workflow_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Valide les données d'entrée pour un workflow"""
        
        workflow = workflow_registry.get_workflow(workflow_name)
        if not workflow:
            return {"valid": False, "error": f"Workflow '{workflow_name}' not found"}
        
        # Vérifie si le workflow a une fonction de validation
        if hasattr(workflow['module'], 'validate_data'):
            try:
                is_valid = workflow['module'].validate_data(data)
                return {"valid": is_valid, "error": None if is_valid else "Data validation failed"}
            except Exception as e:
                return {"valid": False, "error": f"Validation error: {str(e)}"}
        
        # Si pas de fonction de validation, considère comme valide
        return {"valid": True, "error": None}
    
    def reload_workflows(self):
        """Recharge tous les workflows (hot-reload)"""
        workflow_registry.reload_workflows()
        return {"status": "success", "message": "Workflows reloaded successfully"}

async def execute_workflow_with_logs(workflow_name: str, data: Dict[str, Any], execution_id: str):
    """Exécute workflow avec logging en temps réel"""
    
    def log_callback(level: str, message: str, context: Dict[str, Any] = None):
        """Callback pour logs streaming"""
        log_entry = {
            "timestamp": time.time(),
            "level": level,
            "message": message,
            "context": context or {},
            "execution_id": execution_id
        }
        
        logs_buffer[execution_id].append(log_entry)
        
        for websocket in websocket_connections[execution_id]:
            asyncio.create_task(websocket.send_json(log_entry))
    
    try:
        log_callback("INFO", f"Démarrage workflow {workflow_name}")
        
        result = workflow_registry.execute_workflow(workflow_name, data)
        
        log_callback("INFO", f"Workflow terminé avec succès", {"result": result})
        return result
        
    except Exception as e:
        log_callback("ERROR", f"Erreur workflow: {str(e)}")
        raise
    finally:
        asyncio.create_task(cleanup_logs(execution_id, delay=3600))

async def get_workflow_logs_stream(execution_id: str):
    """Stream des logs pour un execution_id"""
    for log_entry in logs_buffer[execution_id]:
        yield log_entry
    
    while execution_id in logs_buffer:
        await asyncio.sleep(0.1)
        new_logs = logs_buffer[execution_id]
        for log_entry in new_logs:
            yield log_entry

async def cleanup_logs(execution_id: str, delay: int = 3600):
    """Nettoyage des logs après délai"""
    await asyncio.sleep(delay)
    if execution_id in logs_buffer:
        del logs_buffer[execution_id]
    if execution_id in websocket_connections:
        del websocket_connections[execution_id]

# Instance globale du moteur
workflow_engine = WorkflowEngine()

if __name__ == "__main__":
    # Test du moteur
    engine = WorkflowEngine()
    
    print("Test d'exécution du workflow lead_nurturing:")
    result = engine.execute_workflow('lead_nurturing', {
        'name': 'Engine Test Lead',
        'email': 'engine.test@example.com',
        'priority': 'high'
    })
    
    print(f"Résultat: {result['status']} - {result['message']}")
    
    print("\nStatistiques:")
    stats = engine.get_workflow_stats()
    print(f"Total: {stats['total']}, Success: {stats['success']}, Success rate: {stats['success_rate']}%")