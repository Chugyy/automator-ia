from typing import Dict, Any, List
from ..base import BaseTool
from .config import YouTubeConfig
from config.common.logger import logger


class YouTubeTool(BaseTool):
    """YouTube tool for video management and analytics"""
    
    def __init__(self, profile: str = "DEFAULT", config: Dict[str, Any] = None):
        super().__init__(profile, config)
        default_config = YouTubeConfig.get_default_config()
        default_config.update(self.config)
        self.config = default_config
    
    def authenticate(self) -> bool:
        """Authenticate with YouTube Data API"""
        if not YouTubeConfig.validate(self.config):
            logger.error("Invalid YouTube configuration")
            return False
        self.authenticated = True
        return True
    
    def execute(self, action: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute YouTube action"""
        params = params or {}
        
        if not self.is_authenticated():
            return {"error": "Not authenticated"}
        
        if action == "search_videos":
            return self._search_videos(params)
        elif action == "get_video_info":
            return self._get_video_info(params)
        elif action == "get_channel_info":
            return self._get_channel_info(params)
        else:
            return {"error": f"Action {action} not supported"}
    
    def get_available_actions(self) -> List[str]:
        """Available actions"""
        return ["search_videos", "get_video_info", "get_channel_info"]
    
    def _search_videos(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search YouTube videos"""
        query = params.get('query', '')
        max_results = params.get('max_results', 10)
        
        logger.info(f"[YOUTUBE-{self.profile}] Searching videos: {query}")
        
        videos = [
            {"id": "dQw4w9WgXcQ", "title": "Sample Video 1", "channel": "Sample Channel"},
            {"id": "oHg5SJYRHA0", "title": "Sample Video 2", "channel": "Another Channel"}
        ]
        
        return {
            "status": "success",
            "data": {"query": query, "videos": videos[:max_results]}
        }
    
    def _get_video_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get video information"""
        video_id = params.get('video_id', '')
        
        logger.info(f"[YOUTUBE-{self.profile}] Getting video info: {video_id}")
        
        return {
            "status": "success",
            "data": {
                "video_id": video_id,
                "title": "Sample Video Title",
                "description": "Sample description",
                "duration": "PT3M42S",
                "view_count": "1000000"
            }
        }
    
    def _get_channel_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get channel information"""
        channel_id = params.get('channel_id', '')
        
        logger.info(f"[YOUTUBE-{self.profile}] Getting channel info: {channel_id}")
        
        return {
            "status": "success",
            "data": {
                "channel_id": channel_id,
                "title": "Sample Channel",
                "subscriber_count": "100000",
                "video_count": "50"
            }
        }