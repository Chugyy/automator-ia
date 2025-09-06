import requests
import functools
import time
from typing import Dict, Any, List
from ..base import BaseTool
from config.logger import logger

def with_retry(max_retries: int = 3, delay: float = 1.0):
    """Retry decorator for API calls"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except requests.HTTPError as e:
                    status_code = e.response.status_code if hasattr(e, 'response') else 0
                    if status_code in (400, 401, 403, 422):
                        logger.error(f"HTTP error {status_code} non-retryable: {e}")
                        raise
                    retries += 1
                    if retries > max_retries:
                        logger.error(f"Failed after {max_retries} attempts - HTTP error {status_code}: {e}")
                        raise
                    logger.warning(f"Attempt {retries}/{max_retries} failed - HTTP error {status_code}: {e}")
                    time.sleep(delay * (2 ** (retries - 1)))
                except (requests.ConnectionError, requests.Timeout) as e:
                    retries += 1
                    if retries > max_retries:
                        logger.error(f"Failed after {max_retries} attempts - Connection error: {e}")
                        raise
                    logger.warning(f"Attempt {retries}/{max_retries} failed - Connection error: {e}")
                    time.sleep(delay * (2 ** (retries - 1)))
                except Exception as e:
                    retries += 1
                    if retries > max_retries:
                        logger.error(f"Failed after {max_retries} attempts: {e}")
                        raise
                    logger.warning(f"Attempt {retries}/{max_retries} failed: {e}")
                    time.sleep(delay)
        return wrapper
    return decorator

class WhatsAppTool(BaseTool):
    """WhatsApp tool using Unipile API for messaging"""
    
    def __init__(self, profile: str = "DEFAULT", config: Dict[str, Any] = None):
        super().__init__(profile, config)
        self.base_url = f"https://{self.config.get('unipile_dsn', 'api12.unipile.com:14215')}/api/v1"
        self.headers = {
            "X-API-KEY": self.config.get('unipile_api_key', ''),
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def authenticate(self) -> bool:
        """Authenticate with Unipile API"""
        if not self.validate_config():
            logger.error("Invalid Unipile WhatsApp configuration")
            return False
        
        if not self.config.get('unipile_api_key') or not self.config.get('wa_accountid'):
            logger.error("Missing UNIPILE_API_KEY or WA_ACCOUNTID")
            return False
        
        self.authenticated = True
        return True
    
    def execute(self, action: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute WhatsApp action"""
        params = params or {}
        
        if not self.is_authenticated():
            return {"error": "Not authenticated"}
        
        try:
            if action == "send_message":
                return self._send_message(params)
            elif action == "send_message_to_chat":
                return self._send_message_to_chat(params)
            elif action == "get_contacts":
                return self._get_contacts(params)
            elif action == "get_conversations":
                return self._get_conversations(params)
            elif action == "get_messages":
                return self._get_messages(params)
            elif action == "sync_chat_history":
                return self._sync_chat_history(params)
            elif action == "get_account_status":
                return self._get_account_status(params)
            else:
                return {"error": f"Action {action} not supported"}
        except Exception as e:
            logger.error(f"Error executing {action}: {e}")
            return {"error": str(e)}
    
    def get_available_actions(self) -> List[str]:
        """Available actions"""
        return ["send_message", "send_message_to_chat", "get_contacts", "get_conversations", "get_messages", "sync_chat_history", "get_account_status"]
    
    def _format_phone_number(self, phone_number: str) -> str:
        """Format phone number for WhatsApp"""
        if not phone_number:
            return ""
        
        # Clean the phone number
        cleaned = phone_number.strip()
        for char in [" ", "-", "(", ")", ".", "/", "\\", ":"]:
            cleaned = cleaned.replace(char, "")
        
        # Remove leading + and convert to digits only
        if cleaned.startswith('+'):
            cleaned = cleaned[1:]
        
        digits = ''.join(ch for ch in cleaned if ch.isdigit())
        
        # Remove leading 00 if present
        if digits.startswith('00'):
            digits = digits[2:]
        
        if not digits or len(digits) < 8:
            logger.error(f"Invalid phone number: '{phone_number}'")
            return ""
        
        logger.debug(f"Formatted phone: '{phone_number}' -> '{digits}'")
        return digits
    
    @with_retry()
    def _get_contact_id(self, phone: str) -> str:
        """Get WhatsApp contact ID for phone number"""
        url = f"{self.base_url}/contacts"
        params = {
            "account_id": self.config.get('wa_accountid'),
            "msisdn": phone
        }
        
        try:
            logger.debug(f"Searching Unipile contact for {phone}")
            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            resp.raise_for_status()
            
            data = resp.json().get("data", [])
            if not data:
                logger.warning(f"No Unipile contact found for {phone}, using standard @c.us format")
                return f"{phone}@c.us"
            
            contact_id = data[0]["id"]
            logger.debug(f"Unipile contact ID found for {phone}: {contact_id}")
            return contact_id
            
        except Exception as e:
            logger.error(f"Error searching Unipile contact for {phone}: {e}. Using {phone}@c.us")
            return f"{phone}@c.us"  # Fallback
    
    def _send_message(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send WhatsApp message to phone number"""
        phone = params.get('phone_number', params.get('phone', ''))
        message = params.get('message', '')
        
        if not phone or not message:
            return {"error": "Phone number and message are required"}
        
        # Format phone number
        formatted_phone = self._format_phone_number(phone)
        if not formatted_phone:
            return {"error": f"Invalid phone number: {phone}"}
        
        try:
            # Get WhatsApp contact ID
            whatsapp_id = self._get_contact_id(formatted_phone)
            
            # Send message
            payload = {
                "account_id": self.config.get('wa_accountid'),
                "text": message,
                "attendees_ids": [whatsapp_id]
            }
            
            url = f"{self.base_url}/chats"
            logger.debug(f"Sending WhatsApp message to {whatsapp_id}")
            
            resp = requests.post(url, json=payload, headers=self.headers, timeout=15)
            resp.raise_for_status()
            
            result = resp.json()
            chat_id = result.get("chat_id")
            
            return {
                "status": "success",
                "message": f"WhatsApp message sent to {formatted_phone}",
                "data": {
                    "phone": formatted_phone,
                    "whatsapp_id": whatsapp_id,
                    "chat_id": chat_id,
                    "message": message
                }
            }
            
        except requests.HTTPError as e:
            error_msg = f"HTTP error sending WhatsApp message: {e}"
            logger.error(error_msg)
            return {"error": error_msg}
        except Exception as e:
            error_msg = f"Error sending WhatsApp message: {e}"
            logger.error(error_msg)
            return {"error": error_msg}
    
    def _send_message_to_chat(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send WhatsApp message to existing chat"""
        chat_id = params.get('chat_id', '')
        message = params.get('message', '')
        
        if not chat_id or not message:
            return {"error": "Chat ID and message are required"}
        
        try:
            url = f"{self.base_url}/chats/{chat_id}/messages"
            payload = {"text": message}
            
            logger.debug(f"Sending WhatsApp message to chat {chat_id}")
            resp = requests.post(url, json=payload, headers=self.headers, timeout=15)
            resp.raise_for_status()
            
            result = resp.json()
            message_id = result.get("id")
            
            return {
                "status": "success",
                "message": f"Message sent to WhatsApp chat {chat_id}",
                "data": {
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "message": message
                }
            }
            
        except requests.HTTPError as e:
            error_msg = f"HTTP error sending message to chat: {e}"
            logger.error(error_msg)
            return {"error": error_msg}
        except Exception as e:
            error_msg = f"Error sending message to chat: {e}"
            logger.error(error_msg)
            return {"error": error_msg}
    
    @with_retry()
    def _get_contacts(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get WhatsApp contacts"""
        limit = params.get('limit', 50)
        
        try:
            url = f"{self.base_url}/contacts"
            params_api = {
                "account_id": self.config.get('wa_accountid'),
                "limit": min(limit, 100)  # API limit
            }
            
            resp = requests.get(url, params=params_api, headers=self.headers, timeout=10)
            resp.raise_for_status()
            
            data = resp.json().get("data", [])
            contacts = []
            
            for contact in data:
                contacts.append({
                    "id": contact.get("id"),
                    "name": contact.get("name", "Unknown"),
                    "phone": contact.get("msisdn", ""),
                    "profile_picture": contact.get("profile_picture_url")
                })
            
            return {
                "status": "success",
                "data": {
                    "contacts": contacts,
                    "count": len(contacts)
                }
            }
            
        except requests.HTTPError as e:
            error_msg = f"HTTP error getting contacts: {e}"
            logger.error(error_msg)
            return {"error": error_msg}
        except Exception as e:
            error_msg = f"Error getting contacts: {e}"
            logger.error(error_msg)
            return {"error": error_msg}
    
    @with_retry()
    def _get_conversations(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get WhatsApp conversations/chats"""
        limit = params.get('limit', 10)
        
        try:
            url = f"{self.base_url}/chats"
            params_api = {
                "account_id": self.config.get('wa_accountid'),
                "limit": min(limit, 50)  # API limit
            }
            
            resp = requests.get(url, params=params_api, headers=self.headers, timeout=10)
            resp.raise_for_status()
            
            data = resp.json().get("data", [])
            conversations = []
            
            for chat in data:
                # Get contact info (excluding our own account)
                attendees = chat.get("attendees", [])
                contact_name = "Unknown"
                contact_phone = ""
                
                for attendee in attendees:
                    if attendee.get("account_id") != self.config.get('wa_accountid'):
                        contact_name = attendee.get("name", "Unknown")
                        contact_phone = attendee.get("identifier", "")
                        break
                
                # Last message info
                last_message = chat.get("last_message", {})
                
                conversations.append({
                    "chat_id": chat.get("id"),
                    "contact_name": contact_name,
                    "contact_phone": contact_phone,
                    "last_message": {
                        "text": last_message.get("text", ""),
                        "date": last_message.get("date_create", ""),
                        "author": last_message.get("author", {}).get("name", "")
                    },
                    "attendees_count": len(attendees)
                })
            
            return {
                "status": "success",
                "data": {
                    "conversations": conversations,
                    "count": len(conversations)
                }
            }
            
        except requests.HTTPError as e:
            error_msg = f"HTTP error getting conversations: {e}"
            logger.error(error_msg)
            return {"error": error_msg}
        except Exception as e:
            error_msg = f"Error getting conversations: {e}"
            logger.error(error_msg)
            return {"error": error_msg}
    
    @with_retry()
    def _get_messages(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get WhatsApp messages from a specific chat or recent messages"""
        chat_id = params.get('chat_id')
        limit = params.get('limit', 20)
        
        try:
            if chat_id:
                # Get messages from specific chat
                url = f"{self.base_url}/chats/{chat_id}/messages"
                params_api = {"limit": min(limit, 50)}
            else:
                # Get recent messages from all chats
                url = f"{self.base_url}/messages"
                params_api = {
                    "account_id": self.config.get('wa_accountid'),
                    "limit": min(limit, 50)
                }
            
            resp = requests.get(url, params=params_api, headers=self.headers, timeout=10)
            resp.raise_for_status()
            
            data = resp.json().get("data", [])
            messages = []
            
            for msg in data:
                author = msg.get("author", {})
                is_from_me = author.get("account_id") == self.config.get('wa_accountid')
                
                messages.append({
                    "id": msg.get("id"),
                    "text": msg.get("text", ""),
                    "date": msg.get("date_create", ""),
                    "author_name": author.get("name", "Unknown"),
                    "from_me": is_from_me,
                    "chat_id": msg.get("chat_id", "")
                })
            
            return {
                "status": "success",
                "data": {
                    "messages": messages,
                    "count": len(messages),
                    "chat_id": chat_id if chat_id else "all"
                }
            }
            
        except requests.HTTPError as e:
            error_msg = f"HTTP error getting messages: {e}"
            logger.error(error_msg)
            return {"error": error_msg}
        except Exception as e:
            error_msg = f"Error getting messages: {e}"
            logger.error(error_msg)
            return {"error": error_msg}
    
    @with_retry()
    def _sync_chat_history(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronize chat history for a specific chat"""
        chat_id = params.get('chat_id')
        
        if not chat_id:
            return {"error": "Chat ID is required for history sync"}
        
        try:
            url = f"{self.base_url}/chats/{chat_id}/sync"
            
            resp = requests.get(url, headers=self.headers, timeout=10)
            resp.raise_for_status()
            
            result = resp.json()
            
            return {
                "status": "success",
                "message": f"Chat history sync started for {chat_id}",
                "data": {
                    "chat_id": result.get("chat_id"),
                    "sync_status": result.get("status"),
                    "object": result.get("object")
                }
            }
            
        except requests.HTTPError as e:
            error_msg = f"HTTP error syncing chat history: {e}"
            logger.error(error_msg)
            return {"error": error_msg}
        except Exception as e:
            error_msg = f"Error syncing chat history: {e}"
            logger.error(error_msg)
            return {"error": error_msg}
    
    @with_retry()
    def _get_account_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get WhatsApp account status"""
        account_id = params.get('account_id', self.config.get('wa_accountid'))
        
        try:
            if account_id:
                # Get specific account status
                url = f"{self.base_url}/accounts/{account_id}"
            else:
                # Get all accounts
                url = f"{self.base_url}/accounts"
                account_id = "all"
            
            resp = requests.get(url, headers=self.headers, timeout=10)
            resp.raise_for_status()
            
            if account_id == "all":
                accounts = resp.json().get("data", [])
                whatsapp_accounts = [acc for acc in accounts if acc.get("provider") == "whatsapp"]
                
                return {
                    "status": "success",
                    "data": {
                        "accounts": whatsapp_accounts,
                        "count": len(whatsapp_accounts),
                        "account_id": "all"
                    }
                }
            else:
                account = resp.json()
                return {
                    "status": "success",
                    "data": {
                        "account_id": account.get("id"),
                        "provider": account.get("provider"),
                        "status": account.get("status"),
                        "name": account.get("name"),
                        "identifier": account.get("identifier"),
                        "is_connected": account.get("status") == "CONNECTED"
                    }
                }
            
        except requests.HTTPError as e:
            error_msg = f"HTTP error getting account status: {e}"
            logger.error(error_msg)
            return {"error": error_msg}
        except Exception as e:
            error_msg = f"Error getting account status: {e}"
            logger.error(error_msg)
            return {"error": error_msg}