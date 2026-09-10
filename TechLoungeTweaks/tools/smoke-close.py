"""Hidden native WebView2 test: exercise the real close bridge, no system tweaks."""
from pathlib import Path
import os
import sys
import threading
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import webview
from main import Api

api = Api.__new__(Api)
class CloseOnly:
    def close(self): return api.close()
window = webview.create_window('Tech Lounge close test', html='<html><body>Close test</body></html>',
                               js_api=CloseOnly(), hidden=True)
api._window = window
closed = threading.Event()
window.events.closed += lambda: closed.set()
watchdog = threading.Timer(20, lambda: os._exit(2))
watchdog.daemon = True
watchdog.start()
def test():
    if not window.events.loaded.wait(10): os._exit(3)
    window.evaluate_js('window.pywebview.api.close()')
webview.start(test, gui='edgechromium', debug=False)
watchdog.cancel()
assert closed.is_set(), 'Native window did not close'
print('PASS: real WebView2 close callback destroyed its own hidden window.')
