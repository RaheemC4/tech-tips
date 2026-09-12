"""Opt-in live window test. Opens bundled tools; never starts scans or driver changes.

Run elevated, passing --output PATH. Deliberately excluded from unattended release
checks because it executes the personal binaries supplied with this local build.
"""
import argparse
import ctypes
from ctypes import wintypes as w
from pathlib import Path
import sys
import time
import traceback
import faulthandler

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from tool_windows import FloatingTools, inset_rect
from updates import UpdateManager

parser = argparse.ArgumentParser()
parser.add_argument('--output', required=True)
parser.add_argument('--bundle-root')
args = parser.parse_args()
faulthandler.enable()
faulthandler.dump_traceback_later(30)
output = Path(args.output)

def report(text):
    with output.open('a', encoding='utf-8') as stream: stream.write(text + '\n')

u = FloatingTools._native()
u.SetThreadDpiAwarenessContext.argtypes = [ctypes.c_void_p]
u.SetThreadDpiAwarenessContext(ctypes.c_void_p(-4))
u.CreateWindowExW.argtypes = [w.DWORD,w.LPCWSTR,w.LPCWSTR,w.DWORD,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,w.HWND,w.HMENU,w.HINSTANCE,ctypes.c_void_p]
u.CreateWindowExW.restype = w.HWND
u.DestroyWindow.argtypes = [w.HWND]
owner = u.CreateWindowExW(0,'STATIC','TechLounge personal tools test',0x00CF0000,-10000,-10000,1300,900,None,None,None,None)
manager = UpdateManager(bundle_root=args.bundle_root)
floating = FloatingTools()

def settle(seconds):
    until = time.monotonic() + seconds
    message = w.MSG()
    while time.monotonic() < until:
        while u.PeekMessageW(ctypes.byref(message),None,0,0,1):
            u.TranslateMessage(ctypes.byref(message)); u.DispatchMessageW(ctypes.byref(message))
        time.sleep(.01)

try:
    report('START live window checks')
    assert ctypes.windll.shell32.IsUserAnAdmin(), 'Live personal-tools test requires elevation'
    manager._load()
    for key in ('driverbooster','treesize'):
        report('Launching ' + key)
        result = manager.launch(key)
        report('Launched ' + key + ': ' + str(result))
        assert result.get('ok'), result
        floating.attach(key,result['pid'],owner,result['folder'],manager.startup_guards.pop(key,None))
        until = time.monotonic() + 90
        while key not in floating.windows and time.monotonic() < until: settle(.1)
        assert key in floating.windows, f'{key}: no attachable window'
        hwnd = floating.windows[key][0]
        settle(1)
        assert u.GetWindowLongPtrW(hwnd,-8) == owner, f'{key}: ownership failed'
        for x,y,width,height in [(-9500,-9500,1300,900),(-9000,-9200,1100,780)]:
            u.SetWindowPos(owner,None,x,y,width,height,0x0014)
            expected = inset_rect((x,y,x+width,y+height),u.GetDpiForWindow(owner) or 96)
            deadline = time.monotonic() + 5
            while True:
                settle(.1)
                rect = w.RECT(); u.GetWindowRect(hwnd,ctypes.byref(rect))
                actual = (rect.left,rect.top,rect.right-rect.left,rect.bottom-rect.top)
                if actual == expected or time.monotonic() > deadline: break
            assert actual == expected, f'{key}: rectangle {actual} != {expected}'
        assert floating.hide(key)
        settle(.25)
        assert not u.IsWindowVisible(hwnd), f'{key}: hide failed'
        assert floating.focus(key)
        settle(.4)
        assert u.IsWindowVisible(hwnd), f'{key}: reopen failed'
        report(f'PASS {key}: owned, fitted, follows host movement/resizing, hides and reopens')
        floating.close_tool(key)
        deadline = time.monotonic() + 8
        while u.IsWindow(hwnd) and time.monotonic() < deadline: settle(.1)
        assert not u.IsWindow(hwnd), f'{key}: normal close left its main window alive'
        report(f'PASS {key}: normal close destroys the main window')
    report('PASS live personal tools')
except BaseException:
    report(traceback.format_exc())
    raise
finally:
    faulthandler.cancel_dump_traceback_later()
    for process in manager.processes.values():
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
    floating.detach()
    u.DestroyWindow(owner)
