# Conception d'un workflow de A à Z

## Analyse de la demande

Identifier ce que l'utilisateur souhaite obtenir.

Recenser les outils disponibles et voir lesquels correspondent à la demande.

Faire le lien entre besoins exprimés par l'utilisateur et moyens techniques disponibles.

## Sélection des outils

Si plusieurs options sont possibles, demander à l'utilisateur de choisir l'outil le plus pertinent.

Poser des questions simples et courtes pour limiter les frictions.

## Analyse technique des outils choisis

Examiner le config.json pour comprendre la structure et les fonctions de chaque outil.

Définir :
- les étapes d'utilisation,
- les variables d'entrée et de sortie,
- les paramètres requis et facultatifs,
- les valeurs par défaut à prévoir.

## Configuration des outils (NOUVELLE APPROCHE v1)

### Principe : Configuration dans le workflow, pas dans l'outil

Trois modes de configuration supportés :

1. **Profils .env** (variables sensibles pré-configurées)
   ```python
   tool = NotionTool(profile="TEST")  # Lit NOTION_TEST_TOKEN dans .env
   ```

2. **Configuration directe** (données dynamiques via webhook)
   ```python
   tool = NotionTool(config={"token": data.get("notion_token")})
   ```

3. **Inputs manuels** (via interface frontend)
   ```python
   def get_required_inputs() -> List[Dict[str, Any]]:
       return [
           {
               "name": "openai_key",
               "type": "password", 
               "label": "Clé OpenAI",
               "required": True,
               "description": "Votre clé API OpenAI"
           }
       ]
   ```

### Template de workflow standardisé

```python
from typing import Dict, Any, List
from app.private.tools import get_tool_class

def execute(data: Dict[str, Any] = None, tools: Dict[str, Any] = None) -> Dict[str, Any]:
    # Configuration centralisée des outils
    tools_config = build_tools_config(data)
    
    # Initialisation des outils
    tools_instances = {}
    for tool_name, config in tools_config.items():
        tool_class = get_tool_class(tool_name)
        if "profile" in config:
            tools_instances[tool_name] = tool_class(profile=config["profile"])
        else:
            tools_instances[tool_name] = tool_class(config=config["config"])
    
    # Logique métier
    return execute_business_logic(tools_instances, data)

def build_tools_config(data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
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
    """Définit les inputs manuels requis (optionnel)"""
    return []

def get_tools_profiles() -> Dict[str, str]:
    """Définit les profils par défaut ou inputs manuels"""
    return {
        "notion": "TEST",              # Via profil .env
        "openai": "INPUT_OPENAI_KEY",  # Via input manuel  
        "email": "DEFAULT"             # Via profil .env
    }
```

### Configuration workflow (config.json)

Ajouter `inputs_schema` et `tools_profiles` au config.json :

```json
{
    "name": "Example Workflow",
    "description": "Workflow d'exemple",
    "inputs_schema": [
        {
            "name": "openai_key",
            "type": "password",
            "label": "Clé OpenAI", 
            "required": true,
            "description": "Votre clé API OpenAI"
        }
    ],
    "tools_profiles": {
        "notion": "TEST",
        "openai": "INPUT_OPENAI_KEY",
        "email": "DEFAULT"
    }
}
```

## Conception du workflow

Construire le workflow en intégrant les outils sélectionnés avec la nouvelle architecture.

Stockage :
- Workflow définitif → dossier workflow,
- Workflow temporaire → dossier TEMP.

**Structure de fichier workflow :**
```
workflows/nom_workflow/
├── main.py           # Fonctions execute(), get_required_inputs(), get_tools_profiles()
├── config.json       # Configuration avec inputs_schema et tools_profiles
└── README.md         # Documentation (optionnel)
```

## Validation et test

### Scripts de test temporaires

Créer des scripts dans `/temp/` avec pattern standardisé :

```python
#!/usr/bin/env python3
import sys, os
from pathlib import Path

# Ajout path système
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

from app.private.tools.notion.main import NotionTool
from dotenv import load_dotenv

def main():
    load_dotenv("backend/config/.env")
    config = {"token": os.getenv("NOTION_TEST_TOKEN")}
    
    tool = NotionTool(config=config)
    if tool.authenticate():
        result = tool.execute("list_pages", {"limit": 5})
        print(f"✓ Test réussi: {result}")
    else:
        print("✗ Test échoué")

if __name__ == "__main__":
    main()
```

### Validation workflow

1. Tester le fichier : cohérence des variables, exactitude des calculs
2. Vérifier les inputs manuels si définis
3. Tester avec différents modes de configuration
4. Intégrer feedbacks au fur et à mesure
5. Vérifier auprès de l'utilisateur avant finalisation

## Définition du déclencheur

Déterminer comment le workflow sera exécuté :
- **Webhook** : JSON complet avec données dynamiques
- **Manuel via interface** : Formulaire avec inputs requis  
- **Planification** : Intervalles réguliers, horaires prédéfinis
- **Événement spécifique** : Trigger automatique

### Modes d'exécution supportés

1. **Via webhook** (données complètes)
2. **Via interface web** (inputs manuels + profils)
3. **Via API directe** (configuration mixte)
4. **Via planificateur** (profils uniquement)