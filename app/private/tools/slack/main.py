from typing import Dict, Any, List
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import requests
from time import sleep

from ..base import BaseTool
from config.logger import logger

class SlackTool(BaseTool):
    """Slack API integration with full messaging, channels and user management"""
    
    def __init__(self, profile: str = "DEFAULT", config: Dict[str, Any] = None):
        super().__init__(profile, config)
        self.client = None
    
    def authenticate(self) -> bool:
        """Authenticate with Slack API token"""
        if not self.validate_config():
            logger.error("Invalid Slack configuration")
            return False
        
        token = self.config.get('token')
        if not token or not token.startswith('xoxb-'):
            logger.error("Invalid or missing Slack bot token")
            return False
        
        try:
            self.client = WebClient(token=token)
            response = self.client.auth_test()
            if response['ok']:
                logger.info(f"Authenticated as {response['user']} on {response['team']}")
                self.authenticated = True
                return True
        except SlackApiError as e:
            logger.error(f"Slack authentication failed: {e.response['error']}")
        except Exception as e:
            logger.error(f"Slack authentication error: {str(e)}")
        
        return False
    
    def execute(self, action: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute Slack action with rate limiting"""
        params = params or {}
        
        if not self.is_authenticated():
            return {"error": "Not authenticated"}
        
        try:
            actions = {
                "post_message": self._post_message,
                "update_message": self._update_message,
                "delete_message": self._delete_message,
                "get_messages": self._get_messages,
                "create_channel": self._create_channel,
                "archive_channel": self._archive_channel,
                "invite_user": self._invite_user,
                "kick_user": self._kick_user,
                "open_dm": self._open_dm,
                "list_users": self._list_users,
                "list_conversations": self._list_conversations,
                "get_conversation_info": self._get_conversation_info,
                "get_conversation_members": self._get_conversation_members,
                "lookup_user_by_email": self._lookup_user_by_email
            }
            
            if action in actions:
                return self._with_retry(actions[action], params)
            else:
                return {"error": f"Action {action} not supported. Available: {list(actions.keys())}"}
        except Exception as e:
            logger.error(f"Error executing {action}: {e}")
            return {"error": str(e)}
    
    def get_available_actions(self) -> List[str]:
        """Available Slack actions"""
        return [
            "post_message", "update_message", "delete_message",
            "get_messages", "create_channel", "archive_channel",
            "invite_user", "kick_user", "open_dm", "list_users",
            "list_conversations", "get_conversation_info", "get_conversation_members",
            "lookup_user_by_email"
        ]
    
    def _with_retry(self, func, params: Dict[str, Any], max_retries: int = 3) -> Dict[str, Any]:
        """Execute function with rate limit handling"""
        for attempt in range(max_retries):
            try:
                return func(params)
            except SlackApiError as e:
                if e.response['error'] == 'rate_limited':
                    retry_after = int(e.response.get('retry_after', 1))
                    if attempt < max_retries - 1:
                        logger.warning(f"Rate limited, retrying after {retry_after}s")
                        sleep(retry_after)
                        continue
                raise e
        return {"error": "Max retries exceeded"}
    
    def _post_message(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Post message to channel"""
        channel = params.get('channel', self.config.get('channel', '#general'))
        text = params.get('text', '')
        blocks = params.get('blocks')
        
        if not channel:
            return {"error": "Channel is required"}
        if not text and not blocks:
            return {"error": "Text or blocks required"}
        
        try:
            response = self.client.chat_postMessage(
                channel=channel,
                text=text,
                blocks=blocks
            )
            
            return {
                "status": "success",
                "message": f"Message posted to {channel}",
                "data": {
                    "channel": response['channel'],
                    "ts": response['ts'],
                    "text": text
                }
            }
        except SlackApiError as e:
            return {"error": f"Slack API error: {e.response['error']}"}
    
    def _update_message(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing message"""
        channel = params.get('channel')
        ts = params.get('ts')
        text = params.get('text', '')
        
        if not all([channel, ts]):
            return {"error": "Channel and ts (timestamp) are required"}
        
        try:
            response = self.client.chat_update(
                channel=channel,
                ts=ts,
                text=text
            )
            
            return {
                "status": "success",
                "message": "Message updated",
                "data": {"channel": channel, "ts": ts}
            }
        except SlackApiError as e:
            return {"error": f"Slack API error: {e.response['error']}"}
    
    def _delete_message(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Delete message (bot can only delete its own messages)"""
        channel = params.get('channel')
        ts = params.get('ts')
        
        if not all([channel, ts]):
            return {"error": "Channel and ts (timestamp) are required"}
        
        try:
            response = self.client.chat_delete(
                channel=channel,
                ts=ts
            )
            
            return {
                "status": "success",
                "message": "Message deleted",
                "data": {"channel": channel, "ts": ts}
            }
        except SlackApiError as e:
            return {"error": f"Slack API error: {e.response['error']}"}
    
    def _get_messages(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get channel message history"""
        channel = params.get('channel', self.config.get('channel', '#general'))
        limit = min(params.get('limit', 50), 200)
        cursor = params.get('cursor')
        oldest = params.get('oldest')
        latest = params.get('latest')
        
        try:
            response = self.client.conversations_history(
                channel=channel,
                limit=limit,
                cursor=cursor,
                oldest=oldest,
                latest=latest
            )
            
            messages = []
            for msg in response['messages']:
                messages.append({
                    'user': msg.get('user', 'unknown'),
                    'text': msg.get('text', ''),
                    'ts': msg['ts'],
                    'type': msg.get('type', 'message'),
                    'subtype': msg.get('subtype'),
                    'timestamp': msg['ts']
                })
            
            return {
                "status": "success",
                "data": {
                    "channel": channel,
                    "messages": messages,
                    "has_more": response.get('has_more', False),
                    "next_cursor": response.get('response_metadata', {}).get('next_cursor')
                }
            }
        except SlackApiError as e:
            return {"error": f"Slack API error: {e.response['error']}"}
    
    def _create_channel(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create new channel"""
        name = params.get('name')
        is_private = params.get('is_private', False)
        
        if not name:
            return {"error": "Channel name is required"}
        
        try:
            response = self.client.conversations_create(
                name=name,
                is_private=is_private
            )
            
            channel = response['channel']
            return {
                "status": "success",
                "message": f"Channel {'#' + name} created",
                "data": {
                    "id": channel['id'],
                    "name": channel['name'],
                    "is_private": channel['is_private']
                }
            }
        except SlackApiError as e:
            return {"error": f"Slack API error: {e.response['error']}"}
    
    def _archive_channel(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Archive channel"""
        channel = params.get('channel')
        
        if not channel:
            return {"error": "Channel is required"}
        
        try:
            response = self.client.conversations_archive(channel=channel)
            
            return {
                "status": "success",
                "message": f"Channel {channel} archived",
                "data": {"channel": channel}
            }
        except SlackApiError as e:
            return {"error": f"Slack API error: {e.response['error']}"}
    
    def _invite_user(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Invite users to channel"""
        channel = params.get('channel')
        users = params.get('users')
        
        if not channel or not users:
            return {"error": "Channel and users are required"}
        
        if isinstance(users, str):
            users = [users]
        
        try:
            response = self.client.conversations_invite(
                channel=channel,
                users=users
            )
            
            return {
                "status": "success",
                "message": f"Users invited to {channel}",
                "data": {"channel": channel, "users": users}
            }
        except SlackApiError as e:
            return {"error": f"Slack API error: {e.response['error']}"}
    
    def _kick_user(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Remove user from channel"""
        channel = params.get('channel')
        user = params.get('user')
        
        if not channel or not user:
            return {"error": "Channel and user are required"}
        
        try:
            response = self.client.conversations_kick(
                channel=channel,
                user=user
            )
            
            return {
                "status": "success",
                "message": f"User {user} removed from {channel}",
                "data": {"channel": channel, "user": user}
            }
        except SlackApiError as e:
            return {"error": f"Slack API error: {e.response['error']}"}
    
    def _open_dm(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Open DM or group DM"""
        users = params.get('users')
        
        if not users:
            return {"error": "Users are required"}
        
        if isinstance(users, str):
            users = [users]
        
        try:
            response = self.client.conversations_open(users=users)
            
            channel = response['channel']
            return {
                "status": "success",
                "message": f"{'DM' if len(users) == 1 else 'Group DM'} opened",
                "data": {
                    "channel_id": channel['id'],
                    "users": users
                }
            }
        except SlackApiError as e:
            return {"error": f"Slack API error: {e.response['error']}"}
    
    def _list_users(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List workspace users"""
        limit = min(params.get('limit', 100), 1000)
        cursor = params.get('cursor')
        
        try:
            response = self.client.users_list(
                limit=limit,
                cursor=cursor
            )
            
            users = []
            for user in response['members']:
                if not user.get('deleted', False):
                    users.append({
                        'id': user['id'],
                        'name': user['name'],
                        'real_name': user.get('real_name', ''),
                        'email': user.get('profile', {}).get('email', ''),
                        'is_bot': user.get('is_bot', False),
                        'status': user.get('presence', 'unknown')
                    })
            
            return {
                "status": "success",
                "data": {
                    "users": users,
                    "count": len(users),
                    "next_cursor": response.get('response_metadata', {}).get('next_cursor')
                }
            }
        except SlackApiError as e:
            return {"error": f"Slack API error: {e.response['error']}"}
    
    def _list_conversations(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List all conversations (channels, DMs, groups) the bot has access to"""
        types = params.get('types', 'public_channel,private_channel,im,mpim')
        limit = min(params.get('limit', 100), 1000)
        cursor = params.get('cursor')
        exclude_archived = params.get('exclude_archived', True)
        
        try:
            response = self.client.conversations_list(
                types=types,
                limit=limit,
                cursor=cursor,
                exclude_archived=exclude_archived
            )
            
            conversations = []
            for conv in response['channels']:
                conversations.append({
                    'id': conv['id'],
                    'name': conv.get('name', f"DM-{conv['id']}"),
                    'is_channel': conv.get('is_channel', False),
                    'is_private': conv.get('is_private', False),
                    'is_im': conv.get('is_im', False),
                    'is_mpim': conv.get('is_mpim', False),
                    'is_archived': conv.get('is_archived', False),
                    'num_members': conv.get('num_members', 0),
                    'created': conv.get('created'),
                    'creator': conv.get('creator')
                })
            
            return {
                "status": "success",
                "data": {
                    "conversations": conversations,
                    "count": len(conversations),
                    "next_cursor": response.get('response_metadata', {}).get('next_cursor')
                }
            }
        except SlackApiError as e:
            return {"error": f"Slack API error: {e.response['error']}"}
    
    def _get_conversation_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed info about a specific conversation"""
        channel = params.get('channel')
        
        if not channel:
            return {"error": "Channel ID is required"}
        
        try:
            response = self.client.conversations_info(channel=channel)
            
            channel_info = response['channel']
            return {
                "status": "success",
                "data": {
                    "id": channel_info['id'],
                    "name": channel_info.get('name', f"DM-{channel_info['id']}"),
                    "is_channel": channel_info.get('is_channel', False),
                    "is_private": channel_info.get('is_private', False),
                    "is_im": channel_info.get('is_im', False),
                    "is_mpim": channel_info.get('is_mpim', False),
                    "is_archived": channel_info.get('is_archived', False),
                    "topic": channel_info.get('topic', {}).get('value', ''),
                    "purpose": channel_info.get('purpose', {}).get('value', ''),
                    'num_members': channel_info.get('num_members', 0),
                    'created': channel_info.get('created'),
                    'creator': channel_info.get('creator')
                }
            }
        except SlackApiError as e:
            return {"error": f"Slack API error: {e.response['error']}"}
    
    def _get_conversation_members(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get members of a specific conversation"""
        channel = params.get('channel')
        limit = min(params.get('limit', 100), 1000)
        cursor = params.get('cursor')
        
        if not channel:
            return {"error": "Channel ID is required"}
        
        try:
            response = self.client.conversations_members(
                channel=channel,
                limit=limit,
                cursor=cursor
            )
            
            return {
                "status": "success",
                "data": {
                    "channel": channel,
                    "members": response['members'],
                    "count": len(response['members']),
                    "next_cursor": response.get('response_metadata', {}).get('next_cursor')
                }
            }
        except SlackApiError as e:
            return {"error": f"Slack API error: {e.response['error']}"}
    
    def _lookup_user_by_email(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Lookup user by email (fallback to users.list if direct lookup fails)"""
        email = params.get('email')
        
        if not email:
            return {"error": "Email is required"}
        
        try:
            # Try direct lookup first
            try:
                response = self.client.users_lookupByEmail(email=email)
                user = response['user']
                
                return {
                    "status": "success",
                    "method": "direct_lookup",
                    "data": {
                        "id": user['id'],
                        "name": user['name'],
                        "real_name": user.get('real_name', ''),
                        "email": user.get('profile', {}).get('email', ''),
                        "is_bot": user.get('is_bot', False),
                        "deleted": user.get('deleted', False)
                    }
                }
            except SlackApiError as e:
                if e.response['error'] in ['users_not_found', 'invalid_auth', 'missing_scope']:
                    # Fallback to users.list
                    logger.info(f"Direct lookup failed ({e.response['error']}), falling back to users.list")
                    
                    cursor = None
                    while True:
                        response = self.client.users_list(limit=200, cursor=cursor)
                        
                        for user in response['members']:
                            user_email = user.get('profile', {}).get('email', '').lower()
                            if user_email == email.lower() and not user.get('deleted', False):
                                return {
                                    "status": "success",
                                    "method": "fallback_list",
                                    "data": {
                                        "id": user['id'],
                                        "name": user['name'],
                                        "real_name": user.get('real_name', ''),
                                        "email": user_email,
                                        "is_bot": user.get('is_bot', False),
                                        "deleted": user.get('deleted', False)
                                    }
                                }
                        
                        cursor = response.get('response_metadata', {}).get('next_cursor')
                        if not cursor:
                            break
                    
                    return {"error": f"User with email {email} not found"}
                else:
                    raise e
                    
        except SlackApiError as e:
            return {"error": f"Slack API error: {e.response['error']}"}