# Build System

Système de build automatisé qui consolide les dépendances et configurations des outils selon le mode dev/prod.

## Structure

```
backend/
├── .env                               # VERSION=dev/prod + config principale
├── .env.built                         # Variables consolidées (auto-généré)
├── app/
│   ├── build.py                       # Script de build (lancé avant main.py)
│   └── private/tools/
│       ├── slack/
│       │   ├── requirements.txt       # Dépendances Slack
│       │   ├── .env.SLACK_MARKETING   # Profil Marketing
│       │   └── .env.SLACK_SUPPORT     # Profil Support
│       ├── calendar/
│       │   ├── requirements.txt       # Dépendances Calendar
│       │   ├── .env.CALENDAR_PERSONAL # Profil Personnel
│       │   └── .env.CALENDAR_WORK     # Profil Travail
│       └── date/
│           └── .env.DATE_DEFAULT      # Profil par défaut (aucune config)
├── config/
│   ├── common.py                      # Configuration partagée
│   ├── built.py                       # Gestion VERSION et .env.built
│   └── requirements-built.txt         # Dépendances consolidées
```

## Modes de fonctionnement

### Mode Développement (VERSION=dev)
- Les outils lisent **directement** leurs fichiers `.env.{OUTIL}_{PROFIL}`
- Pas de build automatique
- Modification des configurations en temps réel

### Mode Production (VERSION=prod)
- Build automatique au démarrage avec `app/build.py`
- Les outils lisent depuis `.env.built` consolidé
- Variables système prioritaires sur `.env.built`

## Créer des profils d'outils

### 1. Structure d'un outil

```
app/private/tools/mon_outil/
├── main.py                    # Classe MonOutilTool(BaseTool)
├── requirements.txt           # Dépendances spécifiques (optionnel)
├── .env.MON_OUTIL_PROFIL1    # Profil 1
├── .env.MON_OUTIL_PROFIL2    # Profil 2
└── src/                       # Code de l'outil
    └── core.py
```

### 2. Format des fichiers .env

**Nom**: `.env.{OUTIL}_{PROFIL}` (tout en majuscules)

Exemple `.env.SLACK_MARKETING` :
```bash
# Token d'accès Slack Marketing
TOKEN=xoxb-marketing-token-here
CHANNEL_DEFAULT=#marketing
WEBHOOK_URL=https://hooks.slack.com/marketing
```

Exemple `.env.CALENDAR_PERSONAL` :
```bash
# Google Calendar Personnel
API_KEY=your-google-api-key
CALENDAR_ID=personal@gmail.com
TIMEZONE=Europe/Paris
```

### 3. Outils sans configuration

Certains outils (comme `date`) n'ont pas besoin de configuration.
Créer quand même un fichier vide pour la cohérence :

`.env.DATE_DEFAULT` :
```bash
# Outil Date - Aucune configuration requise
```

### 4. Utilisation dans le code

```python
from app.private.tools.slack.main import SlackTool

# En dev: lit directement .env.SLACK_MARKETING
# En prod: lit depuis .env.built (SLACK_MARKETING_TOKEN=...)
slack = SlackTool(profile="MARKETING")
print(slack.config['token'])  # Token automatiquement chargé
```

## Utilisation

### Build Complet
```bash
python build.py
```
- Scan tous les outils
- Consolide les requirements.txt → config/requirements-built.txt
- Installe les dépendances
- Consolide les .env.* → .env.built

### Build Partiel
```bash
# Seulement les dépendances
python build.py --requirements-only

# Seulement les variables d'environnement
python build.py --env-only

# Aide
python build.py --help
```

## Fonctionnement

### 1. Scan Automatique
Le build system découvre automatiquement tous les outils dans `app/private/tools/`.

### 2. Consolidation Requirements
- Lit tous les `requirements.txt` des outils
- Résout les conflits de versions (garde la plus élevée)
- Génère `config/requirements-built.txt`

### 3. Consolidation Variables
- Scan tous les `.env.{OUTIL}_{PROFIL}` dans chaque outil
- Format de sortie: `{OUTIL}_{PROFIL}_{VARIABLE}`
- Génère `.env.built`

### 4. Usage dans le Code
```python
from app.private.tools.slack.main import SlackTool

# Les outils lisent automatiquement depuis .env.built
slack = SlackTool(profile="MARKETING")
print(slack.config['token'])  # xoxb-marketing-token-example
```

## Workflow Développeur

1. **Créer un profil** : `.env.SLACK_MARKETING` dans `app/private/tools/slack/`
2. **Ajouter dépendances** : `requirements.txt` dans le dossier outil
3. **Build** : `python build.py`
4. **Développer** : Les outils utilisent automatiquement les configs

## Git

Les fichiers générés sont automatiquement ignorés :
- `.env.built`
- `config/requirements-built.txt`

Les profils `.env.*` sont également ignorés (credentials sensibles).

## Déploiement Production

En production, les variables peuvent être définies directement dans l'environnement système :
```bash
export SLACK_MARKETING_TOKEN=xoxb-prod-token
export CALENDAR_PERSONAL_API_KEY=prod-api-key
```

BaseTool utilise cette hiérarchie :
1. Variables système (production)
2. `.env.built` (développement)

## Ajouter un Nouvel Outil

1. Créer dossier `app/private/tools/mon_outil/`
2. Ajouter `requirements.txt` si nécessaire
3. Créer profils `.env.MON_OUTIL_PROFIL`
4. Lancer `python build.py`

Le système détecte automatiquement le nouvel outil !