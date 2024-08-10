from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import parse_qs
import os
import logging
import traceback

class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        file_path = os.path.join(os.path.dirname(__file__), 'index.html')
        try:
            with open(file_path, 'r') as file:
                self.wfile.write(file.read().encode('utf-8'))
        except FileNotFoundError:
            self.send_response(404)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'File not found')

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        video_id = parse_qs(post_data).get('video_id', [None])[0]

        if not video_id:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Missing video_id"}).encode('utf-8'))
            return

        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            response = json.dumps(transcript)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(response.encode('utf-8'))
        except Exception as e:
            logging.error(f"An error occurred: {e}")
            logging.error(traceback.format_exc())
            error_response = json.dumps({"error": str(e)})
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(error_response.encode('utf-8'))

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
