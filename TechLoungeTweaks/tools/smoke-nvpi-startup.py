"""Test DWM startup suppression on a separate disposable process, never the GPU tool."""
import ctypes
from ctypes import wintypes as w
from pathlib import Path
import subprocess
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from tool_startup import StartupGuard
from tool_windows import FloatingTools

u=FloatingTools._native()
guard=StartupGuard('nvpi')
child=subprocess.Popen([sys.executable,str(Path(__file__).with_name('smoke-floating-tools.py')),'--child','--nvpi'],stdout=subprocess.PIPE,text=True,creationflags=4)
guard.pid=child.pid
resume=ctypes.WinDLL('ntdll').NtResumeProcess;resume.argtypes=[w.HANDLE]
assert resume(int(child._handle))==0
try:
    hwnd=int(child.stdout.readline());child.stdout.readline()
    u.ShowWindow(hwnd,4)
    until=time.monotonic()+3
    while not guard.is_cloaked(hwnd) and time.monotonic()<until:time.sleep(.01)
    assert guard.is_cloaked(hwnd),'NVPI startup was not cloaked'
    dwm=ctypes.WinDLL('dwmapi')
    dwm.DwmGetWindowAttribute.argtypes=[w.HWND,w.DWORD,ctypes.c_void_p,w.DWORD]
    def cloaked():
        state=w.DWORD()
        assert dwm.DwmGetWindowAttribute(hwnd,14,ctypes.byref(state),4)==0
        return state.value&1
    u.ShowWindow(hwnd,4)
    assert cloaked(),'Showing the initial window escaped suppression'
    # WPF resets its region and restores bounds while loading. This must not
    # reveal a desktop frame or force the guard to rebuild its region.
    u.SetWindowRgn.argtypes=[w.HWND,w.HANDLE,w.BOOL]
    u.SetWindowRgn(hwnd,None,True)
    u.SetWindowPos(hwnd,None,-12000,-12000,1800,1000,0x0014)
    assert cloaked(),'Publisher layout exposed the startup window'
    guard.prepare(hwnd)
    assert cloaked(),'Preparing the frame uncloaked it too early'
    assert hwnd not in guard.handles,'Cloaked startup also used region suppression'
    u.SetWindowPos(hwnd,None,-10000,-10000,900,600,0x0254)
    guard.reveal(hwnd)
    assert not cloaked(),'Fitted tool remained invisible'
    assert guard.stop.is_set(),'Startup guard remained active after reveal'
    # Exercise the complete host attach path, including temporary ownership,
    # caption covers and transfer to the real host once fitting has finished.
    u.CreateWindowExW.argtypes=[w.DWORD,w.LPCWSTR,w.LPCWSTR,w.DWORD,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,w.HWND,w.HMENU,w.HINSTANCE,ctypes.c_void_p]
    u.CreateWindowExW.restype=w.HWND
    owner=u.CreateWindowExW(0,'STATIC','TL NVPI host fixture',0x00CF0000,-10000,-10000,1200,800,None,None,None,None)
    floating=FloatingTools()
    guard=StartupGuard('nvpi');guard.pid=child.pid
    try:
        with guard.lock:guard.suppress(hwnd)
        assert guard.is_cloaked(hwnd)
        assert floating.attach('nvpi',child.pid,owner,guard=guard)
        until=time.monotonic()+4
        while not guard.stop.is_set() and time.monotonic()<until:time.sleep(.01)
        assert guard.stop.is_set() and not guard.cloaked,'Attachment did not finish staging'
        assert u.GetWindowLongPtrW(hwnd,-8)==owner,'Attachment retained the temporary owner'
        assert not cloaked(),'Attached tool remained cloaked'
    finally:
        floating.detach()
        until=time.monotonic()+3
        while floating.active and time.monotonic()<until:time.sleep(.01)
        u.DestroyWindow.argtypes=[w.HWND];u.DestroyWindow(owner)
    print('PASS: NVPI stays DWM-cloaked through show, region reset and resize; reveal removes the cloak after fitting.')
finally:
    guard.close()
    child.terminate();child.wait(timeout=5)
