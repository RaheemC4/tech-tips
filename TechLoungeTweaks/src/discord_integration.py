"""Deploy the on-demand Discord launcher. Never register an autostart mechanism."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def launcher_source():
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS) / 'discord-launcher/DiscordLauncher.exe'
    return Path(__file__).resolve().parent / 'build/discord-launcher/DiscordLauncher.exe'


def _replace(source, destination):
    fd, temporary = tempfile.mkstemp(prefix=destination.name + '-', dir=destination.parent)
    os.close(fd)
    try:
        shutil.copyfile(source, temporary)
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def deploy(downloaded, digest, local_appdata=None):
    """Keep a validated cache outside Discord and integrate existing shortcuts."""
    if hashlib.sha256(Path(downloaded).read_bytes()).hexdigest() != digest.lower():
        raise ValueError('OpenAsar cache failed SHA-256 verification.')
    source = launcher_source()
    if not source.is_file():
        raise FileNotFoundError('The bundled Discord launcher is missing. Rebuild or reinstall TechLoungeTweaks.')
    root = local_appdata or os.environ.get('LOCALAPPDATA')
    if not root:
        raise OSError('Windows LocalAppData could not be located.')
    if local_appdata and os.path.normcase(os.path.abspath(local_appdata)) != os.path.normcase(os.path.abspath(os.environ.get('LOCALAPPDATA', ''))):
        raise ValueError('Shortcut integration must run in the current Windows profile.')
    home = Path(root) / 'TechLoungeTweaks/Discord'
    # Deployment must not follow an unexpected link to a different location.
    for part in (home, *home.parents):
        if part.is_symlink() or part.is_junction():
            raise OSError('Linked launcher directories are not supported.')
    home.mkdir(parents=True, exist_ok=True)
    _replace(downloaded, home / 'openasar.asar')
    fd, temporary = tempfile.mkstemp(prefix='receipt-', dir=home)
    try:
        with os.fdopen(fd, 'w', encoding='ascii') as receipt:
            receipt.write(digest.lower() + '\n')
        os.replace(temporary, home / 'openasar.sha256')
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    _replace(source, home / 'DiscordLauncher.exe')
    # The executable uses the current user's known folders; never run integration
    # against a supplied fixture or another profile.
    result = subprocess.run([str(home / 'DiscordLauncher.exe'), '--integrate'],
                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, timeout=20, creationflags=0x08000000)
    if result.returncode:
        raise OSError('Discord shortcut setup failed. See TechLoungeTweaks/Discord/launcher.log in LocalAppData.')
    return str(home / 'DiscordLauncher.exe')
