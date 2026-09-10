"""Pre-arm a startup visibility guard before a managed tool is allowed to execute."""
import ctypes
from ctypes import wintypes as w
import threading
import time


def should_suppress(key, title, style, exstyle, area, owned):
    """Never suppress XAML input sites, dialogs or unrelated helper windows."""
    if key is None: return True  # Disposable native fixture.
    if key == 'bcu':
        return title.startswith('Bulk Crap Uninstaller') or (owned and not title and not style & 0x00C00000 and bool(exstyle & 0x00080000) and area > 80000)
    if key == 'dlss': return title == 'DLSS Swapper'
    if key == 'nvpi': return title.lower().startswith(('nvpi revamped','nvidia profile inspector'))
    return False


class StartupGuard:
    def __init__(self, key=None):
        self.key=key
        self.pid = None
        self.prepared = None
        self.lock = threading.RLock()
        self.process_ids = set()
        self.handles = {}
        self.cloaked = set()
        self.staged_owners = {}
        self.stage_hwnd = None
        self.stop = threading.Event()
        self.ready = threading.Event()
        self.error = None
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        if not self.ready.wait(5) or self.error:
            self.close()
            raise RuntimeError('Could not prepare the integrated tool window.')

    def suppress(self, hwnd):
        from tool_windows import FloatingTools
        u=FloatingTools._native()
        if hwnd == self.prepared or u.GetAncestor(hwnd,2) != hwnd: return
        if self.key == 'nvpi' and self.stage_hwnd:
            # Let WPF finish its first render without presenting a temporary
            # desktop window or repeatedly changing its rendering region.
            if hwnd in self.cloaked:return
            ctypes.set_last_error(0)
            original=u.SetWindowLongPtrW(hwnd,-8,self.stage_hwnd)
            if not ctypes.get_last_error():
                self.staged_owners[hwnd]=original
                self.cloaked.add(hwnd)
                return
        g=ctypes.WinDLL('gdi32')
        g.CreateRectRgn.argtypes=[ctypes.c_int]*4;g.CreateRectRgn.restype=w.HANDLE
        g.DeleteObject.argtypes=[w.HANDLE]
        u.GetWindowRgn.argtypes=[w.HWND,w.HANDLE];u.SetWindowRgn.argtypes=[w.HWND,w.HANDLE,w.BOOL]
        if hwnd in self.handles:
            current=g.CreateRectRgn(0,0,0,0)
            kind=u.GetWindowRgn(hwnd,current)
            g.DeleteObject(current)
            if kind == 1: return  # NULLREGION already suppresses painting/input.
        saved=self.handles.get(hwnd)
        if hwnd not in self.handles:
            saved=g.CreateRectRgn(0,0,0,0)
            if not u.GetWindowRgn(hwnd,saved): g.DeleteObject(saved);saved=None
        empty=g.CreateRectRgn(0,0,0,0)
        if u.SetWindowRgn(hwnd,empty,True): self.handles[hwnd]=saved
        else:
            g.DeleteObject(empty)
            if saved and hwnd not in self.handles:g.DeleteObject(saved)

    def _run(self):
        import psutil
        from tool_windows import FloatingTools
        u = FloatingTools._native()
        if self.key == 'nvpi':
            u.CreateWindowExW.argtypes=[w.DWORD,w.LPCWSTR,w.LPCWSTR,w.DWORD,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,w.HWND,w.HMENU,w.HINSTANCE,ctypes.c_void_p]
            u.CreateWindowExW.restype=w.HWND
            stage=u.CreateWindowExW(0x08000080,'STATIC','TechLounge NVPI staging',0x80000000,-32000,-32000,1,1,None,None,None,None)
            if stage and self._cloak(stage,True):self.stage_hwnd=stage
            elif stage:
                u.DestroyWindow.argtypes=[w.HWND];u.DestroyWindow(stage)
        cb = ctypes.WINFUNCTYPE(None,w.HANDLE,w.DWORD,w.HWND,w.LONG,w.LONG,w.DWORD,w.DWORD)
        @cb
        def event(hook,code,hwnd,obj,child,thread,stamp):
            if not self.pid or not hwnd or obj or child: return
            if code not in (0x8000,0x8002,0x800B,0x800C): return
            pid=w.DWORD();u.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
            try:
                process=psutil.Process(pid.value)
                ours=pid.value == self.pid or process.ppid() == self.pid or process.ppid() in self.process_ids or any(p.pid == self.pid for p in process.parents())
                title=ctypes.create_unicode_buffer(512);u.GetWindowTextW(hwnd,title,512)
                rect=w.RECT();u.GetWindowRect(hwnd,ctypes.byref(rect))
                eligible=should_suppress(self.key,title.value,u.GetWindowLongPtrW(hwnd,-16),u.GetWindowLongPtrW(hwnd,-20),
                    (rect.right-rect.left)*(rect.bottom-rect.top),bool(u.GetWindowLongPtrW(hwnd,-8)))
                if ours and eligible and hwnd != self.prepared:
                    self.process_ids.add(pid.value)
                    with self.lock: self.suppress(hwnd)
            except (psutil.Error,OSError): pass
        u.SetWinEventHook.argtypes=[w.DWORD,w.DWORD,w.HMODULE,cb,w.DWORD,w.DWORD,w.DWORD]
        u.SetWinEventHook.restype=w.HANDLE
        u.UnhookWinEvent.argtypes=[w.HANDLE]
        # WPF may assign the title after CREATE/SHOW, then restore saved bounds.
        # Catch NAMECHANGE and LOCATIONCHANGE before accepting the main surface.
        # BCU/DLSS retain their CREATE/SHOW-only startup behaviour. Monitoring
        # every location change during BCU's loading layout is unnecessary.
        last_event=0x800C if self.key == 'nvpi' else 0x8002
        hook=u.SetWinEventHook(0x8000,last_event,None,event,0,0,0)
        if not hook: self.error=True
        self.ready.set()
        end=time.monotonic()+95
        try:
            while hook and not self.stop.wait(.005) and time.monotonic()<end:
                msg=w.MSG()
                while u.PeekMessageW(ctypes.byref(msg),None,0,0,1):
                    u.TranslateMessage(ctypes.byref(msg));u.DispatchMessageW(ctypes.byref(msg))
                # WinForms splash fade/opacity changes can replace its region.
                with self.lock:
                    for hwnd in list(self.handles):
                        if u.IsWindow(hwnd): self.suppress(hwnd)
        finally:
            if hook: u.UnhookWinEvent(hook)
            g=ctypes.WinDLL('gdi32');g.DeleteObject.argtypes=[w.HANDLE]
            u.SetWindowRgn.argtypes=[w.HWND,w.HANDLE,w.BOOL]
            for hwnd,region in self.handles.items():
                if u.IsWindow(hwnd): u.ShowWindow(hwnd,0)
                if not u.IsWindow(hwnd) or not u.SetWindowRgn(hwnd,region,True):
                    if region:g.DeleteObject(region)
            with self.lock:
                if self.stage_hwnd:self._cloak(self.stage_hwnd,False)
                for hwnd in list(self.cloaked):
                    if u.IsWindow(hwnd):u.SetWindowLongPtrW(hwnd,-8,self.staged_owners.pop(hwnd,0))
                    self.cloaked.discard(hwnd)
                if self.stage_hwnd:
                    u.DestroyWindow.argtypes=[w.HWND];u.DestroyWindow(self.stage_hwnd)
                    self.stage_hwnd=None

    def prepare(self, hwnd):
        from tool_windows import FloatingTools
        u=FloatingTools._native()
        with self.lock:
            if hwnd in self.cloaked:
                self.prepared=hwnd
                # Keep its compositor surface hidden until layout is fitted.
                return
            u.ShowWindow(hwnd,0)
            self.prepared=hwnd
            # Release only the main surface. Keep the existing loading splash
            # suppressed until it destroys itself; future dialogs remain usable.
            region=self.handles.pop(hwnd,None)
            u.SetWindowRgn.argtypes=[w.HWND,w.HANDLE,w.BOOL]
            if not u.SetWindowRgn(hwnd,region,False) and region:
                g=ctypes.WinDLL('gdi32');g.DeleteObject.argtypes=[w.HANDLE]
                g.DeleteObject(region)

        if self.key in ('dlss','nvpi'):
            self.close()

    @staticmethod
    def _cloak(hwnd, hidden):
        try:
            dwm=ctypes.WinDLL('dwmapi')
            dwm.DwmSetWindowAttribute.argtypes=[w.HWND,w.DWORD,ctypes.c_void_p,w.DWORD]
            flag=w.BOOL(hidden)
            return dwm.DwmSetWindowAttribute(hwnd,13,ctypes.byref(flag),ctypes.sizeof(flag)) == 0
        except OSError:
            return False

    def is_cloaked(self, hwnd):
        with self.lock:
            return hwnd in self.cloaked

    def original_owner(self, hwnd, fallback):
        with self.lock:
            return self.staged_owners.get(hwnd,fallback)

    def reveal(self, hwnd, owner=None):
        from tool_windows import FloatingTools
        with self.lock:
            if hwnd not in self.cloaked:return
            ctypes.WinDLL('dwmapi').DwmFlush()
            # DWM permits cloaking our own staging owner, not the foreign tool.
            # Uncloak while it still owns the tool, then transfer ownership.
            if not self._cloak(self.stage_hwnd,False):
                raise RuntimeError('Could not reveal the prepared tool window.')
            u=FloatingTools._native()
            u.SetWindowLongPtrW(hwnd,-8,owner if owner is not None else self.staged_owners.get(hwnd,0))
            self.cloaked.discard(hwnd)
            self.staged_owners.pop(hwnd,None)
        self.close()

    def close(self):
        self.stop.set()
        if threading.current_thread() is not self.thread: self.thread.join(2)
