"""Register the bundled Inter fonts for this process only (no install)."""

import base64
import ctypes
import os
import tempfile
import zlib

FR_PRIVATE = 0x10

FALLBACK = "Segoe UI"

# Family names as reported by the TTFs themselves.
FAMILY_REGULAR = "Inter"
FAMILY_MEDIUM = "Inter Medium"
FAMILY_SEMIBOLD = "Inter SemiBold"

_loaded = False


def _target_dir():
    base = os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
    d = os.path.join(base, "TechLoungeTweaks", "fonts")
    os.makedirs(d, exist_ok=True)
    return d


def load():
    """Write the fonts out and add them privately. Returns True on success."""
    global _loaded
    if _loaded:
        return True
    try:
        from fonts_payload import FONTS
    except Exception:
        return False

    d = _target_dir()
    ok = 0
    for name, blob in FONTS.items():
        path = os.path.join(d, name)
        try:
            if not os.path.exists(path) or os.path.getsize(path) == 0:
                data = zlib.decompress(base64.b64decode(blob))
                with open(path, "wb") as fh:
                    fh.write(data)
            added = ctypes.windll.gdi32.AddFontResourceExW(
                ctypes.c_wchar_p(path), FR_PRIVATE, 0)
            if added:
                ok += 1
        except Exception:
            pass
    _loaded = ok > 0
    return _loaded


def families(root=None):
    """Pick the best available families after load().

    Returns (regular, medium, semibold, bold_family, bold_weight).
    """
    have = set()
    if root is not None:
        try:
            import tkinter.font as tkfont
            have = set(tkfont.families(root))
        except Exception:
            have = set()

    def pick(name):
        if not have:
            return name if _loaded else FALLBACK
        return name if name in have else FALLBACK

    reg = pick(FAMILY_REGULAR)
    med = pick(FAMILY_MEDIUM)
    semi = pick(FAMILY_SEMIBOLD)
    # Inter-Bold shares the "Inter" family, reached with weight="bold"
    return reg, med, semi
