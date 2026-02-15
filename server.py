from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig
from urllib.parse import parse_qs
import os
import logging
import traceback
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Load proxy details from environment variables
PROXY_USERNAME = os.environ.get('PROXY_USERNAME', '')
PROXY_PASSWORD = os.environ.get('PROXY_PASSWORD', '')
PROXY_HOST = os.environ.get('PROXY_HOST', '')  # e.g., resi.proxy-cheap.com:31112 or ph.smartproxy.com:40003

# Build proxy URL with http:// protocol (proxy itself uses HTTP, even for HTTPS destinations)
PROXY_URL = f"http://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_HOST}" if PROXY_USERNAME and PROXY_PASSWORD and PROXY_HOST else None

# Initialize YouTube Transcript API with proxy config
if PROXY_URL:
    try:
        # Create proxy config with both HTTP and HTTPS
        proxy_config = GenericProxyConfig(
            http_url=PROXY_URL,
            https_url=PROXY_URL
        )
        ytt_api = YouTubeTranscriptApi(proxy_config=proxy_config)
        logging.info(f"YouTube Transcript API initialized with proxy: {PROXY_HOST}")
    except Exception as e:
        logging.error(f"Failed to initialize proxy config: {e}")
        logging.warning("Falling back to no proxy initialization")
        ytt_api = YouTubeTranscriptApi()
else:
    ytt_api = YouTubeTranscriptApi()
    logging.info("YouTube Transcript API initialized without proxy")

# Load OpenAI API key
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

# Load YouTube Data API key
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY', '')
YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/videos"

class RequestHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        self.send_response_with_cors(200, 'text/html', self._read_file('index.html'))

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        
        # Check if JSON or form-encoded
        content_type = self.headers.get('Content-Type', '')
        
        if 'application/json' in content_type:
            # Handle JSON requests
            try:
                data = json.loads(post_data)
                action = data.get('action', 'transcript')
                
                if action == 'summarize':
                    self._handle_summarize(data)
                elif action == 'video_details':
                    self._handle_video_details(data)
                else:
                    self._handle_transcript(data.get('video_id'))
            except json.JSONDecodeError:
                response = json.dumps({"error": "Invalid JSON"})
                self.send_response_with_cors(400, 'application/json', response.encode('utf-8'))
                self.send_response_with_cors(400, 'application/json', response.encode('utf-8'))
        else:
            # Handle form-encoded requests (backwards compatibility)
            video_id = parse_qs(post_data).get('video_id', [None])[0]
            self._handle_transcript(video_id)
    
    def _handle_transcript(self, video_id):
        """Handle transcript fetching"""
        if not video_id:
            response = json.dumps({"error": "Missing video_id parameter"})
            self.send_response_with_cors(400, 'application/json', response.encode('utf-8'))
            return

        # Validate video_id format (basic check)
        if not video_id.replace('-', '').replace('_', '').isalnum():
            response = json.dumps({"error": "Invalid video_id format"})
            self.send_response_with_cors(400, 'application/json', response.encode('utf-8'))
            return

        try:
            # Fetch the transcript - will try auto-generated if manual not available
            logging.info(f"Fetching transcript for {video_id}" + (" using proxy" if PROXY_URL else " without proxy"))
            
            # Use the new API - fetch() method with language preferences
            # This will automatically try both manual and auto-generated transcripts
            fetched_transcript = ytt_api.fetch(
                video_id,
                languages=['en', 'en-US', 'en-GB']
            )
            
            # Convert to raw data format (list of dicts)
            transcript = fetched_transcript.to_raw_data()
            
            response = json.dumps(transcript)
            self.send_response_with_cors(200, 'application/json', response.encode('utf-8'))
        except Exception as e:
            logging.error(f"Error fetching transcript for video {video_id}: {e}")
            logging.error(traceback.format_exc())
            
            # Provide more specific error messages
            error_message = str(e)
            if "Could not retrieve" in error_message or "transcript" in error_message.lower():
                error_message = "Transcript not available for this video. It may be disabled or the video doesn't exist."
            elif "Subtitles are disabled" in error_message:
                error_message = "Subtitles are disabled for this video."
            elif "ProxyError" in str(type(e)) or "proxy" in error_message.lower():
                error_message = "Proxy connection failed. Please check proxy configuration and try again."
            
            error_response = json.dumps({"error": error_message})
            self.send_response_with_cors(500, 'application/json', error_response.encode('utf-8'))
    
    def _handle_summarize(self, data):
        """Handle AI summarization using OpenAI API"""
        text = data.get('text', '')
        
        if not text:
            response = json.dumps({"error": "Missing text parameter"})
            self.send_response_with_cors(400, 'application/json', response.encode('utf-8'))
            return
        
        if not OPENAI_API_KEY:
            response = json.dumps({"error": "OpenAI API key not configured on server"})
            self.send_response_with_cors(500, 'application/json', response.encode('utf-8'))
            return
        
        try:
            logging.info("Generating AI summary using OpenAI API")
            
            # Truncate text if too long (rough estimate: 1 token ≈ 4 chars)
            # Max tokens for gpt-3.5-turbo: 16385, reserve ~1500 for response and system prompt
            max_chars = 14000 * 4  # ~14000 tokens for input
            if len(text) > max_chars:
                logging.warning(f"Transcript too long ({len(text)} chars), truncating to {max_chars} chars")
                text = text[:max_chars] + "\n\n[Transcript truncated due to length]"
            
            # Call OpenAI API
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENAI_API_KEY}"
            }
            
            payload = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that creates concise, well-structured summaries of video transcripts. Format your response with clear headings using **bold** text and use proper paragraphs."
                    },
                    {
                        "role": "user",
                        "content": f"Please summarize the following video transcript:\n\n{text}"
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 1000
            }
            
            api_response = requests.post(
                OPENAI_API_URL,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if api_response.status_code != 200:
                error_msg = f"OpenAI API error: {api_response.status_code}"
                try:
                    error_data = api_response.json()
                    error_msg += f" - {error_data.get('error', {}).get('message', '')}"
                except:
                    pass
                logging.error(error_msg)
                response = json.dumps({"error": error_msg})
                self.send_response_with_cors(500, 'application/json', response.encode('utf-8'))
                return
            
            api_data = api_response.json()
            
            # Extract summary from response
            if api_data and api_data.get('choices') and len(api_data['choices']) > 0:
                choice = api_data['choices'][0]
                if choice.get('message') and choice['message'].get('content'):
                    summary = choice['message']['content'].strip()
                    response = json.dumps({"summary": summary})
                    self.send_response_with_cors(200, 'application/json', response.encode('utf-8'))
                    return
            
            # If we couldn't extract the summary
            response = json.dumps({"error": "No response from AI"})
            self.send_response_with_cors(500, 'application/json', response.encode('utf-8'))
            
        except requests.exceptions.Timeout:
            logging.error("OpenAI API request timeout")
            response = json.dumps({"error": "AI summary request timed out"})
            self.send_response_with_cors(500, 'application/json', response.encode('utf-8'))
        except Exception as e:
            logging.error(f"Error generating summary: {e}")
            logging.error(traceback.format_exc())
            error_response = json.dumps({"error": f"Failed to generate summary: {str(e)}"})
            self.send_response_with_cors(500, 'application/json', error_response.encode('utf-8'))
    
    def _handle_video_details(self, data):
        """Handle YouTube video details fetching"""
        video_id = data.get('video_id', '')
        
        if not video_id:
            response = json.dumps({"error": "Missing video_id parameter"})
            self.send_response_with_cors(400, 'application/json', response.encode('utf-8'))
            return
        
        if not YOUTUBE_API_KEY:
            response = json.dumps({"error": "YouTube API key not configured on server"})
            self.send_response_with_cors(500, 'application/json', response.encode('utf-8'))
            return
        
        try:
            logging.info(f"Fetching video details for {video_id} from YouTube API")
            
            # Call YouTube Data API
            api_response = requests.get(
                YOUTUBE_API_URL,
                params={
                    'id': video_id,
                    'key': YOUTUBE_API_KEY,
                    'part': 'snippet,contentDetails'
                },
                timeout=10
            )
            
            if api_response.status_code != 200:
                error_msg = f"YouTube API error: {api_response.status_code}"
                logging.error(error_msg)
                response = json.dumps({"error": error_msg})
                self.send_response_with_cors(500, 'application/json', response.encode('utf-8'))
                return
            
            api_data = api_response.json()
            
            # Extract video details from response
            if api_data and api_data.get('items') and len(api_data['items']) > 0:
                video_details = api_data['items'][0]
                response = json.dumps(video_details)
                self.send_response_with_cors(200, 'application/json', response.encode('utf-8'))
                return
            
            # If video not found
            response = json.dumps({"error": "Video not found"})
            self.send_response_with_cors(404, 'application/json', response.encode('utf-8'))
            
        except requests.exceptions.Timeout:
            logging.error("YouTube API request timeout")
            response = json.dumps({"error": "YouTube API request timed out"})
            self.send_response_with_cors(500, 'application/json', response.encode('utf-8'))
        except Exception as e:
            logging.error(f"Error fetching video details: {e}")
            logging.error(traceback.format_exc())
            error_response = json.dumps({"error": f"Failed to fetch video details: {str(e)}"})
            self.send_response_with_cors(500, 'application/json', error_response.encode('utf-8'))

    def _read_file(self, filename):
        file_path = os.path.join(os.path.dirname(__file__), filename)
        try:
            with open(file_path, 'r') as file:
                return file.read().encode('utf-8')
        except FileNotFoundError:
            self.send_response_with_cors(404, 'text/html', b'File not found')
            return b'File not found'

    def send_response_with_cors(self, status_code, content_type, body):
        self.send_response(status_code)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-type', content_type)
        self.end_headers()
        self.wfile.write(body)

def run(server_class=HTTPServer, handler_class=RequestHandler):
    port = int(os.environ.get('PORT', 8020))
    logging.basicConfig(level=logging.INFO)
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    logging.info(f'Starting server on port {port}...')
    httpd.serve_forever()

if __name__ == '__main__':
    run()
