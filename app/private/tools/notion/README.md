# Notion Tool

Outil pour intégrer Notion dans votre application.

## Configuration

### Variables d'environnement

Copiez le fichier `.env` et configurez vos credentials :

```bash
# Profil par défaut
NOTION_PROFILE_DEFAULT_TOKEN=your_notion_token_here
NOTION_PROFILE_DEFAULT_DATABASE_ID=your_database_id_here

# Profil de production
NOTION_PROFILE_PROD_TOKEN=prod_token_here
NOTION_PROFILE_PROD_DATABASE_ID=prod_database_id_here
```

### Obtenir un token Notion

1. Allez sur [Notion Developers](https://developers.notion.com/)
2. Créez une nouvelle intégration
3. Copiez le token d'intégration
4. Partagez vos bases de données avec l'intégration

## Utilisation

```python
from tools.notion.main import NotionTool

# Utilisation avec profil par défaut
notion = NotionTool()
if notion.authenticate():
    result = notion.execute("create_page", {
        "title": "Ma nouvelle page",
        "content": "Contenu de la page"
    })

# Utilisation avec profil spécifique
notion_prod = NotionTool(profile="PROD")
if notion_prod.authenticate():
    pages = notion_prod.execute("get_pages", {
        "database_id": "your_db_id"
    })
```

## Actions disponibles

- `create_page` : Crée une nouvelle page
- `update_database` : Met à jour une entrée
- `get_pages` : Récupère les pages d'une base de données