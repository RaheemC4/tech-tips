import ctypes
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from tool_windows import WindowLink, FloatingTools, ToolSurface

class Native:
    def __init__(self):
        self.bounds={1:(100,100,1300,900),2:(128,190,1272,872)}
        self.writes=[]
    def GetWindowRect(self,hwnd,out):
        out._obj.left,out._obj.top,out._obj.right,out._obj.bottom=self.bounds[hwnd];return 1
    def GetDpiForWindow(self,hwnd): return 96
    def IsIconic(self,hwnd): return False
    def IsZoomed(self,hwnd): return False
    def SetWindowPos(self,hwnd,after,x,y,w,h,flags):
        old=self.bounds[hwnd]
        if flags&1: w,h=old[2]-old[0],old[3]-old[1]
        self.bounds[hwnd]=(x,y,x+w,y+h);self.writes.append(hwnd)
    def move(self,hwnd,dx,dy):
        a,b,c,d=self.bounds[hwnd];self.bounds[hwnd]=(a+dx,b+dy,c+dx,d+dy)

class MovementTests(unittest.TestCase):
    def test_chrome_repair_preserves_windows_minimized_state(self):
        u=Mock();u.GetWindowLongPtrW.return_value=0x20CF0000
        surface=ToolSurface.__new__(ToolSurface)
        surface.user=u;surface.hwnd=22;surface.key='bcu';surface.strip=0x21CF0000
        with patch('tool_windows.chrome_insets',return_value=(1,0,1)):
            self.assertTrue(surface.ensure_chrome())
        u.SetWindowLongPtrW.assert_called_once_with(22,-16,0x20000000)

    def test_tool_drags_move_host_without_writing_back_or_feedback(self):
        u=Native();link=WindowLink(u,1,2);link.dragging=2
        for _ in range(100):
            u.move(2,3,-2);link.changed(2)
            link.changed(1);link.changed(2) # queued notifications of our own work
            self.assertEqual(u.bounds[2][0]-u.bounds[1][0],28)
            self.assertEqual(u.bounds[2][1]-u.bounds[1][1],90)
        self.assertEqual(u.writes,[1]*100)
    def test_host_drags_move_tool_without_feedback(self):
        u=Native();link=WindowLink(u,1,2)
        for _ in range(100):
            u.move(1,-2,3);link.changed(1);link.changed(2);link.changed(1)
        self.assertEqual(u.writes,[2]*100)
    def test_hidden_tools_do_not_move_host(self):
        u=Native();link=WindowLink(u,1,2,lambda:False)
        u.move(2,100,100);link.changed(2);self.assertEqual(u.writes,[])
    def test_programmatic_tool_movement_does_not_move_host(self):
        u=Native();link=WindowLink(u,1,2)
        before=u.bounds[1];u.move(2,-32000,-32000);link.changed(2)
        self.assertEqual(u.bounds[1],before)
        self.assertEqual(u.writes,[2])
    def test_close_requests_only_tool_and_never_terminates_process(self):
        floating=FloatingTools();floating.windows={'fixture':(22,11)}
        u=Mock();u.IsWindow.return_value=True;u.IsIconic.return_value=False;u.GetWindowLongPtrW.return_value=11;u.PostMessageW.return_value=1
        floating._native=lambda:u;floating.focus=Mock(return_value=True)
        order=[]
        floating.hide=Mock(side_effect=lambda key:order.append('hide'))
        floating.on_return_focus=lambda:order.append('return focus')
        with patch('tool_windows.handoff_focus',return_value=True) as transfer:
            self.assertTrue(floating.close_tool('fixture')['ok'])
            transfer.assert_called_once_with(u,11,22)
        u.PostMessageW.assert_called_once_with(22,0x10,0,0)
        floating.focus.assert_not_called()
        self.assertEqual(order,['hide','return focus'])
        u.ShowWindow.assert_not_called()

    def test_shutdown_waits_for_tool_that_vetoes_close(self):
        floating=FloatingTools();floating.windows={'fixture':(22,11)};floating.active={'fixture'}
        floating.close_tool=Mock(return_value={'ok':True})
        floating.has_open_windows=Mock(return_value=True)
        self.assertFalse(floating.shutdown(timeout=0))
        floating.close_tool.assert_called_once_with('fixture')
        self.assertFalse(floating.stop.is_set())


class StartupSelectionTests(unittest.TestCase):
    def test_input_sites_and_dialogs_are_not_suppressed(self):
        from tool_startup import should_suppress
        for key in ('dlss','nvpi','bcu'):
            self.assertFalse(should_suppress(key,'',0x80000000,0,100000,True))
            self.assertFalse(should_suppress(key,'Confirm action',0x00CF0000,0,200000,True))
        self.assertTrue(should_suppress('dlss','DLSS Swapper',0,0,100000,False))
        self.assertTrue(should_suppress('bcu','',0x80000000,0x80000,100000,True))
