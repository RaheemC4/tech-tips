"""Standalone entry point; preserve the existing packaged-app layout contract."""
import os
import sys

if '__compiled__' in globals():
    # Existing app modules and update archives use this common bundle layout.
    # Set it before importing the backend (which resolves resources at import).
    sys.frozen = True
    executable_dir = os.path.dirname(sys.executable)
    if os.path.isfile(os.path.join(executable_dir, 'build-info.json')):
        sys._MEIPASS = executable_dir
        sys._tl_app_root = os.path.dirname(executable_dir)
    else:
        sys._MEIPASS = os.path.join(executable_dir, '_internal')
        sys._tl_app_root = executable_dir

import main

if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--package-check':
        # Read-only packaging check; never invoke tweak or activation actions.
        import json
        import traceback
        from pathlib import Path
        report = Path(sys.argv[2])
        try:
            import webview
            from updates import UpdateManager
            manager = UpdateManager()
            assert manager.channel == 'nuitka', 'Packaged update channel is missing'
            assert manager.root.name == 'nuitka', 'Update cache is not channel-isolated'
            assert manager.bundle_root.is_dir(), manager.bundle_root
            assert manager.bundle_manifest.is_file(), manager.bundle_manifest
            assert Path(main.here('web', 'index.html')).is_file()
            assert Path(main.here('apply-update.ps1')).is_file()
            for key, item in json.loads(manager.bundle_manifest.read_text()).items():
                assert (manager.bundle_root / key / item['exe']).is_file(), key
            window = webview.create_window('TechLoungeTweaks package check',
                html='<html><body id="check">Package check</body></html>', hidden=True)
            def check_window():
                try:
                    assert window.evaluate_js('document.getElementById("check").textContent') == 'Package check'
                    report.write_text(json.dumps({'ok': True, 'version': manager.build,
                        'resources': str(manager.bundle_root), 'webview': 'edgechromium'}), encoding='utf-8')
                except Exception:
                    report.write_text(traceback.format_exc(), encoding='utf-8')
                finally:
                    window.destroy()
            webview.start(check_window, gui='edgechromium')
        except Exception:
            report.write_text(traceback.format_exc(), encoding='utf-8')
            raise
    else:
        main.main()
