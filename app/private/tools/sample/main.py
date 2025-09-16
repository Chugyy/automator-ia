from app.private.tools.base import BaseTool
from typing import Dict, Any, List

class ExampleTool(BaseTool):
    def __init__(self, profile: str = "DEFAULT", config: Dict[str, Any] = None):
        super().__init__(profile, config)
    
    def authenticate(self) -> bool:
        if not self.validate_config():
            return False
        
        try:
            api_key = self.config.get("api_key")
            if not api_key:
                return False
                
            self.authenticated = True
            return True
        except Exception:
            return False
    
    def execute(self, action: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        if not self.authenticated and not self.authenticate():
            return {"success": False, "error": "Authentication failed"}
        
        if action == "example_action":
            return self._example_action(params or {})
        elif action == "test_connection":
            return self._test_connection()
        
        return {"success": False, "error": f"Unknown action: {action}"}
    
    def get_available_actions(self) -> List[str]:
        return ["example_action", "test_connection"]
    
    def _example_action(self, params: Dict[str, Any]) -> Dict[str, Any]:
        message = params.get("message", "Hello World")
        return {
            "success": True, 
            "result": f"Example executed: {message}",
            "timestamp": "2024-01-01T00:00:00Z"
        }
    
    def _test_connection(self) -> Dict[str, Any]:
        return {
            "success": True,
            "result": "Connection test successful", 
            "config_valid": self.validate_config()
        }