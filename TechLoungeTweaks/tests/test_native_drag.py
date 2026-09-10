from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from main import Api

class DragTests(unittest.TestCase):
    def setUp(self):
        self.api=Api.__new__(Api)
        self.api._window=Mock()
        self.api._window.native.Handle.ToInt64.return_value=0x123456789
    def test_drag_is_dispatched_to_own_ui_thread(self):
        with patch.dict(sys.modules,{'System':Mock(Action=lambda fn:fn)}):
            self.assertTrue(self.api.start_drag())
        self.api._window.native.BeginInvoke.assert_called_once_with(self.api._begin_native_drag)
        self.assertEqual(self.api._hwnd(),0x123456789)
    def test_native_handoff_releases_capture_and_uses_screen_position(self):
        user=Mock();user.GetAsyncKeyState.return_value=0x8000
        def cursor(out):out._obj.x=-120;out._obj.y=250;return 1
        user.GetCursorPos.side_effect=cursor
        with patch('main.ctypes.WinDLL',return_value=user): self.api._begin_native_drag()
        user.SendMessageW.assert_called_once_with(0x123456789,0xA1,2,((-120)&0xffff)|(250<<16))
        self.assertLess(user.mock_calls.index(user.ReleaseCapture.call_args_list and unittest.mock.call.ReleaseCapture()),
                        user.mock_calls.index(unittest.mock.call.SendMessageW(0x123456789,0xA1,2,((-120)&0xffff)|(250<<16))))
    def test_released_mouse_does_not_start_a_move(self):
        user=Mock();user.GetAsyncKeyState.return_value=0
        with patch('main.ctypes.WinDLL',return_value=user): self.api._begin_native_drag()
        user.ReleaseCapture.assert_not_called();user.SendMessageW.assert_not_called()

    def test_minimize_maximize_restore_are_dispatched_to_ui_thread(self):
        import types
        states=types.SimpleNamespace(Normal=0,Minimized=1,Maximized=2)
        modules={'System':types.SimpleNamespace(Action=lambda fn:fn),
                 'System.Windows.Forms':types.SimpleNamespace(FormWindowState=states)}
        native=self.api._window.native;native.WindowState=0
        with patch.dict(sys.modules,modules):
            self.api.maximize();self.assertEqual(native.WindowState,0)
            native.BeginInvoke.call_args.args[0]();self.assertEqual(native.WindowState,2)
            self.api.maximize();native.BeginInvoke.call_args.args[0]();self.assertEqual(native.WindowState,0)
            self.api.minimize();native.BeginInvoke.call_args.args[0]();self.assertEqual(native.WindowState,1)

    def test_return_focus_uses_host_ui_thread_and_does_not_unminimize(self):
        import types
        modules={'System':types.SimpleNamespace(Action=lambda fn:fn),'System.Windows.Forms':types.SimpleNamespace(FormWindowState=types.SimpleNamespace(Minimized=1))}
        native=self.api._window.native;native.IsDisposed=False;native.WindowState=0
        native.InvokeRequired=True
        native.Invoke.side_effect=lambda action:action()
        with patch.dict(sys.modules,modules):
            self.api._return_tool_focus()
            native.Activate.assert_called_once()
            native.BeginInvoke.assert_not_called()
            native.Activate.reset_mock();native.WindowState=1
            self.api._return_tool_focus()
            native.Activate.assert_not_called()
