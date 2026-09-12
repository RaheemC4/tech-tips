"""Preserve the supplied tool versions and their reviewed startup preferences."""
import configparser
import os
from pathlib import Path
import shutil


def conflicting_copy(path):
    """Avoid a publisher singleton redirecting Open to another installed copy."""
    import psutil
    path = Path(path).resolve()
    for process in psutil.process_iter(['name']):
        try:
            if (process.info['name'] or '').lower() != path.name.lower():
                continue
            if Path(process.exe()).resolve() != path:
                return True
        except psutil.NoSuchProcess:
            continue
        except psutil.AccessDenied:
            return True
    return False


def prepare_driverbooster(settings_root=None, defaults=None):
    """Apply the repack's no-auto-update/no-auto-scan/exit preferences.

    Driver Booster reads its Windows user profile even when launched from a
    portable folder. Preserve other existing preferences and keep a first backup.
    """
    defaults = Path(defaults or Path(__file__).parent / 'vendor/personal-tools/driverbooster.ini')
    desired = configparser.ConfigParser(interpolation=None)
    desired.optionxform = str
    desired.read(defaults, encoding='utf-8-sig')
    root = Path(settings_root or Path(os.environ['APPDATA']) / 'IObit/Driver Booster')
    root.mkdir(parents=True, exist_ok=True)
    path = root / 'Config.ini'
    config = configparser.ConfigParser(interpolation=None, strict=False)
    config.optionxform = str
    if path.exists():
        raw = path.read_bytes()
        encoding = 'utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig'
        config.read_string(raw.decode(encoding))
        backup = root / 'Config.ini.before-techlounge'
        if not backup.exists(): shutil.copy2(path, backup)
    for section, keys in {
        'AutoUpdate': ('UpdateType', 'UpdateTypeX', 'Enabled'),
        'Drivers': ('AutoDownload', 'AutoDownloadX'),
        'Scan': ('AutoScan', 'Schedule'),
        'General': ('CloseAction', 'Scheduler'),
    }.items():
        if not config.has_section(section): config.add_section(section)
        for key in keys:
            config.set(section, key, desired.get(section, key))
    temporary = root / 'Config.ini.techlounge.tmp'
    with temporary.open('w', encoding='utf-16', newline='') as stream:
        config.write(stream, space_around_delimiters=False)
    os.replace(temporary, path)
