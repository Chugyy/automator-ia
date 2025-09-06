# YouTube Tool

🎥 YouTube Data API integration for video management, analytics, and content retrieval.

## Features

- Search videos by keywords
- Get video information and statistics
- Retrieve channel information
- Extract video transcripts
- Get video comments and analytics

## Requirements

```
google-api-python-client>=2.88.0
youtube-transcript-api>=0.6.0
```

## Configuration

1. Create a YouTube Data API key in Google Cloud Console
2. Enable YouTube Data API v3
3. Configure `.env` file with your API key

## Usage

```python
from youtube_tool import YouTubeTool

tool = YouTubeTool()
tool.authenticate()

# Search videos
results = tool.execute("search_videos", {
    "query": "python tutorial",
    "max_results": 10
})

# Get video info
info = tool.execute("get_video_info", {
    "video_id": "dQw4w9WgXcQ"
})
```

## Security

- Keep API keys secure and never commit to version control
- Monitor API quota usage
- Use appropriate scopes for OAuth if needed
- Rate limit requests to avoid hitting quotas