"""Recent read-only Home hardware summary, scoped to this Windows installation."""
import hashlib
import json
import os
from pathlib import Path
import platform
import tempfile
import time

MAX_AGE = 24 * 60 * 60


def cache_path(kind="hardware"):
    if kind not in ("hardware", "tweaks"):
        raise ValueError("Unknown summary")
    import winreg
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as key:
        machine = winreg.QueryValueEx(key, "MachineGuid")[0]
    identity = hashlib.sha256((machine + platform.version()).encode()).hexdigest()
    return Path(os.environ["LOCALAPPDATA"]) / "TechLoungeTweaks" / (kind + "-" + identity + ".json")


def load():
    try:
        data = json.loads(cache_path().read_text(encoding="utf-8"))
        age = time.time() - data["saved"]
        specs = data["specs"]
        if 0 <= age <= MAX_AGE and isinstance(specs, dict) and specs and all(
                isinstance(k, str) and isinstance(v, str) for k, v in specs.items()):
            return specs
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return {}


def _save(kind, field, value):
    temporary = None
    try:
        target = cache_path(kind)
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=target.parent,
                                         delete=False) as stream:
            temporary = stream.name
            json.dump({"saved": time.time(), field: value}, stream)
        os.replace(temporary, target)
    except (OSError, ValueError, KeyError, TypeError):
        pass
    finally:
        if temporary:
            try:
                os.unlink(temporary)
            except OSError:
                pass


def save(specs):
    if specs and "Error" not in specs:
        _save("hardware", "specs", specs)


def load_tweaks():
    try:
        data = json.loads(cache_path("tweaks").read_text(encoding="utf-8"))
        age = time.time() - data["saved"]
        tweaks = data["tweaks"]
        if 0 <= age <= MAX_AGE and isinstance(tweaks, list) and all(
                isinstance(t, dict) and isinstance(t.get("key"), str)
                and isinstance(t.get("name"), str) and isinstance(t.get("category"), str)
                and (t.get("applied") is None or type(t.get("applied")) is bool)
                for t in tweaks):
            return tweaks
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return []


def save_tweaks(tweaks):
    _save("tweaks", "tweaks", tweaks)
