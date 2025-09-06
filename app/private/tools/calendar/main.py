import os
import functools
import time
from datetime import datetime, timezone
from typing import List, Dict, Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..oauth import BaseOAuthTool
from config.common.logger import logger

SCOPES_READ_ONLY = ['https://www.googleapis.com/auth/calendar.readonly']
SCOPES_FULL_ACCESS = ['https://www.googleapis.com/auth/calendar']

class CalendarTool(BaseOAuthTool):
    
    def _load_env_file(self, env_path: str):
        """Load environment variables from .env file"""
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
                    
        # Update config with environment variables
        if not self.config:
            self.config = {}
        self.config.update({
            'token_file': os.environ.get('TOKEN_FILE', 'calendar_token.json'),
            'credentials_file': os.environ.get('CREDENTIALS_FILE', 'calendar_credentials.json'),
            'calendar_id': os.environ.get('CALENDAR_ID', 'primary'),
            'timezone': os.environ.get('TIMEZONE', 'Europe/Paris'),
            'scopes_read_only': os.environ.get('SCOPES_READ_ONLY', 'true').lower() == 'true'
        })
    """Google Calendar tool with full API integration"""
    
    def __init__(self, profile: str = "DEFAULT", config: Dict[str, Any] = None):
        super().__init__(profile, config)
        self.base_dir = os.getcwd()
        
        # Load environment variables from .env.TEST
        env_path = os.path.join(os.path.dirname(__file__), '.env.TEST')
        if os.path.exists(env_path):
            self._load_env_file(env_path)
        
    
    def execute(self, action: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a Calendar action"""
        params = params or {}
        
        if not self.is_authenticated():
            return {"error": "Not authenticated"}
        
        try:
            if action == "list_events":
                return self._list_events(params)
            elif action == "create_event":
                return self._create_event(params)
            elif action == "update_event":
                return self._update_event(params)
            elif action == "delete_event":
                return self._delete_event(params)
            else:
                return {"error": f"Action {action} not supported"}
        except Exception as e:
            logger.error(f"Error executing {action}: {e}")
            return {"error": str(e)}
    
    def get_available_actions(self) -> List[str]:
        """Available actions"""
        return ["list_events", "create_event", "update_event", "delete_event"]
    
    def _with_retry(self, func, max_retries: int = 3, delay: float = 1.0):
        """Retry decorator for API calls"""
        retries = 0
        while True:
            try:
                return func()
            except HttpError as e:
                status_code = e.resp.status if hasattr(e, 'resp') else 0
                if status_code in (400, 401, 403, 404):
                    logger.error(f"Non-retryable HTTP error {status_code}: {e}")
                    raise
                retries += 1
                if retries > max_retries:
                    logger.error(f"Failed after {max_retries} attempts - HTTP error {status_code}: {e}")
                    raise
                logger.warning(f"Attempt {retries}/{max_retries} failed - HTTP error {status_code}: {e}")
                time.sleep(delay * (2 ** (retries - 1)))
            except Exception as e:
                retries += 1
                if retries > max_retries:
                    logger.error(f"Failed after {max_retries} attempts: {e}")
                    raise
                logger.warning(f"Attempt {retries}/{max_retries} failed: {e}")
                time.sleep(delay)
    
    
    def _get_calendar_service(self, read_only: bool = None):
        """Get Google Calendar service"""
        creds = self._get_credentials(read_only=read_only)
        return build('calendar', 'v3', credentials=creds, cache_discovery=False)
    
    def _list_events(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List upcoming events"""
        count = min(max(params.get('count', 10), 1), 100)
        calendar_id = params.get('calendar_id', self.config.get('calendar_id', 'primary'))
        
        def api_call():
            service = self._get_calendar_service(read_only=True)
            now = datetime.now(timezone.utc).isoformat()
            events_result = service.events().list(
                calendarId=calendar_id, timeMin=now,
                maxResults=count, singleEvents=True, orderBy='startTime'
            ).execute()
            return events_result.get('items', [])
        
        events = self._with_retry(api_call)
        
        return {
            "status": "success",
            "data": {
                "calendar_id": calendar_id,
                "events": events,
                "count": len(events)
            }
        }
    
    def _create_event(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new event"""
        if not params.get('summary') or not params.get('start_time') or not params.get('end_time'):
            return {"error": "Missing required parameters: summary, start_time, end_time"}
        
        calendar_id = params.get('calendar_id', self.config.get('calendar_id', 'primary'))
        timezone_config = self.config.get('timezone', 'Europe/Paris')
        
        event_body = {
            'summary': params['summary'],
            'start': {'dateTime': params['start_time'], 'timeZone': timezone_config},
            'end': {'dateTime': params['end_time'], 'timeZone': timezone_config}
        }
        
        if params.get('location'):
            event_body['location'] = params['location']
        if params.get('description'):
            event_body['description'] = params['description']
        if params.get('attendees'):
            event_body['attendees'] = [{'email': email} for email in params['attendees']]
        
        def api_call():
            service = self._get_calendar_service(read_only=False)
            return service.events().insert(calendarId=calendar_id, body=event_body).execute()
        
        created_event = self._with_retry(api_call)
        
        return {
            "status": "success",
            "message": f"Event '{created_event.get('summary')}' created successfully",
            "data": {
                "id": created_event.get('id'),
                "summary": created_event.get('summary'),
                "start": created_event.get('start'),
                "end": created_event.get('end')
            }
        }
    
    def _update_event(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing event"""
        event_id = params.get('event_id')
        if not event_id:
            return {"error": "Missing required parameter: event_id"}
        
        calendar_id = params.get('calendar_id', self.config.get('calendar_id', 'primary'))
        timezone_config = self.config.get('timezone', 'Europe/Paris')
        
        # Build update body
        updates = {}
        if params.get('summary'): updates['summary'] = params['summary']
        if params.get('description'): updates['description'] = params['description']
        if params.get('location'): updates['location'] = params['location']
        if params.get('start_time'): updates['start'] = {'dateTime': params['start_time'], 'timeZone': timezone_config}
        if params.get('end_time'): updates['end'] = {'dateTime': params['end_time'], 'timeZone': timezone_config}
        if params.get('attendees') is not None:
            updates['attendees'] = [{'email': email} for email in params['attendees']]
        
        if not updates:
            return {"error": "No update parameters provided"}
        
        def api_call():
            service = self._get_calendar_service(read_only=False)
            # Verify event exists first
            try:
                service.events().get(calendarId=calendar_id, eventId=event_id).execute()
            except HttpError as e:
                if e.resp.status == 404:
                    raise ValueError(f"Event {event_id} not found")
                raise
            
            return service.events().patch(calendarId=calendar_id, eventId=event_id, body=updates).execute()
        
        updated_event = self._with_retry(api_call)
        
        return {
            "status": "success",
            "message": f"Event {event_id} updated successfully",
            "data": {
                "id": updated_event.get('id'),
                "summary": updated_event.get('summary')
            }
        }
    
    def _delete_event(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Delete an event"""
        event_id = params.get('event_id')
        if not event_id:
            return {"error": "Missing required parameter: event_id"}
        
        calendar_id = params.get('calendar_id', self.config.get('calendar_id', 'primary'))
        
        def api_call():
            service = self._get_calendar_service(read_only=False)
            service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        
        try:
            self._with_retry(api_call)
            return {
                "status": "success",
                "message": f"Event {event_id} deleted successfully"
            }
        except HttpError as e:
            if e.resp.status == 404:
                return {
                    "status": "warning",
                    "message": f"Event {event_id} not found or already deleted"
                }
            raise