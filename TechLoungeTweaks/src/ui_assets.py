"""Serve packaged UI assets without reusing a previous release's WebView cache."""
import hashlib
from pathlib import Path

from bottle import Bottle, HTTPResponse, static_file


def create_ui_app(root):
    root = Path(root).resolve()
    # Include names and bytes, not timestamps: extracted releases can share mtimes.
    digest = hashlib.sha256()
    for path in sorted(root.rglob('*')):
        if path.is_file():
            digest.update(path.relative_to(root).as_posix().encode('utf-8') + b'\0')
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    prefix = '/ui/' + digest.hexdigest() + '/'
    app = Bottle()

    @app.get('/')
    def entry():
        return HTTPResponse(status=302, headers={
            'Location': prefix + 'index.html', 'Cache-Control': 'no-store'})

    @app.get(prefix + '<file:path>')
    def asset(file):
        response = static_file(file, root=str(root))
        # Set headers on the returned response. Bottle replaces global response
        # headers when a route returns an HTTPResponse (as static_file does).
        response.set_header('Cache-Control', 'no-store')
        return response

    return app
