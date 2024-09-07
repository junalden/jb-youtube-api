from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import parse_qs
import os
import logging
import traceback

# Updated proxy details
PROXY_URL = "ph.visitxiangtan.com:40001:sp5gfg7b2l:Y7~folCwj4zlGfVs48"

class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response_with_cors(200, 'text/html', self._read_file('index.html'))

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        video_id = parse_qs(post_data).get('video_id', [None])[0]

        if not video_id:
            response = json.dumps({"error": "Missing video_id"})
            self.send_response_with_cors(400, 'application/json', response.encode('utf-8'))
            return

        try:
            # Fetch the transcript using the proxy
            transcript = YouTubeTranscriptApi.get_transcript(
                video_id,
                proxies={"https": PROXY_URL}
            )
            response = json.dumps(transcript)
            self.send_response_with_cors(200, 'application/json', response.encode('utf-8'))
        except Exception as e:
            logging.error(f"An error occurred: {e}")
            logging.error(traceback.format_exc())
            error_response = json.dumps({"error": str(e)})
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
