import os
import json
import importlib.util
from typing import Dict, List, Any
from pathlib import Path
from datetime import datetime
from app.common.database.crud import *
from app.common.database.models import WorkflowModel, WorkflowExecutionModel, LogModel

class WorkflowRegistry:
    def __init__(self):
        self.workflows_dir = Path(__file__).parent
        self._workflows = {}
        self._load_workflows()
    
    def _load_workflows(self):
        """Synchronise workflows filesystem -> base de données"""
        self._workflows = {}
        filesystem_workflows = set()
        
        # 1. Charger les workflows depuis le filesystem
        for item in self.workflows_dir.iterdir():
            if item.is_dir() and item.name not in ['__pycache__', '.git']:
                config_file = item / 'config.json'
                main_file = item / 'main.py'
                
                if config_file.exists() and main_file.exists():
                    try:
                        with open(config_file, 'r', encoding='utf-8') as f:
                            config = json.load(f)
                        
                        spec = importlib.util.spec_from_file_location(
                            f"workflows.{item.name}.main", main_file)
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        
                        self._workflows[item.name] = {
                            'config': config,
                            'module': module,
                            'path': str(item)
                        }
                        
                        filesystem_workflows.add(item.name)
                        
                        # Sync to database
                        self._sync_workflow_to_db(item.name, config, str(main_file))
                        
                    except Exception as e:
                        print(f"Erreur lors du chargement de {item.name}: {e}")
        
        # 2. Désactiver les workflows orphelins (présents en DB mais absents du filesystem)
        existing_workflows = list_workflows(active_only=False)
        for workflow in existing_workflows:
            if workflow.name not in filesystem_workflows:
                try:
                    # Désactiver le workflow orphelin (plus sûr que la suppression complète)
                    update_workflow(workflow.id, {"active": False})
                    print(f"🗑️ Workflow orphelin {workflow.name} désactivé (dossier supprimé)")
                except Exception as e:
                    print(f"❌ Erreur lors de la désactivation du workflow {workflow.name}: {e}")
    
    def _sync_workflow_to_db(self, name: str, config: Dict[str, Any], file_path: str):
        """Synchronise un workflow vers la base de données"""
        existing_workflows = {w.name: w for w in list_workflows(active_only=False)}
        
        if name not in existing_workflows:
            workflow = WorkflowModel(
                name=name,
                display_name=config.get('name'),
                description=config.get('description'),
                category=config.get('category'),
                schedule=config.get('schedule'),
                triggers=config.get('triggers', []),
                tools_required=config.get('tools_required', []),
                tool_profiles=config.get('tool_profiles', {}),
                author=config.get('author'),
                version=config.get('version', '1.0.0'),
                active=config.get('active', True),
                file_path=file_path
            )
            create_workflow(workflow)
        else:
            # Update existing workflow if needed (but preserve active status)
            workflow = existing_workflows[name]
            updates = {}
            if workflow.display_name != config.get('name'):
                updates['display_name'] = config.get('name')
            if workflow.description != config.get('description'):
                updates['description'] = config.get('description')
            if workflow.category != config.get('category'):
                updates['category'] = config.get('category')
            if workflow.schedule != config.get('schedule'):
                updates['schedule'] = config.get('schedule')
            if workflow.triggers != config.get('triggers', []):
                updates['triggers'] = config.get('triggers', [])
            if workflow.tools_required != config.get('tools_required', []):
                updates['tools_required'] = config.get('tools_required', [])
            if workflow.tool_profiles != config.get('tool_profiles', {}):
                updates['tool_profiles'] = config.get('tool_profiles', {})
            if workflow.author != config.get('author'):
                updates['author'] = config.get('author')
            if workflow.version != config.get('version', '1.0.0'):
                updates['version'] = config.get('version', '1.0.0')
            
            if updates:
                update_workflow(workflow.id, updates)
    
    def get_all_workflows(self) -> Dict[str, Dict[str, Any]]:
        return self._workflows
    
    def get_workflow(self, name: str) -> Dict[str, Any]:
        return self._workflows.get(name)
    
    def get_workflow_module(self, name: str):
        """Retourne le module d'un workflow"""
        workflow_data = self._workflows.get(name)
        if workflow_data:
            return workflow_data['module']
        raise Exception(f"Workflow '{name}' not found")
    
    def get_tool_instances(self, workflow_name: str) -> Dict[str, Any]:
        """Retourne les instances d'outils avec les profils configurés"""
        db_workflow = next((w for w in list_workflows() if w.name == workflow_name), None)
        if not db_workflow:
            return {}
        
        instances = {}
        
        # Pour les workflows qui gèrent leurs propres outils (comme random_text_generator)
        # on ne fournit aucune instance - ils utilisent leurs implémentations internes
        if workflow_name == "random_text_generator":
            return {}
            
        # Pour les autres workflows, on peut essayer d'importer les outils
        try:
            tool_classes = {}
            
            if 'slack' in db_workflow.tools_required:
                from ..tools.slack.main import SlackTool
                tool_classes['slack'] = SlackTool
                
            if 'notion' in db_workflow.tools_required:
                from ..tools.notion.main import NotionTool
                tool_classes['notion'] = NotionTool
            
            if 'calendar' in db_workflow.tools_required:
                from ..tools.calendar.main import CalendarTool
                tool_classes['calendar'] = CalendarTool
            
            if 'date' in db_workflow.tools_required:
                from ..tools.date.main import DateTool
                tool_classes['date'] = DateTool
            
            for tool_name in db_workflow.tools_required:
                if tool_name in tool_classes:
                    profile = db_workflow.tool_profiles.get(tool_name, "DEFAULT")
                    instances[tool_name] = tool_classes[tool_name](profile=profile)
                    
        except ImportError as e:
            print(f"Warning: Could not import tools for {workflow_name}: {e}")
        
        return instances
    
    def get_workflow_config_with_tools(self, name: str) -> Dict[str, Any]:
        """Retourne la configuration du workflow avec les infos des outils disponibles"""
        from ...common.services.tool import ToolsService
        
        workflow = self.get_workflow(name)
        db_workflow = next((w for w in list_workflows() if w.name == name), None)
        
        if not workflow or not db_workflow:
            return {}
        
        available_tools = ToolsService.get_available_tools()
        tools_map = {tool['name']: tool for tool in available_tools}
        
        workflow_tools = []
        for tool_name in db_workflow.tools_required:
            if tool_name in tools_map:
                tool_info = tools_map[tool_name].copy()
                tool_info['selected_profile'] = db_workflow.tool_profiles.get(tool_name, "DEFAULT")
                workflow_tools.append(tool_info)
        
        return {
            'workflow': {
                'id': db_workflow.id,
                'name': db_workflow.name,
                'display_name': db_workflow.display_name,
                'description': db_workflow.description,
                'tools_required': db_workflow.tools_required,
                'tool_profiles': db_workflow.tool_profiles
            },
            'tools': workflow_tools
        }

    def execute_workflow(self, name: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        workflow = self.get_workflow(name)
        db_workflow = next((w for w in list_workflows() if w.name == name), None)
        
        if not workflow or not db_workflow or not db_workflow.active:
            return {"status": "error", "message": f"Workflow '{name}' not found or inactive"}
        
        try:
            execution = WorkflowExecutionModel(
                workflow_id=db_workflow.id,
                trigger_type="manual",
                input_data=data or {}
            )
            execution_id = create_workflow_execution(execution)
            
            # Passer les instances d'outils configurées au workflow
            tool_instances = self.get_tool_instances(name)
            result = workflow['module'].execute(data, tool_instances)
            
            update_workflow_execution(execution_id, {
                "end_time": datetime.utcnow(),
                "status": result.get("status", "success"),
                "result": result,
                "error": result.get("error")
            })
            
            create_log(LogModel(
                entity_type="workflow",
                entity_id=db_workflow.id,
                level="info" if result.get("status") == "success" else "error",
                message=f"Workflow {name} executed: {result.get('message', '')}",
                execution_id=execution_id
            ))
            
            return result
            
        except Exception as e:
            return {"status": "error", "message": f"Workflow execution failed: {str(e)}"}
    
    def toggle_workflow(self, name: str) -> Dict[str, Any]:
        db_workflow = next((w for w in list_workflows(active_only=False) if w.name == name), None)
        if not db_workflow:
            return {"status": "error", "message": f"Workflow '{name}' not found"}
        
        new_active = not db_workflow.active
        if update_workflow(db_workflow.id, {"active": new_active}):
            return {"status": "success", "active": new_active}
        return {"status": "error", "message": "Failed to toggle workflow"}
    
    def get_workflow_summary(self) -> List[Dict[str, Any]]:
        db_workflows = list_workflows(active_only=False)
        summary = []
        
        for db_workflow in db_workflows:
            # Vérifier que le dossier du workflow existe encore
            workflow_dir = self.workflows_dir / db_workflow.name
            if not workflow_dir.exists():
                continue
                
            fs_workflow = self._workflows.get(db_workflow.name, {})
            summary.append({
                'name': db_workflow.name,
                'display_name': db_workflow.display_name or db_workflow.name,
                'description': db_workflow.description or '',
                'category': db_workflow.category or 'other',
                'active': db_workflow.active,
                'tools_required': db_workflow.tools_required,
                'triggers': db_workflow.triggers
            })
        
        return summary
    
    def get_workflow_logs(self, name: str, limit: int = 50) -> List[Dict[str, Any]]:
        db_workflow = next((w for w in list_workflows(active_only=False) if w.name == name), None)
        if not db_workflow:
            return []
        
        logs = get_logs(entity_type="workflow", entity_id=db_workflow.id, limit=limit)
        return [{"timestamp": log.timestamp.isoformat(), "level": log.level, "message": log.message} for log in logs]
    
    def reload_workflows(self):
        self._load_workflows()
        self._notify_scheduler_reload()
    
    def _notify_scheduler_change(self, workflow_name: str, active: bool):
        try:
            from ...common.services.scheduler import workflow_scheduler
            workflow_scheduler.update_workflow_schedule(workflow_name, active)
        except ImportError:
            pass
    
    def _notify_scheduler_reload(self):
        try:
            from ...common.services.scheduler import workflow_scheduler
            workflow_scheduler.reload_schedules()
        except ImportError:
            pass

# Instance globale du registry
workflow_registry = WorkflowRegistry()

if __name__ == "__main__":
    # Test du registry
    registry = WorkflowRegistry()
    
    print("Workflows découverts:")
    for name, workflow in registry.get_all_workflows().items():
        config = workflow['config']
        print(f"  - {name}: {config.get('name', name)} ({config.get('category', 'unknown')})")
    
    print("\nTest d'exécution du workflow lead_nurturing:")
    result = registry.execute_workflow('lead_nurturing', {
        'name': 'Test Lead',
        'email': 'test@example.com',
        'priority': 'high'
    })
    print(f"Résultat: {result['status']} - {result['message']}")
