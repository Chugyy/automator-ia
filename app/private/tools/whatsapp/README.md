# WhatsApp Tool

💬 WhatsApp Business API integration for automated messaging and customer communication.

## Features

- Send messages to WhatsApp contacts
- Retrieve message history
- Manage contacts
- Support for text messages and media
- Webhook integration for real-time messaging

## Requirements

```
requests>=2.31.0
```

## Configuration

1. Set up WhatsApp Business API account
2. Configure `.env` file with your credentials
3. Set up webhook URL for receiving messages (optional)

## Usage

```python
from whatsapp_tool import WhatsAppTool

tool = WhatsAppTool()
tool.authenticate()

# Send message
result = tool.execute("send_message", {
    "phone": "+1234567890",
    "message": "Hello from WhatsApp Bot!"
})

# Get messages
messages = tool.execute("get_messages", {"limit": 10})
```

## Security

- Use secure webhook endpoints
- Validate webhook signatures
- Never commit access tokens to version control
- Use HTTPS for all API calls