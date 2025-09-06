import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List, Optional

from ..base import BaseTool
from config.common.logger import logger

class EmailTool(BaseTool):
    """Email tool with full SMTP/IMAP integration"""
    
    def authenticate(self) -> bool:
        """Validate email configuration"""
        if not self.validate_config():
            logger.error("Invalid email configuration")
            return False
        
        required_params = ['email', 'password', 'smtp_host', 'smtp_port', 'imap_host', 'imap_port']
        for param in required_params:
            if not self.config.get(param):
                logger.error(f"Missing required email parameter: {param}")
                return False
        
        self.authenticated = True
        return True
    
    def execute(self, action: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute email action"""
        params = params or {}
        
        if not self.is_authenticated():
            return {"error": "Not authenticated"}
        
        try:
            if action == "send_email":
                return self._send_email(params)
            elif action == "get_emails":
                return self._get_emails(params)
            else:
                return {"error": f"Action {action} not supported"}
        except Exception as e:
            logger.error(f"Error executing {action}: {e}")
            return {"error": str(e)}
    
    def get_available_actions(self) -> List[str]:
        """Available actions"""
        return ["send_email", "get_emails"]
    
    def _send_email(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send email via SMTP"""
        to = params.get('to', [])
        if isinstance(to, str):
            to = [to]
        if not to:
            return {"error": "Missing required parameter: to"}
        
        subject = params.get('subject', '')
        body = params.get('body', '')
        cc = params.get('cc', [])
        bcc = params.get('bcc', [])
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.config['email']
            msg['To'] = ', '.join(to)
            msg['Subject'] = subject
            
            if cc:
                msg['Cc'] = ', '.join(cc)
            
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(self.config['smtp_host'], self.config['smtp_port']) as server:
                if self.config.get('use_tls', True):
                    server.starttls()
                server.login(self.config['email'], self.config['password'])
                
                recipients = to + cc + bcc
                server.sendmail(self.config['email'], recipients, msg.as_string())
            
            return {
                "status": "success",
                "message": f"Email sent to {', '.join(to)}",
                "data": {
                    "to": to,
                    "cc": cc,
                    "bcc": bcc,
                    "subject": subject
                }
            }
        except Exception as e:
            return {"error": f"SMTP error: {str(e)}"}
    
    def _get_emails(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve emails via IMAP"""
        folder = params.get('folder', 'INBOX')
        limit = min(max(params.get('limit', 10), 1), 100)
        unread_only = params.get('unread_only', False)
        search_query = params.get('search_query')
        
        try:
            with imaplib.IMAP4_SSL(self.config['imap_host'], self.config['imap_port']) as mail:
                mail.login(self.config['email'], self.config['password'])
                mail.select(folder)
                
                search_criteria = 'UNSEEN' if unread_only else 'ALL'
                if search_query:
                    search_criteria = f'({search_criteria} SUBJECT "{search_query}")'
                
                _, message_numbers = mail.search(None, search_criteria)
                emails = []
                
                if message_numbers[0]:
                    for num in message_numbers[0].split()[-limit:]:
                        _, msg_data = mail.fetch(num, '(RFC822)')
                        email_body = msg_data[0][1]
                        email_message = email.message_from_bytes(email_body)
                        
                        emails.append({
                            'id': num.decode(),
                            'from': email_message.get('From', ''),
                            'to': email_message.get('To', ''),
                            'cc': email_message.get('Cc', ''),
                            'subject': email_message.get('Subject', ''),
                            'date': email_message.get('Date', ''),
                            'body': self._extract_body(email_message),
                            'has_attachments': self._has_attachments(email_message),
                            'attachments': self._get_attachment_names(email_message)
                        })
                
                return {
                    "status": "success",
                    "data": {
                        "folder": folder,
                        "emails": emails,
                        "count": len(emails)
                    }
                }
        except Exception as e:
            return {"error": f"IMAP error: {str(e)}"}
    
    def _extract_body(self, email_message) -> str:
        """Extract email body text"""
        try:
            if email_message.is_multipart():
                for part in email_message.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            return payload.decode('utf-8', errors='ignore')
            else:
                payload = email_message.get_payload(decode=True)
                if payload:
                    return payload.decode('utf-8', errors='ignore')
        except Exception:
            pass
        return ""
    
    def _has_attachments(self, email_message) -> bool:
        """Check if email has attachments"""
        return any(part.get_content_disposition() == 'attachment' 
                  for part in email_message.walk())
    
    def _get_attachment_names(self, email_message) -> List[str]:
        """Get attachment filenames"""
        attachments = []
        for part in email_message.walk():
            if part.get_content_disposition() == 'attachment':
                filename = part.get_filename()
                if filename:
                    attachments.append(filename)
        return attachments