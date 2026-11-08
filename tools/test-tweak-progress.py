"""Exercise production bulk methods without importing Windows-changing modules."""
import ast
from pathlib import Path
import threading
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
tree = ast.parse((ROOT / 'TechLoungeTweaks/src/main.py').read_text(encoding='utf-8-sig'))
api = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Api')
methods = []
for method in api.body:
    if isinstance(method, ast.FunctionDef) and method.name in ('_bulk_targets', 'bulk', 'bulk_tweaks', '_read_tweak'):
        if method.name != '_read_tweak':
            method.decorator_list = []
        methods.append(method)
namespace = {'tweak_undo': types.SimpleNamespace(LOCK=threading.RLock())}
fixture_class = ast.ClassDef(name='BulkFixture', bases=[], keywords=[], body=methods, decorator_list=[])
exec(compile(ast.fix_missing_locations(ast.Module(body=[fixture_class], type_ignores=[])), '<production bulk methods>', 'exec'), namespace)


class ProgressTests(unittest.TestCase):
    def setUp(self):
        self.api = namespace['BulkFixture']()
        self.values = {'first': False, 'second': False, 'other': False}
        self.trace = []
        self.api._applied = set()
        self.api.RECOMMENDED_KEYS = {'first', 'second'}
        self.tweaks = {key: types.SimpleNamespace(category='Privacy' if key != 'other' else 'Graphics',
            check=lambda key=key: self.values[key]) for key in self.values}
        self.api._tweaks = lambda: self.tweaks
        self.api._emit = lambda event, data: self.trace.append((event, data))

        def toggle(key, want):
            self.trace.append(('write', key))
            self.values[key] = want
            return {'ok': True, 'applied': want}
        self.api.toggle = toggle

    def test_each_readback_arrives_before_next_write(self):
        result = self.api.bulk('Privacy', True, 42)
        self.assertTrue(result['ok'])
        self.assertEqual(self.trace[:4], [
            ('tweak_progress', {'operation': 42, 'key': 'first', 'phase': 'working', 'completed': 0, 'total': 2}),
            ('write', 'first'),
            ('tweak_progress', {'operation': 42, 'key': 'first', 'phase': 'verified', 'applied': True,
                'message': '', 'completed': 1, 'total': 2}),
            ('tweak_progress', {'operation': 42, 'key': 'second', 'phase': 'working', 'completed': 1, 'total': 2})])
        self.assertFalse(self.values['other'])

    def test_failed_change_is_not_reported_applied(self):
        self.api.toggle = lambda key, want: {'ok': False, 'applied': False, 'message': 'Policy blocked it'}
        result = self.api.bulk('Privacy', True, 7)
        self.assertFalse(result['ok'])
        self.assertEqual(set(result['failed']), {'first', 'second'})
        self.assertEqual(self.trace[1][1]['phase'], 'failed')
        self.assertIs(self.trace[1][1]['applied'], False)

    def test_final_readback_remains_authoritative(self):
        self.api.toggle = lambda key, want: {'ok': True, 'applied': True}
        result = self.api.bulk('Privacy', True, 9)
        self.assertFalse(result['ok'])
        self.assertIs(result['applied']['first'], False)

    def test_invalid_identifiers_do_not_write(self):
        for identifier in (True, 0, -1, 2147483648, '42'):
            self.assertFalse(self.api.bulk('Privacy', True, identifier)['ok'])
        self.assertEqual(self.trace, [])

    def test_recommended_and_legacy_calls_keep_scope(self):
        unrelated_reads = []
        self.tweaks['other'].check = lambda: unrelated_reads.append('other') or False
        result = self.api.bulk_tweaks('recommended', False, 12)
        self.assertTrue(result['ok'])
        self.assertEqual(result['skipped'], ['other'])
        self.assertFalse(self.values['other'])
        self.assertNotIn('other', result['applied'])
        self.assertEqual(unrelated_reads, [])
        self.assertTrue(self.api.bulk('Privacy', False)['ok'])
        self.assertFalse(self.api.bulk_tweaks('all', False, 13)['ok'])


if __name__ == '__main__':
    unittest.main()
