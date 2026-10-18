"""Keep a custom title bar while allowing Windows to animate window states."""
import ctypes
import time
from ctypes import wintypes


class MonitorInfo(ctypes.Structure):
    _fields_ = [('size', wintypes.DWORD), ('monitor', wintypes.RECT), ('work', wintypes.RECT), ('flags', wintypes.DWORD)]


class MinMaxInfo(ctypes.Structure):
    _fields_ = [('reserved', wintypes.POINT), ('max_size', wintypes.POINT), ('max_position', wintypes.POINT), ('min_track', wintypes.POINT), ('max_track', wintypes.POINT)]


class StyleInfo(ctypes.Structure):
    _fields_ = [('old', wintypes.DWORD), ('new', wintypes.DWORD)]


class NativeFrame:
    def __init__(self, handle):
        self.hwnd = int(handle)
        self.user = ctypes.WinDLL('user32', use_last_error=True)
        self.comctl = ctypes.WinDLL('comctl32', use_last_error=True)
        self.user.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
        self.user.GetWindowLongPtrW.restype = ctypes.c_ssize_t
        self.user.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
        self.user.SetWindowLongPtrW.restype = ctypes.c_ssize_t
        self.user.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
        self.user.IsZoomed.argtypes = [wintypes.HWND]
        self.user.GetDpiForWindow.argtypes = [wintypes.HWND]
        self.user.GetSystemMetricsForDpi.argtypes = [ctypes.c_int, wintypes.UINT]
        self.user.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        self.user.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
        self.user.MonitorFromWindow.restype = wintypes.HMONITOR
        self.user.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(MonitorInfo)]
        self.user.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        callback_type = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM, ctypes.c_size_t, ctypes.c_size_t)
        self.callback = callback_type(self._message)
        self.comctl.DefSubclassProc.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        self.comctl.DefSubclassProc.restype = ctypes.c_ssize_t
        self.comctl.SetWindowSubclass.argtypes = [wintypes.HWND, callback_type, ctypes.c_size_t, ctypes.c_size_t]
        self.comctl.RemoveWindowSubclass.argtypes = [wintypes.HWND, callback_type, ctypes.c_size_t]
        if not self.comctl.SetWindowSubclass(self.hwnd, self.callback, 1, 0):
            raise ctypes.WinError(ctypes.get_last_error())
        # Windows requires a real caption/resizing frame for its DWM transitions.
        # NCCALCSIZE below hides the native chrome, preserving our existing UI.
        style = self.user.GetWindowLongPtrW(self.hwnd, -16)
        self.user.SetWindowLongPtrW(self.hwnd, -16, style | 0x00CF0000)
        self.user.SetWindowPos(self.hwnd, None, 0, 0, 0, 0, 0x0037)
        dwm = ctypes.WinDLL('dwmapi')
        dwm.DwmSetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
        disabled = ctypes.c_int(0)
        dwm.DwmSetWindowAttribute(self.hwnd, 3, ctypes.byref(disabled), ctypes.sizeof(disabled))

    def _message(self, hwnd, message, wp, lp, subclass, data):
        if message == 0x0082:  # WM_NCDESTROY: release the native hook.
            self.comctl.RemoveWindowSubclass(hwnd, self.callback, 1)
        elif message == 0x007C and ctypes.c_ssize_t(wp).value == -16:  # WM_STYLECHANGING
            # WinForms reapplies FormBorderStyle during Show/Opacity updates.
            # Preserve the animation frame while NCCALCSIZE hides its chrome.
            style = ctypes.cast(lp, ctypes.POINTER(StyleInfo)).contents
            style.new |= 0x00CF0000
        elif message == 0x0083 and wp:  # WM_NCCALCSIZE
            if self.user.IsZoomed(hwnd):
                dpi = self.user.GetDpiForWindow(hwnd)
                edge = self.user.GetSystemMetricsForDpi(32, dpi) + self.user.GetSystemMetricsForDpi(92, dpi)
                rect = ctypes.cast(lp, ctypes.POINTER(wintypes.RECT)).contents
                rect.left += edge
                rect.top += edge
                rect.right -= edge
                rect.bottom -= edge
            return 0
        elif message == 0x0024:  # WM_GETMINMAXINFO: keep the taskbar outside our client.
            result = self.comctl.DefSubclassProc(hwnd, message, wp, lp)
            monitor = MonitorInfo(size=ctypes.sizeof(MonitorInfo))
            if self.user.GetMonitorInfoW(self.user.MonitorFromWindow(hwnd, 2), ctypes.byref(monitor)):
                dpi = self.user.GetDpiForWindow(hwnd)
                edge = self.user.GetSystemMetricsForDpi(32, dpi) + self.user.GetSystemMetricsForDpi(92, dpi)
                sizes = ctypes.cast(lp, ctypes.POINTER(MinMaxInfo)).contents
                sizes.max_position.x = monitor.work.left - monitor.monitor.left - edge
                sizes.max_position.y = monitor.work.top - monitor.monitor.top - edge
                sizes.max_size.x = monitor.work.right - monitor.work.left + 2 * edge
                sizes.max_size.y = monitor.work.bottom - monitor.work.top + 2 * edge
            return result
        elif message == 0x0084 and not self.user.IsZoomed(hwnd):  # WM_NCHITTEST
            rect = wintypes.RECT()
            if self.user.GetWindowRect(hwnd, ctypes.byref(rect)):
                x = ctypes.c_short(lp & 0xFFFF).value
                y = ctypes.c_short((lp >> 16) & 0xFFFF).value
                edge = max(4, round(6 * self.user.GetDpiForWindow(hwnd) / 96))
                left, right = x < rect.left + edge, x >= rect.right - edge
                top, bottom = y < rect.top + edge, y >= rect.bottom - edge
                if top:
                    return 13 if left else 14 if right else 12
                if bottom:
                    return 16 if left else 17 if right else 15
                if left or right:
                    return 10 if left else 11
        return self.comctl.DefSubclassProc(hwnd, message, wp, lp)

    def change_state(self, action):
        command = 0xF020 if action == 'minimize' else 0xF120 if self.user.IsZoomed(self.hwnd) else 0xF030
        return bool(self.user.PostMessageW(self.hwnd, 0x0112, command, 0))

    def close(self, native):
        """Fade the complete host after save/tool checks, without delaying input."""
        from System.Windows.Forms import Timer
        enabled = ctypes.c_int()
        self.user.SystemParametersInfoW(0x1042, 0, ctypes.byref(enabled), 0)
        if not enabled.value:
            native.Close()
            return
        timer = Timer()
        self._close_timer = timer
        timer.Interval = 15
        started, top = time.perf_counter(), native.Top
        distance = round(6 * self.user.GetDpiForWindow(self.hwnd) / 96)

        def finish():
            timer.Stop()
            timer.Tick -= tick
            timer.Dispose()
            self._close_timer = None
            if not native.IsDisposed:
                native.Close()

        def tick(sender, args):
            if native.IsDisposed:
                finish()
                return
            progress = min(1, (time.perf_counter() - started) / .16)
            try:
                native.Top = top + round(distance * progress * progress)
                native.Opacity = 1 - progress * progress
            except Exception:
                finish()
                return
            if progress >= 1:
                finish()

        timer.Tick += tick
        timer.Start()
