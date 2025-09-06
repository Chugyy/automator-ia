from typing import Dict, Any
import json
import os

class NotionConfig:
    """Configuration pour l'outil Notion"""
    
    @staticmethod
    def get_default_config() -> Dict[str, Any]:
        """Retourne la configuration par défaut"""
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                schema = json.load(f)
                return schema.get('optional_params', {})
        except Exception:
            return {
                'database_id': None,
                'page_size': 100,
                'timeout': 30
            }
    
    @staticmethod
    def validate(config: Dict[str, Any]) -> bool:
        """Valide la configuration Notion"""
        if not config:
            return False
        
        # Le token est requis pour l'authentification
        if not config.get('token'):
            return False
        
        return True