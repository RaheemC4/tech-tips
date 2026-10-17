import sys
import tempfile
import unittest
import uuid
import winreg
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import main
import cleanup
import tweaks_engine as engine
import tweak_undo
import tweak_snapshots


class UndoTests(unittest.TestCase):
    def setUp(self):
        self.path = 'Software\\TechLoungeUndoTests\\' + uuid.uuid4().hex
        winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, self.path).Close()

    def tearDown(self):
        def remove(path):
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_READ) as key:
                children = [winreg.EnumKey(key, i) for i in range(winreg.QueryInfoKey(key)[0])]
            for child in children:
                remove(path + '\\' + child)
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path)
        remove(self.path)

    def tweak(self, path=None, name='value', on=1, off=0):
        return engine.Tweak('test', 'Test', 'Test', 'Test', *engine.simple_reg(
            winreg.HKEY_CURRENT_USER, path or self.path, name, on, off))

    def test_custom_value_type_and_absence_are_restored(self):
        for value, kind in [(7, winreg.REG_DWORD), ('custom', winreg.REG_SZ), (b'\x01\x02',winreg.REG_BINARY), (['one','two'],winreg.REG_MULTI_SZ)]:
            with self.subTest(kind=kind):
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER,self.path,0,winreg.KEY_WRITE) as key:
                    winreg.SetValueEx(key,'value',0,kind,value)
                t=self.tweak();t.apply();t.revert()
                self.assertEqual(t.undo.restore(),{})
                self.assertEqual(tweak_undo.read_value(winreg.HKEY_CURRENT_USER,self.path,'value'),(value,kind))
        t=self.tweak(self.path+'\\new\\leaf','missing');t.apply()
        self.assertEqual(t.undo.restore(),{})
        with self.assertRaises(FileNotFoundError):winreg.OpenKey(winreg.HKEY_CURRENT_USER,self.path+'\\new')

    def test_shared_value_keeps_first_original_and_new_session_is_noop(self):
        a=self.tweak(on=1);b=self.tweak(on=2);b.undo=a.undo
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,self.path,0,winreg.KEY_WRITE) as key:
            winreg.SetValueEx(key,'value',0,winreg.REG_DWORD,7)
        a.apply();b.apply()
        self.assertEqual(a.undo.restore(),{})
        self.assertEqual(engine.reg_get(winreg.HKEY_CURRENT_USER,self.path,'value'),7)
        self.assertEqual(self.tweak().undo.restore(),{})
        self.assertEqual(engine.reg_get(winreg.HKEY_CURRENT_USER,self.path,'value'),7)

    def test_successful_undo_resets_created_key_tracking_for_next_cycle(self):
        path=self.path+'\\cycle'
        t=self.tweak(path);t.apply()
        self.assertEqual(t.undo.restore(),{})
        self.assertEqual(t.undo.created_keys,set())
        winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER,path).Close()
        t.apply();t._revert=lambda:engine.reg_del_tree('HKCU',path);t.revert()
        self.assertEqual(t.undo.restore(),{})
        winreg.OpenKey(winreg.HKEY_CURRENT_USER,path).Close()
        self.assertIsNone(tweak_undo.read_value(winreg.HKEY_CURRENT_USER,path,'value'))

    def test_partial_failure_preserves_undo_and_failed_restore_is_retryable(self):
        t=self.tweak()
        def partial():
            engine.reg_set(winreg.HKEY_CURRENT_USER,self.path,'value',9)
            raise OSError('second write refused')
        t._apply=partial
        with self.assertRaises(OSError):t.apply()
        with patch.object(winreg,'DeleteValue',side_effect=PermissionError('locked')):
            self.assertTrue(t.undo.restore())
        self.assertEqual(t.undo.restore(),{})
        self.assertIsNone(tweak_undo.read_value(winreg.HKEY_CURRENT_USER,self.path,'value'))

    def test_capture_failure_prevents_write(self):
        t=self.tweak()
        with patch.object(tweak_undo,'read_value',side_effect=PermissionError('capture denied')):
            with self.assertRaises(PermissionError):t.apply()
        self.assertIsNone(tweak_undo.read_value(winreg.HKEY_CURRENT_USER,self.path,'value'))

    def test_tree_delete_preserves_original_values_and_created_key_absence(self):
        for existed in (False, True):
            path=self.path+'\\tree'
            if existed:
                with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER,path) as key:
                    winreg.SetValueEx(key,'custom',0,winreg.REG_SZ,'original')
                winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER,path+'\\empty').Close()
            t=self.tweak(path+'\\leaf','value')
            t.apply()
            t._revert=lambda: engine.reg_del_tree('HKCU',path)
            t.revert()
            self.assertEqual(t.undo.restore(),{})
            if existed:
                self.assertEqual(tweak_undo.read_value(winreg.HKEY_CURRENT_USER,path,'custom'),('original',winreg.REG_SZ))
                winreg.OpenKey(winreg.HKEY_CURRENT_USER,path+'\\empty').Close()
            else:
                with self.assertRaises(FileNotFoundError):winreg.OpenKey(winreg.HKEY_CURRENT_USER,path)

    def test_external_power_and_bcd_restore_exact_original(self):
        guid='11111111-2222-3333-4444-555555555555'
        with patch.object(tweak_snapshots,'checked',side_effect=[guid,'',guid]) as cmd:
            restore=tweak_snapshots.capture_external('ultimate_power');restore()
            self.assertEqual(cmd.call_args_list[1].args[0],['powercfg','/setactive',guid])
        with patch.object(tweak_snapshots,'checked',side_effect=['identifier {current}','disabledynamictick Yes','','identifier {current}']) as cmd:
            restore=tweak_snapshots.capture_external('dynamic_tick');restore()
            self.assertEqual(cmd.call_args_list[2].args[0],['bcdedit','/deletevalue','{current}','disabledynamictick'])

    def test_mixed_firewall_values_restore_per_profile(self):
        state='[{"Name":"Domain","Notify":"True"},{"Name":"Private","Notify":"False"}]'
        with patch.object(tweak_snapshots,'ps_checked',side_effect=[state,'','',state]) as ps:
            restore=tweak_snapshots.capture_external('firewall_notify');restore()
            self.assertIn("-Name 'Domain' -NotifyOnListen 'True'",ps.call_args_list[1].args[0])
            self.assertIn("-Name 'Private' -NotifyOnListen 'False'",ps.call_args_list[2].args[0])


    def test_external_snapshot_scripts_parse_without_running_them(self):
        import json, subprocess
        samples = {
            'mem_compression':[{'MemoryCompression':True}],
            'page_combining':[{'PageCombining':False}],
            'sysmain':[{'Name':'SysMain','Status':'Paused'}],
            'diagtrack':[{'Name':'DiagTrack','Status':'Stopped'}],
            'firewall_notify':[{'Name':'Domain','Notify':'NotConfigured'}],
            'nic_offload':[{'Chimney':'Disabled','ReceiveSegmentCoalescing':'Enabled','PacketCoalescingFilter':'Disabled'}],
            'usb_power_mgmt':[{'InstanceName':"USB\\test's device",'Enable':True}],
            'nv_telemetry':[{'TaskPath':'\\NVIDIA\\','TaskName':"NvTmRep's test",'Enabled':False}],
        }
        scripts=[]
        for key, rows in samples.items():
            payload=json.dumps(rows)
            with patch.object(tweak_snapshots,'ps_checked',side_effect=[payload,'',payload]) as ps:
                restore=tweak_snapshots.capture_external(key);restore()
                scripts.extend(call.args[0] for call in ps.call_args_list)
        with tempfile.TemporaryDirectory() as directory:
            file=Path(directory)/'scripts.json';file.write_text(json.dumps(scripts),encoding='utf-8')
            command='$scripts=Get-Content -Raw -LiteralPath '+tweak_snapshots.quote(file)+' | ConvertFrom-Json; foreach($s in $scripts){$e=$null;[void][System.Management.Automation.Language.Parser]::ParseInput($s,[ref]$null,[ref]$e);if($e.Count){$e | Out-String;exit 1}}'
            result=subprocess.run(['powershell','-NoProfile','-Command',command],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)


class BulkTests(unittest.TestCase):
    def api(self, tweaks):
        api=main.Api.__new__(main.Api);api._tweaks=lambda:tweaks;api._applied=set()
        return api

    def test_bulk_returns_refusal_noop_unknown_and_verified_success(self):
        refused=Mock(category='Test',error=None);refused.apply.side_effect=PermissionError('refused');refused.check.return_value=False
        noop=Mock(category='Test',error=None);noop.check.return_value=False
        unknown=Mock(category='Test',error=None);unknown.check.side_effect=OSError('cannot read')
        good=Mock(category='Test',error=None);good.check.return_value=True
        api=self.api(dict(refused=refused,noop=noop,unknown=unknown,good=good))
        for result in [api.bulk('Test',True),api.bulk_tweaks('all',True)]:
            self.assertFalse(result['ok'])
            self.assertEqual(set(result['failed']),{'refused','noop','unknown'})
            self.assertEqual(result['applied'],dict(refused=False,noop=False,unknown=None,good=True))

    def test_restore_never_reverts_untouched_tweaks(self):
        t=Mock(error=None);t.undo=tweak_undo.SessionUndo();t.check.return_value=False
        result=self.api({'untouched':t}).bulk_tweaks('revert')
        self.assertTrue(result['ok']);t.apply.assert_not_called();t.revert.assert_not_called()


class CleanupTests(unittest.TestCase):
    def test_bridge_rejects_arbitrary_paths_before_any_deletion(self):
        api=main.Api.__new__(main.Api);api._emit=Mock()
        with patch.object(cleanup,'clean') as clean:
            for selection in [[{'name':'bad','path':'C:\\Windows','kind':'files'}],['C:\\Windows'],['unknown'],None]:
                self.assertFalse(api.clean_run(selection)['ok'])
            clean.assert_not_called()
        with patch.object(cleanup,'_paths',return_value=[('Temp','C:\\test-temp','files',True,'Temp')]),patch.object(cleanup,'clean',return_value=(12,0,[])) as clean:
            self.assertTrue(api.clean_run(['user_temp','user_temp'])['ok'])
            self.assertEqual(clean.call_args.args[0],[('Temp','C:\\test-temp','files')])

    def test_cleanup_skips_junction_and_preserves_outside_file(self):
        import subprocess,os
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)/'cache';root.mkdir();outside=Path(folder)/'outside';outside.mkdir()
            (root/'remove.tmp').write_bytes(b'12345');(outside/'keep.txt').write_text('keep')
            link=root/'junction'
            subprocess.run(['cmd','/c','mklink','/J',str(link),str(outside)],check=True,capture_output=True)
            try:
                self.assertEqual(cleanup._dir_size(str(root)),(5,1))
                freed,skipped=cleanup._purge_dir(str(root))
                self.assertEqual(freed,5);self.assertGreaterEqual(skipped,1)
                self.assertEqual((outside/'keep.txt').read_text(),'keep')
                self.assertFalse((root/'remove.tmp').exists())
                self.assertEqual(cleanup._purge_dir(str(link)),(0,1))
            finally:os.rmdir(link)

if __name__=='__main__':unittest.main()
