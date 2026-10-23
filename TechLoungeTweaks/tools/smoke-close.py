"""Native WebView2 fixture: exercise the real window/close bridge, no system tweaks."""
from pathlib import Path
import os
import sys
import threading
from unittest.mock import Mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import webview
from main import Api, centre_window

api = Api.__new__(Api)
class CloseOnly:
    def close(self): return api.close()
    def updates_restart(self): return api.updates_restart()
window = webview.create_window('Tech Lounge close test', html='<html><body>Close test</body></html>',
                               js_api=CloseOnly(), hidden=True, frameless=True, easy_drag=False)
api._window = window
def prepare_native_window():
    global initial_work
    from System.Windows.Forms import Screen, Cursor
    initial_work=Screen.FromPoint(Cursor.Position).WorkingArea
    from native_frame import NativeFrame
    api._native_frame = NativeFrame(window.native.Handle.ToInt64())
    centre_window(window)
window.events.before_show += prepare_native_window
window.events.closing += api._on_closing
closed = threading.Event()
window.events.closed += lambda: closed.set()
watchdog = threading.Timer(20, lambda: os._exit(2))
watchdog.daemon = True
watchdog.start()
def test():
    if not window.events.loaded.wait(10): os._exit(3)
    window.show()
    style=api._native_frame.user.GetWindowLongPtrW(api._native_frame.hwnd,-16)
    assert style&0x00CF0000==0x00CF0000,'WinForms removed the animation frame after showing the window'
    import time
    def wait_state(expected):
        until=time.monotonic()+3
        while int(window.native.WindowState)!=expected and time.monotonic()<until: time.sleep(.01)
        assert int(window.native.WindowState)==expected,('Native window state did not change', expected, int(window.native.WindowState))
    from System.Windows.Forms import Screen
    work=initial_work
    assert abs(window.native.Left-(work.Left+max(0,(work.Width-window.native.Width)//2)))<=1,('Initial horizontal centre', window.native.Left, work.Left, work.Width, window.native.Width)
    assert abs(window.native.Top-(work.Top+max(0,(work.Height-window.native.Height)//2)))<=1,('Initial vertical centre', window.native.Top, work.Top, work.Height, window.native.Height)
    initial=(window.native.Left,window.native.Top,window.native.Width,window.native.Height)
    # Repeat without animation sleeps to catch lost rapid restore requests.
    for cycle in range(5):
        api.maximize();wait_state(2)
        maximized_work=Screen.FromHandle(window.native.Handle).WorkingArea
        # WinForms reports Maximized before WM_SIZE finishes applying bounds.
        until=time.monotonic()+3
        def fits_work_area():
            return (abs(window.native.ClientSize.Width-maximized_work.Width)<=2 and
                    abs(window.native.ClientSize.Height-maximized_work.Height)<=2)
        while not fits_work_area() and time.monotonic()<until:time.sleep(.01)
        assert fits_work_area(),('Maximized content missed the monitor work area',
                                 window.native.ClientSize.Width,window.native.ClientSize.Height,
                                 maximized_work.Width,maximized_work.Height)
        api.maximize();wait_state(0)
        until=time.monotonic()+3
        while (window.native.Left,window.native.Top,window.native.Width,window.native.Height)!=initial and time.monotonic()<until:time.sleep(.01)
        assert (window.native.Left,window.native.Top,window.native.Width,window.native.Height)==initial,('Restore changed the original bounds',initial,(window.native.Left,window.native.Top,window.native.Width,window.native.Height))
        api.minimize();wait_state(1)
        api.maximize();wait_state(2)
        api.maximize();wait_state(0)
    dispatched=threading.Event();on_ui=[]
    api._begin_native_drag=lambda:(on_ui.append(not window.native.InvokeRequired),dispatched.set())
    api.start_drag()
    assert dispatched.wait(3) and on_ui==[True],'Drag did not reach the window UI thread'
    assert api._hwnd()==window.native.Handle.ToInt64(),'Window controls targeted another instance'
    # Exercise the exact Restart and apply bridge; substitute only the disk
    # updater so this fixture never replaces or launches an installed app.
    api._floating_tools=Mock()
    api._floating_tools.has_open_windows.return_value=False
    api._floating_tools.shutdown.return_value=True
    api._updates=Mock()
    api._updates.processes={}
    api._updates.status.return_value={'busy':False}
    api._updates.restart.return_value={'ok':True}
    api._jobslock=threading.Lock();api._jobs={}
    window.evaluate_js('window.pywebview.api.updates_restart()')
webview.start(test, gui='edgechromium', debug=False)
watchdog.cancel()
assert closed.is_set(), 'Native window did not close'
api._updates.restart.assert_called_once()
print('PASS: native maximize/minimize/restore, drag UI-thread dispatch, instance handle and close.')
