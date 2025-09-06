from typing import Dict, Any, List
from ..base import BaseTool
from .config import SlackConfig

class SlackTool(BaseTool):
    """Outil Slack pour envoyer des messages et récupérer des données"""
    
    def __init__(self, profile: str = "DEFAULT", config: Dict[str, Any] = None):
        super().__init__(profile, config)
        default_config = SlackConfig.get_default_config()
        default_config.update(self.config)
        self.config = default_config
    
    def authenticate(self) -> bool:
        """Authentifie avec le token Slack"""
        if not SlackConfig.validate(self.config):
            return False
        self.authenticated = True
        return True
    
    def execute(self, action: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Exécute une action Slack"""
        params = params or {}
        
        if not self.is_authenticated():
            return {"error": "Not authenticated"}
        
        if action == "post_message":
            return self._post_message(params)
        elif action == "get_messages":
            return self._get_messages(params)
        elif action == "create_channel":
            return self._create_channel(params)
        else:
            return {"error": f"Action {action} not supported"}
    
    def get_available_actions(self) -> List[str]:
        """Actions disponibles"""
        return ["post_message", "get_messages", "create_channel"]
    
    def _post_message(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Poste un message dans un canal"""
        channel = params.get('channel', self.config.get('channel'))
        text = params.get('text', '')
        
        print(f"[SLACK-{self.profile}] Posting to {channel}: {text}")
        
        return {
            "status": "success",
            "message": f"Message posted to {channel}",
            "data": {"channel": channel, "text": text}
        }
    
    def _get_messages(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Récupère les messages d'un canal"""
        channel = params.get('channel', self.config.get('channel'))
        limit = params.get('limit', 10)
        
        messages = [
            {"user": "john", "text": "New lead from website", "timestamp": "2024-01-01T10:00:00Z"},
            {"user": "alice", "text": "Priority: High", "timestamp": "2024-01-01T10:01:00Z"}
        ]
        
        return {
            "status": "success", 
            "data": {"channel": channel, "messages": messages[:limit]}
        }
    
    def _create_channel(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Crée un nouveau canal"""
        name = params.get('name', 'new-channel')
        private = params.get('private', False)
        
        print(f"[SLACK-{self.profile}] Creating {'private' if private else 'public'} channel: {name}")
        
        return {
            "status": "success",
            "data": {"channel": name, "private": private}
        }