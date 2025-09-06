# Configuration de l'API

Ce dossier contient les fichiers de configuration de l'API.

## Fichiers

- `config.py` : Configuration principale de l'application
- `logger.py` : Configuration du système de logs
- `.env` : Variables d'environnement (à créer)

## Utilisation

### Variables d'environnement

Créez un fichier `.env` à la racine du dossier config avec les variables suivantes :

```
APP_NAME=MonSuperAPI
DEBUG=True
HOST=127.0.0.1
PORT=8000
```

### Configuration dans votre code

Pour utiliser la configuration dans votre code :

```python
from config.common.config import settings

# Accès aux variables de configuration
app_name = settings.app_name
debug_mode = settings.debug
host = settings.host
port = settings.port
```

### Utilisation du logger

Pour utiliser le système de logs :

```python
from config.common.logger import logger

# Exemples d'utilisation
logger.debug("Message de debug")
logger.info("Information importante")
logger.warning("Attention")
logger.error("Une erreur s'est produite")
```

### Personnalisation

Vous pouvez modifier les valeurs par défaut dans `config.py` ou les surcharger avec des variables d'environnement. 