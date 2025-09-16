# Backend Workflow Platform

Plateforme d'automatisation modulaire avec outils, workflows et interfaces personnalisables.

## 🚀 Démarrage Rapide

### Installation
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows
pip install -r config/requirements.txt
```

### Lancement
```bash
python -m app.main
```

### Accès
- **Dashboard** : http://localhost:8000
- **API Docs** : http://localhost:8000/docs

## 🎯 Architecture Common vs Private

### 🔒 Common (NE PAS modifier)
```
app/common/
├── database/     # Base de données SQLite
├── engine.py     # Moteur d'exécution workflows
├── services/     # Services système (scheduler, tools, oauth)
└── interfaces/   # Dashboard principal
```

### ✅ Private (Zone utilisateur)
```
app/private/
├── tools/        # Vos outils personnalisés
├── workflows/    # Vos workflows métier
├── interfaces/   # Vos interfaces web
└── temp/         # Scripts temporaires (LLM)
```

**Règle d'or** : Modifiez uniquement le dossier `private/`.

## 🔐 Système de Profils & OAuth

### Configuration des Profils

Les profils permettent d'utiliser le même outil avec différentes configurations.

**Format variable** : `{OUTIL}_{PROFIL}_{PARAMETRE}`

**Fichier** : `config/.env`
```bash
# Profil TEST pour Google Calendar
GOOGLE_CALENDAR_TEST_CREDENTIALS_FILE=etc/secrets/google_test_credentials.json
GOOGLE_CALENDAR_TEST_TOKEN_FILE=etc/secrets/google_test_token.json
GOOGLE_CALENDAR_TEST_CALENDAR_ID=test@company.com

# Profil WORK pour Google Calendar  
GOOGLE_CALENDAR_WORK_CREDENTIALS_FILE=etc/secrets/google_work_credentials.json
GOOGLE_CALENDAR_WORK_TOKEN_FILE=etc/secrets/google_work_token.json
GOOGLE_CALENDAR_WORK_CALENDAR_ID=work@company.com
```

### Utilisation dans le Code
```python
# Utilise automatiquement les variables GOOGLE_CALENDAR_TEST_*
calendar = CalendarTool(profile="TEST")

# Utilise les variables GOOGLE_CALENDAR_WORK_*
calendar = CalendarTool(profile="WORK")
```

### OAuth Google

**Système unifié** pour tous les services Google (Calendar, Drive, Sheets).

#### Étapes d'authentification :

1. **Créer credentials Google** :
   - Aller sur [Google Cloud Console](https://console.cloud.google.com)
   - Créer projet → Activer APIs → Créer credentials OAuth 2.0
   - Redirect URI : `http://localhost:8000/oauth/google/callback`

2. **Placer le fichier** :
   ```bash
   # Exemple pour profil TEST
   backend/etc/secrets/google_test_credentials.json
   ```

3. **Authentifier** :
   ```
   http://localhost:8000/oauth/google/auth?service=calendar&profile=TEST
   ```

4. **Token généré automatiquement** :
   ```bash
   backend/etc/secrets/google_test_token.json
   ```

### Vérifier l'état OAuth
```bash
# Tous les outils OAuth
curl http://localhost:8000/api/oauth/status

# Outil spécifique
curl http://localhost:8000/api/oauth/status/google_calendar?profile=TEST
```

## 🔧 Créer un Outil

### Structure minimale
```bash
mkdir app/private/tools/mon_outil
cd app/private/tools/mon_outil
```

### 1. config.json
```json
{
  "tool_name": "mon_outil",
  "display_name": "Mon Outil",
  "description": "Description de votre outil",
  "required_params": ["api_key"],
  "optional_params": {
    "timeout": 30,
    "base_url": "https://api.example.com"
  },
  "actions": {
    "search": {
      "description": "Recherche des données",
      "parameters": {
        "query": "Terme de recherche (requis)",
        "limit": "Nombre de résultats (optionnel, défaut: 10)"
      },
      "example": {
        "action": "search",
        "params": {"query": "test", "limit": 5}
      }
    }
  },
  "profile_examples": {
    "PROD": {
      "api_key": "your_prod_api_key",
      "base_url": "https://api.prod.example.com"
    },
    "TEST": {
      "api_key": "your_test_api_key", 
      "base_url": "https://api.test.example.com"
    }
  }
}
```

### 2. main.py
```python
from typing import Dict, Any, List
from ..base import BaseTool
from config.logger import logger

class MonOutilTool(BaseTool):
    def authenticate(self) -> bool:
        if not self.validate_config():
            return False
        
        # Test de connexion
        api_key = self.config.get('api_key')
        if not api_key:
            logger.error("API key missing")
            return False
        
        self.authenticated = True
        return True
    
    def execute(self, action: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        params = params or {}
        
        if not self.is_authenticated():
            return {"error": "Not authenticated"}
        
        if action == "search":
            return self._search(params)
        
        return {"error": f"Action {action} not supported"}
    
    def get_available_actions(self) -> List[str]:
        return ["search"]
    
    def _search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        query = params.get('query')
        if not query:
            return {"error": "Query parameter required"}
        
        try:
            # Votre logique API ici
            results = {"query": query, "results": []}
            return {"status": "success", "data": results}
        except Exception as e:
            logger.error(f"Search error: {e}")
            return {"error": str(e)}
```

### 3. Configuration du profil
```bash
# Dans config/.env
MON_OUTIL_TEST_API_KEY=test_api_key_123
MON_OUTIL_TEST_BASE_URL=https://api.test.example.com

MON_OUTIL_PROD_API_KEY=prod_api_key_456  
MON_OUTIL_PROD_BASE_URL=https://api.example.com
```

### 4. Test
```python
# Script temporaire dans app/private/temp/
from app.private.tools.mon_outil.main import MonOutilTool

tool = MonOutilTool(profile="TEST")
if tool.authenticate():
    result = tool.execute("search", {"query": "test"})
    print(result)
```

## 📋 Créer un Workflow

### Questions à se poser AVANT

1. **Besoin** : Quel problème résout ce workflow ?
2. **Outils** : Quels outils existants utiliser ?
3. **Données** : Quelles données d'entrée sont nécessaires ?
4. **Profils** : Quels profils d'outils utiliser ?
5. **Déclencheurs** : Manuel, webhook, planifié ?

### Structure
```bash
mkdir app/private/workflows/mon_workflow
cd app/private/workflows/mon_workflow
```

### 1. config.json
```json
{
  "name": "Mon Workflow",
  "description": "Description du workflow",
  "schedule": "0 9 * * 1-5",
  "triggers": ["webhook", "manual", "schedule"],
  "category": "automation",
  "tools_required": ["mon_outil", "google_calendar"],
  "inputs_schema": [
    {
      "name": "user_email",
      "type": "email",
      "label": "Email utilisateur",
      "required": true,
      "description": "Email de l'utilisateur à traiter"
    }
  ],
  "tools_profiles": {
    "mon_outil": "PROD",
    "google_calendar": "WORK"
  },
  "active": true
}
```

### 2. main.py
```python
from typing import Dict, Any, List
from app.private.tools.mon_outil.main import MonOutilTool
from app.private.tools.google_calendar.main import CalendarTool

def execute(data: Dict[str, Any] = None, tools: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Fonction principale du workflow
    
    Args:
        data: Paramètres d'entrée
        tools: Outils configurés (optionnel)
    
    Returns:
        Résultat avec status et données
    """
    try:
        # === 1. RÉCUPÉRATION DES OUTILS ===
        tools_config = build_tools_config(data)
        tools_instances = {}
        
        for tool_name, config in tools_config.items():
            if tool_name == "mon_outil":
                tools_instances[tool_name] = MonOutilTool(profile=config["profile"])
            elif tool_name == "google_calendar":
                tools_instances[tool_name] = CalendarTool(profile=config["profile"])
        
        # === 2. AUTHENTIFICATION ===
        for tool_name, tool in tools_instances.items():
            if not tool.authenticate():
                return {
                    "status": "error", 
                    "message": f"Authentication failed for {tool_name}",
                    "auth_required": True,
                    "tool": tool_name
                }
        
        # === 3. LOGIQUE MÉTIER ===
        user_email = data.get('user_email')
        if not user_email:
            return {"status": "error", "message": "user_email required"}
        
        # Exemple : recherche puis création d'événement
        search_result = tools_instances["mon_outil"].execute("search", {
            "query": f"user:{user_email}"
        })
        
        if search_result.get("status") == "success":
            calendar_result = tools_instances["google_calendar"].execute("create_event", {
                "summary": f"Meeting with {user_email}",
                "start_time": "2024-12-25T14:00:00",
                "end_time": "2024-12-25T15:00:00"
            })
            
            return {
                "status": "success",
                "message": "Workflow completed",
                "data": {
                    "search": search_result["data"],
                    "calendar": calendar_result["data"]
                }
            }
        
        return {"status": "error", "message": "Search failed"}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

def build_tools_config(data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Configure les profils des outils"""
    tools_profiles = get_tools_profiles()
    
    config = {}
    for tool_name, profile in tools_profiles.items():
        config[tool_name] = {"profile": profile}
    
    return config

def get_required_inputs() -> List[Dict[str, Any]]:
    """Définit les inputs requis pour l'interface"""
    return [
        {
            "name": "user_email",
            "type": "email",
            "label": "Email utilisateur",
            "required": True,
            "description": "Email de l'utilisateur à traiter"
        }
    ]

def get_tools_profiles() -> Dict[str, str]:
    """Définit les profils par défaut"""
    return {
        "mon_outil": "PROD",
        "google_calendar": "WORK"
    }
```

### 3. Test du workflow
```bash
# Via API
curl -X POST "http://localhost:8000/api/workflows/execute/mon_workflow" \
  -H "Content-Type: application/json" \
  -d '{"user_email": "test@example.com"}'

# Via webhook  
curl -X POST "http://localhost:8000/api/webhooks/mon_workflow?user_email=test@example.com"

# Via interface web
http://localhost:8000/dashboard/
```

## 🖥️ Créer une Interface

### Structure
```bash
mkdir app/private/interfaces/mon_interface
mkdir app/private/interfaces/mon_interface/src
```

### 1. main.py
```python
from fastapi import APIRouter
from fastapi.responses import FileResponse
import os

DISPLAY_NAME = "Mon Interface"
DESCRIPTION = "Interface personnalisée"
ROUTE = "/mon-interface"
ICON = "🎯"

router = APIRouter(prefix=ROUTE)

@router.get("/")
def get_interface():
    return FileResponse(os.path.join(os.path.dirname(__file__), "src", "index.html"))

def get_router():
    return router
```

### 2. src/index.html
```html
<!DOCTYPE html>
<html>
<head>
    <title>Mon Interface</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .container { max-width: 800px; margin: 0 auto; }
        button { padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 Mon Interface</h1>
        <p>Interface personnalisée pour mes workflows</p>
        
        <button onclick="triggerWorkflow()">Déclencher Workflow</button>
        
        <div id="result" style="margin-top: 20px;"></div>
    </div>

    <script>
        async function triggerWorkflow() {
            const result = document.getElementById('result');
            result.innerHTML = 'Exécution en cours...';
            
            try {
                const response = await fetch('/api/workflows/trigger/mon_workflow?user_email=test@example.com');
                const data = await response.json();
                result.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
            } catch (error) {
                result.innerHTML = `Erreur: ${error.message}`;
            }
        }
    </script>
</body>
</html>
```

### 3. Accès
```
http://localhost:8000/mon-interface/
```

## ⚡ Fichiers Temporaires

### Usage LLM

Les fichiers temporaires permettent au LLM de tester du code directement sans créer d'outils permanents.

### Pattern standardisé
```python
#!/usr/bin/env python3
import sys, os
from pathlib import Path

# Ajout du chemin projet  
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

from app.private.tools.google_calendar.main import CalendarTool
from dotenv import load_dotenv

def main():
    # Charger l'environnement
    load_dotenv("backend/config/.env")
    
    # Initialiser l'outil
    tool = CalendarTool(profile="TEST")
    
    if tool.authenticate():
        # Test de l'action
        result = tool.execute("list_events", {"count": 5})
        print(f"✅ Test réussi: {result}")
    else:
        print("❌ Authentication failed")
        status = tool.get_oauth_status()
        print(f"Auth URL: {status.get('auth_url')}")

if __name__ == "__main__":
    main()
```

### Cycle de vie
1. **Création** : LLM crée le script dans `app/private/temp/`
2. **Exécution** : `python -m app.private.temp.mon_script`
3. **Nettoyage** : Suppression après validation

### Bonnes pratiques
- Préfixe `test_` pour les scripts temporaires
- Toujours des chemins relatifs
- Import depuis le projet root
- Gestion d'erreurs explicite

## 📊 API & Commandes

### API Principales
```bash
# Workflows
GET  /api/workflows                    # Liste workflows
POST /api/workflows/execute/{name}     # Exécuter (JSON body)
GET  /api/workflows/trigger/{name}     # Déclencher (params URL)
POST /api/webhooks/{name}              # Webhook
GET  /api/workflows/logs/{name}        # Logs

# OAuth
GET  /api/oauth/status                 # État global OAuth
GET  /api/oauth/status/{tool}          # État outil spécifique

# Scheduler
GET  /api/scheduler/jobs               # Jobs programmés

# Admin
POST /api/reload                       # Hot-reload système
```

### Commandes Essentielles
```bash
# Lancer la plateforme
python -m app.main

# Tests
python -m app.private.temp.mon_test

# Build system (auto au démarrage)
python -m app.build

# Hot-reload
curl -X POST "http://localhost:8000/api/reload"
```

### Expressions Cron (Schedule)
```bash
"0 9 * * 1-5"    # Jours ouvrés 9h
"*/15 * * * *"   # Toutes les 15min
"0 */2 * * *"    # Toutes les 2h
"0 0 1 * *"      # 1er du mois
```

## 🔥 Fonctionnalités

- **🔄 Auto-Discovery** : Détection automatique workflows/interfaces
- **🔐 OAuth Unifié** : Système centralisé Google services
- **📊 Profils Multi** : Configurations par environnement
- **⏰ Scheduler** : Planification cron avec persistence
- **🌐 Hot-Reload** : Modifications sans redémarrage
- **📱 Multi-Interface** : Dashboard + interfaces personnalisées
- **🧪 Mode Temporaire** : Tests LLM sans impact

---

**Architecture minimaliste** : Modifiez seulement `app/private/` pour vos besoins !