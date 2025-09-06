# Slack Tool

Outil pour intégrer Slack dans votre application.

## Configuration

### Variables d'environnement

Copiez le fichier `.env` et configurez vos credentials :

```bash
# Profil par défaut
SLACK_PROFILE_DEFAULT_TOKEN=your_slack_token_here
SLACK_PROFILE_DEFAULT_CHANNEL=#general

# Profil marketing
SLACK_PROFILE_MARKETING_TOKEN=marketing_token_here
SLACK_PROFILE_MARKETING_CHANNEL=#marketing
```

### Obtenir un token Slack

1. Allez sur [Slack API](https://api.slack.com/apps)
2. Créez une nouvelle app
3. Dans "OAuth & Permissions", ajoutez les scopes nécessaires
4. Copiez le "Bot User OAuth Token"

## Utilisation

```python
from tools.slack.main import SlackTool

# Utilisation avec profil par défaut
slack = SlackTool()
if slack.authenticate():
    result = slack.execute("post_message", {
        "channel": "#general",
        "text": "Hello World!"
    })

# Utilisation avec profil spécifique
slack_marketing = SlackTool(profile="MARKETING")
if slack_marketing.authenticate():
    messages = slack_marketing.execute("get_messages", {
        "channel": "#marketing",
        "limit": 50
    })
```

## Actions disponibles

- `post_message` : Envoie un message dans un canal
- `get_messages` : Récupère les messages d'un canal
- `create_channel` : Crée un nouveau canal