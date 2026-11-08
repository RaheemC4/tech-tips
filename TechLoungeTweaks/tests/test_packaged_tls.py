import ast
import io
from pathlib import Path
import ssl
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP / 'src'))
import companion_worker as worker


class PackagedTlsTests(unittest.TestCase):
    def spec_data(self, runtime):
        tree = ast.parse((APP / 'src/TechLoungeTweaks.spec').read_text(encoding='utf-8'))
        setup = []
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(isinstance(n, ast.Name) and n.id == 'binaries' for n in node.targets):
                break
            setup.append(node)
        namespace = {}
        with patch.object(ssl, '__file__', str(runtime / 'ssl.py')):
            exec(compile(ast.Module(body=setup, type_ignores=[]), '<production packaging setup>', 'exec'), namespace)
        return namespace['datas']

    def test_runtime_policy_is_collected_beside_frozen_ssl(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root)
            policy = folder / 'codex-rejected-cas.pem'
            policy.write_bytes(b'Inert packaging fixture')
            self.assertIn((str(policy), '.'), self.spec_data(folder))

    def test_standard_python_does_not_require_a_codex_resource(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertFalse(any('codex-rejected' in item[0] for item in self.spec_data(Path(root))))

    def test_worker_reads_bounded_https_bytes_with_default_verification(self):
        response = io.BytesIO(b'verified fixture bytes')
        response.status = 206
        context = types.SimpleNamespace(verify_mode=ssl.CERT_REQUIRED, check_hostname=True)
        with patch('ssl.create_default_context', return_value=context), patch('urllib.request.urlopen', return_value=response) as opening:
            self.assertEqual(worker.execute('https-probe', None, lambda _: None),
                             {'ok': True, 'certificate_verification': True, 'status': 206, 'bytes_received': 22})
            request = opening.call_args.args[0]
            self.assertEqual(request.full_url, 'https://api.github.com/repos/RaheemC4/tech-tips')
            self.assertIs(opening.call_args.kwargs['context'], context)

    def test_worker_refuses_disabled_verification_and_custom_addresses(self):
        for mode, hostname in ((ssl.CERT_NONE, True), (ssl.CERT_REQUIRED, False)):
            with patch('ssl.create_default_context', return_value=types.SimpleNamespace(verify_mode=mode, check_hostname=hostname)), patch('urllib.request.urlopen') as opening:
                with self.assertRaises(RuntimeError):
                    worker.https_probe()
                opening.assert_not_called()
        with patch.object(worker, 'https_probe') as probe:
            with self.assertRaises(ValueError):
                worker.execute('https-probe', 'https://untrusted.example', lambda _: None)
            probe.assert_not_called()


if __name__ == '__main__':
    unittest.main()
