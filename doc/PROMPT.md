# Instructions LLM - Développement Workflow Platform

Guide pour automatiser le développement avec un LLM sur cette codebase.

## 🎯 Rôle et Architecture

### Responsabilité LLM
Vous êtes un **développeur senior minimaliste** qui assiste sur cette plateforme d'automatisation. Votre zone d'intervention prioritaire : **`app/private/`**.

### Architecture Critique
```
backend/
├── app/
│   ├── common/          # ❌ NE PAS MODIFIER (système core)
│   │   ├── database/    # Base SQLite + ORM
│   │   ├── engine.py    # Moteur exécution workflows  
│   │   ├── services/    # OAuth, scheduler, tools
│   │   └── interfaces/  # Dashboard principal
│   └── private/         # ✅ ZONE LLM (modifications autorisées)
│       ├── tools/       # Outils utilisateur
│       ├── workflows/   # Workflows métier
│       ├── interfaces/  # Interfaces personnalisées
│       └── temp/        # Scripts temporaires LLM
```

**Règle absolue** : Concentrez-vous sur `app/private/`. Évitez de modifier `app/common/` sauf demande explicite.

## 🔐 Gestion Profils & OAuth

### Système de Profils

**Concept** : Un même outil peut avoir plusieurs configurations (TEST, PROD, PERSONAL).

**Format variable** : `{OUTIL}_{PROFIL}_{PARAMETRE}`

**Exemple** :
```bash
# Dans config/.env
GOOGLE_CALENDAR_TEST_CREDENTIALS_FILE=etc/secrets/google_test_credentials.json
GOOGLE_CALENDAR_TEST_TOKEN_FILE=etc/secrets/google_test_token.json
GOOGLE_CALENDAR_WORK_CREDENTIALS_FILE=etc/secrets/google_work_credentials.json
GOOGLE_CALENDAR_WORK_TOKEN_FILE=etc/secrets/google_work_token.json
```

### Pattern Outil avec Profils
```python
# L'outil charge automatiquement les variables selon le profil
calendar_test = CalendarTool(profile="TEST")    # Uses GOOGLE_CALENDAR_TEST_*
calendar_work = CalendarTool(profile="WORK")    # Uses GOOGLE_CALENDAR_WORK_*
```

### OAuth Google Unifié

**Système centralisé** pour tous les services Google.

#### URLs d'authentification :
```
/oauth/google/auth?service=calendar&profile=TEST
/oauth/google/auth?service=drive&profile=WORK  
/oauth/google/auth?service=sheets&profile=PERSONAL
```

#### Vérification statut OAuth :
```bash
curl http://localhost:8000/api/oauth/status/google_calendar?profile=TEST
```

#### Gestion des erreurs OAuth dans workflows :
```python
def execute_business_logic(tools: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    calendar_tool = tools.get("google_calendar")
    
    if not calendar_tool.authenticate():
        profile = get_tools_profiles().get("google_calendar", "TEST")
        return {
            "success": False, 
            "error": f"Calendar authentication required for profile '{profile}'",
            "auth_required": True,
            "auth_url": f"/oauth/google/auth?service=calendar&profile={profile}",
            "profile": profile
        }
```

### Pattern de Configuration Workflow
```python
def get_tools_profiles() -> Dict[str, str]:
    """Définit les profils par défaut"""
    return {
        "google_calendar": "TEST",     # Profile pour cet environnement
        "notion": "WORK",
        "slack": "MARKETING"
    }
```

## 🧪 Gestion Fichiers Temporaires

### Usage et Cycle de Vie

Les fichiers temporaires permettent de **tester directement** sans créer d'outils permanents.

**Cycle** :
1. **Création** dans `app/private/temp/`
2. **Exécution** avec `python -m app.private.temp.nom_fichier`
3. **Validation** des résultats
4. **Nettoyage** (suppression ou conservation selon besoin)

### Template Standardisé
```python
#!/usr/bin/env python3
"""
Test temporaire : [Description de ce que fait le script]
Créé le : [Date]
"""
import sys
import os
from pathlib import Path

# === SETUP PROJET ===
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))
os.chdir(project_root)

# === IMPORTS ===
from app.private.tools.google_calendar.main import CalendarTool
from dotenv import load_dotenv
from config.logger import logger

def main():
    """Fonction principale de test"""
    try:
        # Charger l'environnement
        load_dotenv("backend/config/.env")
        
        # Initialiser l'outil avec profil
        tool = CalendarTool(profile="TEST")
        
        # Test authentification
        if not tool.authenticate():
            print("❌ Authentication failed")
            status = tool.get_oauth_status()
            print(f"🔗 Auth URL: {status.get('auth_url')}")
            return
        
        print("✅ Authentication successful")
        
        # === TEST DE L'ACTION ===
        result = tool.execute("list_events", {"count": 3})
        
        if result.get("status") == "success":
            events = result.get("data", {}).get("events", [])
            print(f"✅ Found {len(events)} events")
            for event in events:
                print(f"  - {event.get('summary', 'No title')}")
        else:
            print(f"❌ Error: {result.get('error')}")
            
    except Exception as e:
        logger.error(f"Test failed: {e}")
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    main()
```

### Conventions de Nommage
```python
# Scripts temporaires
test_calendar_basic.py          # Test simple
test_workflow_newsletter.py     # Test workflow complet
debug_oauth_calendar.py         # Debug spécifique
validate_tool_setup.py          # Validation configuration
```

### Bonnes Pratiques
- **Toujours** des chemins relatifs
- **Prefix descriptif** (`test_`, `debug_`, `validate_`)
- **Documentation** inline du but du script
- **Gestion d'erreurs** explicite
- **Nettoyage** après validation

## 🔍 Méthode Socratique de Conception

### Questions Préparatoires

Avant de créer un workflow/outil, **toujours** se poser ces questions :

#### Phase 1: Analyse du Besoin
1. **Problème** : Quel problème exact résout ce workflow ?
2. **Outils existants** : Quels outils de `app/private/tools/` peuvent être réutilisés ?
3. **Données** : Quelles données d'entrée sont nécessaires ?
4. **Sorties** : Quel résultat attendu ?

#### Phase 2: Architecture
1. **Profils** : Quels profils d'outils utiliser (TEST, PROD, WORK) ?
2. **Authentification** : Quels outils nécessitent OAuth ?
3. **Inputs manuels** : L'utilisateur doit-il saisir des données ?
4. **Déclencheurs** : Manuel, webhook, ou planifié ?

#### Phase 3: Validation
1. **Test unitaire** : Comment tester chaque outil individuellement ?
2. **Test intégration** : Comment tester le workflow complet ?
3. **Scénarios d'échec** : Que se passe-t-il si un outil échoue ?
4. **Monitoring** : Comment tracer l'exécution ?

### Hypothèses à Valider

Avant l'implémentation, formuler des hypothèses :

```python
# Hypothèse 1: Le profil TEST du calendar est configuré
# Validation: Créer test_calendar_auth.py
# Résultat attendu: Authentification réussie

# Hypothèse 2: L'API externe répond en < 30s
# Validation: Créer test_api_timeout.py  
# Résultat attendu: Réponse dans les temps

# Hypothèse 3: Le workflow peut traiter 100 événements
# Validation: Créer test_workflow_load.py
# Résultat attendu: Traitement sans erreur
```

### Expériences de Vérification

Pour chaque hypothèse, créer un script de test dans `temp/` :

```python
# test_hypothesis_calendar_auth.py
def test_calendar_auth():
    """Vérifie que le profil TEST Calendar est configuré"""
    tool = CalendarTool(profile="TEST")
    assert tool.authenticate(), "Calendar TEST profile should be configured"
    print("✅ Hypothesis validated: Calendar TEST profile works")

# test_hypothesis_api_performance.py  
def test_api_performance():
    """Vérifie les performances de l'API"""
    import time
    start = time.time()
    tool = MyTool(profile="TEST")
    result = tool.execute("search", {"query": "test"})
    duration = time.time() - start
    assert duration < 30, f"API too slow: {duration}s"
    print(f"✅ Hypothesis validated: API responds in {duration:.2f}s")
```

## 🔧 Patterns de Développement

### Environnement Virtuel

**Toujours** activer `.venv` avant toute commande :
```bash
source backend/.venv/bin/activate  # Une seule fois par session
python -m app.main                 # Lancement correct
```

### Exécution avec python -m

**JAMAIS** de chemins absolus. **TOUJOURS** `python -m` :
```bash
# ✅ Correct
python -m app.main
python -m app.private.temp.test_calendar
python -m app.build

# ❌ Incorrect  
python /absolute/path/to/main.py
python app/main.py
./backend/app/main.py
```

### Structure de Tests

**Tests permanents** : `app/tests/`
```python
# app/tests/test_calendar_tool.py
import pytest
from app.private.tools.google_calendar.main import CalendarTool

def test_calendar_authentication():
    tool = CalendarTool(profile="TEST")
    assert tool.authenticate()
```

**Tests temporaires LLM** : `app/private/temp/`
```python
# app/private/temp/test_new_feature.py
# Script ponctuel pour valider une fonctionnalité
```

### Gestion d'Erreurs

Pattern uniforme pour les outils :
```python
def execute(self, action: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    try:
        if action == "search":
            return self._search(params)
        return {"error": f"Action {action} not supported"}
    except Exception as e:
        logger.error(f"Error in {action}: {e}")
        return {"error": str(e)}
```

Pattern uniforme pour les workflows :
```python
def execute(data: Dict[str, Any] = None, tools: Dict[str, Any] = None) -> Dict[str, Any]:
    try:
        # Logique métier
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"Workflow error: {e}")
        return {"status": "error", "message": str(e)}
```

### Logging

```python
from config.logger import logger

# Niveaux appropriés
logger.info("Workflow started")           # Informations importantes
logger.debug("Processing item 1/10")      # Détails de débogage  
logger.warning("API slow response")       # Avertissements non bloquants
logger.error("Authentication failed")     # Erreurs fonctionnelles
```

## ⚠️ Anti-patterns et Erreurs à Éviter

### ❌ Modifications Interdites

```python
# ❌ Ne jamais modifier
app/common/engine.py          # Moteur central
app/common/services/          # Services système
app/common/database/          # Base de données
app/common/interfaces/dashboard/  # Dashboard principal
```

### ❌ Fichiers Doublons

```bash
# ❌ Ne jamais créer
calendar_tool_old.py
calendar_tool_backup.py  
calendar_tool_better.py
workflow_v1.py, workflow_v2.py
test_final.py, test_final_final.py
```

**Règle** : Éditer les fichiers existants, ne pas en créer de nouveaux.

### ❌ Chemins Absolus

```python
# ❌ Chemins absolus interdits
with open("/Users/hugo/project/config.json")
sys.path.append("/absolute/path")
os.chdir("/full/path/to/backend")

# ✅ Chemins relatifs autorisés
with open("config/config.json")
sys.path.append(str(Path(__file__).parent.parent))
os.chdir(Path(__file__).parent.parent)
```

### ❌ Fuites de Fichiers Temporaires

Après tests, **toujours** nettoyer :
```bash
# Supprimer les scripts de test ponctuels
rm app/private/temp/test_debug_oauth.py
rm app/private/temp/validate_setup.py

# Conserver seulement les scripts utiles long terme
```

### ❌ Variables d'Environnement Hardcodées

```python
# ❌ Hardcodé  
calendar = CalendarTool(config={
    "token_file": "/absolute/path/token.json",
    "api_key": "hardcoded_key_123"
})

# ✅ Via profils
calendar = CalendarTool(profile="TEST")  # Charge automatiquement les variables
```

### ❌ OAuth Mal Géré

```python
# ❌ Pas de gestion d'erreur OAuth
tool = CalendarTool(profile="TEST")
result = tool.execute("list_events")  # Échoue silencieusement

# ✅ Gestion complète OAuth
tool = CalendarTool(profile="TEST")
if not tool.authenticate():
    status = tool.get_oauth_status()
    print(f"Authentication required: {status.get('auth_url')}")
    return {"error": "Authentication required", "auth_url": status.get('auth_url')}
```

## 📋 Checklist Avant Implémentation

### ✅ Préparation
- [ ] Questions socratiques posées et répondues
- [ ] Outils existants identifiés
- [ ] Profils nécessaires définis  
- [ ] Variables d'environnement configurées
- [ ] OAuth configuré si nécessaire

### ✅ Développement
- [ ] Code dans `app/private/` uniquement
- [ ] Chemins relatifs utilisés
- [ ] `python -m` pour exécution
- [ ] Gestion d'erreurs implémentée
- [ ] Logging approprié ajouté

### ✅ Test
- [ ] Script temporaire créé dans `temp/`
- [ ] Test unitaire de chaque outil
- [ ] Test d'intégration du workflow
- [ ] Scénarios d'échec validés
- [ ] Nettoyage des fichiers temporaires

### ✅ Documentation
- [ ] Configuration claire dans `config.json`
- [ ] Exemples d'usage fournis
- [ ] Messages d'erreur explicites
- [ ] Instructions OAuth si nécessaire

---

**Philosophie** : Code minimaliste, lisible, testé. Chaque ligne doit avoir une justification claire.