Architecture actuelle

  1. Classe GoogleOAuthTool unifiée (oauth.py:370-575)
  - Gère tous les services Google (calendar, drive, sheets, etc.)
  - Authentication automatique dans le constructeur : self.authenticated = self.authenticate()
  - Scopes combinés intelligents pour éviter les re-authentifications

  2. Outils Google simplifiés
  - CalendarTool hérite de GoogleOAuthTool('calendar')
  - Plus besoin de dupliquer la logique OAuth dans chaque outil
  - Configuration automatique des credentials/tokens

  3. Configuration des profils
  {
    "credentials_file": "etc/secrets/google_credentials.json",
    "token_file": "etc/secrets/google_test_token.json"
  }

  Fonctionnement OAuth

  URL d'auth unifiée : /oauth/google/auth?service=calendar&profile=TEST

  Callback unifié : /oauth/google/callback

  Gestion des scopes :
  - Détection automatique des services utilisés par le profil
  - Scopes combinés pour éviter multiple auth
  - Ex: Si calendar + drive → demande les 2 sets de permissions

  Status OAuth :
  {
    "authenticated": true,
    "provider": "google",
    "scopes": ["calendar", "drive"],
    "auth_url": "/oauth/google/auth?service=calendar&profile=TEST"
  }

  Le workflow calendar_scheduler utilise maintenant cette architecture simplifiée avec reconnexion
  automatique si l'auth manque.