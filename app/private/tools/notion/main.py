from typing import Dict, Any, List
from ..base import BaseTool
from .config import NotionConfig

class NotionTool(BaseTool):
    """Outil Notion pour créer des pages et gérer les bases de données"""
    
    def __init__(self, profile: str = "DEFAULT", config: Dict[str, Any] = None):
        super().__init__(profile, config)
        default_config = NotionConfig.get_default_config()
        default_config.update(self.config)
        self.config = default_config
    
    def authenticate(self) -> bool:
        """Authentifie avec l'API token Notion"""
        if not NotionConfig.validate(self.config):
            return False
        self.authenticated = True
        return True
    
    def execute(self, action: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Exécute une action Notion"""
        params = params or {}
        
        if not self.is_authenticated():
            return {"error": "Not authenticated"}
        
        if action == "create_page":
            return self._create_page(params)
        elif action == "update_database":
            return self._update_database(params)
        elif action == "get_pages":
            return self._get_pages(params)
        else:
            return {"error": f"Action {action} not supported"}
    
    def get_available_actions(self) -> List[str]:
        """Actions disponibles"""
        return ["create_page", "update_database", "get_pages"]
    
    def _create_page(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Crée une nouvelle page"""
        title = params.get('title', 'Untitled')
        content = params.get('content', '')
        database_id = params.get('database_id', self.config.get('database_id'))
        
        print(f"[NOTION-{self.profile}] Creating page: {title}")
        
        return {
            "status": "success",
            "message": f"Page '{title}' created",
            "data": {"title": title, "id": "page_123", "database_id": database_id}
        }
    
    def _update_database(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Met à jour une entrée dans une base de données"""
        database_id = params.get('database_id', self.config.get('database_id'))
        page_id = params.get('page_id')
        properties = params.get('properties', {})
        
        print(f"[NOTION-{self.profile}] Updating database entry: {page_id}")
        
        return {
            "status": "success",
            "data": {"database_id": database_id, "page_id": page_id, "properties": properties}
        }
    
    def _get_pages(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Récupère les pages d'une base de données"""
        database_id = params.get('database_id', self.config.get('database_id'))
        filter_params = params.get('filter', {})
        
        pages = [
            {"id": "page_1", "title": "Lead - John Doe", "status": "New"},
            {"id": "page_2", "title": "Lead - Jane Smith", "status": "Contacted"}
        ]
        
        return {
            "status": "success",
            "data": {"database_id": database_id, "pages": pages}
        }