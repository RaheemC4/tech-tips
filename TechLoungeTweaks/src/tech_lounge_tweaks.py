"""
Tech Lounge Tweaks
A Paragon-style toggle-based Windows tweaking utility built from
The Tech Lounge's Tech-Tips Discord archive.

Run on Windows only. Some tweaks require admin rights and a restart to
fully apply.
"""

import sys
import ctypes
import subprocess
import tkinter as tk
from tkinter import messagebox

if sys.platform != "win32":
    print("This app only runs on Windows.")
    sys.exit(1)

import winreg  # noqa: E402

# ---- Fix blurry text on high-DPI displays ----
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PER_MONITOR_AWARE
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# ---- Theme ----
BG = "#0e0e0e"
PANEL = "#161616"
CARD = "#1b1b1b"
CARD_BORDER = "#2a2a2a"
CARD_BORDER_ACTIVE = "#e0212b"
ACCENT = "#e0212b"
TEXT = "#f2f2f2"
SUBTEXT = "#9a9a9a"
SIDEBAR_HOVER = "#1f1f1f"


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def relaunch_as_admin():
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, " ".join(sys.argv), None, 1
    )
    sys.exit(0)


def set_reg(hive, path, name, value, vtype):
    key = winreg.CreateKeyEx(hive, path, 0, winreg.KEY_SET_VALUE)
    with key:
        winreg.SetValueEx(key, name, 0, vtype, value)


def create_restore_point():
    ps_cmd = (
        'Checkpoint-Computer -Description "TechLoungeTweaks" '
        '-RestorePointType "MODIFY_SETTINGS"'
    )
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            check=False, capture_output=True, timeout=60,
        )
    except Exception:
        pass


# ---- Tweak definitions: (name, description, apply, revert) ----

def tweak_gamedvr():
    def apply():
        set_reg(winreg.HKEY_CURRENT_USER, r"System\GameConfigStore",
                "GameDVR_Enabled", 0, winreg.REG_DWORD)
        set_reg(winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\PolicyManager\default\ApplicationManagement\AllowGameDVR",
                "value", 0, winreg.REG_DWORD)

    def revert():
        set_reg(winreg.HKEY_CURRENT_USER, r"System\GameConfigStore",
                "GameDVR_Enabled", 1, winreg.REG_DWORD)
        set_reg(winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\PolicyManager\default\ApplicationManagement\AllowGameDVR",
                "value", 1, winreg.REG_DWORD)

    return apply, revert


def tweak_mouse_accel():
    def apply():
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Mouse",
                              0, winreg.KEY_SET_VALUE)
        with key:
            winreg.SetValueEx(key, "MouseSpeed", 0, winreg.REG_SZ, "0")
            winreg.SetValueEx(key, "MouseThreshold1", 0, winreg.REG_SZ, "0")
            winreg.SetValueEx(key, "MouseThreshold2", 0, winreg.REG_SZ, "0")

    def revert():
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Mouse",
                              0, winreg.KEY_SET_VALUE)
        with key:
            winreg.SetValueEx(key, "MouseSpeed", 0, winreg.REG_SZ, "1")
            winreg.SetValueEx(key, "MouseThreshold1", 0, winreg.REG_SZ, "6")
            winreg.SetValueEx(key, "MouseThreshold2", 0, winreg.REG_SZ, "10")

    return apply, revert


def tweak_dynamic_search():
    def apply():
        set_reg(winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\SearchSettings",
                "IsDynamicSearchBoxEnabled", 0, winreg.REG_DWORD)

    def revert():
        set_reg(winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\SearchSettings",
                "IsDynamicSearchBoxEnabled", 1, winreg.REG_DWORD)

    return apply, revert


def tweak_bing_search():
    def apply():
        set_reg(winreg.HKEY_CURRENT_USER,
                r"SOFTWARE\Policies\Microsoft\Windows\Explorer",
                "DisableSearchBoxSuggestions", 1, winreg.REG_DWORD)

    def revert():
        set_reg(winreg.HKEY_CURRENT_USER,
                r"SOFTWARE\Policies\Microsoft\Windows\Explorer",
                "DisableSearchBoxSuggestions", 0, winreg.REG_DWORD)

    return apply, revert


def tweak_classic_context_menu():
    def apply():
        path = r"SOFTWARE\CLASSES\CLSID\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}\InprocServer32"
        set_reg(winreg.HKEY_CURRENT_USER, path, "", "", winreg.REG_SZ)

    def revert():
        try:
            key_path = r"SOFTWARE\CLASSES\CLSID\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}"
            subprocess.run(["reg", "delete", f"HKCU\\{key_path}", "/f"],
                           check=False, capture_output=True)
        except Exception:
            pass

    return apply, revert


def tweak_snap_layout():
    def apply():
        set_reg(winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                "EnableSnapAssistFlyout", 0, winreg.REG_DWORD)

    def revert():
        set_reg(winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                "EnableSnapAssistFlyout", 1, winreg.REG_DWORD)

    return apply, revert


def tweak_lockscreen():
    def apply():
        set_reg(winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Policies\Microsoft\Windows\Personalization",
                "NoLockScreen", 1, winreg.REG_DWORD)

    def revert():
        set_reg(winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Policies\Microsoft\Windows\Personalization",
                "NoLockScreen", 0, winreg.REG_DWORD)

    return apply, revert


def tweak_fast_shutdown():
    def apply():
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control",
                "WaitToKillServiceTimeout", "500", winreg.REG_SZ)

    def revert():
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control",
                "WaitToKillServiceTimeout", "5000", winreg.REG_SZ)

    return apply, revert


def tweak_network_throttle():
    def apply():
        p = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile"
        set_reg(winreg.HKEY_LOCAL_MACHINE, p, "NetworkThrottlingIndex", 0xffffffff, winreg.REG_DWORD)
        set_reg(winreg.HKEY_LOCAL_MACHINE, p, "SystemResponsiveness", 0, winreg.REG_DWORD)

    def revert():
        p = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile"
        set_reg(winreg.HKEY_LOCAL_MACHINE, p, "NetworkThrottlingIndex", 10, winreg.REG_DWORD)
        set_reg(winreg.HKEY_LOCAL_MACHINE, p, "SystemResponsiveness", 20, winreg.REG_DWORD)

    return apply, revert


def tweak_firewall_notify():
    def apply():
        subprocess.run(["powershell", "-NoProfile", "-Command",
                         "Set-NetFirewallProfile -All -NotifyOnListen False"],
                        check=False, capture_output=True)

    def revert():
        subprocess.run(["powershell", "-NoProfile", "-Command",
                         "Set-NetFirewallProfile -All -NotifyOnListen True"],
                        check=False, capture_output=True)

    return apply, revert


CATEGORIES = {
    "General": [
        ("Disable GameDVR", "Turns off Xbox Game Bar recording/overlay for better game performance.", tweak_gamedvr),
        ("Disable Mouse Acceleration", "Improves aim consistency by removing pointer acceleration curve.", tweak_mouse_accel),
        ("Speed Up Shutdown", "Reduces the time Windows waits for services to close on shutdown.", tweak_fast_shutdown),
    ],
    "Explorer & UI": [
        ("Disable Dynamic Search Box", "Stops the Windows search box resizing/animating.", tweak_dynamic_search),
        ("Remove Bing Suggestions from Start", "Keeps Start Menu search local-only, no web suggestions.", tweak_bing_search),
        ("Restore Classic Context Menu", "Brings back the Windows 10-style right-click menu on Windows 11.", tweak_classic_context_menu),
        ("Disable Snap Layout Flyout", "Removes the hover popup when hovering the maximize button.", tweak_snap_layout),
        ("Disable Lock Screen", "Skips straight to the sign-in screen, no lock screen.", tweak_lockscreen),
    ],
    "Networking": [
        ("Network Throttle Fix", "Disables network throttling index, sets system responsiveness to 0 for lower latency.", tweak_network_throttle),
        ("Disable Firewall Notifications", "Stops the 'app blocked by firewall' popups.", tweak_firewall_notify),
    ],
}


class ToggleSwitch(tk.Canvas):
    """Simple rounded on/off switch drawn on a canvas."""

    WIDTH, HEIGHT = 46, 24

    def __init__(self, parent, command=None, initial=False, **kwargs):
        super().__init__(parent, width=self.WIDTH, height=self.HEIGHT,
                          bg=parent["bg"], highlightthickness=0, **kwargs)
        self.command = command
        self.state = initial
        self.bind("<Button-1>", self._on_click)
        self._draw()

    def _draw(self):
        self.delete("all")
        on = self.state
        track = ACCENT if on else "#3d3d3d"
        h = self.HEIGHT
        r = h / 2                      # track radius
        # rounded track: circle + rect + circle
        self.create_oval(0, 0, h, h, fill=track, outline="")
        self.create_oval(self.WIDTH - h, 0, self.WIDTH, h, fill=track, outline="")
        self.create_rectangle(r, 0, self.WIDTH - r, h, fill=track, outline="")
        # knob
        kr = r - 3
        kx = (self.WIDTH - r) if on else r
        self.create_oval(kx - kr, r - kr, kx + kr, r + kr,
                         fill="#ffffff", outline="")

    def _on_click(self, _event):
        new_state = not self.state
        try:
            if self.command:
                self.command(new_state)
            self.state = new_state
        except Exception as e:
            messagebox.showerror("Error", str(e))
        self._draw()

    def set_state(self, value):
        self.state = value
        self._draw()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Tech Lounge Tweaks")
        self.geometry("980x640")
        self.minsize(860, 560)
        self.configure(bg=BG)

        self.current_category = tk.StringVar(value=list(CATEGORIES.keys())[0])

        self._build_sidebar()
        self._build_main()
        self.render_category()

    # ---------- Sidebar ----------
    def _build_sidebar(self):
        sidebar = tk.Frame(self, bg=PANEL, width=220)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        header = tk.Frame(sidebar, bg=PANEL)
        header.pack(fill="x", pady=(20, 24), padx=18)
        tk.Label(header, text="Tech Lounge", font=("Segoe UI", 14, "bold"),
                 bg=PANEL, fg=TEXT).pack(anchor="w")
        tk.Label(header, text="Tweaking Utility", font=("Segoe UI", 9),
                 bg=PANEL, fg=SUBTEXT).pack(anchor="w")

        tk.Frame(sidebar, bg=CARD_BORDER, height=1).pack(fill="x", padx=18, pady=(0, 12))

        self.nav_buttons = {}
        for cat in CATEGORIES:
            btn = tk.Label(sidebar, text=cat, font=("Segoe UI", 11), bg=PANEL,
                            fg=TEXT, anchor="w", padx=18, pady=10, cursor="hand2")
            btn.pack(fill="x")
            btn.bind("<Button-1>", lambda e, c=cat: self.switch_category(c))
            btn.bind("<Enter>", lambda e, b=btn: b.configure(bg=SIDEBAR_HOVER))
            btn.bind("<Leave>", lambda e, b=btn: self._refresh_nav_colors())
            self.nav_buttons[cat] = btn

        tk.Frame(sidebar, bg=PANEL).pack(fill="both", expand=True)

        tk.Button(sidebar, text="Create Restore Point", command=self.on_restore_point,
                  bg=ACCENT, fg="white", activebackground="#b81b23", activeforeground="white",
                  relief="flat", font=("Segoe UI", 10, "bold"), pady=8
                  ).pack(fill="x", padx=18, pady=18)

        self._refresh_nav_colors()

    def _refresh_nav_colors(self):
        for cat, btn in self.nav_buttons.items():
            if cat == self.current_category.get():
                btn.configure(bg=SIDEBAR_HOVER, fg=ACCENT)
            else:
                btn.configure(bg=PANEL, fg=TEXT)

    def switch_category(self, cat):
        self.current_category.set(cat)
        self._refresh_nav_colors()
        self.render_category()

    # ---------- Main content ----------
    def _build_main(self):
        main = tk.Frame(self, bg=BG)
        main.pack(side="left", fill="both", expand=True)

        top = tk.Frame(main, bg=BG)
        top.pack(fill="x", padx=28, pady=(24, 8))
        self.title_label = tk.Label(top, text="", font=("Segoe UI", 18, "bold"), bg=BG, fg=TEXT)
        self.title_label.pack(anchor="w")
        self.subtitle_label = tk.Label(top, text="Toggle a tweak to apply it. Toggle off to revert.",
                                        font=("Segoe UI", 10), bg=BG, fg=SUBTEXT)
        self.subtitle_label.pack(anchor="w", pady=(2, 0))

        self.cards_container = tk.Frame(main, bg=BG)
        self.cards_container.pack(fill="both", expand=True, padx=20, pady=10)

    def render_category(self):
        for widget in self.cards_container.winfo_children():
            widget.destroy()

        cat = self.current_category.get()
        self.title_label.configure(text=cat)

        cols = 2
        for i, (name, desc, factory) in enumerate(CATEGORIES[cat]):
            apply_fn, revert_fn = factory()
            r, c = divmod(i, cols)

            card = tk.Frame(self.cards_container, bg=CARD, highlightbackground=CARD_BORDER,
                             highlightthickness=1, padx=16, pady=14)
            card.grid(row=r, column=c, sticky="nsew", padx=8, pady=8)
            self.cards_container.grid_columnconfigure(c, weight=1, uniform="col")

            row = tk.Frame(card, bg=CARD)
            row.pack(fill="x")
            tk.Label(row, text=name, font=("Segoe UI", 11, "bold"), bg=CARD, fg=TEXT,
                     anchor="w", wraplength=230, justify="left").pack(side="left", fill="x", expand=True)

            def on_toggle(state, a=apply_fn, r=revert_fn, n=name):
                if state:
                    a()
                else:
                    r()

            switch = ToggleSwitch(row, command=on_toggle, initial=False)
            switch.pack(side="right")

            tk.Label(card, text=desc, font=("Segoe UI", 9), bg=CARD, fg=SUBTEXT,
                     anchor="w", wraplength=290, justify="left",
                     height=3).pack(fill="x", pady=(6, 0))

        note = tk.Label(self.cards_container, text="Some tweaks need a restart to fully apply.",
                         font=("Segoe UI", 8), bg=BG, fg="#666666")
        note.grid(row=99, column=0, columnspan=2, sticky="w", pady=(16, 0), padx=8)

    def on_restore_point(self):
        create_restore_point()
        messagebox.showinfo("Restore Point", "Attempted to create a system restore point.")


if __name__ == "__main__":
    if not is_admin():
        relaunch_as_admin()
    else:
        App().mainloop()
