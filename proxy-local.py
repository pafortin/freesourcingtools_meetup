"""
Proxy local pour tester meetup-pipeline via Serper Google Search.
Relaie les requêtes POST vers l'API Serper.

Usage :
    python proxy-local.py

Dans meetup-pipeline.astro :
    const SERPER_URL = 'http://localhost:8787';

Laisser tourner le terminal pendant le test. Ctrl+C pour arrêter.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request
import sys

PORT = 8787
SERPER_API = 'https://google.serper.dev/search'

CORS = {
    'Access-Control-Allow-Origin':  '*',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, X-API-KEY',
}


class ProxyHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        print(f'[proxy] {fmt % args}')

    def send_cors(self):
        for k, v in CORS.items():
            self.send_header(k, v)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors()
        self.end_headers()

    def do_GET(self):
        self._respond(200, b'{"status":"Proxy Serper actif. Utilise POST /search."}')

    def do_POST(self):
        length   = int(self.headers.get('Content-Length', 0))
        body     = self.rfile.read(length)
        api_key  = self.headers.get('X-API-KEY', '')

        if not api_key:
            self._respond(401, b'{"error":"Missing X-API-KEY header"}')
            return

        req = urllib.request.Request(
            SERPER_API,
            data=body,
            headers={
                'Content-Type': 'application/json',
                'X-API-KEY':    api_key,
            },
            method='POST',
        )

        try:
            with urllib.request.urlopen(req) as resp:
                result = resp.read()
                status = resp.status
        except urllib.error.HTTPError as e:
            result = e.read()
            status = e.code
        except Exception as e:
            self._respond(502, f'{{"error":"{e}"}}'.encode())
            return

        self._respond(status, result)

    def _respond(self, status, body):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_cors()
        self.end_headers()
        self.wfile.write(body)


if __name__ == '__main__':
    server = HTTPServer(('localhost', PORT), ProxyHandler)
    print(f'Proxy Serper démarré → http://localhost:{PORT}')
    print('Dans meetup-pipeline.astro, utilise :')
    print(f"  const SERPER_URL = 'http://localhost:{PORT}';")
    print('Ctrl+C pour arrêter.\n')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nProxy arrêté.')
        sys.exit(0)
