from abc import ABC
from typing import Dict, Any, List, Optional
import os
import json
import secrets
import time
from urllib.parse import urlencode

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.errors import HttpError

from .base import BaseTool
from config.logger import logger
from config.config import settings

# Allow insecure transport for local development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

class BaseOAuthTool(BaseTool):
    """Base class for tools requiring OAuth authentication"""
    
    def __init__(self, profile: str = "DEFAULT", config: Dict[str, Any] = None):
        super().__init__(profile, config)
        self.oauth_config = self._load_oauth_config()
        self.provider = self.oauth_config.get('provider', 'google')
        self.scopes = self.oauth_config.get('scopes', [])
        self.redirect_uri = self._get_redirect_uri()
        
    def _load_oauth_config(self) -> Dict[str, Any]:
        """Load OAuth configuration from config.json"""
        schema = self._load_config_schema()
        return schema.get('oauth_config', {})
    
    def _get_redirect_uri(self) -> str:
        """Generate redirect URI for this tool"""
        # Prefer explicit config; otherwise use prod/dev base URLs
        if self.config.get('oauth_url'):
            base_url = self.config['oauth_url']
        else:
            if settings.env == 'prod':
                base_url = settings.prod_base_url
            else:
                base_url = settings.base_url
        return f"{base_url}/oauth/{self.tool_name.lower()}/callback"
        
    # --- Path resolution helpers ---
    def _get_backend_dir(self) -> str:
        tool_dir = os.path.dirname(os.path.abspath(__file__))
        # backend/app/private/tools -> backend (three levels up)
        return os.path.abspath(os.path.join(tool_dir, '..', '..', '..'))

    def _get_repo_root(self) -> str:
        return os.path.abspath(os.path.join(self._get_backend_dir(), '..'))

    def _resolve_path(self, rel_or_abs: str) -> Optional[str]:
        """Return an existing absolute path for a given relative/absolute path, if found."""
        if not rel_or_abs:
            return None
        # Absolute path
        if os.path.isabs(rel_or_abs):
            return rel_or_abs if os.path.exists(rel_or_abs) else None
        candidates = [
            os.path.abspath(os.path.join(self.base_dir, rel_or_abs)),
            os.path.abspath(os.path.join(self._get_backend_dir(), rel_or_abs)),
            os.path.abspath(os.path.join(self._get_repo_root(), rel_or_abs)),
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
        return None

    def _resolve_write_path(self, rel_or_abs: str) -> str:
        """Choose a write path for tokens based on existing dirs or create them."""
        if os.path.isabs(rel_or_abs):
            target = rel_or_abs
        else:
            # prefer repo root location if directory exists, else backend dir, else base dir
            backend_target = os.path.abspath(os.path.join(self._get_backend_dir(), rel_or_abs))
            repo_target = os.path.abspath(os.path.join(self._get_repo_root(), rel_or_abs))
            base_target = os.path.abspath(os.path.join(self.base_dir, rel_or_abs))
            for t in (backend_target, repo_target, base_target):
                parent = os.path.dirname(t)
                try:
                    os.makedirs(parent, exist_ok=True)
                    target = t
                    break
                except Exception:
                    continue
            else:
                # Fallback to base_target without creating
                target = base_target
        return target
    
    def get_auth_url(self) -> str:
        """Generate OAuth authorization URL"""
        if self.provider == 'google':
            return self._get_google_auth_url()
        else:
            raise ValueError(f"Unsupported OAuth provider: {self.provider}")
    
    def _get_google_auth_url(self) -> str:
        """Generate Google OAuth authorization URL"""
        configured = self.config.get('credentials_file')
        credentials_path = self._resolve_path(configured)
        if not credentials_path:
            raise FileNotFoundError(
                f"Credentials file not found for '{configured}'. "
                f"Tried under base_dir, repo root and backend dirs."
            )
        
        flow = Flow.from_client_secrets_file(
            credentials_path,
            scopes=self.scopes,
            redirect_uri=self.redirect_uri
        )
        
        auth_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        # Store state for validation
        self._store_oauth_state(state)
        return auth_url
    
    def handle_oauth_callback(self, authorization_response: str, state: str = None) -> bool:
        """Handle OAuth callback and exchange code for tokens"""
        try:
            logger.info(f"Processing OAuth callback for {self.tool_name}")
            logger.debug(f"Authorization response: {authorization_response[:100]}...")
            logger.debug(f"State parameter: {state}")
            
            if not self._validate_oauth_state(state):
                logger.error(f"Invalid OAuth state for {self.tool_name}")
                return False
            
            if self.provider == 'google':
                return self._handle_google_callback(authorization_response, state)
            else:
                raise ValueError(f"Unsupported OAuth provider: {self.provider}")
                
        except Exception as e:
            logger.error(f"OAuth callback error for {self.tool_name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _handle_google_callback(self, authorization_response: str, state: str) -> bool:
        """Handle Google OAuth callback"""
        try:
            configured = self.config.get('credentials_file')
            credentials_path = self._resolve_path(configured)
            logger.info(f"Using credentials file: {credentials_path}")
            
            if not credentials_path or not os.path.exists(credentials_path):
                raise FileNotFoundError(f"Credentials file not found: {credentials_path}")
            
            flow = Flow.from_client_secrets_file(
                credentials_path,
                scopes=self.scopes,
                redirect_uri=self.redirect_uri,
                state=state
            )
            
            logger.info("Fetching token from authorization response")
            flow.fetch_token(authorization_response=authorization_response)
            
            # Save credentials
            logger.info("Saving OAuth credentials")
            self._save_credentials(flow.credentials)
            self.authenticated = True
            
            logger.info(f"OAuth authentication successful for {self.tool_name}")
            return True
            
        except Exception as e:
            logger.error(f"Google OAuth callback error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def _store_oauth_state(self, state: str) -> None:
        """Store OAuth state for validation"""
        state_file = os.path.join(self.base_dir, f".oauth_state_{self.tool_name.lower()}")
        try:
            data = {}
            if os.path.exists(state_file):
                try:
                    with open(state_file, 'r') as f:
                        data = json.load(f) or {}
                except Exception:
                    data = {}
            entries = data.get('entries', [])
            entries.append({'state': state, 'timestamp': time.time(), 'profile': self.profile})
            data['entries'] = entries[-20:]
            with open(state_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            logger.warning(f"Could not store OAuth state: {e}")
    
    def _validate_oauth_state(self, state: str) -> bool:
        """Validate OAuth state parameter"""
        if not state:
            logger.warning("No state parameter provided")
            return False
            
        state_file = os.path.join(self.base_dir, f".oauth_state_{self.tool_name.lower()}")
        logger.debug(f"Checking state file: {state_file}")
        
        try:
            if not os.path.exists(state_file):
                logger.warning(f"State file not found: {state_file}")
                return False
                
            with open(state_file, 'r') as f:
                stored_data = json.load(f)
            entries = stored_data.get('entries')
            if isinstance(entries, list):
                match = next((e for e in entries if e.get('state') == state), None)
                if not match:
                    logger.warning("OAuth state not found in entries")
                    return False
                ts = match.get('timestamp', 0)
                if time.time() - ts > 600:
                    logger.warning("OAuth state expired")
                    return False
                return True
            else:
                # backward compat old format
                stored_state = stored_data.get('state')
                timestamp = stored_data.get('timestamp', 0)
                logger.debug(f"Stored state: {stored_state}")
                logger.debug(f"Provided state: {state}")
                logger.debug(f"State age: {time.time() - timestamp} seconds")
                if time.time() - timestamp > 600:
                    logger.warning("OAuth state expired")
                    os.remove(state_file)
                    return False
                is_valid = stored_state == state
                if is_valid:
                    os.remove(state_file)
                return is_valid
            
        except Exception as e:
            logger.error(f"Could not validate OAuth state: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _get_credentials(self, read_only: bool = None) -> Credentials:
        """Get OAuth credentials with automatic refresh"""
        if read_only is None:
            read_only = self.config.get('scopes_read_only', True)
        
        # Use appropriate scopes based on read_only flag
        scopes = self.scopes
        if self.provider == 'google' and read_only is not None:
            # Try to use read-only scopes if available and requested
            readonly_scope = "https://www.googleapis.com/auth/calendar.readonly"
            full_scope = "https://www.googleapis.com/auth/calendar"
            if read_only and readonly_scope in self.scopes:
                scopes = [readonly_scope]
            elif not read_only and full_scope in self.scopes:
                scopes = [full_scope]
        
        creds = None
        token_config = self.config.get('token_file')
        token_path = self._resolve_path(token_config) or os.path.abspath(os.path.join(self.base_dir, token_config))
        
        # Load existing token
        if os.path.exists(token_path):
            try:
                with open(token_path, 'r') as token_file:
                    creds_data = json.load(token_file)
                creds = Credentials.from_authorized_user_info(creds_data, scopes)
                logger.debug("OAuth token loaded from file")
            except Exception as e:
                logger.error(f"Error loading OAuth token: {e}")
        
        # Refresh if needed
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logger.debug("OAuth token refreshed successfully")
                    self._save_credentials(creds)
                except Exception as e:
                    logger.error(f"Error refreshing OAuth token: {e}")
                    creds = None
            
            if not creds:
                raise PermissionError(
                    f"{self.tool_name} OAuth authentication required. "
                    f"Please authenticate via /oauth/{self.tool_name.lower()}/auth"
                )
        
        return creds
    
    def _save_credentials(self, credentials: Credentials) -> None:
        """Save OAuth credentials to file"""
        token_path = self._resolve_write_path(self.config.get('token_file'))
        
        # Create token directory if needed
        token_dir = os.path.dirname(token_path)
        if not os.path.exists(token_dir):
            os.makedirs(token_dir, exist_ok=True)
        
        try:
            with open(token_path, 'w') as token_file:
                token_file.write(credentials.to_json())
            logger.debug(f"OAuth token saved to {token_path}")
        except Exception as e:
            logger.warning(f"Cannot save OAuth token to {token_path}: {e}")
    
    def get_oauth_status(self) -> Dict[str, Any]:
        """Get OAuth authentication status"""
        try:
            self._get_credentials()
            return {
                "authenticated": True,
                "provider": self.provider,
                "scopes": self.scopes,
                "tool": self.tool_name,
                "auth_url": f"/oauth/{self.tool_name.lower()}/auth?profile={self.profile}"
            }
        except PermissionError:
            return {
                "authenticated": False,
                "provider": self.provider,
                "scopes": self.scopes,
                "tool": self.tool_name,
                "auth_url": f"/oauth/{self.tool_name.lower()}/auth?profile={self.profile}"
            }
        except Exception as e:
            return {
                "authenticated": False,
                "provider": self.provider,
                "error": str(e),
                "tool": self.tool_name
            }
    
    def authenticate(self) -> bool:
        """Check OAuth authentication status"""
        try:
            self._get_credentials()
            self.authenticated = True
            return True
        except Exception as e:
            logger.error(f"OAuth authentication check failed: {e}")
            return False
