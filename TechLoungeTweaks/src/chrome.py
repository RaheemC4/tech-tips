"""Window chrome: rounded corners, dark title bar, prism sidebar art."""

import ctypes
import os
import tempfile
from ctypes import wintypes

DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWA_SYSTEMBACKDROP_TYPE = 38
DWMWCP_ROUND = 2
DWMSBT_MAINWINDOW = 2       # Mica


def _hwnd(root):
    root.update_idletasks()
    try:
        return wintypes.HWND(int(root.frame(), 16))
    except Exception:
        try:
            return wintypes.HWND(int(root.wm_frame(), 16))
        except Exception:
            return None


def _set_attr(hwnd, attr, value):
    try:
        val = ctypes.c_int(value)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, ctypes.c_int(attr), ctypes.byref(val), ctypes.sizeof(val))
        return True
    except Exception:
        return False


def apply(root, mica=False):
    """Dark title bar + rounded corners. Returns True if anything took."""
    hwnd = _hwnd(root)
    if not hwnd:
        return False
    ok = _set_attr(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, 1)
    ok = _set_attr(hwnd, DWMWA_WINDOW_CORNER_PREFERENCE, DWMWCP_ROUND) or ok
    if mica:
        _set_attr(hwnd, DWMWA_SYSTEMBACKDROP_TYPE, DWMSBT_MAINWINDOW)
    return ok


# ---------------------------------------------------------------- prism art

def prism_image(width, height, base="#0b0b0c"):
    """Soft frosted-glass wash for the sidebar.

    Real acrylic blur is not achievable here: Tk can only make a colour
    fully transparent, which would also make the sidebar click-through and
    break the nav. This fakes the same read - a cool, softly-lit pane -
    without the rainbow.
    """
    try:
        from PIL import Image, ImageDraw, ImageFilter
    except Exception:
        return None

    img = Image.new("RGB", (width, height), base)
    glow = Image.new("RGB", (width, height), base)
    d = ImageDraw.Draw(glow)

    # two cool highlights: one high-left, one low, both heavily blurred
    d.ellipse([-width * 0.7, -height * 0.10, width * 1.05, height * 0.42],
              fill=(58, 66, 86))
    d.ellipse([-width * 0.4, height * 0.55, width * 0.95, height * 1.25],
              fill=(44, 48, 66))
    d.ellipse([width * 0.15, height * 0.28, width * 1.3, height * 0.72],
              fill=(34, 38, 52))

    glow = glow.filter(ImageFilter.GaussianBlur(radius=max(28, width // 3)))
    img = Image.blend(img, glow, 0.55)

    # a hairline sheen down the right edge, like the lit edge of glass
    d2 = ImageDraw.Draw(img)
    d2.line([(width - 1, 0), (width - 1, height)], fill=(52, 56, 70))

    path = os.path.join(tempfile.gettempdir(), "tl_sidebar.png")
    try:
        img.save(path)
        return path
    except Exception:
        return None


# ------------------------------------------------------------------ window

GWL_EXSTYLE = -20
GWL_STYLE = -16
WS_EX_APPWINDOW = 0x00040000
WS_EX_TOOLWINDOW = 0x00000080
SW_MINIMIZE = 6
SW_RESTORE = 9


def _raw_hwnd(root):
    """The real top-level HWND (Tk nests its window inside a wrapper)."""
    try:
        return ctypes.windll.user32.GetParent(root.winfo_id())
    except Exception:
        return None


def set_app_id(app_id="TechLounge.Tweaks"):
    """Without this Windows groups us under python.exe in the taskbar."""
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass


def set_icon(root, ico_path):
    """Title bar + taskbar icon. --icon only sets the icon ON THE FILE."""
    try:
        if ico_path and os.path.exists(ico_path):
            root.iconbitmap(default=ico_path)
            return True
    except Exception:
        pass
    return False


def make_frameless(root):
    """Drop the OS title bar but stay a proper taskbar window.

    overrideredirect alone makes Windows treat the window as a tool window,
    so it vanishes from the taskbar and Alt-Tab. Re-asserting
    WS_EX_APPWINDOW and re-showing puts it back.
    """
    try:
        root.overrideredirect(True)
        root.update_idletasks()
        hwnd = _raw_hwnd(root)
        if not hwnd:
            return False
        get = (ctypes.windll.user32.GetWindowLongPtrW
               if hasattr(ctypes.windll.user32, "GetWindowLongPtrW")
               else ctypes.windll.user32.GetWindowLongW)
        setl = (ctypes.windll.user32.SetWindowLongPtrW
                if hasattr(ctypes.windll.user32, "SetWindowLongPtrW")
                else ctypes.windll.user32.SetWindowLongW)
        style = get(hwnd, GWL_EXSTYLE)
        style = (style & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW
        setl(hwnd, GWL_EXSTYLE, style)
        root.withdraw()
        root.after(10, root.deiconify)
        return True
    except Exception:
        return False


def minimize(root):
    hwnd = _raw_hwnd(root)
    if hwnd:
        try:
            ctypes.windll.user32.ShowWindow(hwnd, SW_MINIMIZE)
            return
        except Exception:
            pass
    try:
        root.iconify()
    except Exception:
        pass


def work_area():
    """Screen area excluding the taskbar."""
    class RECT(ctypes.Structure):
        _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                    ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
    r = RECT()
    try:
        ctypes.windll.user32.SystemParametersInfoW(0x0030, 0,
                                                   ctypes.byref(r), 0)
        return r.left, r.top, r.right - r.left, r.bottom - r.top
    except Exception:
        return 0, 0, 1280, 800
