"""Exercise native ownership/movement using disposable off-screen windows."""
import ctypes
from ctypes import wintypes
import subprocess
import sys
import time
import threading
worker_errors=[]
threading.excepthook=lambda args:worker_errors.append(args.exc_value)
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from tool_windows import FloatingTools, inset_rect, chrome_insets

user=ctypes.WinDLL('user32',use_last_error=True)
user.SetThreadDpiAwarenessContext.argtypes=[ctypes.c_void_p]
user.SetThreadDpiAwarenessContext.restype=ctypes.c_void_p
user.SetThreadDpiAwarenessContext(ctypes.c_void_p(-4))
user.CreateWindowExW.argtypes=[wintypes.DWORD,wintypes.LPCWSTR,wintypes.LPCWSTR,wintypes.DWORD,
                              ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,wintypes.HWND,wintypes.HMENU,wintypes.HINSTANCE,ctypes.c_void_p]
user.CreateWindowExW.restype=wintypes.HWND
user.DestroyWindow.argtypes=[wintypes.HWND]
owner=user.CreateWindowExW(0,'STATIC','NVPI Revamped fixture' if '--nvpi' in sys.argv else 'TL floating fixture',0x00CF0000,-10000,-10000,1200,800,None,None,None,None)
if '--child' in sys.argv:
    # Model BCU saving settings during shutdown, longer than the old reveal timer.
    proc_type=ctypes.WINFUNCTYPE(ctypes.c_ssize_t,wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM)
    user.SetWindowLongPtrW.argtypes=[wintypes.HWND,ctypes.c_int,ctypes.c_void_p]
    user.SetWindowLongPtrW.restype=ctypes.c_void_p
    user.CallWindowProcW.argtypes=[ctypes.c_void_p,wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
    user.CallWindowProcW.restype=ctypes.c_ssize_t
    @proc_type
    def slow_close(hwnd,msg,wp,lp):
        if msg==0x10:time.sleep(1.4)
        return user.CallWindowProcW(original_proc,hwnd,msg,wp,lp)
    original_proc=user.SetWindowLongPtrW(owner,-4,ctypes.cast(slow_close,ctypes.c_void_p))
    splash=user.CreateWindowExW(0,'STATIC','',0x80000000,-10000,-10000,600,400,owner,None,None,None)
    print(int(owner),flush=True)
    print(int(splash),flush=True)
    message=wintypes.MSG()
    while user.GetMessageW(ctypes.byref(message),None,0,0)>0:
        user.TranslateMessage(ctypes.byref(message));user.DispatchMessageW(ctypes.byref(message))
    sys.exit(0)

def settle(seconds):
    until=time.monotonic()+seconds
    message=wintypes.MSG()
    while time.monotonic()<until:
        while user.PeekMessageW(ctypes.byref(message),None,0,0,1):
            user.TranslateMessage(ctypes.byref(message));user.DispatchMessageW(ctypes.byref(message))
        time.sleep(.005)

from tool_startup import StartupGuard
guard=StartupGuard()
child=subprocess.Popen([sys.executable,__file__,'--child'],stdout=subprocess.PIPE,text=True,creationflags=4)
guard.pid=child.pid
resume=ctypes.WinDLL('ntdll').NtResumeProcess
resume.argtypes=[wintypes.HANDLE]
assert resume(int(child._handle))==0
floating=FloatingTools()
try:
    hwnd=int(child.stdout.readline())
    splash=int(child.stdout.readline())
    deadline=time.monotonic()+2
    while hwnd not in guard.handles and time.monotonic()<deadline:settle(.01)
    assert hwnd in guard.handles,'Startup window was not suppressed before attachment'
    assert floating.attach('fixture',child.pid,owner,guard=guard)
    native=floating._native()
    deadline=time.monotonic()+5
    while native.GetWindowLongPtrW(hwnd,-8)!=owner and time.monotonic()<deadline:settle(.05)
    assert native.GetWindowLongPtrW(hwnd,-8)==owner,'Window ownership was not applied'
    assert floating.has_open_windows(),'Open tool was not detected for restart protection'
    settle(.3)
    assert native.IsWindowVisible(hwnd),'Integrated tool was not revealed'
    assert splash in guard.handles,'Attachment released the separate splash'
    native.SetWindowRgn.argtypes=[wintypes.HWND,wintypes.HANDLE,wintypes.BOOL]
    native.SetWindowRgn(splash,None,True)  # Publisher resets its splash during fade-in.
    settle(.1)
    gdi=ctypes.WinDLL('gdi32');gdi.CreateRectRgn.restype=wintypes.HANDLE
    gdi.DeleteObject.argtypes=[wintypes.HANDLE]
    probe=gdi.CreateRectRgn(0,0,0,0)
    deadline=time.monotonic()+2
    while native.GetWindowRgn(splash,probe)!=1 and time.monotonic()<deadline:settle(.01)
    assert native.GetWindowRgn(splash,probe)==1,'Splash became visible after attachment'
    gdi.DeleteObject(probe)
    assert not (native.GetWindowLongPtrW(hwnd,-16)&0x00040000),'Tool is still resizable'
    assert not (native.GetWindowLongPtrW(hwnd,-20)&0x00040000),'Tool has a taskbar entry'
    assert native.GetWindowLongPtrW(hwnd,-20)&0x80,'Tool window style missing'
    border,crop,_=chrome_insets(native,hwnd,'fixture',native.GetDpiForWindow(owner) or 96)
    # Parent movement must propagate without calling the WebView bridge.
    native.SetWindowPos(owner,None,-9000,-9000,1100,750,0x0014)
    settle(.5)
    rect=wintypes.RECT();native.GetWindowRect(hwnd,ctypes.byref(rect))
    expected=inset_rect((-9000,-9000,-7900,-8250),native.GetDpiForWindow(owner) or 96)
    assert (rect.left+border,rect.top+crop)==expected[:2],(rect.left,rect.top,expected)
    # Shell popups punch through the native surface without hiding its session.
    gdi=ctypes.WinDLL('gdi32')
    gdi.CreateRectRgn.argtypes=[ctypes.c_int]*4;gdi.CreateRectRgn.restype=wintypes.HANDLE
    gdi.PtInRegion.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_int]
    gdi.DeleteObject.argtypes=[wintypes.HANDLE]
    native.GetWindowRgn.argtypes=[wintypes.HWND,wintypes.HANDLE]
    native.ClientToScreen.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.POINT)]
    origin=wintypes.POINT();native.ClientToScreen(owner,ctypes.byref(origin))
    native.GetWindowRect(hwnd,ctypes.byref(rect))
    point=(origin.x+130-rect.left,origin.y+175-rect.top)
    floating.overlay_regions=((80,140,100,70,1),)
    settle(.15)
    region=gdi.CreateRectRgn(0,0,0,0)
    try:
        native.GetWindowRgn(hwnd,region)
        assert not gdi.PtInRegion(region,*point),'Tool covers shell popup'
        assert gdi.PtInRegion(region,point[0]+200,point[1]),'Rest of tool was hidden'
        assert native.IsWindowVisible(hwnd) and child.poll() is None
        floating.overlay_regions=()
        settle(.15);native.GetWindowRgn(hwnd,region)
        assert gdi.PtInRegion(region,*point),'Tool region was not restored after popup closed'
    finally: gdi.DeleteObject(region)
    # Native tool movement must pull its owner along, never snap back.
    native.NotifyWinEvent.argtypes=[wintypes.DWORD,wintypes.HWND,wintypes.LONG,wintypes.LONG]
    native.NotifyWinEvent(0x000A,hwnd,0,0);settle(.05)
    for step in range(12):
        native.GetWindowRect(hwnd,ctypes.byref(rect))
        x,y=rect.left+13,rect.top+7
        native.SetWindowPos(hwnd,None,x,y,0,0,0x0015)
        settle(.06)
        native.GetWindowRect(hwnd,ctypes.byref(rect))
        assert (rect.left,rect.top)==(x,y), 'Tool was snapped backwards'
        parent=wintypes.RECT();native.GetWindowRect(owner,ctypes.byref(parent))
        target=inset_rect((parent.left,parent.top,parent.right,parent.bottom),native.GetDpiForWindow(owner) or 96)
        assert target[:2]==(x+border,y+crop), 'Host did not follow the tool'
    native.NotifyWinEvent(0x000B,hwnd,0,0);settle(.1)
    native.GetWindowRect(owner,ctypes.byref(parent))
    owner_before=(parent.left,parent.top,parent.right,parent.bottom)
    native.SetWindowPos(hwnd,None,-15000,-15000,1500,1000,0x0014);settle(.15)
    native.GetWindowRect(owner,ctypes.byref(parent))
    assert owner_before==(parent.left,parent.top,parent.right,parent.bottom),'Programmatic tool movement moved the host'
    native.ShowWindow(owner,6);settle(.15)
    assert child.poll() is None,'Minimizing host terminated tool'
    assert not native.IsWindowVisible(hwnd) or native.IsIconic(hwnd),'Tool remained visible while host minimized'
    native.ShowWindow(owner,9);settle(.2)
    assert native.IsWindowVisible(hwnd),'Visible tool did not return with host'
    assert floating.hide('fixture')
    native.ShowWindow(owner,6);settle(.1)
    native.ShowWindow(owner,9);settle(.15)
    assert not native.IsWindowVisible(hwnd),'Backdrop-hidden tool reappeared on host restore'
    assert not native.IsWindowVisible(hwnd)
    assert child.poll() is None
    # Move the host while the session is hidden, then reopen in its new inset.
    parent=wintypes.RECT();native.GetWindowRect(owner,ctypes.byref(parent))
    native.SetWindowPos(owner,None,parent.left+60,parent.top+40,0,0,0x0015)
    settle(.1)
    assert floating.focus('fixture')
    settle(.2)
    assert native.IsWindowVisible(hwnd)
    parent=wintypes.RECT();native.GetWindowRect(owner,ctypes.byref(parent))
    native.GetWindowRect(hwnd,ctypes.byref(rect))
    expected=inset_rect((parent.left,parent.top,parent.right,parent.bottom),native.GetDpiForWindow(owner) or 96)
    assert (rect.left+border,rect.top+crop)==expected[:2],'Reopened tool used its old position'
    assert child.poll() is None
    floating.detach();settle(.25)
    assert native.GetWindowLongPtrW(hwnd,-16)&0x00040000,'Resize style not restored on detach'
    assert native.GetWindowLongPtrW(hwnd,-8)==0,'Ownership was not restored'
    assert child.poll() is None,'Detaching terminated the tool'
    floating=FloatingTools()
    native.SetWindowTextW.argtypes=[wintypes.HWND,wintypes.LPCWSTR]
    native.SetWindowTextW(hwnd,'NVPI Revamped fixture')
    assert floating.attach('nvpi',child.pid,owner)
    settle(.8)
    assert not native.GetWindowLongPtrW(hwnd,-16)&0x00C00000,'NVPI retained native caption'
    dpi=native.GetDpiForWindow(hwnd) or 96
    border,top,bottom=chrome_insets(native,hwnd,'nvpi',dpi)
    assert top<round(12*dpi/96),'NVPI client header was cropped like a caption'
    # Maximize/restore and repeated resizing must fit the final host rectangle.
    for cycle in range(8):
        native.ShowWindow(owner,3 if cycle%2 == 0 else 9)
        settle(.2)
        if cycle%2:
            native.SetWindowPos(owner,None,100+cycle*5,100,1000+cycle*20,750,0x0014)
            settle(.2)
        native.GetWindowRect(owner,ctypes.byref(parent))
        native.GetWindowRect(hwnd,ctypes.byref(rect))
        border,top,bottom=chrome_insets(native,hwnd,'nvpi',native.GetDpiForWindow(owner) or 96)
        expected=inset_rect((parent.left,parent.top,parent.right,parent.bottom),native.GetDpiForWindow(owner) or 96)
        assert (rect.left+border,rect.top+top)==expected[:2], f'NVPI shifted after maximize/resize: cycle={cycle}, actual={(rect.left+border,rect.top+top)}, expected={expected}, owner={(parent.left,parent.top,parent.right,parent.bottom)}'
        assert abs((rect.right-rect.left-2*border)-expected[2])<=2, 'NVPI width did not follow host'
    native.GetWindowRect(hwnd,ctypes.byref(rect))
    region=gdi.CreateRectRgn(0,0,0,0)
    native.GetWindowRgn(hwnd,region)
    width=rect.right-rect.left
    assert gdi.PtInRegion(region,width//2,top+8),'NVPI profile selector is clipped'
    assert gdi.PtInRegion(region,width-20,top+8),'NVPI header still contains black-producing cut-outs'
    gdi.DeleteObject(region)
    floating.detach();settle(.25)
    floating=FloatingTools()
    native.SetWindowTextW(hwnd,'Bulk Crap Uninstaller fixture')
    assert floating.attach('bcu',child.pid,owner)
    settle(.4)
    assert not native.GetWindowLongPtrW(hwnd,-16)&0x00C80000,'BCU still has native caption/close button'
    # Reproduce WinForms restoring its chrome after its initial loading layout.
    native.SetWindowLongPtrW(hwnd,-16,native.GetWindowLongPtrW(hwnd,-16)|0x00CF0000)
    native.SetWindowPos(hwnd,None,0,0,0,0,0x0037)
    settle(.2)
    assert not native.GetWindowLongPtrW(hwnd,-16)&0x00CF0000,'BCU restored native buttons above the host X'
    border,top,bottom=chrome_insets(native,hwnd,'bcu',native.GetDpiForWindow(hwnd) or 96)
    assert top<12,'BCU client menu was cropped with its removed caption'
    native.GetWindowRect(owner,ctypes.byref(parent))
    native.GetWindowRect(hwnd,ctypes.byref(rect))
    target=inset_rect((parent.left,parent.top,parent.right,parent.bottom),native.GetDpiForWindow(owner) or 96)
    assert (rect.left+border,rect.top+top)==target[:2],'BCU body moved over the themed close button after restoring its caption'
    # A competing desktop window must stay behind the host when the tool X
    # closes. Start with the tool active, as after interacting with BCU.
    competitor=user.CreateWindowExW(0,'STATIC','TL unrelated fixture',0x00CF0000,-15000,-15000,600,400,None,None,None,None)
    native.GetForegroundWindow.restype=wintypes.HWND
    native.ShowWindow(competitor,5)
    native.ShowWindow(owner,5)
    # The test has no mouse click to grant foreground rights. Establish its
    # initial active window explicitly; the production handoff only accepts
    # an already active host/tool family.
    current_thread=ctypes.WinDLL('kernel32').GetCurrentThreadId()
    foreground_thread=native.GetWindowThreadProcessId(native.GetForegroundWindow(),None)
    native.AttachThreadInput.argtypes=[wintypes.DWORD,wintypes.DWORD,wintypes.BOOL]
    joined=foreground_thread!=current_thread and native.AttachThreadInput(current_thread,foreground_thread,True)
    try:assert native.SetForegroundWindow(owner),'Could not establish fixture foreground'
    finally:
        if joined:native.AttachThreadInput(current_thread,foreground_thread,False)
    assert native.SetForegroundWindow(hwnd),'Could not activate fixture tool'
    settle(.15)
    assert native.GetForegroundWindow()==hwnd,'Fixture tool was not active before close'
    class LastInput(ctypes.Structure):
        _fields_=[('size',wintypes.UINT),('tick',wintypes.DWORD)]
    def input_tick():
        value=LastInput(ctypes.sizeof(LastInput),0)
        native.GetLastInputInfo(ctypes.byref(value))
        return value.tick
    initial_input=input_tick()
    focus_returns=[]
    def return_host_focus():
        # Production supplies Api._return_tool_focus (BringToFront/Activate on
        # its UI thread). A no-op callback does not exercise that close path.
        native.SetWindowPos(owner,0,0,0,0,0,0x0013)
        focus_returns.append(bool(native.SetForegroundWindow(owner)))
    floating.on_return_focus=return_host_focus
    assert floating.close_tool('bcu')['ok']
    assert focus_returns==[True],'Host activation callback did not run successfully'
    settle(.95)
    assert native.IsWindow(owner) and not native.IsIconic(owner),'Tool close minimized its host'
    assert native.GetForegroundWindow()==owner, f'Tool close sent its host behind another window: current={native.GetForegroundWindow()}, host={owner}, tool={hwnd}, competitor={competitor}, input={initial_input}->{input_tick()}'
    assert not native.IsWindowVisible(hwnd),'Slow shutdown reactivated the closing tool'
    settle(.7)
    assert native.GetForegroundWindow()==owner, f'Tool destruction lost host foreground: current={native.GetForegroundWindow()}, host={owner}, tool={hwnd}, competitor={competitor}, input={initial_input}->{input_tick()}'
    user.DestroyWindow(competitor)
    import threading
    result=[]
    worker=threading.Thread(target=lambda:result.append(floating.shutdown(timeout=3)))
    worker.start()
    settle(.6)
    worker.join(timeout=1)
    assert result==[True],'Host shutdown did not close hidden tool'
    assert not native.IsWindow(hwnd),'Close request did not reach the tool'
    assert native.IsWindow(owner), 'Closing the tool closed its host'
    assert not worker_errors,repr(worker_errors)
    print('PASS: native movement, hide/restore, close preserves host foreground with a competing window, and non-destructive detach.')
finally:
    floating.detach()
    child.terminate();child.wait(timeout=5)
    user.DestroyWindow(owner)

