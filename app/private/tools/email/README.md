# Email Tool

📧 Professional email management tool for sending and retrieving emails.

## Features

- Send emails with attachments
- Retrieve emails from inbox
- Support for Gmail, Outlook, and custom SMTP/IMAP servers
- HTML and plain text email support

## Requirements

```
smtplib (built-in)
imaplib (built-in)
email (built-in)
```

## Configuration

1. Copy `.env` file and configure your email settings
2. For Gmail, use app-specific passwords instead of your regular password
3. Update `config.py` with your SMTP/IMAP server details if not using Gmail

## Usage

```python
from email_tool import EmailTool

tool = EmailTool()
tool.authenticate()

# Send email
result = tool.execute("send_email", {
    "to": "recipient@example.com",
    "subject": "Test Email",
    "body": "Hello from EmailTool!"
})

# Get emails
emails = tool.execute("get_emails", {"limit": 10})
```

## Security

- Use app-specific passwords for Gmail
- Never commit credentials to version control
- Configure firewall rules for SMTP/IMAP ports if needed