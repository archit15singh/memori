"""Small loopback companion for the existing Markdown vault and retrieval API."""
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import subprocess
import sys
import threading
from urllib.parse import parse_qs, urlsplit

from lorevell import PyVault

ASSETS = Path(__file__).parent / 'data' / 'ui'


def summary(note):
    lines = note['content'].strip().splitlines()
    title = next((line[2:].strip() for line in lines if line.startswith('# ')), note['path'])
    metadata = note['metadata']
    return {'id': note['id'], 'path': note['path'], 'title': title,
            'type': metadata.get('type') if isinstance(metadata.get('type'), str) else '',
            'tags': [tag for tag in metadata.get('tags', []) if isinstance(tag, str)] if isinstance(metadata.get('tags'), list) else [],
            'excerpt': ' '.join(line for line in lines if line and not line.startswith('#'))[:220]}


class CompanionServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, root, port=0):
        self.root = Path(root).resolve()
        self.vault = PyVault(str(self.root))
        self.token = secrets.token_urlsafe(32)
        self.lock = threading.RLock()
        super().__init__(('127.0.0.1', port), Handler)

    @property
    def url(self):
        return f'http://127.0.0.1:{self.server_port}'


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # Search text and note IDs are not written to a request log.

    def respond(self, status, value, content_type='application/json; charset=utf-8'):
        body = (json.dumps(value, ensure_ascii=False).encode() if content_type.startswith('application/json')
                else value if isinstance(value, bytes) else value.encode())
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def allowed(self, api=False):
        allowed = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
        host = self.headers.get('Host', '')
        origin = self.headers.get('Origin')
        if host not in allowed or (origin and origin not in {'http://' + h for h in allowed}):
            self.respond(403, {'error': 'This workspace is available only from its local address.'})
            return False
        if api and not secrets.compare_digest(self.headers.get('X-Lorevell-Token', '').encode(), self.server.token.encode()):
            self.respond(403, {'error': 'Reload the workspace to reconnect.'})
            return False
        return True

    def do_GET(self):
        self.handle_request(False)

    def do_POST(self):
        self.handle_request(True)

    def handle_request(self, post):
        route = urlsplit(self.path)
        if not self.allowed(api=route.path.startswith('/api/')):
            return
        try:
            if not post and route.path in ('/', '/app.js', '/style.css'):
                name, mime = {'/': ('index.html', 'text/html'), '/app.js': ('app.js', 'text/javascript'), '/style.css': ('style.css', 'text/css')}[route.path]
                value = (ASSETS / name).read_text().replace('__TOKEN__', self.server.token)
                return self.respond(200, value, mime + '; charset=utf-8')
            params = parse_qs(route.query, max_num_fields=10)
            if post:
                if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                    raise ValueError('Expected JSON request')
                length = int(self.headers.get('Content-Length', '0'))
                if self.headers.get('Transfer-Encoding') or not 0 < length <= 65536:
                    raise ValueError('Request body must be between 1 and 65536 bytes')
                self.connection.settimeout(15)
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict):
                    raise ValueError('Expected a JSON object')
            else:
                body = {}
            mode = body.get('mode', params.get('mode', ['keyword'])[0])
            if mode not in ('keyword', 'hybrid'):
                raise ValueError('Choose keyword or hybrid search')
            with self.server.lock:
                vault = self.server.vault
                if not post and route.path == '/api/catalog':
                    report = vault.index(embeddings=False)
                    notes = [summary(n) for n in vault.notes()]
                    return self.respond(200, {'vault': str(self.server.root), 'name': self.server.root.name,
                                             'total': len(notes), 'notes': notes[:500], 'truncated': len(notes) > 500,
                                             'types': sorted({n['type'] for n in notes if n['type']}), 'index': report,
                                             'indexed_at': datetime.now(timezone.utc).isoformat()})
                if not post and route.path == '/api/search':
                    query = params.get('q', [''])[0].strip()
                    if not query or len(query) > 1000:
                        raise ValueError('Enter a question or keyword (up to 1000 characters)')
                    vault.index(embeddings=mode == 'hybrid')
                    kind = params.get('type', [''])[0]
                    result = vault.search(query, limit=40, graph_limit=3, text_only=mode == 'keyword',
                                          filter={'type': kind} if kind else None)
                    return self.respond(200, {'matches': [dict(summary(hit['note']), score=hit['score']) for hit in result['matches']],
                                             'context': [dict(summary(hit['note']), via=hit['via']) for hit in result['context']]})
                if not post and route.path == '/api/note':
                    vault.index(embeddings=False)
                    view = vault.show(params.get('id', [''])[0], neighbor_limit=50)
                    return self.respond(200, dict(view, title=summary(view['note'])['title'],
                                                  absolute_path=str(self.server.root / view['note']['path'])))
                if post and route.path == '/api/index':
                    return self.respond(200, vault.index(embeddings=mode == 'hybrid'))
                if post and route.path == '/api/notes':
                    title, content, kind = body.get('title'), body.get('content'), body.get('type', 'note')
                    if not isinstance(title, str) or not title.strip() or len(title) > 140 or '\n' in title or '\r' in title:
                        raise ValueError('Add a single-line title, up to 140 characters')
                    if not isinstance(content, str) or not content.strip() or len(content) > 32768:
                        raise ValueError('Add a lesson, up to 32768 characters')
                    if kind not in ('note', 'procedure', 'decision'):
                        raise ValueError('Choose note, procedure or decision')
                    note = vault.add(f'# {title.strip()}\n\n{content.strip()}', metadata={'type': kind})
                    warning = None
                    try:
                        vault.index(embeddings=False)
                    except RuntimeError as error:
                        warning = f'Note saved to {note["path"]}, but indexing needs attention: {error}'
                    return self.respond(201, {'note': note, 'warning': warning, 'absolute_path': str(self.server.root / note['path'])})
            self.respond(404, {'error': 'Not found'})
        except (ValueError, RuntimeError, OSError) as error:
            self.respond(422, {'error': str(error)})
        except BaseException as error:
            if isinstance(error, (KeyboardInterrupt, SystemExit)):
                raise
            # PyO3 model-init failures are PanicException (not Exception). Keep the UI recoverable.
            self.respond(500, {'error': f'Search could not complete: {error}. Try keyword mode.'})


def serve(root, port=8765, open_browser=True):
    server = CompanionServer(root, port)
    print(f'Lorevell workspace: {server.url}', flush=True)
    print(f'Vault: {server.root}\nPress Ctrl+C to stop.', flush=True)
    if open_browser:
        if sys.platform == 'darwin':
            subprocess.run(['open', '-a', 'Brave Browser', server.url], check=False)
        else:
            import webbrowser
            webbrowser.open(server.url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
