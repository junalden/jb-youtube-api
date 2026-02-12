# YouTube Transcript API Server

A simple Python HTTP server that fetches YouTube video transcripts using the `youtube-transcript-api` library.

## Features

- Fetches YouTube video transcripts via POST requests
- CORS enabled for cross-origin requests
- Optional proxy support for rate limiting and geo-restrictions
- JSON response format

## Setup

### Installation

```bash
pip install -r requirements.txt
```

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

**Required Variables:**
- `PORT` - Server port (default: 8020)
- `YOUTUBE_API_KEY` - YouTube Data API v3 key for video metadata
- `OPENAI_API_KEY` - OpenAI API key for AI summarization

**Optional Variables (for proxy):****
- `PROXY_USERNAME` - Proxy authentication username
- `PROXY_PASSWORD` - Proxy authentication password
- `PROXY_HOST` - Proxy server host and port
### Proxy Setup (Optional)

A proxy is optional but recommended to avoid YouTube rate limiting, especially on cloud hosting.

**When you need a proxy:**
- Deployed on cloud platforms (Render, Heroku, Railway, etc.)
- High traffic / multiple requests
- Getting 429 (Too Many Requests) or 403 errors

**Recommended Proxy Providers:**

1. **Proxy-Cheap** (Budget-friendly: ~$5-10/month)
   - Website: https://app.proxy-cheap.com/
   - Get residential proxy credentials
   - Format: `PROXY_HOST=resi.proxy-cheap.com:31112`

2. **SmartProxy** (~$28-75/month)
   - Website: https://smartproxy.com/
   - Format: `PROXY_HOST=ph.smartproxy.com:40003`

3. **BrightData** (Enterprise, expensive)
   - Website: https://brightdata.com/

**Configuration:**
```env
PROXY_USERNAME=your_username
PROXY_PASSWORD=your_password
PROXY_HOST=resi.proxy-cheap.com:31112
```

If proxy variables are not set, the server will attempt direct connections to YouTube.

### Getting API Keys

**YouTube Data API v3:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable YouTube Data API v3
4. Go to **Credentials** → **Create Credentials** → **API Key**
5. Copy the API key

**OpenAI API:**
1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Sign up or log in
3. Go to [API Keys](https://platform.openai.com/api-keys)
4. Click **Create new secret key**
5. Copy the API key immediately (you won't see it again)
6. Note: Requires payment method on file, but offers free trial credits

### Running Locally

```bash
python server.py
```

Server will start on `http://localhost:8020`

### Running on Render.com

1. Set environment variables in Render dashboard
2. Deploy from GitHub repository

## API Endpoints

### POST / (Transcript)

Fetch transcript for a YouTube video.

**Request (Form-encoded):**
```
Content-Type: application/x-www-form-urlencoded
Body: video_id=VIDEO_ID
```

**Request (JSON):**
```json
{
  "action": "transcript",
  "video_id": "VIDEO_ID"
}
```

**Response:**
```json
[
  {
    "text": "Transcript text",
    "start": 0.0,
    "duration": 2.5
  }
]
```

### POST / (Summarize)

Generate AI summary using OpenAI (GPT-3.5-turbo).

**Request (JSON only):****
```json
{
  "action": "summarize",
  "text": "Full transcript text to summarize"
}
```

**Response:**
```json
{
  "summary": "AI-generated summary text"
}
```

### POST / (Video Details)

Get YouTube video metadata.

**Request (JSON only):**
```json
{
  "action": "video_details",
  "video_id": "VIDEO_ID"
}
```

**Response:**
```json
{
  "snippet": {
    "title": "Video title",
    "channelTitle": "Channel name",
    "description": "Video description"
  },
  "contentDetails": {
    "duration": "PT1H2M3S"
  }
}
```

**Error Response:**
```json
{
  "error": "Error message"
}
```

## Security Notes

- Never commit `.env` file with actual credentials
- Use environment variables for all sensitive data
- Proxy credentials should be kept secure
- API keys should never be exposed in frontend code

## FAQ

### Do I need a proxy?

**No, but it's recommended for production.** Try without a proxy first. If you encounter:
- `429 Too Many Requests` errors
- `Could not retrieve transcript` errors
- `403 Forbidden` from YouTube

Then add a proxy. For low-traffic personal projects on cloud hosting, **Proxy-Cheap** (~$5-10/month) is the most affordable option.

### Which proxy provider should I use?

- **Starting out / Budget:** Proxy-Cheap ($5-10/month)
- **More reliability:** SmartProxy ($28+/month)
- **Enterprise:** BrightData (expensive)

### How do I set up Proxy-Cheap?

1. Sign up at https://app.proxy-cheap.com/
2. Purchase a residential proxy plan (cheapest tier usually works)
3. Go to your proxy dashboard and get credentials
4. Add to Render environment variables:
   ```
   PROXY_USERNAME=your_username_from_proxycheap
   PROXY_PASSWORD=your_password_from_proxycheap
   PROXY_HOST=resi.proxy-cheap.com:31112
   ```
5. Redeploy your service
