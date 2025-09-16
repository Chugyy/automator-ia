# Guide de Refactorisation v1

## Vue d'Ensemble

Ce guide documente l'architecture refactorisée pour supporter :
- Mode configuration direct (sans profil .env)
- Inputs manuels via interface web
- Logs streaming en temps réel
- Compatibilité avec l'architecture existante

## Architecture BaseTool

### Comparaison Ancien vs Nouveau

**Ancien (Mode profil uniquement) :**
```python
# Configuration exclusivement via profil .env
tool = NotionTool(profile="TEST")  # Lit NOTION_TEST_TOKEN dans .env
```

**Nouveau (Mode profil + direct) :**
```python
# Mode profil (existant, inchangé)
tool = NotionTool(profile="TEST")

# Mode direct (nouveau)
tool = NotionTool(config={"token": "secret_token"})
```

### Implémentation BaseTool

Le BaseTool existant est déjà compatible. La logique actuelle :

```python
def __init__(self, profile: str = "DEFAULT", config: Dict[str, Any] = None, free_mode: bool = False):
    self.profile = profile
    self.tool_name = self.__class__.__name__.replace("Tool", "").upper()
    self.free_mode = free_mode
    self.config = config or self._load_config()  # Mode direct si config fournie
    self.authenticated = False
```

**Comportement :**
- Si `config` est fourni → utilise cette config directement
- Si `config` est None → charge depuis profil .env (comportement existant)

## Architecture Outils

### Template Outil Standardisé

```python
from app.private.tools.base import BaseTool
from typing import Dict, Any, List

class ExampleTool(BaseTool):
    def __init__(self, profile: str = "DEFAULT", config: Dict[str, Any] = None):
        super().__init__(profile, config)
    
    def authenticate(self) -> bool:
        """Authentification automatique"""
        if not self.validate_config():
            return False
        
        try:
            # Logique d'authentification spécifique
            self.authenticated = True
            return True
        except Exception:
            return False
    
    def execute(self, action: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Auto-authentification + exécution"""
        if not self.authenticated and not self.authenticate():
            return {"success": False, "error": "Authentication failed"}
        
        # Logique métier par action
        if action == "example_action":
            return self._example_action(params or {})
        
        return {"success": False, "error": f"Unknown action: {action}"}
    
    def get_available_actions(self) -> List[str]:
        return ["example_action"]
    
    def _example_action(self, params: Dict[str, Any]) -> Dict[str, Any]:
        # Implémentation action
        return {"success": True, "result": "example_result"}
```

### Configuration Outil (config.json)

```json
{
    "name": "Example Tool",
    "description": "Outil d'exemple",
    "required_params": ["api_key"],
    "optional_params": {
        "base_url": "https://api.example.com",
        "timeout": 30
    },
    "inputs_schema": [
        {
            "name": "api_key",
            "type": "password",
            "label": "Clé API",
            "required": true,
            "description": "Votre clé API Example"
        }
    ],
    "actions": [
        {
            "name": "example_action",
            "description": "Action d'exemple",
            "params": [
                {
                    "name": "param1",
                    "type": "string",
                    "required": true
                }
            ]
        }
    ]
}
```

## Architecture Workflows

### Template Workflow Standardisé

```python
from typing import Dict, Any, List
from app.private.tools import get_tool_class

def execute(data: Dict[str, Any] = None, tools: Dict[str, Any] = None) -> Dict[str, Any]:
    """Exécute le workflow avec configuration centralisée"""
    
    # 1. Configuration centralisée des outils
    tools_config = build_tools_config(data)
    
    # 2. Initialisation des outils
    tools_instances = {}
    for tool_name, config in tools_config.items():
        tool_class = get_tool_class(tool_name)
        tools_instances[tool_name] = tool_class(config=config)
    
    # 3. Logique métier
    return execute_business_logic(tools_instances, data)

def build_tools_config(data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Construit la configuration des outils"""
    tools_profiles = get_tools_profiles()
    
    config = {}
    for tool_name, profile in tools_profiles.items():
        if profile.startswith("INPUT_"):
            # Configuration via input manuel
            input_key = profile.replace("INPUT_", "").lower()
            config[tool_name] = {"config": {input_key: data.get(input_key)}}
        else:
            # Configuration via profil
            config[tool_name] = {"profile": profile}
    
    return config

def get_required_inputs() -> List[Dict[str, Any]]:
    """Définit les inputs manuels requis"""
    return [
        {
            "name": "openai_key",
            "type": "password",
            "label": "Clé OpenAI",
            "required": True,
            "description": "Votre clé API OpenAI"
        },
        {
            "name": "target_email",
            "type": "email",
            "label": "Email cible",
            "required": True,
            "description": "Adresse email de destination"
        }
    ]

def get_tools_profiles() -> Dict[str, str]:
    """Définit les profils par défaut ou inputs manuels"""
    return {
        "notion": "TEST",           # Via profil .env
        "openai": "INPUT_OPENAI_KEY",  # Via input manuel
        "email": "DEFAULT"          # Via profil .env
    }

def execute_business_logic(tools: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    """Logique métier du workflow"""
    # Implémentation spécifique
    return {"success": True, "result": "workflow_completed"}
```

### Configuration Workflow (config.json)

```json
{
    "name": "Example Workflow",
    "description": "Workflow d'exemple",
    "inputs_schema": [
        {
            "name": "openai_key",
            "type": "password",
            "label": "Clé OpenAI",
            "required": true
        },
        {
            "name": "target_email", 
            "type": "email",
            "label": "Email cible",
            "required": true
        }
    ],
    "tools_profiles": {
        "notion": "TEST",
        "openai": "INPUT_OPENAI_KEY",
        "email": "DEFAULT"
    }
}
```

## Architecture Temp Scripts

### Template Script Temp Standardisé

```python
#!/usr/bin/env python3
"""Script de test temporaire"""

import sys
import os
from pathlib import Path

# Ajout du path système pour imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

from app.private.tools.notion.main import NotionTool
from dotenv import load_dotenv

def main():
    """Test en mode direct"""
    # Chargement .env pour récupérer token
    load_dotenv("backend/config/.env")
    
    # Configuration directe
    config = {
        "token": os.getenv("NOTION_TEST_TOKEN"),
        "database_id": "your_database_id"
    }
    
    # Initialisation en mode direct
    tool = NotionTool(config=config)
    
    # Test authentification
    if tool.authenticate():
        print("✓ Authentification réussie")
        
        # Test action
        result = tool.execute("list_pages", {"limit": 5})
        if result["success"]:
            print(f"✓ Action réussie: {len(result['result'])} pages trouvées")
        else:
            print(f"✗ Erreur action: {result['error']}")
    else:
        print("✗ Échec authentification")

if __name__ == "__main__":
    main()
```

## Architecture Backend Extensions

### Nouveaux Endpoints Dashboard

```python
# backend/app/dashboard/main.py - AJOUTS

@router.get("/api/workflows/{workflow_name}/inputs")
async def get_workflow_inputs(workflow_name: str):
    """Récupère les inputs requis pour un workflow"""
    try:
        workflow_module = import_workflow(workflow_name)
        if hasattr(workflow_module, 'get_required_inputs'):
            inputs = workflow_module.get_required_inputs()
            return {"inputs": inputs}
        return {"inputs": []}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/api/workflows/{workflow_name}/execute-stream")
async def execute_workflow_stream(workflow_name: str, inputs: Dict[str, Any]):
    """Exécute workflow avec inputs manuels et streaming logs"""
    try:
        # Génération ID unique pour cette exécution
        execution_id = f"{workflow_name}_{int(time.time())}"
        
        # Lancement workflow en arrière-plan avec logging
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
        # Streaming des logs depuis le buffer
        async for log_entry in get_workflow_logs_stream(execution_id):
            await websocket.send_json(log_entry)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})
    finally:
        await websocket.close()
```

### Engine Logging Extensions

```python
# backend/app/private/engine.py - AJOUTS

import asyncio
from collections import defaultdict

# Buffer global pour logs par execution_id
logs_buffer = defaultdict(list)
websocket_connections = defaultdict(list)

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
        
        # Ajout au buffer
        logs_buffer[execution_id].append(log_entry)
        
        # Envoi aux WebSocket connectées
        for websocket in websocket_connections[execution_id]:
            asyncio.create_task(websocket.send_json(log_entry))
    
    try:
        log_callback("INFO", f"Démarrage workflow {workflow_name}")
        
        # Exécution workflow avec logging
        result = execute_workflow(workflow_name, data, log_callback)
        
        log_callback("INFO", f"Workflow terminé avec succès", {"result": result})
        return result
        
    except Exception as e:
        log_callback("ERROR", f"Erreur workflow: {str(e)}")
        raise
    finally:
        # Nettoyage après 1h
        asyncio.create_task(cleanup_logs(execution_id, delay=3600))

async def get_workflow_logs_stream(execution_id: str):
    """Stream des logs pour un execution_id"""
    for log_entry in logs_buffer[execution_id]:
        yield log_entry
    
    # Attendre de nouveaux logs
    while execution_id in logs_buffer:
        await asyncio.sleep(0.1)
        new_logs = logs_buffer[execution_id][len(logs_buffer[execution_id]):]
        for log_entry in new_logs:
            yield log_entry
```

## Architecture Frontend Extensions

### Modal Inputs Manuels

```javascript
// frontend/js/workflow-inputs.js

function showWorkflowInputsModal(workflow, inputs) {
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.innerHTML = `
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Configuration ${workflow.name}</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <form id="workflow-inputs-form">
                        ${generateInputsForm(inputs)}
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Annuler</button>
                    <button type="button" class="btn btn-primary" onclick="executeWorkflowWithInputs('${workflow.name}')">Exécuter</button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    new bootstrap.Modal(modal).show();
}

function generateInputsForm(inputs) {
    return inputs.map(input => {
        const inputType = input.type === 'password' ? 'password' : 'text';
        const required = input.required ? 'required' : '';
        
        return `
            <div class="mb-3">
                <label for="${input.name}" class="form-label">
                    ${input.label} ${input.required ? '*' : ''}
                </label>
                <input type="${inputType}" 
                       class="form-control" 
                       id="${input.name}" 
                       name="${input.name}" 
                       ${required}
                       placeholder="${input.description || ''}">
                <small class="form-text text-muted">${input.description || ''}</small>
            </div>
        `;
    }).join('');
}

async function executeWorkflowWithInputs(workflowName) {
    const form = document.getElementById('workflow-inputs-form');
    const formData = new FormData(form);
    const inputs = Object.fromEntries(formData.entries());
    
    try {
        // Lancement avec streaming
        const response = await fetch(`/api/workflows/${workflowName}/execute-stream`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(inputs)
        });
        
        const result = await response.json();
        
        // Ouverture modal logs
        showWorkflowLogsModal(workflowName, result.execution_id);
        
    } catch (error) {
        console.error('Erreur exécution:', error);
    }
}
```

### Streaming Logs Modal

```javascript
// frontend/js/workflow-logs.js

function showWorkflowLogsModal(workflowName, executionId) {
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.innerHTML = `
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Logs ${workflowName}</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div id="logs-container" style="height: 400px; overflow-y: auto; background: #1e1e1e; color: #fff; padding: 10px; font-family: monospace;">
                        <div class="text-info">Connexion aux logs...</div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fermer</button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    const modalInstance = new bootstrap.Modal(modal);
    modalInstance.show();
    
    // Connexion WebSocket logs
    connectWorkflowLogs(workflowName, executionId);
}

function connectWorkflowLogs(workflowName, executionId) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/workflows/${workflowName}/logs/${executionId}`;
    
    const websocket = new WebSocket(wsUrl);
    const container = document.getElementById('logs-container');
    
    websocket.onopen = function() {
        container.innerHTML = '<div class="text-success">✓ Connecté aux logs</div>';
    };
    
    websocket.onmessage = function(event) {
        const logEntry = JSON.parse(event.data);
        appendLogEntry(container, logEntry);
    };
    
    websocket.onerror = function(error) {
        container.innerHTML += '<div class="text-danger">✗ Erreur connexion logs</div>';
    };
    
    websocket.onclose = function() {
        container.innerHTML += '<div class="text-warning">➤ Connexion fermée</div>';
    };
}

function appendLogEntry(container, logEntry) {
    const timestamp = new Date(logEntry.timestamp * 1000).toLocaleTimeString();
    const levelClass = {
        'INFO': 'text-info',
        'SUCCESS': 'text-success', 
        'WARNING': 'text-warning',
        'ERROR': 'text-danger'
    }[logEntry.level] || 'text-light';
    
    const logLine = document.createElement('div');
    logLine.className = levelClass;
    logLine.innerHTML = `[${timestamp}] ${logEntry.level}: ${logEntry.message}`;
    
    container.appendChild(logLine);
    container.scrollTop = container.scrollHeight;
}
```

## Migration Progressive

### Étape 1 : Outils Existants (Compatible)
Les outils existants continuent à fonctionner sans modification :
```python
# Fonctionne toujours
notion_tool = NotionTool(profile="TEST")
```

### Étape 2 : Nouveaux Workflows avec Inputs
Nouveaux workflows peuvent utiliser les inputs manuels :
```python
# Nouveau workflow avec inputs
def get_required_inputs():
    return [{"name": "api_key", "type": "password"}]
```

### Étape 3 : Interface Web Étendue
Interface supporte automatiquement les workflows avec inputs.

## Exemples Concrets

### Exemple Tool : NotionTool Étendu

```python
# backend/app/private/tools/notion/main.py - EXTENSION
def execute(self, action: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    # Auto-authentification
    if not self.authenticated and not self.authenticate():
        return {"success": False, "error": "Authentication failed"}
    
    # Actions existantes + logs
    if hasattr(self, '_log_callback') and self._log_callback:
        self._log_callback("INFO", f"Exécution action {action}", {"params": params})
    
    return super().execute(action, params)
```

### Exemple Workflow : Notion + OpenAI

```python
# backend/app/private/workflows/notion_openai_sync/main.py

def get_required_inputs():
    return [
        {"name": "openai_key", "type": "password", "label": "Clé OpenAI", "required": True},
        {"name": "notion_database", "type": "text", "label": "ID Database Notion", "required": True}
    ]

def get_tools_profiles():
    return {
        "notion": "TEST",
        "openai": "INPUT_OPENAI_KEY"
    }

def execute(data: Dict[str, Any] = None, tools: Dict[str, Any] = None) -> Dict[str, Any]:
    # Configuration des outils
    tools_config = {
        "notion": {"profile": "TEST"},
        "openai": {"config": {"api_key": data.get("openai_key")}}
    }
    
    # Initialisation
    notion = NotionTool(profile="TEST")
    openai = OpenAITool(config={"api_key": data.get("openai_key")})
    
    # Logique métier
    pages = notion.execute("list_pages", {"database_id": data.get("notion_database")})
    
    if pages["success"]:
        for page in pages["result"]:
            # Traitement IA
            analysis = openai.execute("analyze_text", {"text": page["content"]})
            # Mise à jour Notion avec analyse
    
    return {"success": True, "processed": len(pages.get("result", []))}
```

Ce guide documente l'architecture complète permettant une migration progressive tout en préservant la compatibilité existante.