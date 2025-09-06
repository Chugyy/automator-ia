# 🚀 Workflow Automation Platform

Plateforme d'automatisation ultra-scalable basée sur des workflows modulaires et des interfaces dynamiques.

## 🏗️ Architecture

### Structure Minimaliste
```
backend/
├── app/
│   ├── tools/                 # 🔧 Banque d'outils (Slack, Notion, etc.)
│   ├── workflows/             # 📋 Un dossier = un workflow
│   │   ├── lead_nurturing/    
│   │   │   ├── main.py        # Logique principale
│   │   │   └── config.json    # Métadonnées
│   │   └── registry.py        # Auto-discovery
│   ├── interfaces/            # 🖥️ Interfaces web modulaires
│   │   ├── dashboard/         # Interface principale
│   │   ├── crm_interface/     # Interface CRM spécialisée
│   │   └── registry.py        # Auto-discovery
│   ├── core/
│   │   └── engine.py          # Moteur d'exécution
│   └── api/
│       └── main.py            # API principale
```

## 🚀 Démarrage Rapide

1. **Installation**
```bash
cd backend
pip install fastapi uvicorn pydantic
```

2. **Lancement**
```bash
python app/main.py
```

3. **Accès**
- Dashboard: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Interface CRM: http://localhost:8000/crm

## 🔄 Développement et Modifications

### ⚠️ **Important : Redémarrage Obligatoire**

**À chaque modification du code Python**, le serveur doit être **redémarré manuellement** :

```bash
# 1. Arrêter le serveur (Ctrl+C)
^C

# 2. Relancer
python app/main.py
```

### 🔧 **Alternatives pour le Hot-Reload**

```bash
# Option 1: Mode développement avec auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Option 2: Utiliser le reload API (sans redémarrage serveur)
curl -X POST "http://localhost:8000/api/reload"
```

**Note :** Le reload API ne fonctionne que pour les **workflows et interfaces**. Les modifications du **code core** (scheduler, services) nécessitent un redémarrage complet.

## 📋 Tutoriel Complet : Créer un Workflow avec Outils

### 🎯 Exemple Concret : Workflow "Newsletter Automation"

**Objectif** : Automatiser l'envoi d'une newsletter quotidienne en récupérant des vidéos YouTube récentes et en notifiant l'équipe sur Slack.

### Étape 1 : Structure du Workflow

```bash
mkdir app/private/workflows/newsletter_automation
```

### Étape 2 : Configuration (config.json)

```json
{
  "name": "Newsletter Automation",
  "description": "Récupère les dernières vidéos YouTube et envoie une newsletter automatisée",
  "schedule": "0 8 * * 1-5",
  "triggers": ["webhook", "manual", "schedule"],
  "category": "marketing",
  "interface": "dashboard",
  "tools_required": ["youtube", "slack", "email"],
  "tool_profiles": {
    "youtube": "TECH_CHANNEL",
    "slack": "MARKETING", 
    "email": "NEWSLETTER"
  },
  "active": true
}
```

## ⏰ Planification des Workflows (Scheduler)

### 🎯 Configuration du Schedule

Pour programmer l'exécution automatique de votre workflow, ajoutez dans `config.json` :

```json
{
  "name": "Mon Workflow",
  "schedule": "0 9 * * 1-5",
  "triggers": ["webhook", "manual", "schedule"],
  "active": true
}
```

**⚠️ Important :** Le trigger `"schedule"` doit être inclus dans `triggers` pour activer la planification.

### 📅 Expressions Cron Supportées

| Expression | Description | Exécution |
|------------|-------------|-----------|
| `* * * * *` | Chaque minute | Toutes les minutes |
| `0 * * * *` | Chaque heure | À l'heure pile (ex: 9h00, 10h00) |
| `0 9 * * *` | Tous les jours à 9h | Quotidien à 9h00 |
| `0 9 * * 1-5` | Jours ouvrés à 9h | Lundi au vendredi à 9h00 |
| `*/15 * * * *` | Toutes les 15 min | Toutes les 15 minutes |
| `0 */2 * * *` | Toutes les 2h | Toutes les 2 heures |
| `30 14 15 * *` | Le 15 du mois | 14h30 le 15 de chaque mois |
| `0 0 * * 0` | Tous les dimanches | Dimanche à minuit |
| `0 6 1 1 *` | Jour de l'an | 1er janvier à 6h00 |

**Format :** `minute heure jour_mois mois jour_semaine`

### 🛠️ Gestion des Jobs Programmés

#### 📊 Monitoring des Jobs
```bash
# Voir tous les jobs actifs
curl "http://localhost:8000/api/scheduler/jobs"

# Réponse typique
[{
  "id": "uuid-job",
  "workflow_name": "newsletter_automation",
  "workflow_display_name": "Newsletter Automation", 
  "cron_expression": "0 9 * * 1-5",
  "active": true,
  "next_run": "2024-01-15T09:00:00",
  "last_run": "2024-01-14T09:00:00",
  "workflow_active": true
}]
```

#### ✅ Conditions d'Exécution

Le scheduler vérifie **automatiquement** avant chaque exécution :

1. **Workflow actif** : Le workflow doit être `active: true`
2. **Outils disponibles** : Tous les `tools_required` doivent être actifs
3. **Déclencheurs** : `"schedule"` doit être dans `triggers`

#### 🔄 Contrôle des Jobs

```bash
# Activer/désactiver un workflow (et son job)
curl -X POST "http://localhost:8000/api/workflows/toggle/mon_workflow"

# Recharger tous les schedules
curl -X POST "http://localhost:8000/api/reload"
```

### 🚨 Comportements Automatiques

- **Workflow désactivé** → Job automatiquement supprimé
- **Outil requis inactif** → Exécution sautée (workflow reste programmé)
- **Erreur d'exécution** → Job continue selon planning
- **Reload système** → Tous les jobs reprogrammés
- **Timestamps BDD** → `next_run` et `last_run` mis à jour automatiquement

### 💡 Exemples de Cas d'Usage

```json
// Backup quotidien
{
  "schedule": "0 2 * * *",
  "description": "Sauvegarde à 2h du matin"
}

// Rapport hebdomadaire  
{
  "schedule": "0 8 * * 1",
  "description": "Rapport le lundi matin"
}

// Vérification fréquente
{
  "schedule": "*/5 * * * *", 
  "description": "Toutes les 5 minutes"
}

// Nettoyage mensuel
{
  "schedule": "0 3 1 * *",
  "description": "Le 1er du mois à 3h"
}
```

### Étape 3 : Logique Métier (main.py)

```python
from typing import Dict, Any
from tools.youtube.main import YouTubeTool
from tools.slack.main import SlackTool
from tools.email.main import EmailTool

def execute(data: Dict[str, Any] = None, tools: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Workflow de newsletter automation
    
    Args:
        data: Paramètres d'entrée (ex: {"keyword": "python", "max_videos": 5})
        tools: Outils configurés avec leurs profils
    
    Returns:
        Résultat du workflow avec status et données
    """
    
    try:
        # === 1. RÉCUPÉRATION DES OUTILS ===
        youtube = tools.get('youtube') if tools else YouTubeTool()
        slack = tools.get('slack') if tools else SlackTool()
        email_tool = tools.get('email') if tools else EmailTool()
        
        # === 2. AUTHENTIFICATION ===
        if not all([youtube.authenticate(), slack.authenticate(), email_tool.authenticate()]):
            return {"status": "error", "message": "Authentication failed for one or more tools"}
        
        # === 3. PARAMÈTRES D'ENTRÉE ===
        params = data or {}
        keyword = params.get('keyword', 'tech news')
        max_videos = params.get('max_videos', 3)
        
        results = []
        
        # === 4. RÉCUPÉRATION VIDÉOS YOUTUBE ===
        youtube_result = youtube.execute('search_videos', {
            'query': keyword,
            'max_results': max_videos,
            'published_after': '7days'  # Dernière semaine
        })
        
        if youtube_result.get('status') != 'success':
            return {"status": "error", "message": "Failed to fetch YouTube videos"}
        
        videos = youtube_result.get('data', {}).get('videos', [])
        results.append({'step': 'youtube_search', 'result': youtube_result})
        
        # === 5. CRÉATION DU CONTENU NEWSLETTER ===
        newsletter_content = "📹 **Dernières vidéos tech de la semaine**\n\n"
        for i, video in enumerate(videos, 1):
            title = video.get('title', 'Sans titre')
            url = video.get('url', '#')
            views = video.get('view_count', 0)
            newsletter_content += f"{i}. **{title}**\n   👁️ {views:,} vues - {url}\n\n"
        
        # === 6. NOTIFICATION SLACK ===
        slack_result = slack.execute('post_message', {
            'channel': '#marketing',
            'text': f"📧 Newsletter prête ! {len(videos)} vidéos trouvées pour '{keyword}'"
        })
        results.append({'step': 'slack_notification', 'result': slack_result})
        
        # === 7. ENVOI EMAIL ===
        email_result = email_tool.execute('send_email', {
            'to': ['subscribers@company.com'],
            'subject': f'Newsletter Tech - {keyword.title()}',
            'body': newsletter_content,
            'format': 'markdown'
        })
        results.append({'step': 'email_send', 'result': email_result})
        
        # === 8. CONFIRMATION FINALE ===
        final_message = f"✅ Newsletter envoyée avec succès ! {len(videos)} vidéos incluses"
        slack.execute('post_message', {
            'channel': '#marketing',
            'text': final_message
        })
        
        return {
            "status": "success",
            "message": final_message,
            "data": {
                "keyword": keyword,
                "videos_found": len(videos),
                "steps_executed": len(results),
                "newsletter_content": newsletter_content,
                "results": results
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Newsletter workflow failed: {str(e)}",
            "data": {"error_details": str(e)}
        }

def validate_data(data: Dict[str, Any]) -> bool:
    """Validation optionnelle des données d'entrée"""
    # Aucune donnée obligatoire pour ce workflow
    return True

# Test en local
if __name__ == "__main__":
    test_data = {
        "keyword": "python tutorials",
        "max_videos": 3
    }
    
    result = execute(test_data)
    print(f"Test result: {result}")
```

### Étape 4 : Outils Disponibles

**Outils pré-configurés dans le système :**

- **📺 YouTube** : `search_videos`, `get_video_info`, `get_channel_info`
- **💬 Slack** : `post_message`, `get_messages`, `create_channel`
- **📧 Email** : `send_email`, `send_bulk_email` 
- **📅 Calendar** : `create_event`, `list_events`, `update_event`
- **📝 Notion** : `create_page`, `update_page`, `query_database`
- **💬 WhatsApp** : `send_message`, `get_messages`
- **🔍 Web Search** : `search`, `get_page_content`
- **📅 Date** : `get_current_date`, `format_date`, `calculate_date`

### Étape 5 : Test et Déploiement

1. **Test local**
```bash
cd app/private/workflows/newsletter_automation
python main.py
```

2. **Test via API**
```bash
# Déclenchement manuel avec paramètres
curl "http://localhost:8000/api/workflows/trigger/newsletter_automation?keyword=AI+news&max_videos=5"

# Webhook 
curl -X POST "http://localhost:8000/api/webhooks/newsletter_automation" \
  -H "Content-Type: application/json" \
  -d '{"keyword": "machine learning", "max_videos": 3}'
```

3. **Auto-détection** : Le workflow apparaît automatiquement dans le dashboard !

### 🔧 Configuration des Profils d'Outils

Les profils permettent d'utiliser plusieurs configurations du même outil :

```json
"tool_profiles": {
  "youtube": "TECH_CHANNEL",    # Profile spécifique pour chaînes tech
  "slack": "MARKETING",         # Canal marketing
  "email": "NEWSLETTER"         # Template newsletter
}
```

**Fichier de configuration** : `app/private/tools/youtube/config.json`
```json
{
  "profiles": {
    "TECH_CHANNEL": {
      "api_key": "your_youtube_api_key",
      "default_channel": "UC_tech_channel_id",
      "region": "FR"
    }
  }
}
```

## 🔧 Créer un Nouvel Outil

```python
# app/tools/mon_outil.py
from .base import BaseTool

class MonOutil(BaseTool):
    def authenticate(self):
        return True
    
    def execute(self, action, params=None):
        # Votre logique ici
        return {"status": "success"}
    
    def get_available_actions(self):
        return ["action1", "action2"]
```

## 🖥️ Créer une Nouvelle Interface

L'interface permet de servir des fichiers HTML statiques pour le rendu côté client.

1. **Structure obligatoire**
```bash
mkdir app/interfaces/mon_interface/src
```

2. **Créer src/index.html** (obligatoire)
```html
<!DOCTYPE html>
<html>
<head>
    <title>Mon Interface</title>
</head>
<body>
    <h1>Mon Interface</h1>
</body>
</html>
```

3. **Créer main.py** (pour servir l'HTML)
```python
from fastapi import APIRouter
from fastapi.responses import FileResponse
import os

DISPLAY_NAME = "Mon Interface"
DESCRIPTION = "Description de l'interface"
ROUTE = "/mon-interface"
ICON = "🎯"

router = APIRouter(prefix=ROUTE)

@router.get("/")
def get_interface():
    return FileResponse(os.path.join(os.path.dirname(__file__), "src", "index.html"))

def get_router():
    return router
```

## 🔌 API Endpoints

### Workflows
- `GET /api/workflows` - Liste des workflows
- `POST /api/workflows/execute/{name}` - Exécuter un workflow (avec JSON body)
- `GET /api/workflows/trigger/{name}` - Déclenchement manuel (avec paramètres URL)
- `POST /api/webhooks/{name}` - Webhook avec support paramètres URL + JSON
- `GET /api/workflows/logs/{name}` - Logs d'exécution
- `GET /api/workflows/stats` - Statistiques globales
- `GET /api/workflows/stats/{name}` - Statistiques d'un workflow
- `POST /api/workflows/toggle/{name}` - Activer/désactiver un workflow

### Scheduler ⏰
- `GET /api/scheduler/jobs` - **Nouveau!** Liste des jobs programmés avec statuts
  - Affiche `next_run`, `last_run`, `cron_expression`, statuts actifs

### Administration
- `POST /api/reload` - Hot-reload du système
- `GET /health` - Santé de l'application

## 💡 Exemples d'Usage

### Via API (JSON Body)
```bash
curl -X POST "http://localhost:8000/api/workflows/execute/lead_nurturing" \
  -H "Content-Type: application/json" \
  -d '{"data": {"name": "John Doe", "email": "john@example.com"}}'
```

### Via Déclenchement Manuel (URL simple)
```bash
# Déclencher avec paramètres d'URL - plus simple !
curl "http://localhost:8000/api/workflows/trigger/lead_nurturing?name=John+Doe&email=john@example.com&priority=high"
```

### Via Webhook (Paramètres URL + JSON)
```bash
# Paramètres d'URL combinés au JSON body
curl -X POST "http://localhost:8000/api/webhooks/lead_nurturing?source=website&priority=high" \
  -H "Content-Type: application/json" \
  -d '{"name": "Jane Doe", "email": "jane@example.com"}'

# Ou juste avec paramètres d'URL
curl -X POST "http://localhost:8000/api/webhooks/lead_nurturing?name=Jane+Doe&email=jane@example.com&priority=high"
```

### Scheduler - Monitoring des Jobs ⏰
```bash
# Voir tous les jobs programmés
curl "http://localhost:8000/api/scheduler/jobs"

# Réponse exemple
[{
  "workflow_name": "newsletter_automation",
  "cron_expression": "0 9 * * 1-5",
  "next_run": "2024-01-15T09:00:00+00:00",
  "last_run": "2024-01-14T09:00:15",
  "active": true,
  "workflow_active": true
}]

# Contrôler l'exécution
curl -X POST "http://localhost:8000/api/workflows/toggle/newsletter_automation"  # Pause/Resume
curl -X POST "http://localhost:8000/api/reload"  # Reprogrammer tous les jobs
```

## 🔥 Fonctionnalités Clés

- **🔄 Auto-Discovery** : Workflows et interfaces détectés automatiquement
- **🌐 Multi-Interface** : Dashboard central + interfaces spécialisées
- **🔧 Hot-Reload** : Modifications sans redémarrage
- **📊 Monitoring** : Logs, stats, historique complet
- **⚡ Triple Triggers** : 
  - **⏰ Scheduler** : Planification automatique avec expressions cron + persistence BDD
  - **🔗 Webhook** : Support paramètres URL + JSON body combinés
  - **👆 Manuel** : Déclenchement simple via GET avec paramètres URL
- **🧩 Modulaire** : Ajout de composants sans modification du core
- **🛡️ Sécurité** : Vérifications automatiques workflow/outils actifs avant exécution

## 🎯 Cas d'Usage

- **Marketing** : Lead nurturing, campaigns
- **Sales** : Client onboarding, suivi
- **Operations** : Notifications, reporting
- **Custom** : N'importe quel processus métier

Architecture pensée pour **maximum de flexibilité** avec **minimum de code** !