import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import companion_worker as worker


class CompanionWorkerTests(unittest.TestCase):
    def test_power_listing_preserves_local_names_and_active_state(self):
        text = 'Power Scheme GUID: 381b4222-f694-41f0-9685-ff5bb260df2e  (Balanced) *\n'
        with patch.object(worker, 'power', return_value=text):
            self.assertEqual(worker.plans(), [{'id': '381b4222-f694-41f0-9685-ff5bb260df2e', 'name': 'Balanced', 'active': True}])

    def test_missing_ultimate_is_created_then_activated_and_checked(self):
        with patch.object(worker, 'plans', side_effect=[[{'id': 'other', 'name': 'Balanced', 'active': True}],
                         [{'id': worker.MANAGED_ULTIMATE, 'name': 'Ultimate Performance', 'active': True}]]), patch.object(worker, 'power') as power:
            result = worker.select_plan('ultimate')
            self.assertEqual([c.args[0] for c in power.call_args_list], [
                ['/duplicatescheme', worker.ULTIMATE, worker.MANAGED_ULTIMATE], ['/setactive', worker.MANAGED_ULTIMATE]])
            self.assertTrue(result['plans'][0]['active'])

    def test_existing_ultimate_is_reused(self):
        available = [{'id': 'existing', 'name': 'Ultimate Performance', 'active': True}]
        with patch.object(worker, 'plans', return_value=available), patch.object(worker, 'power') as power:
            worker.select_plan('ultimate')
            power.assert_called_once_with(['/setactive', 'existing'])

    def test_unlisted_plan_is_rejected_without_executing(self):
        with patch.object(worker, 'plans', return_value=[{'id': 'known'}]), patch.object(worker, 'power') as power:
            with self.assertRaises(ValueError): worker.select_plan('bad & command')
            power.assert_not_called()

    def test_unknown_action_is_rejected(self):
        with self.assertRaises(ValueError): worker.execute('shell', 'anything', lambda _: None)

    def test_worker_rejects_arbitrary_output_paths(self):
        self.assertEqual(worker.entry([r'C:\arbitrary.txt', 'plans', 'bnVsbA==']), 2)


if __name__ == '__main__': unittest.main()
