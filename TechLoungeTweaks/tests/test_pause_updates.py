import sys
from pathlib import Path
import unittest
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import tweaks_engine as engine
import main

class PauseUpdatesTests(unittest.TestCase):
    def test_pause_resume_and_partial_state_use_only_update_pause_keys(self):
        values={}
        def put(h,p,n,v,*args):values[(p,n)]=v
        def get(h,p,n,default=None):return values.get((p,n),default)
        def delete(h,p,n):values.pop((p,n),None)
        with patch.object(engine,'reg_set',side_effect=put),patch.object(engine,'reg_get',side_effect=get),patch.object(engine,'reg_del_value',side_effect=delete):
            apply,resume,check=engine.t_pause_windows_updates()
            self.assertFalse(check());apply();self.assertTrue(check())
            self.assertEqual(values[(engine.WU_PAUSE_SETTINGS,'PauseUpdatesExpiryTime')],'2051-12-31T00:00:00Z')
            self.assertEqual(set(p for p,n in values),{engine.WU_PAUSE_SETTINGS,engine.WU_PAUSE_POLICY})
            values.pop((engine.WU_PAUSE_SETTINGS,'PauseQualityUpdatesEndTime'))
            self.assertFalse(check());apply();resume();self.assertFalse(check())
            self.assertFalse(any('Time' in n for p,n in values))

    def test_both_dashboard_presets_apply_pause(self):
        for mode in ('all','recommended'):
            with self.subTest(mode=mode):
                values={}
                def put(h,p,n,v,*args):values[(p,n)]=v
                def get(h,p,n,default=None):return values.get((p,n),default)
                with patch.object(engine,'reg_set',side_effect=put),patch.object(engine,'reg_get',side_effect=get):
                    apply,resume,check=engine.t_pause_windows_updates()
                    pause=Mock(apply=Mock(side_effect=apply),check=check)
                    api=main.Api.__new__(main.Api);api._tweaks=lambda:{'pause_windows_updates':pause};api._applied=set()
                    self.assertFalse(check())
                    result=main.Api.bulk_tweaks.__wrapped__(api,mode,True)
                    self.assertTrue(result['ok'])
                    pause.apply.assert_called_once()
                    self.assertIs(result['applied']['pause_windows_updates'],True)
                    self.assertNotIn('pause_windows_updates',result['skipped'])
