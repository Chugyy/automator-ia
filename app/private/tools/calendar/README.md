# Calendar Tool

Outil pour intégrer Google Calendar dans votre application.

## Configuration

### Variables d'environnement

Copiez le fichier `.env` et configurez vos credentials :

```bash
# Profil par défaut
CALENDAR_PROFILE_DEFAULT_TOKEN_FILE=token.json
CALENDAR_PROFILE_DEFAULT_CREDENTIALS_FILE=credentials.json
CALENDAR_PROFILE_DEFAULT_CALENDAR_ID=primary
CALENDAR_PROFILE_DEFAULT_TIMEZONE=Europe/Paris
CALENDAR_PROFILE_DEFAULT_SCOPES_READ_ONLY=true
```

### Obtenir les credentials Google Calendar

1. Allez sur [Google Cloud Console](https://console.cloud.google.com/)
2. Activez l'API Google Calendar
3. Créez des credentials OAuth 2.0
4. Téléchargez le fichier `credentials.json`
5. Placez-le dans votre répertoire de projet

## Utilisation

```python
from tools.calendar.main import CalendarTool

# Utilisation avec profil par défaut
calendar = CalendarTool()
if calendar.authenticate():
    result = calendar.execute("list_events", {
        "count": 10
    })

# Création d'événement
result = calendar.execute("create_event", {
    "summary": "Réunion importante",
    "start_time": "2024-07-01T10:00:00",
    "end_time": "2024-07-01T11:00:00",
    "description": "Description de la réunion"
})
```

## Actions disponibles

- `list_events` : Liste les événements à venir
- `create_event` : Crée un nouvel événement
- `update_event` : Met à jour un événement existant
- `delete_event` : Supprime un événement

## Requirements

- google-api-python-client
- google-auth
- google-auth-oauthlib