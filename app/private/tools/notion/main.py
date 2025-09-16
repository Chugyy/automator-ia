from typing import Dict, Any, List, Optional
import requests
import time
import re
from ..base import BaseTool
from .config import NotionConfig

class NotionTool(BaseTool):
    """Modern Notion API tool using 2025-09-03 version with data sources"""
    
    NOTION_API_BASE = "https://api.notion.com/v1"
    NOTION_VERSION = "2025-09-03"
    RATE_LIMIT_DELAY = 0.33  # ~3 req/s
    
    def __init__(self, profile: str = "DEFAULT", config: Dict[str, Any] = None):
        super().__init__(profile, config)
        default_config = NotionConfig.get_default_config()
        incoming = self.config or {}
        default_config.update(incoming)
        self.config = default_config
        self._last_request_time = 0
    
    def authenticate(self) -> bool:
        """Authentifie avec l'API token Notion"""
        if not NotionConfig.validate(self.config):
            print(f"[auth] Config validation failed - token: {bool(self.config.get('token'))}")
            self.authenticated = False
            return False
        
        headers = self._get_headers()
        try:
            response = requests.get(f"{self.NOTION_API_BASE}/users/me", headers=headers)
            if response.status_code == 200:
                self.authenticated = True
                return True
            
            # Expose le vrai motif d'échec
            try:
                detail = response.json()
            except Exception:
                detail = response.text
            print(f"[auth] failed: {response.status_code} {detail}")
            self.authenticated = False
            return False
        except requests.RequestException as e:
            print(f"[auth] request exception: {e}")
            self.authenticated = False
            return False
    
    def execute(self, action: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Exécute une action Notion"""
        params = params or {}
        
        # Auto-auth si pas encore authentifié
        if not self.is_authenticated():
            if not self.authenticate():
                return {"error": "Authentication failed"}
        
        actions = {
            "search": self._search,
            "create_page": self._create_page,
            "update_page": self._update_page,
            "archive_page": self._archive_page,
            "query_data_source": self._query_data_source,
            "get_database": self._get_database,
            "get_data_source": self._get_data_source,
            "create_database": self._create_database,
            "create_data_source": self._create_data_source,
            "update_data_source": self._update_data_source,
            "get_page_from_url": self._get_page_from_url,
            "get_page_content": self._get_page_content,
            "update_page_content": self._update_page_content
        }
        
        if action not in actions:
            return {"error": f"Action {action} not supported"}
        
        return actions[action](params)
    
    def get_available_actions(self) -> List[str]:
        """Actions disponibles selon l'API 2025-09-03"""
        return [
            "search", "create_page", "update_page", "archive_page",
            "query_data_source", "get_database", "get_data_source",
            "create_database", "create_data_source", "update_data_source",
            "get_page_from_url", "get_page_content", "update_page_content"
        ]
    
    def _get_headers(self) -> Dict[str, str]:
        """Headers pour toutes les requêtes API"""
        return {
            "Authorization": f"Bearer {self.config['token']}",
            "Notion-Version": self.NOTION_VERSION,
            "Content-Type": "application/json"
        }
    
    def _rate_limit(self) -> None:
        """Gestion du rate limiting"""
        current_time = time.time()
        elapsed = current_time - self._last_request_time
        if elapsed < self.RATE_LIMIT_DELAY:
            time.sleep(self.RATE_LIMIT_DELAY - elapsed)
        self._last_request_time = time.time()
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute API request with rate limiting and error handling"""
        self._rate_limit()
        
        url = f"{self.NOTION_API_BASE}/{endpoint}"
        headers = self._get_headers()
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data)
            elif method == "PATCH":
                response = requests.patch(url, headers=headers, json=data)
            else:
                return {"error": f"Unsupported HTTP method: {method}"}
            
            if response.status_code == 429:
                time.sleep(1)
                return self._make_request(method, endpoint, data)
            
            response.raise_for_status()
            return {"status": "success", "data": response.json()}
            
        except requests.RequestException as e:
            return {"error": f"Request failed: {str(e)}"}
    
    def _search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search pages/databases"""
        query = params.get("query", "")
        filter_obj = params.get("filter", {})
        sort_obj = params.get("sort", {"timestamp": "last_edited_time", "direction": "descending"})
        page_size = params.get("page_size", self.config.get("page_size", 100))
        
        data = {
            "query": query,
            "page_size": page_size
        }
        if filter_obj:
            data["filter"] = filter_obj
        if sort_obj:
            data["sort"] = sort_obj
        
        return self._make_request("POST", "search", data)
    
    def _create_page(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create page in data source"""
        parent = params.get("parent")
        properties = params.get("properties", {})
        
        if not parent:
            return {"error": "Parent (data_source_id or page_id) required"}
        
        data = {
            "parent": parent,
            "properties": properties
        }
        
        return self._make_request("POST", "pages", data)
    
    def _update_page(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update page properties"""
        page_id = params.get("page_id")
        properties = params.get("properties", {})
        
        if not page_id:
            return {"error": "page_id required"}
        
        data = {"properties": properties}
        return self._make_request("PATCH", f"pages/{page_id}", data)
    
    def _archive_page(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Archive (delete) page"""
        page_id = params.get("page_id")
        
        if not page_id:
            return {"error": "page_id required"}
        
        data = {"archived": True}
        return self._make_request("PATCH", f"pages/{page_id}", data)
    
    def _query_data_source(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Query data source with filters and sorts"""
        data_source_id = params.get("data_source_id")
        filter_obj = params.get("filter")
        sorts = params.get("sorts")
        page_size = params.get("page_size", self.config.get("page_size", 100))
        start_cursor = params.get("start_cursor")
        
        if not data_source_id:
            return {"error": "data_source_id required"}
        
        data = {"page_size": page_size}
        if filter_obj:
            data["filter"] = filter_obj
        if sorts:
            data["sorts"] = sorts
        if start_cursor:
            data["start_cursor"] = start_cursor
        
        return self._make_request("POST", f"data_sources/{data_source_id}/query", data)
    
    def _get_database(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get database metadata and data sources"""
        database_id = params.get("database_id")
        
        if not database_id:
            return {"error": "database_id required"}
        
        return self._make_request("GET", f"databases/{database_id}")
    
    def _get_data_source(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get data source schema"""
        data_source_id = params.get("data_source_id")
        
        if not data_source_id:
            return {"error": "data_source_id required"}
        
        return self._make_request("GET", f"data_sources/{data_source_id}")
    
    def _create_database(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create database with initial data source"""
        parent = params.get("parent")
        title = params.get("title", [])
        initial_data_source = params.get("initial_data_source")
        
        if not parent or not initial_data_source:
            return {"error": "parent and initial_data_source required"}
        
        data = {
            "parent": parent,
            "title": title,
            "initial_data_source": initial_data_source
        }
        
        return self._make_request("POST", "databases", data)
    
    def _create_data_source(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create new data source in existing database"""
        parent = params.get("parent")
        name = params.get("name", "Untitled Data Source")
        properties = params.get("properties", {})
        
        if not parent:
            return {"error": "parent (database_id) required"}
        
        data = {
            "parent": parent,
            "name": name,
            "properties": properties
        }
        
        return self._make_request("POST", "data_sources", data)
    
    def _update_data_source(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update data source schema (add/modify/remove properties)"""
        data_source_id = params.get("data_source_id")
        properties = params.get("properties", {})
        
        if not data_source_id:
            return {"error": "data_source_id required"}
        
        data = {"properties": properties}
        return self._make_request("PATCH", f"data_sources/{data_source_id}", data)
    
    def _extract_page_id(self, url: str) -> str:
        """Extract page ID from Notion URL"""
        clean_url = url.split('?')[0]
        match = re.search(r'[0-9a-fA-F]{32}(?=$)', clean_url)
        if not match:
            raise ValueError("Page ID not found in URL")
        
        hex_id = match.group(0).lower()
        return f"{hex_id[:8]}-{hex_id[8:12]}-{hex_id[12:16]}-{hex_id[16:20]}-{hex_id[20:]}"
    
    def _get_page_from_url(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get page metadata from URL"""
        url = params.get("url")
        if not url:
            return {"error": "url required"}
        
        try:
            page_id = self._extract_page_id(url)
            return self._make_request("GET", f"pages/{page_id}")
        except ValueError as e:
            return {"error": str(e)}
    
    def _get_page_content(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get page content (blocks)"""
        url = params.get("url")
        page_id = params.get("page_id")
        
        if not page_id and url:
            try:
                page_id = self._extract_page_id(url)
            except ValueError as e:
                return {"error": str(e)}
        
        if not page_id:
            return {"error": "page_id or url required"}
        
        blocks = []
        start_cursor = None
        
        while True:
            endpoint = f"blocks/{page_id}/children"
            if start_cursor:
                endpoint += f"?start_cursor={start_cursor}"
            
            result = self._make_request("GET", endpoint)
            if result.get("error"):
                return result
            
            data = result.get("data", {})
            blocks.extend(data.get("results", []))
            
            if not data.get("has_more"):
                break
            
            start_cursor = data.get("next_cursor")
        
        return {"status": "success", "data": {"blocks": blocks}}
    
    def _update_page_content(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update page content by appending blocks"""
        url = params.get("url")
        page_id = params.get("page_id")
        blocks = params.get("blocks", [])
        
        if not page_id and url:
            try:
                page_id = self._extract_page_id(url)
            except ValueError as e:
                return {"error": str(e)}
        
        if not page_id:
            return {"error": "page_id or url required"}
        
        if not blocks:
            return {"error": "blocks required"}
        
        data = {"children": blocks}
        return self._make_request("PATCH", f"blocks/{page_id}/children", data)