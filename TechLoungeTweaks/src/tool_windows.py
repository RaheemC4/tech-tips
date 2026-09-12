"""Present unmodified third-party apps as floating owned Windows windows.

Ownership preserves their normal message loops, dialogs, DPI handling and
accessibility. We deliberately do not reparent another process into WebView2.
"""
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import threading
import time


def handoff_focus(user, owner, tool):
    """Transfer this active tool's input to its host before hiding/destroying it.

    A WebView bridge call runs on a worker thread, outside both input queues.
    Temporarily join only this window family's queues; never steal focus from
    an unrelated app and always detach in reverse order.
    """
    user.GetForegroundWindow.restype=wintypes.HWND
    foreground=user.GetForegroundWindow()
    ancestor=foreground
    for _ in range(32):
        if not ancestor or ancestor in (owner,tool): break
        ancestor=user.GetWindowLongPtrW(ancestor,-8)
    if ancestor not in (owner,tool) or user.IsIconic(owner):return False
    kernel=ctypes.WinDLL('kernel32')
    current=kernel.GetCurrentThreadId()
    user.AttachThreadInput.argtypes=[wintypes.DWORD,wintypes.DWORD,wintypes.BOOL]
    user.SetActiveWindow.argtypes=[wintypes.HWND]
    user.SetFocus.argtypes=[wintypes.HWND]
    attached=[]
    try:
        for thread in {user.GetWindowThreadProcessId(foreground,None),user.GetWindowThreadProcessId(owner,None)}:
            if thread and thread!=current and user.AttachThreadInput(current,thread,True):attached.append(thread)
        result=bool(user.SetForegroundWindow(owner))
        if result:
            user.SetActiveWindow(owner)
            user.SetFocus(owner)
        return result
    finally:
        for thread in reversed(attached):user.AttachThreadInput(current,thread,False)


def is_main_tool_window(key, title):
    if key == 'driverbooster': return title.lower().startswith(('driver booster', 'iobit driver booster'))
    if key == 'treesize': return title == 'TreeSize' or title.startswith('TreeSize ') or title.endswith(' - TreeSize')
    # BCU's welcome/news/legend windows are not its main application surface.
    if key == 'bcu': return title.startswith('Bulk Crap Uninstaller')
    if key == 'dlss': return title == 'DLSS Swapper'
    if key == 'nvpi': return title.lower().startswith(('nvpi revamped','nvidia profile inspector'))
    return True


def has_close_dialog(user, tool):
    found=[]
    callback_type=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
    @callback_type
    def visit(hwnd,unused):
        if hwnd==tool or not user.IsWindowVisible(hwnd):return True
        if user.GetWindowLongPtrW(hwnd,-20)&0x08000000:return True
        ancestor=user.GetWindowLongPtrW(hwnd,-8)
        for _ in range(32):
            if not ancestor or ancestor==tool:break
            ancestor=user.GetWindowLongPtrW(ancestor,-8)
        title=ctypes.create_unicode_buffer(256)
        user.GetWindowTextW(hwnd,title,256)
        if ancestor==tool and (title.value or user.GetWindowLongPtrW(hwnd,-16)&0x00C00000):found.append(hwnd)
        return True
    user.EnumWindows(visit,0)
    return bool(found)


def inset_rect(rect, dpi=96):
    left, top, right, bottom = rect
    inset = max(20, round(28 * dpi / 96))
    title = max(70, round(90 * dpi / 96))
    return left + inset, top + title, max(100, right-left-2*inset), max(100, bottom-top-title-inset)


def caption_holes(key, width, dpi):
    """Remove only custom window buttons; keep menus and ribbon controls."""
    dimensions = {'driverbooster': (112, 32), 'treesize': (26, 24)}
    if key not in dimensions: return []
    w, h = dimensions[key]
    return [(max(0, width-round(w*dpi/96)), 0, width, round(h*dpi/96))]


def chrome_insets(user, hwnd, key, dpi):
    # Custom app headers contain menus and must remain fully accessible.
    if key in ('driverbooster', 'treesize'): return 0, 0, 0
    rect=wintypes.RECT();user.GetWindowRect(hwnd,ctypes.byref(rect))
    origin=wintypes.POINT(0,0)
    user.ClientToScreen.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.POINT)]
    user.ClientToScreen(hwnd,ctypes.byref(origin))
    border=max(1,min(round(12*dpi/96),origin.x-rect.left))
    if key in ('nvpi','bcu'):
        # BCU uses a standard WinForms caption, which we remove completely.
        # NVPI's profile selector lives in its client header. Never crop either
        # app's client controls using an estimated native title-bar height.
        return border, max(0, origin.y-rect.top), border
    class TitleInfo(ctypes.Structure):
        _fields_=[('size',wintypes.DWORD),('rect',wintypes.RECT),('state',wintypes.DWORD*6)]
    info=TitleInfo();info.size=ctypes.sizeof(info)
    user.GetTitleBarInfo.argtypes=[wintypes.HWND,ctypes.POINTER(TitleInfo)]
    top=user.GetSystemMetricsForDpi(51,dpi)+border
    if user.GetTitleBarInfo(hwnd,ctypes.byref(info)):
        measured=info.rect.bottom-rect.top
        if 0 < measured < round(80*dpi/96): top=measured
    if key=='dlss': top=round(32*dpi/96)
    return border,top,border


class ToolSurface:
    """Clip publisher chrome while preserving its client UI and message loop."""
    def __init__(self, user, hwnd, key, owner=None, overlays=lambda: (), folder=None):
        self.user, self.hwnd, self.key = user, hwnd, key
        self.owner, self.overlays = owner, overlays
        self.style = user.GetWindowLongPtrW(hwnd, -16)
        self.exstyle = user.GetWindowLongPtrW(hwnd, -20)
        self.gdi = ctypes.WinDLL('gdi32', use_last_error=True)
        self.gdi.CreateRectRgn.argtypes = [ctypes.c_int]*4
        self.gdi.CreateRectRgn.restype = wintypes.HANDLE
        self.gdi.CreateRoundRectRgn.argtypes = [ctypes.c_int]*6
        self.gdi.CreateRoundRectRgn.restype = wintypes.HANDLE
        self.gdi.CombineRgn.argtypes = [wintypes.HANDLE,wintypes.HANDLE,wintypes.HANDLE,ctypes.c_int]
        self.gdi.DeleteObject.argtypes = [wintypes.HANDLE]
        user.GetWindowRgn.argtypes = [wintypes.HWND,wintypes.HANDLE]
        user.SetWindowRgn.argtypes = [wintypes.HWND,wintypes.HANDLE,wintypes.BOOL]
        user.GetSystemMetricsForDpi.argtypes = [ctypes.c_int,wintypes.UINT]
        self.saved_region = self.gdi.CreateRectRgn(0,0,0,0)
        if not user.GetWindowRgn(hwnd,self.saved_region):
            self.gdi.DeleteObject(self.saved_region);self.saved_region=None
        self.covers = None
        self.crop = (0,0,0)
        self.last_region = None
        self.applied_region = None
        # Keep the caption's layout but make it invisible via the window region.
        # Removing thickframe prevents edge resizing, including custom app chrome.
        self.strip = 0x21070000 | (0x00C80000 if key in ('nvpi','bcu') else 0)
        user.SetWindowLongPtrW(hwnd,-16,self.style & ~self.strip)
        # Owned tool window: no independent taskbar or Alt-Tab entry.
        user.SetWindowLongPtrW(hwnd,-20,(self.exstyle & ~0x00040000) | 0x00000080)
        user.SetWindowPos(hwnd,None,0,0,0,0,0x0037)  # FRAMECHANGED, no move/size/activate.

        if key == 'nvpi':
            from tool_masks import CaptionCovers
            from nvpi_settings import title_colour
            self.covers=CaptionCovers(user,hwnd,title_colour(folder))

    def geometry(self, bounds, dpi):
        self.ensure_chrome()
        self.crop = chrome_insets(self.user,self.hwnd,self.key,dpi)
        border,top,bottom = self.crop
        x,y,w,h = inset_rect(bounds,dpi)
        return x-border,y-top,w+2*border,h+top+bottom

    def ensure_chrome(self):
        # WinForms may recreate native caption styles after loading/restoring.
        # Reapply only when publisher changes reintroduce managed chrome.
        style=self.user.GetWindowLongPtrW(self.hwnd,-16)
        chrome=self.strip & ~0x21000000  # Leave runtime minimize/maximize state to Windows.
        if style & chrome:
            self.user.SetWindowLongPtrW(self.hwnd,-16,style & ~chrome)
            self.user.SetWindowPos(self.hwnd,None,0,0,0,0,0x0237)
            self.crop=chrome_insets(self.user,self.hwnd,self.key,self.user.GetDpiForWindow(self.hwnd) or 96)
            self.last_region=None
            return True
        return False

    def apply_crop(self):
        if self.ensure_chrome() and self.owner and self.user.IsWindow(self.owner):
            bounds=wintypes.RECT()
            if self.user.GetWindowRect(self.owner,ctypes.byref(bounds)):
                target=self.geometry((bounds.left,bounds.top,bounds.right,bounds.bottom),self.user.GetDpiForWindow(self.owner) or 96)
                self.user.SetWindowPos(self.hwnd,None,*target,0x0214)
        rect=wintypes.RECT()
        if not self.user.GetWindowRect(self.hwnd,ctypes.byref(rect)): return
        left,top,bottom=self.crop
        size=(rect.right-rect.left,rect.bottom-rect.top,left,top,bottom)
        holes=caption_holes(self.key,size[0],self.user.GetDpiForWindow(self.hwnd) or 96)
        if self.owner:
            origin=wintypes.POINT(0,0)
            self.user.ClientToScreen(self.owner,ctypes.byref(origin))
            for x,y,w,h,scale in self.overlays():
                holes.append((round(origin.x+x*scale-rect.left),round(origin.y+y*scale-rect.top),
                              round(origin.x+(x+w)*scale-rect.left),round(origin.y+(y+h)*scale-rect.top)))
        signature=(size,tuple(holes))
        if signature == self.last_region:
            # Publishers can reset regions during startup/theme changes.
            current=self.gdi.CreateRectRgn(0,0,0,0)
            self.user.GetWindowRgn(self.hwnd,current)
            self.gdi.EqualRgn.argtypes=[wintypes.HANDLE,wintypes.HANDLE]
            same=self.applied_region and self.gdi.EqualRgn(current,self.applied_region)
            self.gdi.DeleteObject(current)
            if same:
                if self.covers: self.covers.update(self.applied_region,signature)
                return
        radius=round(12*(self.user.GetDpiForWindow(self.hwnd) or 96)/96)
        region=self.gdi.CreateRoundRectRgn(left,top,size[0]-left+1,size[1]-bottom+1,radius,radius)
        for bounds in holes:
            hole=self.gdi.CreateRectRgn(*bounds)
            result=self.gdi.CombineRgn(region,region,hole,4)  # RGN_DIFF: HTML owns these pixels/input.
            self.gdi.DeleteObject(hole)
            if not result:
                self.gdi.DeleteObject(region)
                raise ctypes.WinError(ctypes.get_last_error())
        if self.applied_region: self.gdi.DeleteObject(self.applied_region)
        self.applied_region=self.gdi.CreateRectRgn(0,0,0,0)
        self.gdi.CombineRgn(self.applied_region,region,region,5)
        if not self.user.SetWindowRgn(self.hwnd,region,True):
            self.gdi.DeleteObject(region)
            if not self.user.IsWindow(self.hwnd): return  # Normal close raced this paint.
            raise ctypes.WinError(ctypes.get_last_error())
        self.last_region=signature  # Windows owns the successfully applied region.
        if self.covers: self.covers.update(self.applied_region,signature)

    def restore(self):
        if self.covers: self.covers.close();self.covers=None
        if self.applied_region:
            self.gdi.DeleteObject(self.applied_region);self.applied_region=None
        if self.user.IsWindow(self.hwnd):
            self.user.SetWindowLongPtrW(self.hwnd,-16,self.style)
            self.user.SetWindowLongPtrW(self.hwnd,-20,self.exstyle)
            if self.user.SetWindowRgn(self.hwnd,self.saved_region,True):
                self.saved_region=None
            self.user.SetWindowPos(self.hwnd,None,0,0,0,0,0x0037)
        if self.saved_region:
            self.gdi.DeleteObject(self.saved_region);self.saved_region=None


class WindowLink:
    """Bidirectional movement. Never write back to the window being dragged.

    Expected rectangles absorb our own queued location events, preventing a
    feedback loop. Windows events drive movement rather than a snap-back timer.
    """
    def __init__(self, user, owner, tool, visible=lambda: True, surface=None):
        self.user, self.owner, self.tool = user, owner, tool
        self.visible = visible
        self.surface = surface
        self.owner_rect = self.rect(owner)
        self.tool_rect = self.rect(tool)
        self.updating = False
        self.dragging = None
        self.hooks = []
        self.callback = None
        self.pending_events = []

    def rect(self, hwnd):
        value = wintypes.RECT()
        if not self.user.GetWindowRect(hwnd, ctypes.byref(value)):
            return None
        return value.left, value.top, value.right, value.bottom

    def from_owner(self):
        bounds = self.rect(self.owner)
        if not bounds: return
        geometry = self.surface.geometry if self.surface else inset_rect
        desired = geometry(bounds, self.user.GetDpiForWindow(self.owner) or 96)
        self.user.SetWindowPos(self.tool, None, *desired, 0x0014)
        if self.surface: self.surface.apply_crop()
        self.owner_rect, self.tool_rect = self.rect(self.owner), self.rect(self.tool)

    def changed(self, source):
        if self.updating or not self.visible(): return
        u = self.user
        if u.IsIconic(self.owner) or u.IsIconic(self.tool): return
        owner, tool = self.rect(self.owner), self.rect(self.tool)
        if not owner or not tool: return
        self.updating = True
        try:
            if source == self.owner:
                if owner != self.owner_rect and self.dragging != self.tool:
                    self.from_owner()
            elif source == self.tool and tool != self.tool_rect:
                if self.dragging != self.tool or (self.surface and self.surface.key in ('driverbooster','treesize')):
                    # Startup/layout/close movements are not user drags.
                    # In particular, never propagate an app's maximized bounds.
                    if u.IsZoomed(self.tool): u.ShowWindow(self.tool,9)
                    self.from_owner()
                    return
                # A host change can arrive before its event. Respect its origin.
                if owner != self.owner_rect and self.dragging != self.tool:
                    self.from_owner()
                    return
                dx, dy = tool[0]-self.tool_rect[0], tool[1]-self.tool_rect[1]
                if dx or dy:
                    if u.IsZoomed(self.owner):
                        u.ShowWindow(self.owner, 9)
                        owner = self.rect(self.owner)
                        offset = inset_rect(owner, u.GetDpiForWindow(self.owner) or 96)
                        x, y = tool[0]-(offset[0]-owner[0]), tool[1]-(offset[1]-owner[1])
                    else:
                        x, y = owner[0]+dx, owner[1]+dy
                    # NOSIZE | NOZORDER | NOACTIVATE. No repositioning of tool.
                    u.SetWindowPos(self.owner, None, x, y, 0, 0, 0x0015)
                self.owner_rect, self.tool_rect = self.rect(self.owner), self.rect(self.tool)
        finally:
            self.updating = False

    def start(self):
        u = self.user
        self.updating = True
        try: self.from_owner()
        finally: self.updating = False
        callback_type = ctypes.WINFUNCTYPE(None, wintypes.HANDLE, wintypes.DWORD,
            wintypes.HWND, wintypes.LONG, wintypes.LONG, wintypes.DWORD, wintypes.DWORD)
        @callback_type
        def event(hook, code, hwnd, object_id, child_id, thread_id, timestamp):
            if hwnd not in (self.owner, self.tool) or object_id or child_id: return
            # Never resize foreign windows inside a WinEvent callback. These
            # callbacks can re-enter while Windows is negotiating DPI/layout.
            self.pending_events.append((code, hwnd))
        self.callback = event  # Keep the callback alive until all hooks are removed.
        u.SetWinEventHook.argtypes = [wintypes.DWORD,wintypes.DWORD,wintypes.HMODULE,
            callback_type,wintypes.DWORD,wintypes.DWORD,wintypes.DWORD]
        u.SetWinEventHook.restype = wintypes.HANDLE
        u.UnhookWinEvent.argtypes = [wintypes.HANDLE]
        for first, last in ((0x800B,0x800B),(0x000A,0x000B)):
            handle = u.SetWinEventHook(first,last,None,event,0,0,0)
            if not handle:
                self.close()
                raise ctypes.WinError(ctypes.get_last_error())
            self.hooks.append(handle)

    def process_events(self):
        u = self.user
        events, self.pending_events = self.pending_events, []
        # Read final rectangles after the native notification has returned.
        for code, hwnd in events:
            if code == 0x000A:
                self.dragging = hwnd
            elif code == 0x000B:
                self.changed(hwnd)
                self.dragging = None
                if self.visible() and not u.IsIconic(self.owner) and not u.IsIconic(self.tool):
                    self.updating = True
                    try: self.from_owner()
                    finally: self.updating = False
            elif code == 0x800B:
                self.changed(hwnd)

    def pump(self):
        # WinEvent callbacks are delivered on this thread's message queue.
        u = self.user
        u.MsgWaitForMultipleObjects(0,None,False,50,0x04FF)
        message = wintypes.MSG()
        for _ in range(256):
            if not u.PeekMessageW(ctypes.byref(message),None,0,0,1): break
            u.TranslateMessage(ctypes.byref(message))
            u.DispatchMessageW(ctypes.byref(message))
        self.process_events()
        # Custom publisher drag loops can move/reset ownership without the
        # standard move-start/end events. Personal tools stay fitted to the host.
        if self.surface and self.surface.key in ('driverbooster', 'treesize') and self.visible():
            if not u.IsIconic(self.owner) and not u.IsIconic(self.tool):
                if u.GetWindowLongPtrW(self.tool,-8) != self.owner:
                    u.SetWindowLongPtrW(self.tool,-8,self.owner)
                bounds=self.rect(self.owner)
                if bounds:
                    x,y,w,h=self.surface.geometry(bounds,u.GetDpiForWindow(self.owner) or 96)
                    if self.rect(self.tool)!=(x,y,x+w,y+h):self.from_owner()

    def close(self):
        for handle in self.hooks: self.user.UnhookWinEvent(handle)
        self.hooks.clear()


class FloatingTools:
    def __init__(self, on_visibility=None, on_return_focus=None):
        self.stop = threading.Event()
        self.lock = threading.Lock()
        self.windows = {}
        self.active = set()
        self.hidden = {}
        self.reveals = set()
        self.closing = {}
        self.close_prompts = set()
        self.overlay_regions = ()
        self.on_visibility = on_visibility or (lambda key, visible: None)
        self.on_return_focus = on_return_focus or (lambda: None)

    def focus(self, key):
        with self.lock:
            window = self.windows.get(key)
            if window and self._native().IsWindow(window[0]):
                self.reveals.add(key)
                return True
        return False

    def hide_others(self, key):
        with self.lock:
            others = [name for name in self.windows if name != key and name not in self.hidden]
        for name in others: self.hide(name)

    def hide(self, key):
        """Hide the main window and owned dialogs without stopping their processes."""
        user = self._native()
        with self.lock:
            window = self.windows.get(key)
            if not window or not user.IsWindow(window[0]): return False
            handles = []
            callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            @callback_type
            def visit(handle, unused):
                ancestor = handle
                for _ in range(32):
                    if not ancestor or ancestor == window[0]: break
                    ancestor = user.GetWindowLongPtrW(ancestor, -8)
                if user.IsWindowVisible(handle) and ancestor == window[0]:
                    handles.append(handle)
                return True
            user.EnumWindows(visit, 0)
            self.hidden[key] = handles
            # Hide without activating another window or moving the owner in
            # the z-order (SWP_HIDEWINDOW | NOACTIVATE | NOOWNERZORDER).
            for handle in handles:
                user.SetWindowPos(handle,None,0,0,0,0,0x0297)
        self.on_visibility(key, False)
        return True

    def close_tool(self, key):
        """Ask only the tool to close. Honour its save/busy confirmation dialogs."""
        with self.lock:
            window = self.windows.get(key)
            if not window or not self._native().IsWindow(window[0]):
                return {'ok': False, 'message': 'This tool is no longer open.'}
            hwnd=window[0]
            self.closing[key] = time.monotonic()
            self.close_prompts.discard(key)
        user=self._native()
        # Activating a dying owned window leaves Windows choosing an unrelated
        # foreground app. Hand focus to the host BEFORE requesting tool closure.
        owner=user.GetWindowLongPtrW(hwnd,-8)
        if owner and user.IsWindow(owner) and not user.IsIconic(owner):
            handoff_focus(user,owner,hwnd)
        self.hide(key)
        # Activate on the host UI thread AFTER the owned window is hidden;
        # WinForms activation can otherwise select the still-visible tool.
        self.on_return_focus()
        user.PostMessageW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
        return {'ok': bool(user.PostMessageW(hwnd,0x0010,0,0))}

    def has_open_windows(self):
        if os.name != 'nt':
            return False
        user = self._native()
        with self.lock:
            return any(user.IsWindow(window[0]) for window in self.windows.values())

    def attach(self, key, pid, owner, folder=None, guard=None):
        if not owner or os.name != 'nt':
            return False
        with self.lock:
            if key in self.active:
                hwnd = self.windows.get(key)
                if hwnd:
                    self._native().SetForegroundWindow(hwnd[0])
                return True
            self.active.add(key)
        threading.Thread(target=self._follow, args=(key, pid, owner, folder, guard), daemon=True).start()
        return True

    @staticmethod
    def _native():
        user = ctypes.WinDLL('user32', use_last_error=True)
        user.GetWindowTextW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
        user.IsWindow.argtypes = [wintypes.HWND]
        user.IsWindowVisible.argtypes = [wintypes.HWND]
        user.IsZoomed.argtypes = [wintypes.HWND]
        user.IsIconic.argtypes = [wintypes.HWND]
        user.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        user.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
        user.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        user.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
        user.GetAncestor.restype = wintypes.HWND
        user.GetSystemMenu.argtypes = [wintypes.HWND, wintypes.BOOL]
        user.GetSystemMenu.restype = wintypes.HMENU
        user.EnableMenuItem.argtypes = [wintypes.HMENU, wintypes.UINT, wintypes.UINT]
        user.SetForegroundWindow.argtypes = [wintypes.HWND]
        user.GetDpiForWindow.argtypes = [wintypes.HWND]
        user.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
        user.GetWindowLongPtrW.restype = ctypes.c_ssize_t
        user.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
        user.SetWindowLongPtrW.restype = ctypes.c_ssize_t
        return user

    def _follow(self, key, pid, owner, folder=None, guard=None):
        import psutil
        user = self._native()
        user.SetThreadDpiAwarenessContext.argtypes=[ctypes.c_void_p]
        user.SetThreadDpiAwarenessContext.restype=ctypes.c_void_p
        old_dpi=user.SetThreadDpiAwarenessContext(ctypes.c_void_p(-4))
        hwnd = None
        original_owner = 0
        link = None
        surface = None
        menu_states = {}
        candidate_key = None
        candidate_since = 0
        deadline = time.monotonic() + 90
        process_ids = {pid}
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        try:
            while not self.stop.is_set() and user.IsWindow(owner):
                if link:
                    link.pump()
                    if surface: surface.apply_crop()
                elif self.stop.wait(.15): break
                if not hwnd or not user.IsWindow(hwnd):
                    if hwnd:
                        self.on_visibility(key, False)
                        break
                    hwnd = None
                    if time.monotonic() > deadline:
                        break
                    try:
                        process_ids.update(p.pid for p in psutil.Process(pid).children(recursive=True))
                    except psutil.Error:
                        pass
                    if folder:
                        for process in psutil.process_iter(['pid', 'exe']):
                            try:
                                if process.info['exe'] and Path(process.info['exe']).is_relative_to(Path(folder)):
                                    process_ids.add(process.info['pid'])
                            except (psutil.Error, OSError):
                                pass
                    if key in ('driverbooster', 'treesize') and folder:
                        expected = Path(folder) / ('DriverBooster.exe' if key == 'driverbooster' else 'TreeSize.exe')
                        exact = set()
                        for process_id in process_ids:
                            try:
                                if Path(psutil.Process(process_id).exe()).resolve() == expected.resolve():
                                    exact.add(process_id)
                            except (psutil.Error, OSError):
                                pass
                        process_ids = exact
                    candidates = []
                    @callback_type
                    def visit(candidate, unused):
                        process_id = wintypes.DWORD()
                        user.GetWindowThreadProcessId(candidate, ctypes.byref(process_id))
                        if process_id.value in process_ids:
                            title=ctypes.create_unicode_buffer(512)
                            user.GetWindowTextW(candidate,title,512)
                            if not is_main_tool_window(key,title.value): return True
                            rect = wintypes.RECT()
                            user.GetWindowRect(candidate, ctypes.byref(rect))
                            area = (rect.right-rect.left)*(rect.bottom-rect.top)
                            if area > 80000:
                                candidates.append((area, candidate))
                        return True
                    user.EnumWindows(visit, 0)
                    if not candidates:
                        continue
                    selected = max(candidates)[1]
                    if key == 'nvpi' and not (guard and guard.is_cloaked(selected)):
                        bounds=wintypes.RECT();user.GetWindowRect(selected,ctypes.byref(bounds))
                        current=(selected,bounds.left,bounds.top,bounds.right,bounds.bottom)
                        if current != candidate_key:
                            candidate_key=current;candidate_since=time.monotonic()
                            continue
                        if time.monotonic()-candidate_since < .35: continue
                    hwnd = selected
                    original_owner = user.GetWindowLongPtrW(hwnd, -8)
                    staged=guard and guard.is_cloaked(hwnd)
                    if staged:original_owner=guard.original_owner(hwnd,original_owner)
                    with self.lock:
                        if self.stop.is_set():
                            break
                        ctypes.set_last_error(0)
                        if not staged:user.SetWindowLongPtrW(hwnd, -8, owner)
                        if ctypes.get_last_error():
                            break  # Leave the publisher's normal window intact.
                        self.windows[key] = (hwnd, original_owner)
                    try:
                        dwm = ctypes.WinDLL('dwmapi')
                        dwm.DwmSetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
                        enabled = ctypes.c_int(2)
                        # NVPI owns its WPF nonclient rendering. Forcing DWM to
                        # recreate that frame on attach can flash its compositor;
                        # our window region already supplies the rounded outline.
                        if key != 'nvpi':
                            dwm.DwmSetWindowAttribute(hwnd, 2, ctypes.byref(enabled), 4)
                            dwm.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(enabled), 4)
                    except OSError:
                        pass
                    menu = user.GetSystemMenu(hwnd, False)
                    if menu:
                        for command in (0xF000, 0xF030):
                            menu_states[command] = user.EnableMenuItem(menu, command, 1)
                    if guard: guard.prepare(hwnd)
                    surface = ToolSurface(user, hwnd, key, owner, lambda: self.overlay_regions, folder)
                    link = WindowLink(user, owner, hwnd, lambda: key not in self.hidden and (key not in self.closing or time.monotonic()-self.closing[key] > .25) and not self.stop.is_set(), surface)
                    link.start()
                    user.SetWindowPos(hwnd,None,0,0,0,0,0x0257)
                    if guard: guard.reveal(hwnd,owner)
                    user.SetForegroundWindow(hwnd)
                    self.on_visibility(key, True)
                # Slow shutdown is not a veto. The previous .75-second timer
                # reactivated BCU while it was exiting, undoing the focus handoff.
                # Reveal only when a real owned modal dialog disables the tool.
                user.IsWindowEnabled.argtypes=[wintypes.HWND]
                if key in self.closing and key not in self.close_prompts and not user.IsWindowEnabled(hwnd) and has_close_dialog(user,hwnd):
                    self.close_prompts.add(key)
                    self.reveals.add(key)
                if key in self.reveals:
                    self.reveals.discard(key)
                    link.updating = True
                    try: link.from_owner()
                    finally: link.updating = False
                    with self.lock:
                        hidden = self.hidden.pop(key, [])
                    user.ShowWindow(hwnd, 9)
                    for handle in hidden:
                        if handle != hwnd and user.IsWindow(handle): user.ShowWindow(handle,5)
                    user.SetForegroundWindow(hwnd)
                    self.on_visibility(key,True)
                if user.IsIconic(hwnd) and not user.IsIconic(owner) and key not in self.hidden:
                    self.hide(key)
        finally:
            if guard: guard.close()
            if link: link.close()
            if surface: surface.restore()
            if hwnd and user.IsWindow(hwnd):
                user.SetWindowLongPtrW(hwnd, -8, original_owner)
                menu = user.GetSystemMenu(hwnd, False)
                for command, state in menu_states.items():
                    if menu and state != -1: user.EnableMenuItem(menu, command, state)
                for handle in self.hidden.pop(key, []):
                    if user.IsWindow(handle): user.ShowWindow(handle, 5)
            self.on_visibility(key, False)
            with self.lock:
                self.windows.pop(key, None)
                self.active.discard(key)
                self.closing.pop(key,None)
                self.close_prompts.discard(key)
            if old_dpi: user.SetThreadDpiAwarenessContext(old_dpi)

    def shutdown(self, timeout=8):
        """Gracefully close every hosted surface, including hidden/starting tools.

        A tool may veto WM_CLOSE to show a save/busy dialog. Keep the host alive
        in that case, rather than orphaning it or terminating active work.
        """
        deadline=time.monotonic()+timeout
        sent=set()
        while True:
            with self.lock:
                windows=dict(self.windows)
                pending=bool(self.active)
            for key,(hwnd,unused) in windows.items():
                if hwnd not in sent:
                    self.close_tool(key)
                    sent.add(hwnd)
            if not pending and not self.has_open_windows():
                self.stop.set()
                return True
            if time.monotonic()>=deadline: return False
            time.sleep(.05)

    def detach(self):
        """Release ownership before closing the host; never kill an uninstaller."""
        self.stop.set()
        if os.name != 'nt':
            return
        user = self._native()
        with self.lock:
            for hwnd, owner in self.windows.values():
                if user.IsWindow(hwnd):
                    user.SetWindowLongPtrW(hwnd, -8, owner)
            for handles in self.hidden.values():
                for handle in handles:
                    if user.IsWindow(handle): user.ShowWindow(handle, 5)
