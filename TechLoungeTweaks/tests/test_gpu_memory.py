import sys
from pathlib import Path
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import gpu_memory as gpu
import sysinfo


class MemoryTests(unittest.TestCase):
    def test_large_capacities_and_small_integrated_memory(self):
        for gb in (8, 16, 32):
            adapter = dict(name='RTX 4060 Ti', vendor=0x10de, device=0x2803,
                           subsys=1, revision=1, memory=gb * 1024**3)
            row = dict(Name='RTX 4060 Ti', PNPDeviceID=r'PCI\VEN_10DE&DEV_2803&SUBSYS_00000001&REV_01')
            self.assertEqual(gpu.format_memory(gpu.dedicated_memory(row, [adapter])), f'{gb} GB')
        self.assertEqual(gpu.format_memory(128 * 1024**2), '128 MB')

    def test_ambiguous_adapters_are_not_guessed(self):
        adapters = [dict(name='GPU', memory=n * 1024**3) for n in (8, 16)]
        self.assertIsNone(gpu.dedicated_memory({'Name': 'GPU'}, adapters))
        self.assertIsNone(gpu.dedicated_memory({'Name': 'Other'}, adapters))

    def test_pci_mismatch_does_not_fall_back_to_name(self):
        self.assertIsNone(gpu.dedicated_memory(
            {'Name': 'GPU', 'PNPDeviceID': r'PCI\VEN_10DE&DEV_0001'},
            [dict(name='GPU', vendor=0x10de, device=2, memory=8*1024**3)]))

    def test_failed_read_does_not_use_truncated_wmi_memory(self):
        with patch.object(sysinfo, '_q', return_value=[{'Name':'GPU', 'AdapterRAM':4294967295}]), patch.object(sysinfo, 'adapters', return_value=[]):
            self.assertEqual(dict(sysinfo.graphics()[0])['Dedicated VRAM'], 'N/A')
