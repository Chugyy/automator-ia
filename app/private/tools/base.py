from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import os
import json

class BaseTool(ABC):
    """Interface commune pour tous les outils"""
    
    def __init__(self, profile: str = "DEFAULT", config: Dict[str, Any] = None, free_mode: bool = False):
        self.profile = profile
        self.tool_name = self.__class__.__name__.replace("Tool", "").upper()
        self.free_mode = free_mode
        self.config = config or self._load_config()
        self.authenticated = False
    
    def _load_config(self) -> Dict[str, Any]:
        """Charge la configuration depuis config.json et .env selon le mode"""
        if self.free_mode and hasattr(self, '_free_config'):
            return self._free_config
        
        config_schema = self._load_config_schema()
        if self.free_mode:
            return config_schema.get('optional_params', {})
        
        return self._load_profile_config(config_schema)
    
    def _load_config_schema(self) -> Dict[str, Any]:
        """Charge le schéma depuis config.json"""
        tool_dir = os.path.dirname(os.path.abspath(__file__))
        current_tool_dir = f"{tool_dir}/{self.tool_name.lower()}"
        config_file = f"{current_tool_dir}/config.json"
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        
        return {"required_params": [], "optional_params": {}}
    
    def _load_profile_config(self, config_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Charge la configuration depuis config/.env"""
        config = config_schema.get('optional_params', {}).copy()
        prefix = f"{self.tool_name}_{self.profile}_"
        
        # Chemin vers le fichier .env central
        config_env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "config", ".env")
        
        if os.path.exists(config_env_file):
            from dotenv import dotenv_values
            env_vars = dotenv_values(config_env_file)
            
            for key, value in env_vars.items():
                if key.startswith(prefix):
                    config_key = key[len(prefix):].lower()
                    config[config_key] = value
        
        # Aussi vérifier les variables d'environnement système
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lower()
                config[config_key] = value
        
        return config
    
    def set_free_config(self, config: Dict[str, Any]) -> None:
        """Définit la configuration en mode libre"""
        self._free_config = config
        self.config = config
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Retourne le schéma de configuration"""
        return self._load_config_schema()
    
    def validate_config(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """Valide la configuration actuelle ou fournie"""
        config_to_validate = config or self.config
        schema = self._load_config_schema()
        
        for param in schema.get('required_params', []):
            if param not in config_to_validate or not config_to_validate[param]:
                return False
        return True
    
    @abstractmethod
    def authenticate(self) -> bool:
        """Authentifie l'outil avec ses credentials"""
        pass
    
    @abstractmethod
    def execute(self, action: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Exécute une action avec les paramètres donnés"""
        pass
    
    @abstractmethod
    def get_available_actions(self) -> List[str]:
        """Retourne la liste des actions disponibles"""
        pass
    
    def is_authenticated(self) -> bool:
        """Vérifie si l'outil est authentifié"""
        return self.authenticated