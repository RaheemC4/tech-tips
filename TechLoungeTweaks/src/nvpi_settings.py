"""Presentation preferences for the managed NVPI window."""
from pathlib import Path
import re
import xml.etree.ElementTree as ET

# TitleBarBackgroundColor from the bundled NVPI-R 7.2.1.0 theme dictionaries.
# These are source colours, not screen samples (HDR changes captured colours).
TITLE_COLOURS = {
    'MidnightTheme.xaml': 0x15110F,
    'DarkTheme.xaml': 0x202020,
    'AmoledTheme.xaml': 0x000000,
    'SlateLightTheme.xaml': 0xFFFFFF,
    'CleanWhiteTheme.xaml': 0xFFFFFF,
}


def read_settings(path):
    raw = Path(path).read_bytes()
    try:
        return ET.ElementTree(ET.fromstring(raw))
    except ET.ParseError:
        # NVPI's distributed file has a UTF-8 BOM but declares UTF-16.
        # Decode only positively identified UTF-8, retaining all user settings.
        if raw.startswith(b'\xef\xbb\xbf') or raw.lstrip().startswith(b'<?xml'):
            text = raw.decode('utf-8-sig')
            text = re.sub(r'^(\s*<\?xml\b[^?]*?)\s+encoding=[\"\'][^\"\']+[\"\']', r'\1', text, count=1)
            return ET.ElementTree(ET.fromstring(text))
        raise


def title_colour(folder):
    try:
        theme = read_settings(Path(folder) / 'Settings.xml').getroot().findtext('Theme')
    except (OSError, ET.ParseError, TypeError):
        theme = None
    return TITLE_COLOURS.get(theme, TITLE_COLOURS['MidnightTheme.xaml'])


def prepare_window(executable):
    """Prevent saved maximization/splash/backdrop before NVPI creates its HWND."""
    path = Path(executable).parent / 'Settings.xml'
    if not path.is_file():
        return
    tree = read_settings(path)
    root = tree.getroot()
    for name, value in (('WindowState', 'Normal'), ('DisableSplashScreen', 'true'),
                        ('Win11BackdropMode', 'Disabled')):
        node = root.find(name)
        if node is None:
            node = ET.SubElement(root, name)
        node.text = value
    temporary = path.with_suffix('.xml.tmp')
    tree.write(temporary, encoding='utf-8', xml_declaration=True)
    temporary.replace(path)
