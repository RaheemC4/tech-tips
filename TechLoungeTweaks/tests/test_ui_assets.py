"""Exercise HTTP upgrade behaviour with identical extraction timestamps."""
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from wsgiref.util import setup_testing_defaults

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from ui_assets import create_ui_app


def request(app, path):
    env = {}
    setup_testing_defaults(env)
    env.update(PATH_INFO=path, **{'wsgi.input': io.BytesIO()})
    result = {}

    def start(status, headers, exc_info=None):
        result.update(status=status, headers=dict(headers))

    response = app(env, start)
    try:
        result['body'] = b''.join(response)
    finally:
        if hasattr(response, 'close'):
            response.close()
    return result


class UIAssetsTests(unittest.TestCase):
    def test_upgrade_changes_asset_address_even_with_same_size_and_timestamp(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'index.html').write_text('<script src="app.js"></script>')
            script = root / 'app.js'
            script.write_bytes(b'old UI')
            os.utime(script, (1000000000, 1000000000))
            old = create_ui_app(root)
            old_url = request(old, '/')['headers']['Location']
            self.assertEqual(request(old, old_url.replace('index.html', 'app.js'))['body'], b'old UI')
            script.write_bytes(b'new UI')
            os.utime(script, (1000000000, 1000000000))
            new = create_ui_app(root)
            entry = request(new, '/')
            new_url = entry['headers']['Location']
            self.assertNotEqual(new_url, old_url)
            self.assertEqual(entry['headers']['Cache-Control'], 'no-store')
            asset = request(new, new_url.replace('index.html', 'app.js'))
            self.assertEqual(asset['body'], b'new UI')
            self.assertEqual(asset['headers']['Cache-Control'], 'no-store')
            self.assertTrue(request(new, old_url)['status'].startswith('404'))
            self.assertEqual(request(create_ui_app(root), '/')['headers']['Location'], new_url)

    def test_assets_cannot_read_outside_web_root(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            root = base / 'web'
            root.mkdir()
            (root / 'index.html').write_text('interface')
            (base / 'private.txt').write_text('not a UI asset')
            app = create_ui_app(root)
            url = request(app, '/')['headers']['Location']
            result = request(app, url.replace('index.html', '../private.txt'))
            self.assertTrue(result['status'].startswith('403'))
            self.assertNotIn(b'not a UI asset', result['body'])
