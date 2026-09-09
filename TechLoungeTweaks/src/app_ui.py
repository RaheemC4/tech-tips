"""Tech Lounge Tweaks - Paragon-style UI built on CustomTkinter."""

import base64
import ctypes
import os
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
import webbrowser

import customtkinter as ctk
from PIL import ImageTk

from tweaks_engine import (build_tweaks, CATEGORY_ORDER, CATEGORY_ICONS,
                           run, CREATE_NO_WINDOW)
import time

import boot_payload
import bootparse
import chrome
import cleanup
import gfx
import drivers
import fontloader
import nettest
import sysinfo
import tooltip
import biosinfo

# ---------------------------------------------------------------- palette
BG          = "#0b0b0c"
SIDEBAR     = "#111113"
CARD        = "#171719"
CARD_HOVER  = "#1d1d20"
BORDER      = "#242428"
BORDER_ON   = "#2f7d4f"
ACCENT      = "#e11d2a"
ACCENT_DIM  = "#8f141d"
TEXT        = "#f4f4f5"
MUTED       = "#8b8b92"
FAINT       = "#5c5c63"
WARN_BG     = "#2b2411"
WARN_FG     = "#e3b23c"
OK_BG       = "#12301f"
OK_FG       = "#57d98a"
LOCK_BG     = "#1b2838"
LOCK_FG     = "#6ba4e0"

ctk.set_appearance_mode("dark")

# Resolved once the Tk root exists; falls back to Segoe UI.
F_REG = "Segoe UI"
F_MED = "Segoe UI"
F_SEMI = "Segoe UI"
F_SYM = "Segoe UI Symbol"


def resolve_fonts(root):
    global F_REG, F_MED, F_SEMI
    try:
        fontloader.load()
        F_REG, F_MED, F_SEMI = fontloader.families(root)
    except Exception:
        pass


def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def bind_scroll(scrollable):
    """Make the wheel work anywhere over a scrollable page.

    CTkScrollableFrame only binds the wheel to itself and its scrollbar, so
    the wheel does nothing while the cursor is over a card - which is most
    of the page.
    """
    canvas = getattr(scrollable, "_parent_canvas", None)
    if canvas is None:
        return

    def on_wheel(event):
        try:
            canvas.yview_scroll(int(-1 * (event.delta / 40)), "units")
        except Exception:
            pass
        return "break"

    def apply(widget):
        try:
            widget.bind("<MouseWheel>", on_wheel, add="+")
        except Exception:
            pass
        for child in widget.winfo_children():
            apply(child)

    apply(scrollable)
    scrollable.after(600, lambda: apply(scrollable))
    scrollable.after(2500, lambda: apply(scrollable))



def raise_page(widget):
    """Bring a page to the front of the stack.

    CTkScrollableFrame proxies grid()/pack() to an internal parent frame but
    NOT tkraise(), so calling tkraise() on it raises the inner frame and the
    old page stays visible. Raise whatever is actually being managed.
    """
    target = getattr(widget, "_parent_frame", None)
    try:
        (target or widget).tkraise()
    except Exception:
        try:
            widget.tkraise()
        except Exception:
            pass



def _mix(c1, c2, t):
    """Blend two #rrggbb colours; t=0 -> c1, t=1 -> c2."""
    def parts(c):
        c = c.lstrip("#")
        return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    a, b = parts(c1), parts(c2)
    return "#%02x%02x%02x" % tuple(
        int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def animate_colour(widget, option, start, end, steps=7, ms=16, done=None):
    """Ease a colour option from start to end over a few frames."""
    def step(i):
        t = i / steps
        t = t * t * (3 - 2 * t)          # smoothstep
        try:
            widget.configure(**{option: _mix(start, end, t)})
        except Exception:
            return
        if i < steps:
            widget.after(ms, lambda: step(i + 1))
        elif done:
            done()
    step(0)



class TweakCard(ctk.CTkFrame):
    """One tweak: icon, name, description, status badge and switch."""

    def __init__(self, master, tweak, on_change):
        super().__init__(master, fg_color=CARD, corner_radius=10,
                         border_width=1, border_color=BORDER)
        self.tweak = tweak
        self.on_change = on_change
        self.locked = False
        self.applied = False
        self._busy = False

        self.grid_columnconfigure(1, weight=1)

        icon = ctk.CTkLabel(self, text=tweak.icon, width=38, height=38,
                            corner_radius=8, fg_color="#232327",
                            text_color=TEXT,
                            font=ctk.CTkFont(family=F_SYM, size=17))
        icon.grid(row=0, column=0, padx=(14, 10), pady=(14, 0), sticky="nw")

        self.title_lbl = ctk.CTkLabel(
            self, text=tweak.name, text_color=TEXT, anchor="w",
            justify="left", wraplength=225, height=38,
            font=ctk.CTkFont(family=F_SEMI, size=14))
        self.title_lbl.grid(row=0, column=1, columnspan=2, padx=(0, 14),
                            pady=(14, 0), sticky="w")

        self.desc_lbl = ctk.CTkLabel(
            self, text=tweak.desc, text_color=MUTED, anchor="nw",
            justify="left", wraplength=272, height=54,
            font=ctk.CTkFont(family=F_REG, size=12))
        self.desc_lbl.grid(row=1, column=0, columnspan=3, padx=14,
                           pady=(4, 0), sticky="new")

        foot = ctk.CTkFrame(self, fg_color="transparent")
        foot.grid(row=2, column=0, columnspan=3, padx=14, pady=(12, 13),
                  sticky="ew")
        foot.grid_columnconfigure(0, weight=1)

        self.badge = ctk.CTkLabel(
            foot, text="", corner_radius=6, height=22,
            font=ctk.CTkFont(family=F_SEMI, size=10))
        self.badge.grid(row=0, column=0, sticky="w")

        self.switch = ctk.CTkSwitch(
            foot, text="", width=44, height=22, switch_width=40,
            switch_height=20, corner_radius=11,
            progress_color=ACCENT, button_color="#ffffff",
            fg_color="#3a3a40", command=self._toggled)
        self.switch.grid(row=0, column=1, sticky="e")

        self.warn = ctk.CTkLabel(
            self,
            text=("  ▲  " + tweak.warning + "  ")
            if tweak.warning else "",
            corner_radius=10, height=42, anchor="w", justify="left",
            wraplength=248,
            fg_color=WARN_BG if tweak.warning else "transparent",
            text_color=WARN_FG,
            font=ctk.CTkFont(family=F_SEMI, size=11))
        self.warn.grid(row=3, column=0, columnspan=3, padx=14,
                       pady=(0, 12), sticky="w")

        self._hovered = False
        self._bind_hover()
        body = tweak.desc
        if tweak.warning:
            body += "\n\nHeads up: " + tweak.warning + "."
        if tweak.needs_restart:
            body += "\n\nNeeds a restart before it takes effect."
        tooltip.attach(self, tweak.name, body,
                       good=("Safe to turn on and off - the toggle puts it "
                             "back exactly as it was."),
                       font_semi=F_SEMI, font_reg=F_REG)

    def _bind_hover(self):
        targets = [self] + list(self.winfo_children())
        for w in targets:
            w.bind("<Enter>", lambda e: self._hover(True), add="+")
            w.bind("<Leave>", lambda e: self._hover(False), add="+")

    def _hover(self, on):
        if getattr(self, "_hovered", False) == on:
            return
        self._hovered = on
        base = CARD
        edge = BORDER_ON if self.applied and not self.locked else BORDER
        animate_colour(self, "fg_color", CARD if on else CARD_HOVER,
                       CARD_HOVER if on else base)
        animate_colour(self, "border_color", edge if on else "#3c3c46",
                       "#3c3c46" if on else edge)

    # -------------------------------------------------- state rendering
    def set_state(self, applied, locked):
        self.applied = applied
        self.locked = locked
        if applied:
            self.switch.select()
        else:
            self.switch.deselect()

        if locked:
            self.switch.configure(state="disabled")
            self.badge.configure(text="  ALREADY ON  ", fg_color=LOCK_BG,
                                 text_color=LOCK_FG)
            self.configure(border_color=BORDER)
        elif applied:
            self.switch.configure(state="normal")
            self.badge.configure(text="  APPLIED  ", fg_color=OK_BG,
                                 text_color=OK_FG)
            self.configure(border_color=BORDER_ON)
        else:
            self.switch.configure(state="normal")
            self.badge.configure(text="  NOT APPLIED  ", fg_color="#1c1c20",
                                 text_color=FAINT)
            self.configure(border_color=BORDER)

    def _toggled(self):
        if self._busy or self.locked:
            return
        want = bool(self.switch.get())
        self._busy = True
        self.badge.configure(text="  WORKING…  ", fg_color="#2a2a30",
                             text_color=MUTED)

        def work():
            err = None
            try:
                if want:
                    self.tweak.apply()
                else:
                    self.tweak.revert()
            except Exception as e:
                err = e
            self.after(0, lambda: self._done(want, err))

        threading.Thread(target=work, daemon=True).start()

    def _done(self, want, err):
        self._busy = False
        if err is not None:
            self.badge.configure(text="  FAILED  ", fg_color="#3a1216",
                                 text_color="#ef6b76")
            self.switch.deselect()
        else:
            self.set_state(want, False)
        self.on_change()


NAV_LAYOUT = [
    ("section", "GENERAL"),
    ("page", "Home", "⌂"),
    ("section", "TWEAKS"),
    ("cat", "Performance"), ("cat", "Graphics"), ("cat", "GPU"),
    ("cat", "Networking"),
    ("cat", "Power"), ("cat", "Advanced"), ("cat", "System"),
    ("cat", "Privacy"), ("cat", "Explorer & UI"),
    ("section", "SYSTEM"),
    ("page", "System Info", "▣"), ("page", "Disk Cleanup", "◫"),
    ("page", "Drivers", "◨"), ("page", "Resources", "▤"),
    ("section", "TOOLS"),
    ("page", "Boot Optimizer", "▲"), ("page", "BIOS Info", "▦"),
    ("page", "System Restore", "⟲"),
]

ROW_H = 34
SIDEBAR_W = 252


class Sidebar(tk.Canvas):
    """Canvas-drawn nav so the prism artwork shows through behind it."""

    def __init__(self, master, on_select):
        super().__init__(master, width=SIDEBAR_W, bg=SIDEBAR,
                         highlightthickness=0, bd=0)
        self.on_select = on_select
        self.active = None
        self.hover = None
        self.chips = {}
        self.rows = []
        self._bg_img = None
        self._art_path = None
        self.footer_text = "0 tweaks applied"
        self.footer_sub = ""
        self.footer_ok = True

        self._resize_job = None
        self._drift = 0.0
        self._drift_dir = 1
        self._img_id = None
        self.bind("<Configure>", self._on_configure)
        self.after(400, self._tick_drift)
        self.bind("<Motion>", self._motion)
        self.bind("<Leave>", lambda e: self._sethover(None))
        self.bind("<Button-1>", self._click)

    def _on_configure(self, _event=None):
        """Coalesce resize events - repainting on every one locks the UI."""
        if self._resize_job is not None:
            try:
                self.after_cancel(self._resize_job)
            except Exception:
                pass
        self._resize_job = self.after(90, self._resize_done)

    def _resize_done(self):
        self._resize_job = None
        self.redraw()

    def _tick_drift(self):
        """Very slow vertical drift so the panel never looks frozen.

        Just moves the pre-rendered image - no repainting, no CPU cost.
        """
        try:
            if self._img_id is not None and self._art_path:
                span = max(0, self._art_path[1] - (self.winfo_height() or 900))
                if span > 40:
                    self._drift += 0.22 * self._drift_dir
                    if self._drift <= -min(span, 260) or self._drift >= 0:
                        self._drift_dir *= -1
                    self.coords(self._img_id, 0, self._drift)
        except Exception:
            pass
        self.after(50, self._tick_drift)

    # -------------------------------------------------- helpers
    def _round_rect(self, x0, y0, x1, y1, r, **kw):
        pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r,
               x1, y1, x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r,
               x0, y0 + r, x0, y0]
        return self.create_polygon(pts, smooth=True, **kw)

    def set_chip(self, key, text, colour):
        self.chips[key] = (text, colour)
        self.redraw()

    def set_active(self, key):
        self.active = key
        self.redraw()

    def set_footer(self, text, sub, ok=True):
        self.footer_text, self.footer_sub, self.footer_ok = text, sub, ok
        self.redraw()

    def _row_at(self, y):
        for r in self.rows:
            if r["y0"] <= y <= r["y1"]:
                return r["key"]
        return None

    def _sethover(self, key):
        if key != self.hover:
            self.hover = key
            self._hover_t = 0.0
            self.redraw()
            self._ease_hover(0)

    def _ease_hover(self, i):
        if i > 6:
            return
        self._hover_t = (i / 6.0)
        self.redraw()
        self.after(18, lambda: self._ease_hover(i + 1))

    def _motion(self, e):
        self._sethover(self._row_at(e.y))
        self.configure(cursor="hand2" if self.hover else "")

    def _click(self, e):
        key = self._row_at(e.y)
        if key:
            self.on_select(key)

    # -------------------------------------------------- painting
    def redraw(self):
        self.delete("all")
        w = self.winfo_width() or SIDEBAR_W
        h = self.winfo_height() or 900

        # Render once, tall enough for any window, and reuse. Regenerating
        # per resize is what made dragging the window fall apart.
        art_h = max(1600, h)
        if self._art_path is None or self._art_path[0] != w or \
                self._art_path[1] < h:
            path = chrome.prism_image(w, art_h, SIDEBAR)
            if path:
                try:
                    self._bg_img = tk.PhotoImage(file=path)
                    self._art_path = (w, art_h)
                except Exception:
                    self._bg_img = None
        if self._bg_img:
            self._img_id = self.create_image(0, self._drift, image=self._bg_img,
                                             anchor="nw")

        # ---- logo
        self._round_rect(18, 22, 56, 60, 11, fill=ACCENT, outline="")
        self.create_text(37, 41, text="TL", fill="#ffffff",
                         font=(F_SEMI, 14, "bold"))
        self.create_text(68, 33, text="Tech Lounge", anchor="w", fill=TEXT,
                         font=(F_SEMI, 14, "bold"))
        self.create_text(68, 52, text="Tweaking Utility", anchor="w",
                         fill=MUTED, font=(F_REG, 9))

        y = 84
        self.rows = []
        for entry in NAV_LAYOUT:
            if entry[0] == "section":
                y += 14
                self.create_text(22, y, text=entry[1], anchor="w", fill=FAINT,
                                 font=(F_SEMI, 8, "bold"))
                y += 14
                continue

            key = entry[1]
            icon = (CATEGORY_ICONS.get(key, "⚙") if entry[0] == "cat"
                    else entry[2])
            y0, y1 = y, y + ROW_H
            is_active = (key == self.active)
            is_hover = (key == self.hover)

            if is_active:
                self._round_rect(10, y0, w - 12, y1, 9,
                                 fill="#1e1e23", outline="")
                self.create_rectangle(10, y0 + 8, 13, y1 - 8,
                                      fill=ACCENT, outline="")
            elif is_hover:
                t = getattr(self, "_hover_t", 1.0)
                self._round_rect(10, y0, w - 12, y1, 9,
                                 fill=_mix(SIDEBAR, "#1c1c22", t),
                                 outline="")

            fg = TEXT if (is_active or is_hover) else MUTED
            self.create_text(30, (y0 + y1) // 2, text=icon, anchor="w",
                             fill=ACCENT if is_active else MUTED,
                             font=(F_SYM, 12))
            self.create_text(52, (y0 + y1) // 2, text=key, anchor="w",
                             fill=fg, font=(F_REG, 11))

            chip = self.chips.get(key)
            if chip and chip[0]:
                self.create_text(w - 22, (y0 + y1) // 2, text=chip[0],
                                 anchor="e", fill=chip[1], font=(F_REG, 9))

            self.rows.append({"key": key, "y0": y0, "y1": y1})
            y = y1 + 2

        # ---- footer card
        fy = h - 82
        self._round_rect(12, fy, w - 12, h - 16, 11,
                         fill="#141418", outline="")
        self.create_text(w // 2, fy + 26, text=self.footer_text, fill=TEXT,
                         font=(F_SEMI, 11, "bold"))
        self.create_text(w // 2, fy + 48, text=self.footer_sub,
                         fill=OK_FG if self.footer_ok else WARN_FG,
                         font=(F_REG, 9))


class App(ctk.CTk):
    def __init__(self):
        super().__init__(fg_color=BG)
        resolve_fonts(self)
        self.title("Tech Lounge Tweaks")
        self.geometry("1320x860")
        self.minsize(1160, 720)

        self.tweaks = build_tweaks()
        self.cards = {}
        self.page = "Home"
        self._bios_loaded = False
        self._sys_loaded = False
        self._clean_loaded = False
        self._home_loaded = False
        self._drv_loaded = False
        self.sys_section = sysinfo.SECTIONS[0][0]

        self._maximized = False
        self._normal_geom = None
        self._build_titlebar()
        self.shell = ctk.CTkFrame(self, fg_color="transparent",
                                  corner_radius=0)
        self.shell.pack(fill="both", expand=True)

        self.sidebar = Sidebar(self.shell, self.show_page)
        self.sidebar.pack(side="left", fill="y")
        self._build_main()
        self.show_page("Home")
        self.after(60, self._setup_window)
        self.after(900, self._bind_all_scrolling)
        self.after(200, self.rescan)


    # ------------------------------------------------------- window shell
    def _setup_window(self):
        chrome.set_app_id()
        icon = os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(
            os.path.abspath(__file__))), "app.ico")
        chrome.set_icon(self, icon)
        chrome.apply(self)
        # Drop the OS title bar so the whole window is one surface.
        if not chrome.make_frameless(self):
            self.titlebar.pack_forget()

    def _bind_all_scrolling(self):
        for page in getattr(self, "_all_pages", ()):
            if isinstance(page, ctk.CTkScrollableFrame):
                bind_scroll(page)
        for extra in (getattr(self, "sys_body", None),
                      getattr(self, "clean_body", None),
                      getattr(self, "bios_grid", None),
                      getattr(self, "boot_results", None)):
            if isinstance(extra, ctk.CTkScrollableFrame):
                bind_scroll(extra)

    def _build_titlebar(self):
        bar = ctk.CTkFrame(self, height=40, corner_radius=0,
                           fg_color="#0e0e11")
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)
        self.titlebar = bar

        dot = ctk.CTkLabel(bar, text="", width=10, height=10,
                           corner_radius=5, fg_color=ACCENT)
        dot.pack(side="left", padx=(16, 8))
        name = ctk.CTkLabel(bar, text="Tech Lounge Tweaks", text_color=MUTED,
                            font=ctk.CTkFont(family=F_SEMI, size=11))
        name.pack(side="left")

        def win_btn(txt, cmd, hover="#26262e", fg=MUTED):
            b = ctk.CTkLabel(bar, text=txt, width=44, height=40,
                             text_color=fg, fg_color="transparent",
                             font=ctk.CTkFont(family=F_SYM, size=13))
            b.pack(side="right")
            b.bind("<Button-1>", lambda e: cmd())
            b.bind("<Enter>", lambda e: b.configure(fg_color=hover,
                                                    text_color=TEXT))
            b.bind("<Leave>", lambda e: b.configure(fg_color="transparent",
                                                    text_color=fg))
            b.configure(cursor="hand2")
            return b

        win_btn("✕", self.destroy, hover="#c02b33")
        win_btn("▢", self._toggle_max)
        win_btn("─", lambda: chrome.minimize(self))

        for w in (bar, dot, name):
            w.bind("<Button-1>", self._drag_start)
            w.bind("<B1-Motion>", self._drag_move)
            w.bind("<Double-Button-1>", lambda e: self._toggle_max())

    def _drag_start(self, event):
        self._drag_x = event.x_root - self.winfo_x()
        self._drag_y = event.y_root - self.winfo_y()

    def _drag_move(self, event):
        if self._maximized:
            return
        try:
            self.geometry(f"+{event.x_root - self._drag_x}"
                          f"+{event.y_root - self._drag_y}")
        except Exception:
            pass

    def _toggle_max(self):
        if self._maximized:
            if self._normal_geom:
                self.geometry(self._normal_geom)
            self._maximized = False
        else:
            self._normal_geom = self.geometry()
            x, y, w, h = chrome.work_area()
            self.geometry(f"{w}x{h}+{x}+{y}")
            self._maximized = True

    # --------------------------------------------------------------- main
    def _build_main(self):
        main = ctk.CTkFrame(self.shell, fg_color=BG, corner_radius=0)
        main.pack(side="left", fill="both", expand=True)

        self.crumb = ctk.CTkLabel(
            main, text="", text_color=FAINT, anchor="w",
            font=ctk.CTkFont(family=F_REG, size=12))
        self.crumb.pack(fill="x", padx=30, pady=(18, 0))

        header = ctk.CTkFrame(main, fg_color="transparent")
        header.pack(fill="x", padx=30, pady=(6, 0))

        left = ctk.CTkFrame(header, fg_color="transparent")
        left.pack(side="left", anchor="w")
        self.title_lbl = ctk.CTkLabel(
            left, text="", text_color=TEXT, anchor="w",
            font=ctk.CTkFont(family=F_SEMI, size=24))
        self.title_lbl.pack(anchor="w")
        self.sub_lbl = ctk.CTkLabel(
            left, text="", text_color=MUTED, anchor="w",
            font=ctk.CTkFont(family=F_REG, size=12))
        self.sub_lbl.pack(anchor="w", pady=(2, 0))

        right = ctk.CTkFrame(header, fg_color="transparent")
        right.pack(side="right", anchor="e")
        self.count_lbl = ctk.CTkLabel(
            right, text="", text_color=MUTED,
            font=ctk.CTkFont(family=F_REG, size=12))
        self.count_lbl.pack(side="left", padx=(0, 14))

        self.btn_apply = ctk.CTkButton(
            right, text="Apply All", width=92, height=32, corner_radius=8,
            fg_color=ACCENT, hover_color=ACCENT_DIM, text_color="#ffffff",
            font=ctk.CTkFont(family=F_SEMI, size=12),
            command=lambda: self.bulk(True))
        self.btn_apply.pack(side="left", padx=(0, 8))

        self.btn_revert = ctk.CTkButton(
            right, text="Revert All", width=92, height=32, corner_radius=8,
            fg_color="#232327", hover_color="#2d2d33", text_color=TEXT,
            font=ctk.CTkFont(family=F_REG, size=12),
            command=lambda: self.bulk(False))
        self.btn_revert.pack(side="left", padx=(0, 8))

        self.btn_scan = ctk.CTkButton(
            right, text="Rescan", width=78, height=32, corner_radius=8,
            fg_color="#232327", hover_color="#2d2d33", text_color=TEXT,
            font=ctk.CTkFont(family=F_REG, size=12),
            command=self.rescan)
        self.btn_scan.pack(side="left")

        self.body = ctk.CTkFrame(main, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=22, pady=(16, 18))
        self.body.grid_rowconfigure(0, weight=1)
        self.body.grid_columnconfigure(0, weight=1)

        # ---- tweak grid page
        self.grid_page = ctk.CTkScrollableFrame(
            self.body, fg_color="transparent", scrollbar_button_color="#2a2a30",
            scrollbar_button_hover_color="#3a3a42")
        for c in range(3):
            self.grid_page.grid_columnconfigure(c, weight=1, uniform="cards")

        # ---- networking page (test + its own tweak cards)
        self.net_page = self._build_net_page()

        for tw in self.tweaks:
            parent = (self.net_cards_holder if tw.category == "Networking"
                      else self.grid_page)
            self.cards[tw.key] = TweakCard(parent, tw, self.refresh_counts)

        i = 0
        for tw in self.tweaks:
            if tw.category == "Networking":
                r, c = divmod(i, 3)
                self.cards[tw.key].grid(row=r, column=c, padx=8, pady=8,
                                        sticky="nsew")
                i += 1

        # ---- boot optimiser page
        self.boot_page = self._build_boot_page()
        # ---- restore page
        self.restore_page = self._build_restore_page()
        self.bios_page = self._build_bios_page()
        self.sys_page = self._build_sys_page()
        self.clean_page = self._build_clean_page()
        self.res_page = self._build_res_page()
        self.home_page = self._build_home_page()
        self.drv_page = self._build_drv_page()

    def _build_boot_page(self):
        f = ctk.CTkFrame(self.body, fg_color="transparent")

        info = ctk.CTkFrame(f, fg_color=CARD, corner_radius=10,
                            border_width=1, border_color=BORDER)
        info.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(
            info,
            text="Detects your CPU and GPU, then applies the boot tweaks that "
                 "suit them. Secure Boot, TPM and VBS are never touched, so "
                 "kernel anti-cheat keeps working. Every change is written to "
                 "a rollback file.",
            text_color=MUTED, justify="left", anchor="w", wraplength=820,
            font=ctk.CTkFont(family=F_REG, size=12)).pack(
            padx=18, pady=14, anchor="w")

        btns = ctk.CTkFrame(f, fg_color="transparent")
        btns.pack(fill="x", pady=(0, 12))
        self.boot_preview = ctk.CTkButton(
            btns, text="Preview Changes", width=160, height=36,
            corner_radius=8, fg_color="#232327", hover_color="#2d2d33",
            text_color=TEXT, font=ctk.CTkFont(family=F_REG, size=12),
            command=lambda: self.run_boot(False, preview=True))
        self.boot_preview.pack(side="left", padx=(0, 8))
        self.boot_run = ctk.CTkButton(
            btns, text="Apply", width=120, height=36, corner_radius=8,
            fg_color=ACCENT, hover_color=ACCENT_DIM,
            font=ctk.CTkFont(family=F_SEMI, size=12),
            command=lambda: self.run_boot(False))
        self.boot_run.pack(side="left", padx=(0, 8))
        self.boot_undo = ctk.CTkButton(
            btns, text="Undo", width=110, height=36, corner_radius=8,
            fg_color="#232327", hover_color="#2d2d33", text_color=TEXT,
            font=ctk.CTkFont(family=F_REG, size=12),
            command=lambda: self.run_boot(True))
        self.boot_undo.pack(side="left")

        self.boot_raw_btn = ctk.CTkButton(
            btns, text="Show raw output", width=140, height=36,
            corner_radius=8, fg_color="transparent", hover_color="#1c1c20",
            text_color=MUTED, font=ctk.CTkFont(family=F_REG, size=11),
            command=self.toggle_raw)
        self.boot_raw_btn.pack(side="right")

        # ---------- live status panel ----------
        self.boot_status = ctk.CTkFrame(f, fg_color=CARD, corner_radius=12,
                                        border_width=1, border_color=BORDER)

        self.step_row = ctk.CTkFrame(self.boot_status, fg_color="transparent")
        self.step_row.pack(pady=(22, 4))
        self.step_dots = []
        for i in range(7):
            d = ctk.CTkLabel(self.step_row, text="●", text_color="#2e2e34",
                             font=ctk.CTkFont(family=F_SYM, size=13))
            d.pack(side="left", padx=7)
            self.step_dots.append(d)

        self.boot_stepname = ctk.CTkLabel(
            self.boot_status, text="", text_color=TEXT,
            font=ctk.CTkFont(family=F_SEMI, size=17))
        self.boot_stepname.pack(pady=(6, 12))

        self.boot_activity = ctk.CTkLabel(
            self.boot_status, text="// waiting…", text_color=MUTED,
            fg_color="#101012", corner_radius=8, height=38, anchor="w",
            font=ctk.CTkFont(family="Consolas", size=12))
        self.boot_activity.pack(fill="x", padx=26, pady=(0, 14))

        self.feed = ctk.CTkFrame(self.boot_status, fg_color="transparent")
        self.feed.pack(fill="x", padx=26, pady=(0, 22))
        self.feed_rows = []
        for i in range(4):
            row = ctk.CTkLabel(
                self.feed, text="", text_color=FAINT, anchor="w",
                font=ctk.CTkFont(family=F_REG, size=12))
            row.pack(fill="x", pady=2)
            self.feed_rows.append(row)

        # ---------- results ----------
        self.boot_results = ctk.CTkScrollableFrame(
            f, fg_color="transparent", scrollbar_button_color="#2a2a30")

        # ---------- raw log ----------
        self.boot_log = ctk.CTkTextbox(
            f, fg_color="#0e0e10", text_color="#c8c8d0", corner_radius=10,
            border_width=1, border_color=BORDER, wrap="word",
            font=ctk.CTkFont(family="Consolas", size=11))
        self.boot_log.insert("end", "Ready.\n")
        self.boot_log.configure(state="disabled")
        self.raw_shown = False

        self.boot_idle = ctk.CTkLabel(
            f,
            text="Press Preview Changes to see exactly what would change, "
                 "without touching anything.",
            text_color=FAINT, font=ctk.CTkFont(family=F_REG, size=12))
        self.boot_idle.pack(pady=40)
        return f

    def toggle_raw(self):
        self.raw_shown = not self.raw_shown
        if self.raw_shown:
            self.boot_results.pack_forget()
            self.boot_idle.pack_forget()
            self.boot_log.pack(fill="both", expand=True)
            self.boot_raw_btn.configure(text="Hide raw output")
        else:
            self.boot_log.pack_forget()
            self.boot_raw_btn.configure(text="Show raw output")
            self.boot_results.pack(fill="both", expand=True)


    def _build_restore_page(self):
        f = ctk.CTkFrame(self.body, fg_color="transparent")
        card = ctk.CTkFrame(f, fg_color=CARD, corner_radius=10,
                            border_width=1, border_color=BORDER)
        card.pack(fill="x")
        ctk.CTkLabel(
            card,
            text="Create a Windows restore point before applying tweaks. "
                 "If anything misbehaves you can roll the whole system back "
                 "from Windows Recovery.",
            text_color=MUTED, justify="left", anchor="w", wraplength=700,
            font=ctk.CTkFont(family=F_REG, size=12)).pack(
            padx=18, pady=(16, 12), anchor="w")
        self.restore_btn = ctk.CTkButton(
            card, text="Create Restore Point", width=180, height=36,
            corner_radius=8, fg_color=ACCENT, hover_color=ACCENT_DIM,
            font=ctk.CTkFont(family=F_SEMI, size=12),
            command=self.make_restore_point)
        self.restore_btn.pack(padx=18, pady=(0, 18), anchor="w")
        self.restore_status = ctk.CTkLabel(
            f, text="", text_color=MUTED,
            font=ctk.CTkFont(family=F_REG, size=12))
        self.restore_status.pack(anchor="w", pady=(10, 0))
        return f

    # -------------------------------------------------------------- pages
    def show_page(self, page):
        self.page = page
        self.sidebar.set_active(page)

        self._all_pages = (self.grid_page, self.boot_page, self.restore_page,
                           self.net_page, self.bios_page, self.sys_page,
                           self.clean_page, self.res_page, self.home_page,
                           self.drv_page)
        for w in self._all_pages:
            managed = getattr(w, "_parent_frame", w)
            if not managed.winfo_manager():
                w.grid(row=0, column=0, sticky="nsew")

        is_tweaks = page in CATEGORY_ORDER and page != "Networking"
        for b in (self.btn_apply, self.btn_revert, self.btn_scan):
            if is_tweaks:
                b.pack(side="left", padx=(0, 8))
            else:
                b.pack_forget()
        self.count_lbl.configure(text="" if not is_tweaks else self.count_lbl.cget("text"))

        if page == "Home":
            self.crumb.configure(text="General  ›  Home")
            self.title_lbl.configure(text="Overview")
            self.sub_lbl.configure(
                text="How tuned this machine is right now.")
            raise_page(self.home_page)
            self.refresh_home()
            if not self._home_loaded:
                self._home_loaded = True
                self.load_home_specs()
            return
        if page == "Drivers":
            self.crumb.configure(text="System  ›  Drivers")
            self.title_lbl.configure(text="Graphics Drivers")
            self.sub_lbl.configure(
                text="Check what you have against the latest release.")
            raise_page(self.drv_page)
            # Always re-query on open - a cached answer from an hour ago is
            # worse than useless for "is my driver current?".
            self.check_drivers()
            return
        if page == "Networking":
            self.count_lbl.configure(text="")
            self.crumb.configure(text="Tweaks  ›  Networking")
            self.title_lbl.configure(text="Networking")
            self.sub_lbl.configure(
                text="Test your connection, then tune it.")
            raise_page(self.net_page)
            self.refresh_counts()
            return
        if is_tweaks:
            self.crumb.configure(text="Tweaks  ›  " + page)
            self.title_lbl.configure(text=page + " Tweaks")
            self.sub_lbl.configure(
                text="Toggle a tweak to apply it. Toggle off to revert.")
            self._layout_cards(page)
            raise_page(self.grid_page)
        elif page == "System Info":
            self.crumb.configure(text="System  ›  System Info")
            self.title_lbl.configure(text="System Information")
            self.sub_lbl.configure(text="What is actually inside this machine.")
            raise_page(self.sys_page)
            if not self._sys_loaded:
                self._sys_loaded = True
                self.load_sys(self.sys_section)
        elif page == "Disk Cleanup":
            self.crumb.configure(text="System  ›  Disk Cleanup")
            self.title_lbl.configure(text="Disk Cleanup")
            self.sub_lbl.configure(
                text="Find and remove junk that is safe to delete.")
            raise_page(self.clean_page)
            if not self._clean_loaded:
                self._clean_loaded = True
                self.scan_cleanup()
        elif page == "Resources":
            self.crumb.configure(text="System  ›  Resources")
            self.title_lbl.configure(text="Resources")
            self.sub_lbl.configure(text="Repair tools for a misbehaving Windows.")
            raise_page(self.res_page)
        elif page == "BIOS Info":
            self.crumb.configure(text="Tools  ›  BIOS Info")
            self.title_lbl.configure(text="Firmware & BIOS")
            self.sub_lbl.configure(
                text="What Windows can see about your firmware.")
            raise_page(self.bios_page)
            if not self._bios_loaded:
                self._bios_loaded = True
                self.load_bios()
        elif page == "Boot Optimizer":
            self.crumb.configure(text="Tools  ›  Boot Optimizer")
            self.title_lbl.configure(text="Boot Optimizer")
            self.sub_lbl.configure(
                text="Automatic startup and shutdown tuning for this machine.")
            raise_page(self.boot_page)
        else:
            self.crumb.configure(text="Tools  ›  System Restore")
            self.title_lbl.configure(text="System Restore")
            self.sub_lbl.configure(text="Make a safety net before you tweak.")
            raise_page(self.restore_page)
        self.refresh_counts()

    def _layout_cards(self, cat):
        if cat == "Networking":
            return
        for key, card in self.cards.items():
            if card.tweak.category != "Networking":
                card.grid_forget()
        i = 0
        for tw in self.tweaks:
            if tw.category != cat:
                continue
            r, c = divmod(i, 3)
            self.cards[tw.key].grid(row=r, column=c, padx=8, pady=8,
                                    sticky="nsew")
            i += 1

    # ------------------------------------------------------------ scanning
    def rescan(self):
        self.btn_scan.configure(text="Scanning…", state="disabled")

        def work():
            states = {}
            lines = []
            for tw in self.tweaks:
                val = tw.check()
                states[tw.key] = val
                lines.append(f"{tw.key:<18} {tw.category:<14} "
                             f"{'APPLIED' if val else 'not applied'}")
                if tw.error:
                    lines.append("    ERROR: " +
                                 tw.error.replace("\n", "\n    "))
            self._write_scan_log(lines)
            self.after(0, lambda: self._apply_scan(states))

        threading.Thread(target=work, daemon=True).start()

    def _write_scan_log(self, lines):
        """Drop a scan log beside the exe; falls back to LOCALAPPDATA."""
        header = ["Tech Lounge Tweaks - scan log",
                  "elevated=" + str(is_admin()), ""]
        body = "\n".join(header + lines) + "\n"
        for folder in (os.path.dirname(os.path.abspath(sys.executable)),
                       os.path.join(os.environ.get("LOCALAPPDATA",
                                                   tempfile.gettempdir()),
                                    "TechLoungeTweaks")):
            try:
                os.makedirs(folder, exist_ok=True)
                with open(os.path.join(folder, "TL-scan.log"), "w",
                          encoding="utf-8") as fh:
                    fh.write(body)
                return
            except Exception:
                continue

    def _apply_scan(self, states):
        for key, applied in states.items():
            # already on before we touched anything -> lock it
            self.cards[key].set_state(applied, locked=applied)
        self.btn_scan.configure(text="Rescan", state="normal")
        self.refresh_counts()

    def refresh_counts(self):
        total_on = 0
        for cat in CATEGORY_ORDER:
            items = [t for t in self.tweaks if t.category == cat]
            on = sum(1 for t in items
                     if self.cards[t.key].applied or self.cards[t.key].locked)
            total_on += on
            self.sidebar.set_chip(cat, f"{on}/{len(items)}",
                                  OK_FG if on else FAINT)
            if cat == self.page and self.page != "Networking":
                self.count_lbl.configure(text=f"{on}/{len(items)} applied")
        word = "tweak" if total_on == 1 else "tweaks"
        self.refresh_home()
        self.sidebar.set_footer(
            f"{total_on} {word} applied",
            "Administrator" if is_admin() else "Not elevated", is_admin())

    # --------------------------------------------------------------- bulk
    def bulk(self, apply_all):
        targets = [t for t in self.tweaks
                   if t.category == self.page and not self.cards[t.key].locked]
        if not targets:
            return
        self.btn_apply.configure(state="disabled")
        self.btn_revert.configure(state="disabled")

        def work():
            for t in targets:
                try:
                    if apply_all:
                        t.apply()
                    else:
                        t.revert()
                except Exception:
                    pass
                self.after(0, lambda k=t.key: self.cards[k].set_state(
                    apply_all, False))
            self.after(0, self._bulk_done)

        threading.Thread(target=work, daemon=True).start()

    def _bulk_done(self):
        self.btn_apply.configure(state="normal")
        self.btn_revert.configure(state="normal")
        self.refresh_counts()


    # ------------------------------------------------------ bufferbloat
    # ------------------------------------------------ networking page
    def _card(self, parent, title, icon):
        card = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=12,
                            border_width=1, border_color=BORDER)
        head = ctk.CTkFrame(card, fg_color="transparent")
        head.pack(fill="x", padx=16, pady=(14, 8))
        ctk.CTkLabel(head, text=icon, width=36, height=36, corner_radius=9,
                     fg_color="#232327", text_color=TEXT,
                     font=ctk.CTkFont(family=F_SYM, size=15)).pack(side="left")
        ctk.CTkLabel(head, text=title, text_color=TEXT,
                     font=ctk.CTkFont(family=F_SEMI, size=15)).pack(
            side="left", padx=(12, 0))
        return card

    def _build_net_page(self):
        page = ctk.CTkScrollableFrame(
            self.body, fg_color="transparent",
            scrollbar_button_color="#2a2a30")

        # ---------- action bar ----------
        bar = ctk.CTkFrame(page, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 12))
        self.net_run = ctk.CTkButton(
            bar, text="Run Test", width=130, height=36, corner_radius=8,
            fg_color=ACCENT, hover_color=ACCENT_DIM,
            font=ctk.CTkFont(family=F_SEMI, size=12), command=self.run_nettest)
        self.net_run.pack(side="left")
        self.net_opt = ctk.CTkButton(
            bar, text="Optimize Network", width=170, height=36,
            corner_radius=8, fg_color="#232327", hover_color="#2d2d33",
            text_color=TEXT, font=ctk.CTkFont(family=F_SEMI, size=12),
            command=lambda: self.net_bulk(True))
        self.net_opt.pack(side="left", padx=8)
        self.net_reset = ctk.CTkButton(
            bar, text="Revert Network", width=150, height=36, corner_radius=8,
            fg_color="transparent", hover_color="#1c1c20", text_color=MUTED,
            font=ctk.CTkFont(family=F_REG, size=12),
            command=lambda: self.net_bulk(False))
        self.net_reset.pack(side="left")
        self.net_status = ctk.CTkLabel(
            bar, text="Saturates the line for about 30 seconds.",
            text_color=FAINT, font=ctk.CTkFont(family=F_REG, size=11))
        self.net_status.pack(side="right")

        self.net_bar = ctk.CTkProgressBar(page, height=4, corner_radius=2,
                                          progress_color=ACCENT,
                                          fg_color="#1c1c20")
        self.net_bar.set(0)
        self.net_bar.pack(fill="x", pady=(0, 14))

        # ---------- top row ----------
        row = ctk.CTkFrame(page, fg_color="transparent")
        row.pack(fill="x")
        for c in range(3):
            row.grid_columnconfigure(c, weight=1, uniform="n")

        g = self._card(row, "Bufferbloat Grade", "◆")
        g.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        tooltip.attach(
            g, "Bufferbloat - the lag spike when your line gets busy",
            "Your router holds packets in a queue when the connection is "
            "full. Ping looks fine idle, then jumps the moment someone "
            "streams or a game updates. This grade is how much your ping "
            "rose while the line was saturated. Higher grade is better.",
            "A or better means you will barely notice it. C or worse is "
            "worth fixing with Smart Queue / SQM on your router - no "
            "Windows tweak can fix bufferbloat.",
            font_semi=F_SEMI, font_reg=F_REG)
        # Frames, not a Canvas: a tk.Canvas inside a CTkScrollableFrame
        # leaves trails behind when the page scrolls.
        self.grade_img = ctk.CTkLabel(g, text="", fg_color=CARD)
        self.grade_img.pack(fill="x", padx=16, pady=(4, 10))
        self._grade_photo = None
        self._grade_split = 0.5
        grow = ctk.CTkFrame(g, fg_color="transparent")
        grow.pack(fill="x", padx=16)
        self.net_grade = ctk.CTkLabel(
            grow, text="—", text_color=MUTED, width=54, anchor="w",
            font=ctk.CTkFont(family=F_SEMI, size=40))
        self.net_grade.pack(side="left")
        leg = ctk.CTkFrame(grow, fg_color="transparent")
        leg.pack(side="left", padx=(6, 0))
        for txt, col in (("Unloaded", "#e0338f"), ("Under load", "#2f9db5")):
            r = ctk.CTkFrame(leg, fg_color="transparent")
            r.pack(anchor="w", pady=2)
            ctk.CTkLabel(r, text="", width=11, height=11, corner_radius=3,
                         fg_color=col).pack(side="left")
            ctk.CTkLabel(r, text=" " + txt, text_color=MUTED,
                         font=ctk.CTkFont(family=F_REG, size=11)).pack(
                side="left")
        vrow = ctk.CTkFrame(g, fg_color="transparent")
        vrow.pack(fill="x", padx=16, pady=(10, 16))
        self.net_dot = ctk.CTkLabel(vrow, text="●", text_color=FAINT, width=12,
                                    font=ctk.CTkFont(family=F_SYM, size=10))
        self.net_dot.pack(side="left", anchor="n", pady=2)
        self.net_verdict = ctk.CTkLabel(
            vrow, text="Run a test to measure your connection.",
            text_color=MUTED, anchor="w", justify="left", wraplength=225,
            font=ctk.CTkFont(family=F_REG, size=12))
        self.net_verdict.pack(side="left", padx=(4, 0))

        sp = self._card(row, "Internet Speed", "⊕")
        sp.grid(row=0, column=1, sticky="nsew", padx=8)
        tooltip.attach(
            sp, "Download and upload speed",
            "How much data your line can move per second, measured over "
            "several parallel connections once the connection has settled. "
            "Higher is better. Download matters for game installs and "
            "streaming; upload matters for streaming out, calls and "
            "uploading clips.",
            "Gaming needs surprisingly little - 25 Mbps down is plenty. "
            "Speed is not what causes lag; latency and jitter are.",
            font_semi=F_SEMI, font_reg=F_REG)
        self.net_down = self._speed_row(sp, "Download", "#e0335f")
        self.net_up = self._speed_row(sp, "Upload", "#7a6fd0")
        ctk.CTkFrame(sp, fg_color="transparent", height=8).pack()

        la = self._card(row, "Latency", "⌒")
        la.grid(row=0, column=2, sticky="nsew", padx=(8, 0))
        lr = ctk.CTkFrame(la, fg_color="transparent")
        lr.pack(fill="x", padx=16, pady=(0, 16))
        for c in range(3):
            lr.grid_columnconfigure(c, weight=1, uniform="lat")
        self.lat_cells = []
        LAT_HELP = {
            "Unloaded": ("Ping when nothing else is using the line",
                         "How long a packet takes to reach the internet and "
                         "come back while the connection is quiet. Lower is "
                         "better.",
                         "Under 20 ms is great, under 40 ms is fine."),
            "Download": ("Ping while downloading flat out",
                         "The same round trip, measured while the connection "
                         "is saturated. If this is far higher than your idle "
                         "ping, that is bufferbloat - your router is queueing "
                         "packets. Lower is better.",
                         "Ideally within 30 ms of your idle ping."),
            "Upload": ("Ping while uploading flat out",
                       "Same idea in the other direction. Upload is usually "
                       "the worse of the two, because home connections have "
                       "far less upstream bandwidth. Lower is better.",
                       "Ideally within 30 ms of your idle ping."),
        }
        for i, (name, sub, col) in enumerate(
                (("Unloaded", "", "#d99a2b"),
                 ("Download", "Active", "#2f9db5"),
                 ("Upload", "Active", "#7a6fd0"))):
            cell = ctk.CTkFrame(lr, fg_color="transparent")
            cell.grid(row=0, column=i, sticky="nsew")
            top = ctk.CTkFrame(cell, fg_color="transparent")
            top.pack(anchor="w")
            ctk.CTkLabel(top, text="", width=10, height=10, corner_radius=2,
                         fg_color=col).pack(side="left")
            ctk.CTkLabel(top, text=" " + name, text_color=MUTED,
                         font=ctk.CTkFont(family=F_REG, size=10)).pack(
                side="left")
            if sub:
                ctk.CTkLabel(cell, text=sub, text_color=FAINT, anchor="w",
                             font=ctk.CTkFont(family=F_REG, size=9)).pack(
                    anchor="w", padx=12)
            val = ctk.CTkLabel(cell, text="—", text_color=TEXT, anchor="w",
                               font=ctk.CTkFont(family=F_SEMI, size=22))
            val.pack(anchor="w", pady=(4, 0))
            self.lat_cells.append(val)
            t, b, g = LAT_HELP[name]
            tooltip.attach_all([cell, val], t, b, g,
                               font_semi=F_SEMI, font_reg=F_REG)

        jrow = ctk.CTkFrame(la, fg_color="transparent")
        jrow.pack(fill="x", padx=16, pady=(2, 16))
        ctk.CTkLabel(jrow, text="Jitter", text_color=FAINT, anchor="w",
                     font=ctk.CTkFont(family=F_REG, size=10)).pack(side="left")
        self.jitter_lbl = ctk.CTkLabel(
            jrow, text="—", text_color=TEXT, anchor="e",
            font=ctk.CTkFont(family=F_SEMI, size=14))
        self.jitter_lbl.pack(side="right")
        tooltip.attach_all(
            [jrow, self.jitter_lbl], "Jitter - how steady your ping is",
            "Ping tells you how far away the server feels. Jitter tells you "
            "how much that distance wobbles from packet to packet. High "
            "jitter is what makes a game feel rubber-bandy even when your "
            "ping looks fine. Lower is better.",
            "Under 5 ms is excellent. Over 20 ms and you will feel it. "
            "Two numbers means idle / under load - the second is always "
            "higher because saturating the line adds queueing noise.",
            font_semi=F_SEMI, font_reg=F_REG)

        # ---------- second row ----------
        row2 = ctk.CTkFrame(page, fg_color="transparent")
        row2.pack(fill="x", pady=(14, 0))
        row2.grid_columnconfigure(0, weight=4, uniform="n2")
        row2.grid_columnconfigure(1, weight=5, uniform="n2")

        conn = self._card(row2, "Your Connection", "▤")
        conn.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        tooltip.attach(
            conn, "What your connection can actually handle",
            "Each row checks your measured speed and your ping under load "
            "against what that activity really needs. A tick means you are "
            "comfortably above the requirement; a cross means something "
            "would stutter. A question mark means the test could not "
            "measure that direction.",
            "Low latency gaming is the strictest row - it wants your ping "
            "under load to stay below about 75 ms.",
            font_semi=F_SEMI, font_reg=F_REG)
        hdr = ctk.CTkFrame(conn, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(0, 4))
        hdr.grid_columnconfigure(0, weight=3, uniform="c")
        hdr.grid_columnconfigure(1, weight=2, uniform="c")
        ctk.CTkLabel(hdr, text="", ).grid(row=0, column=0)
        ctk.CTkLabel(hdr, text="CURRENTLY", text_color=FAINT,
                     font=ctk.CTkFont(family=F_SEMI, size=9)).grid(
            row=0, column=1)
        self.conn_rows = []
        for name, _m, _b in nettest.REQUIREMENTS:
            r = ctk.CTkFrame(conn, fg_color="transparent")
            r.pack(fill="x", padx=16, pady=2)
            r.grid_columnconfigure(0, weight=3, uniform="c")
            r.grid_columnconfigure(1, weight=2, uniform="c")
            ctk.CTkLabel(r, text=name, text_color=TEXT, anchor="w",
                         font=ctk.CTkFont(family=F_REG, size=12)).grid(
                row=0, column=0, sticky="w")
            cell = ctk.CTkLabel(r, text="—", text_color=FAINT, height=24,
                                corner_radius=6, fg_color="#1b1b1f",
                                font=ctk.CTkFont(family=F_SEMI, size=12))
            cell.grid(row=0, column=1, sticky="ew", padx=(10, 0))
            self.conn_rows.append(cell)
        ctk.CTkFrame(conn, fg_color="transparent", height=10).pack()

        dist = self._card(row2, "Latency Distribution", "▦")
        dist.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        tooltip.attach(
            dist, "How spread out your ping was",
            "The coloured bar covers the middle half of all the pings taken "
            "in that phase, and the white line is the middle value. A short "
            "bar means a steady connection. A long bar means your ping was "
            "jumping around, which feels worse than a high but stable ping.",
            "You want the download and upload bars to sit close to the "
            "unloaded one, and to be short.",
            font_semi=F_SEMI, font_reg=F_REG)
        self.dist_rows = []
        for name, col in (("Unloaded", "#d99a2b"), ("Download", "#2f9db5"),
                          ("Upload", "#7a6fd0")):
            r = ctk.CTkFrame(dist, fg_color="transparent")
            r.pack(fill="x", padx=16, pady=5)
            ctk.CTkLabel(r, text=name, text_color=MUTED, width=76, anchor="w",
                         font=ctk.CTkFont(family=F_REG, size=11)).pack(
                side="left")
            cv = ctk.CTkFrame(r, height=22, corner_radius=4,
                              fg_color="#1b1b1f")
            cv.pack(side="left", fill="x", expand=True, padx=6)
            cv.pack_propagate(False)
            box = ctk.CTkFrame(cv, corner_radius=3, fg_color=col)
            box.place(relx=0, rely=0.22, relwidth=0.0, relheight=0.56)
            tick = ctk.CTkFrame(cv, corner_radius=0, fg_color="#ffffff",
                                width=2)
            tick.place(relx=0, rely=0.1, relwidth=0.006, relheight=0.8)
            cv.box, cv.tick = box, tick
            val = ctk.CTkLabel(r, text="—", text_color=TEXT, width=58,
                               anchor="e",
                               font=ctk.CTkFont(family=F_SEMI, size=12))
            val.pack(side="right")
            self.dist_rows.append((cv, val, col))
        ctk.CTkFrame(dist, fg_color="transparent", height=8).pack()

        # ---------- tweaks in the same page ----------
        ctk.CTkLabel(page, text="NETWORK TWEAKS", text_color=FAINT,
                     anchor="w",
                     font=ctk.CTkFont(family=F_SEMI, size=10)).pack(
            fill="x", pady=(22, 6))
        self.net_cards_holder = ctk.CTkFrame(page, fg_color="transparent")
        self.net_cards_holder.pack(fill="x")
        for c in range(3):
            self.net_cards_holder.grid_columnconfigure(c, weight=1,
                                                       uniform="ncards")
        return page

    def _speed_row(self, parent, label, colour):
        r = ctk.CTkFrame(parent, fg_color="transparent")
        r.pack(fill="x", padx=16, pady=(2, 6))
        top = ctk.CTkFrame(r, fg_color="transparent")
        top.pack(fill="x")
        ctk.CTkLabel(top, text="", width=9, height=9, corner_radius=5,
                     fg_color=colour).pack(side="left")
        ctk.CTkLabel(top, text=" " + label, text_color=MUTED,
                     font=ctk.CTkFont(family=F_REG, size=11)).pack(side="left")
        val = ctk.CTkLabel(top, text="—", text_color=TEXT,
                           font=ctk.CTkFont(family=F_SEMI, size=17))
        val.pack(side="right")
        line = ctk.CTkProgressBar(r, height=4, corner_radius=2,
                                  progress_color=colour, fg_color="#1c1c20")
        line.set(0)
        line.pack(fill="x", pady=(6, 0))
        return (val, line)

    # ---------- drawing (frames only - canvases ghost when scrolled) ----
    def _draw_grade_bar(self, idle_ms, loaded_ms):
        split = 0.5
        if idle_ms:
            loaded_ms = loaded_ms or idle_ms
            total = max(loaded_ms, idle_ms * 1.2, 1)
            split = max(0.08, min(0.92, idle_ms / total))
        self._grade_split = split
        w = max(200, self.grade_img.winfo_width() or 240)
        try:
            img = gfx.split_bar(w, 26, split, "#c02c7d", "#256f80",
                                bg=CARD, marker=split)
            self._grade_photo = ImageTk.PhotoImage(img)
            self.grade_img.configure(image=self._grade_photo, text="")
        except Exception:
            pass

    def _draw_dist(self, idx, st, scale_max):
        cv, _val, _col = self.dist_rows[idx]
        if not st or not scale_max:
            return

        def frac(v):
            return max(0.0, min(1.0, v / scale_max))

        lo, hi = frac(st["p25"]), frac(st["p75"])
        cv.box.place_configure(relx=lo, relwidth=max(0.02, hi - lo))
        cv.tick.place_configure(relx=max(0.0, min(0.99, frac(st["med"]))))

    def run_nettest(self):
        self.net_run.configure(state="disabled", text="Running…")
        self.net_bar.set(0)
        self.net_grade.configure(text="—", text_color=MUTED)
        self.net_dot.configure(text_color=FAINT)
        self.net_verdict.configure(text="Measuring…")
        for cell in self.lat_cells:
            cell.configure(text="—")
        for v, l in (self.net_down, self.net_up):
            v.configure(text="—")
            l.set(0)
        for cell in self.conn_rows:
            cell.configure(text="—", text_color=FAINT, fg_color="#1b1b1f")

        def prog(label, frac):
            self.after(0, lambda: (self.net_status.configure(
                text=label + "…", text_color=MUTED),
                self.net_bar.set(max(0.0, min(1.0, frac)))))

        def partial(stage, res):
            self.after(0, lambda: self._nettest_partial(stage, res))

        def work():
            try:
                res = nettest.run_test(progress=prog, on_partial=partial)
            except Exception as e:
                res = {"error": str(e)}
            self.after(0, lambda: self._nettest_done(res))

        threading.Thread(target=work, daemon=True).start()

    @staticmethod
    def _fmt_speed(mbps):
        if not mbps:
            return "—"
        if mbps >= 1000:
            return f"{mbps / 1000:.2f} Gbps"
        return f"{mbps:.0f} Mbps"

    def _nettest_partial(self, stage, res):
        """Fill each panel the moment its stage finishes."""
        def ms(v):
            return f"{v:.0f} ms" if v else "—"

        if stage == "idle" and res.get("idle"):
            self.lat_cells[0].configure(text=ms(res["idle"]["med"]))
            self._set_dist(0, res["idle"], res)
        elif stage == "download":
            val, line = self.net_down
            val.configure(text=self._fmt_speed(res.get("download_mbps")))
            line.set(max(0.02, min(1.0, (res.get("download_mbps") or 0)
                                   / 2500.0)))
            if res.get("down"):
                self.lat_cells[1].configure(text=ms(res["down"]["med"]))
                self._set_dist(1, res["down"], res)
        elif stage == "upload":
            val, line = self.net_up
            val.configure(text=self._fmt_speed(res.get("upload_mbps")))
            line.set(max(0.02, min(1.0, (res.get("upload_mbps") or 0)
                                   / 1000.0)))
            if res.get("up"):
                self.lat_cells[2].configure(text=ms(res["up"]["med"]))
                self._set_dist(2, res["up"], res)

    def _set_dist(self, idx, st, res):
        all_st = [res.get("idle"), res.get("down"), res.get("up")]
        scale = max((x["p95"] for x in all_st if x), default=0) * 1.15
        for i, x in enumerate(all_st):
            if x:
                self._draw_dist(i, x, scale)

    def _nettest_done(self, res):
        self.net_run.configure(state="normal", text="Run Test")

        if "error" in res:
            self.net_bar.set(0)
            self.net_status.configure(text=res["error"], text_color=WARN_FG)
            return

        self.net_bar.set(1)
        inc = res.get("increase_ms")
        self.net_status.configure(
            text=f"Latency rose {inc:.0f} ms under load."
            if inc is not None else "Done.", text_color=FAINT)

        def ms(v):
            return f"{v:.0f} ms" if v else "—"

        val, line = self.net_down
        val.configure(text=self._fmt_speed(res.get("download_mbps")))
        line.set(max(0.02, min(1.0, (res.get("download_mbps") or 0) / 2500.0)))
        val, line = self.net_up
        val.configure(text=self._fmt_speed(res.get("upload_mbps")))
        line.set(max(0.02, min(1.0, (res.get("upload_mbps") or 0) / 1000.0)))

        all_st = [res.get("idle"), res.get("down"), res.get("up")]
        for cell, st in zip(self.lat_cells, all_st):
            cell.configure(text=(ms(st["med"])) if st else "—")
        # Headline the idle figure - that is what ping-test sites report.
        # The loaded figure is shown after it for context.
        j = res.get("idle_jitter")
        loaded_j = res.get("jitter_ms")
        txt = ms(j)
        if loaded_j and j and loaded_j > j * 1.5:
            txt = f"{j:.0f} / {loaded_j:.0f} ms"
        self.jitter_lbl.configure(
            text=txt,
            text_color=(OK_FG if j is not None and j < 5 else
                        WARN_FG if j is not None and j < 20 else
                        "#ef6b76" if j is not None else TEXT))
        scale = max((x["p95"] for x in all_st if x), default=0) * 1.15
        for i, (cv, val2, _c) in enumerate(self.dist_rows):
            st = all_st[i]
            if st:
                self._draw_dist(i, st, scale)
                val2.configure(text=ms(st["med"]))

        for cell, (name, ok) in zip(self.conn_rows, res["activities"]):
            if ok is None:
                cell.configure(text="?", text_color=FAINT, fg_color="#1b1b1f")
            elif ok:
                cell.configure(text="✓", text_color=OK_FG, fg_color=OK_BG)
            else:
                cell.configure(text="✕", text_color="#ef6b76",
                               fg_color="#2a1417")

        # grade last, once everything else is on screen
        colour = {"A+": OK_FG, "A": OK_FG, "B": OK_FG,
                  "C": WARN_FG, "D": WARN_FG}.get(res["grade"], "#ef6b76")
        self.net_grade.configure(text=res["grade"], text_color=colour)
        self.net_dot.configure(text_color=colour)
        self.net_verdict.configure(
            text=res["verdict"] + f"\n(base ping {res['idle_ms']:.0f} ms)")
        self._draw_grade_bar(res.get("idle_ms"), res.get("loaded_ms"))

    def net_bulk(self, apply_all):
        targets = [t for t in self.tweaks
                   if t.category == "Networking"
                   and not self.cards[t.key].locked]
        if not targets:
            return
        self.net_opt.configure(state="disabled", text="Working…")
        self.net_reset.configure(state="disabled")

        def work():
            for t in targets:
                try:
                    t.apply() if apply_all else t.revert()
                except Exception:
                    pass
                self.after(0, lambda k=t.key: self.cards[k].set_state(
                    apply_all, False))
            self.after(0, self._net_bulk_done)

        threading.Thread(target=work, daemon=True).start()

    def _net_bulk_done(self):
        self.net_opt.configure(state="normal", text="Optimize Network")
        self.net_reset.configure(state="normal")
        self.refresh_counts()


    # ------------------------------------------------------------ BIOS
    def _build_bios_page(self):
        f = ctk.CTkFrame(self.body, fg_color="transparent")

        self.bios_support = ctk.CTkLabel(
            f, text="  Checking firmware…  ", corner_radius=8, height=30,
            fg_color="#1c1c20", text_color=MUTED, anchor="w",
            font=ctk.CTkFont(family=F_SEMI, size=11))
        self.bios_support.pack(anchor="w", pady=(0, 12))

        self.bios_grid = ctk.CTkScrollableFrame(
            f, fg_color="transparent", scrollbar_button_color="#2a2a30")
        self.bios_grid.pack(fill="both", expand=True)
        self.bios_grid.grid_columnconfigure(0, weight=1, uniform="b")
        self.bios_grid.grid_columnconfigure(1, weight=1, uniform="b")
        return f

    def load_bios(self):
        def work():
            try:
                rows = biosinfo.collect()
                sup = biosinfo.vendor_support()
            except Exception as e:
                rows, sup = [("Error", str(e))], (False, None, None)
            self.after(0, lambda: self._bios_done(rows, sup))

        threading.Thread(target=work, daemon=True).start()

    def _bios_done(self, rows, sup):
        supported, label, _ns = sup
        if supported:
            self.bios_support.configure(
                text=f"  Vendor BIOS interface available: {label}  ",
                fg_color=OK_BG, text_color=OK_FG)
        else:
            self.bios_support.configure(
                text="  Read-only - this board has no supported Windows "
                     "interface for changing BIOS settings  ",
                fg_color=LOCK_BG, text_color=LOCK_FG)

        for w in self.bios_grid.winfo_children():
            w.destroy()

        for i, (k, v) in enumerate(rows):
            r, c = divmod(i, 2)
            card = ctk.CTkFrame(self.bios_grid, fg_color=CARD,
                                corner_radius=10, border_width=1,
                                border_color=BORDER)
            card.grid(row=r, column=c, sticky="nsew", padx=8, pady=6)
            ctk.CTkLabel(card, text=k, text_color=MUTED, anchor="w",
                         font=ctk.CTkFont(family=F_REG, size=11)).pack(
                fill="x", padx=16, pady=(12, 0))
            ctk.CTkLabel(card, text=v or "Unknown", text_color=TEXT,
                         anchor="w", justify="left", wraplength=360,
                         font=ctk.CTkFont(family=F_SEMI, size=13)).pack(
                fill="x", padx=16, pady=(2, 13))

        note = ctk.CTkFrame(self.bios_grid, fg_color=CARD, corner_radius=10,
                            border_width=1, border_color=BORDER)
        note.grid(row=99, column=0, columnspan=2, sticky="ew", padx=8,
                  pady=(12, 6))
        ctk.CTkLabel(
            note,
            text="Why this page is read-only: Dell, HP and Lenovo publish "
                 "supported WMI interfaces for changing BIOS settings from "
                 "Windows, and this app will use them when it finds one. "
                 "Consumer boards (ASUS, MSI, Gigabyte) publish nothing "
                 "equivalent - the only way in is writing firmware NVRAM "
                 "through an undocumented driver, and a bad write bricks the "
                 "board with no way back. Change those settings in the "
                 "firmware itself at POST.",
            text_color=MUTED, justify="left", anchor="w", wraplength=800,
            font=ctk.CTkFont(family=F_REG, size=12)).pack(
            padx=18, pady=16, anchor="w")

    # ------------------------------------------------------------- home
    def _build_home_page(self):
        f = ctk.CTkFrame(self.body, fg_color="transparent")

        top = ctk.CTkFrame(f, fg_color="transparent")
        top.pack(fill="x")
        top.grid_columnconfigure(0, weight=4, uniform="h")
        top.grid_columnconfigure(1, weight=6, uniform="h")

        # ---- score dial
        score = ctk.CTkFrame(top, fg_color=CARD, corner_radius=14,
                             border_width=1, border_color=BORDER)
        score.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ctk.CTkLabel(score, text="TWEAK SCORE", text_color=FAINT,
                     font=ctk.CTkFont(family=F_SEMI, size=10)).pack(
            anchor="w", padx=20, pady=(18, 0))
        self.score_img = ctk.CTkLabel(score, text="", fg_color=CARD)
        self.score_img.pack(padx=20, pady=(6, 0))
        self.score_num = ctk.CTkLabel(score, text="", text_color=TEXT,
                                      fg_color=CARD)
        self._score_photo = None
        self.score_note = ctk.CTkLabel(
            score, text="", text_color=MUTED, anchor="w", justify="left",
            wraplength=280, font=ctk.CTkFont(family=F_REG, size=12))
        self.score_note.pack(anchor="w", padx=20, pady=(0, 18))
        tooltip.attach(
            score, "Tweak score",
            "Simply how many of the tweaks in this app are currently "
            "applied, out of the total available for your hardware. It is a "
            "progress bar, not a health rating - a low score does not mean "
            "anything is wrong with your PC.",
            "There is no need to chase 100. Some tweaks trade security or "
            "battery life for speed, and skipping those is a fair choice.",
            font_semi=F_SEMI, font_reg=F_REG)

        # ---- machine summary
        spec = ctk.CTkFrame(top, fg_color=CARD, corner_radius=14,
                            border_width=1, border_color=BORDER)
        spec.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        ctk.CTkLabel(spec, text="THIS MACHINE", text_color=FAINT,
                     font=ctk.CTkFont(family=F_SEMI, size=10)).pack(
            anchor="w", padx=20, pady=(18, 8))
        self.spec_rows = {}
        for key in ("CPU", "Graphics", "Memory", "Motherboard", "Windows",
                    "Storage"):
            row = ctk.CTkFrame(spec, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=3)
            ctk.CTkLabel(row, text=key, text_color=FAINT, width=104,
                         anchor="w",
                         font=ctk.CTkFont(family=F_REG, size=11)).pack(
                side="left")
            val = ctk.CTkLabel(row, text="Reading…", text_color=TEXT,
                               anchor="w", justify="left", wraplength=420,
                               font=ctk.CTkFont(family=F_SEMI, size=12))
            val.pack(side="left", fill="x", expand=True)
            self.spec_rows[key] = val
        ctk.CTkFrame(spec, fg_color="transparent", height=14).pack()

        # ---- per-category breakdown
        ctk.CTkLabel(f, text="BY CATEGORY", text_color=FAINT, anchor="w",
                     font=ctk.CTkFont(family=F_SEMI, size=10)).pack(
            fill="x", pady=(20, 6))
        grid = ctk.CTkFrame(f, fg_color="transparent")
        grid.pack(fill="x")
        for c in range(3):
            grid.grid_columnconfigure(c, weight=1, uniform="hc")
        self.home_cats = {}
        for i, cat in enumerate(CATEGORY_ORDER):
            r, c = divmod(i, 3)
            card = ctk.CTkFrame(grid, fg_color=CARD, corner_radius=10,
                                border_width=1, border_color=BORDER)
            card.grid(row=r, column=c, sticky="nsew", padx=6, pady=6)
            card.bind("<Button-1>", lambda e, k=cat: self.show_page(k))
            head = ctk.CTkFrame(card, fg_color="transparent")
            head.pack(fill="x", padx=14, pady=(12, 2))
            ctk.CTkLabel(head, text=CATEGORY_ICONS.get(cat, "⚙"),
                         text_color=MUTED,
                         font=ctk.CTkFont(family=F_SYM, size=12)).pack(
                side="left")
            ctk.CTkLabel(head, text="  " + cat, text_color=TEXT, anchor="w",
                         font=ctk.CTkFont(family=F_SEMI, size=12)).pack(
                side="left")
            count = ctk.CTkLabel(head, text="0/0", text_color=FAINT,
                                 font=ctk.CTkFont(family=F_SEMI, size=11))
            count.pack(side="right")
            bar = ctk.CTkProgressBar(card, height=5, corner_radius=3,
                                     progress_color=ACCENT,
                                     fg_color="#1c1c20")
            bar.set(0)
            bar.pack(fill="x", padx=14, pady=(6, 14))
            self.home_cats[cat] = (count, bar)

        # ---- quick actions
        ctk.CTkLabel(f, text="QUICK ACTIONS", text_color=FAINT, anchor="w",
                     font=ctk.CTkFont(family=F_SEMI, size=10)).pack(
            fill="x", pady=(20, 6))
        acts = ctk.CTkFrame(f, fg_color="transparent")
        acts.pack(fill="x", pady=(0, 10))
        for label, target in (("Create Restore Point", "System Restore"),
                              ("Run Boot Optimizer", "Boot Optimizer"),
                              ("Test Connection", "Networking"),
                              ("Clean Up Disk", "Disk Cleanup"),
                              ("Check Drivers", "Drivers")):
            ctk.CTkButton(
                acts, text=label, height=34, corner_radius=8,
                fg_color="#1c1c21", hover_color="#26262c", text_color=TEXT,
                font=ctk.CTkFont(family=F_REG, size=12),
                command=lambda t=target: self.show_page(t)).pack(
                side="left", padx=(0, 8))
        return f

    def _draw_score(self, pct):
        """Rendered in PIL at 4x - Tk's canvas has no anti-aliasing, which
        is what made the old ring look jagged."""
        size = 168
        if pct >= 70:
            c1, c2 = "#2f9db5", OK_FG
        elif pct >= 35:
            c1, c2 = "#e0a92b", "#e07b2b"
        else:
            c1, c2 = "#e0552b", ACCENT
        try:
            img = gfx.ring(size, pct, c1, track="#212127", bg=CARD,
                           width=14, gradient_to=c2)
            self._score_photo = ImageTk.PhotoImage(img)
            self.score_img.configure(image=self._score_photo, text="")
        except Exception:
            self.score_img.configure(text=f"{pct:.0f}%")

        if not self.score_num.winfo_ismapped():
            self.score_num.place(in_=self.score_img, relx=0.5, rely=0.42,
                                 anchor="center")
            self.score_sub = ctk.CTkLabel(
                self.score_img, text="OUT OF 100", text_color=FAINT,
                fg_color="transparent",
                font=ctk.CTkFont(family=F_REG, size=9))
            self.score_sub.place(relx=0.5, rely=0.645, anchor="center")
        self.score_num.configure(
            text=f"{pct:.0f}",
            font=ctk.CTkFont(family=F_SEMI, size=36))

    def refresh_home(self):
        if not hasattr(self, "home_cats"):
            return
        total = applied = 0
        for cat in CATEGORY_ORDER:
            items = [t for t in self.tweaks if t.category == cat]
            on = sum(1 for t in items
                     if self.cards[t.key].applied or self.cards[t.key].locked)
            total += len(items)
            applied += on
            count, bar = self.home_cats[cat]
            count.configure(text=f"{on}/{len(items)}",
                            text_color=OK_FG if on else FAINT)
            bar.set(on / len(items) if items else 0)
        pct = (applied / total * 100) if total else 0
        self._draw_score(pct)
        left = total - applied
        if pct >= 90:
            note = "Just about everything is applied. Nice."
        elif pct >= 60:
            note = f"Well tuned. {left} tweak(s) still available."
        elif pct >= 25:
            note = f"Partly tuned - {left} tweak(s) not applied yet."
        else:
            note = ("Mostly untouched. Make a restore point, then work "
                    "through the categories.")
        self.score_note.configure(text=note)

    def load_home_specs(self):
        def work():
            try:
                out = {
                    "CPU": sysinfo.cpu(),
                    "Graphics": sysinfo.graphics(),
                    "Memory": sysinfo.memory(),
                    "Motherboard": sysinfo.mainboard(),
                    "Windows": sysinfo.windows(),
                    "Storage": sysinfo.storage(),
                }
            except Exception:
                out = {}
            self.after(0, lambda: self._home_specs_done(out))

        threading.Thread(target=work, daemon=True).start()

    def _home_specs_done(self, data):
        def first(groups, key, join=False):
            vals = []
            for rows in groups or []:
                for k, v in rows:
                    if k == key and v and v != "N/A":
                        vals.append(v)
            if not vals:
                return "Unknown"
            return "  ·  ".join(dict.fromkeys(vals)) if join else vals[0]

        try:
            self.spec_rows["CPU"].configure(
                text=first(data.get("CPU"), "Name"))
            self.spec_rows["Graphics"].configure(
                text=first(data.get("Graphics"), "Name", join=True))
            mem = data.get("Memory") or []
            cap = first(mem, "Total capacity")
            speed = first(mem, "Running at")
            self.spec_rows["Memory"].configure(
                text=cap + (f"  @  {speed}" if speed != "Unknown" else ""))
            mb = data.get("Motherboard") or []
            self.spec_rows["Motherboard"].configure(
                text=f"{first(mb, 'Manufacturer')}  {first(mb, 'Product')}")
            win = data.get("Windows") or []
            self.spec_rows["Windows"].configure(
                text=f"{first(win, 'Edition')}  (build {first(win, 'Build')})")
            st = data.get("Storage") or []
            self.spec_rows["Storage"].configure(
                text=first(st, "Model", join=True))
        except Exception:
            pass

    # ---------------------------------------------------------- drivers
    def _build_drv_page(self):
        f = ctk.CTkScrollableFrame(self.body, fg_color="transparent",
                                   scrollbar_button_color="#2a2a30")
        bar = ctk.CTkFrame(f, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 10))
        self.drv_btn = ctk.CTkButton(
            bar, text="Check for Updates", width=170, height=36,
            corner_radius=8, fg_color=ACCENT, hover_color=ACCENT_DIM,
            font=ctk.CTkFont(family=F_SEMI, size=12),
            command=self.check_drivers)
        self.drv_btn.pack(side="left")
        self.drv_status = ctk.CTkLabel(
            bar, text="", text_color=FAINT,
            font=ctk.CTkFont(family=F_REG, size=11))
        self.drv_status.pack(side="left", padx=12)

        self.drv_body = ctk.CTkFrame(f, fg_color="transparent")
        self.drv_body.pack(fill="both", expand=True)

        note = ctk.CTkFrame(f, fg_color=CARD, corner_radius=10,
                            border_width=1, border_color=BORDER)
        note.pack(fill="x", pady=(14, 0))
        ctk.CTkLabel(
            note,
            text="Downloads come straight from the vendor's own servers over "
                 "HTTPS, and the app refuses any link that is not on an "
                 "nvidia.com or amd.com host. It saves the installer to your "
                 "Downloads folder and opens it there - it will not run an "
                 "installer for you, so you can see exactly what you are "
                 "about to execute.",
            text_color=MUTED, justify="left", anchor="w", wraplength=820,
            font=ctk.CTkFont(family=F_REG, size=11)).pack(
            padx=18, pady=14, anchor="w")
        return f

    def check_drivers(self):
        self.drv_btn.configure(state="disabled", text="Checking…")
        self.drv_status.configure(text="Querying vendor for latest release…",
                                  text_color=MUTED)
        for w in self.drv_body.winfo_children():
            w.destroy()

        def work():
            found = []
            try:
                for name, ver, vendor in drivers.detect_gpus():
                    latest = None
                    if vendor == "NVIDIA":
                        installed = drivers.nvidia_marketing_version(ver)
                        latest = drivers.nvidia_latest(name)
                    else:
                        installed = ver or "Unknown"
                    found.append((name, vendor, installed, latest))
            except Exception:
                pass
            self.after(0, lambda: self._drivers_done(found))

        threading.Thread(target=work, daemon=True).start()

    def _drivers_done(self, found):
        self.drv_btn.configure(state="normal", text="Check for Updates")
        stamp = time.strftime("%H:%M:%S")
        online = any(latest for _n, _v, _i, latest in found)
        self.drv_status.configure(
            text=(f"Checked against vendor at {stamp}" if online else
                  f"Checked at {stamp} - could not reach the vendor, "
                  "showing installed versions only"),
            text_color=FAINT if online else WARN_FG)
        if not found:
            ctk.CTkLabel(self.drv_body, text="No display adapters detected.",
                         text_color=FAINT,
                         font=ctk.CTkFont(family=F_REG, size=12)).pack(
                anchor="w", pady=10)
            return

        for name, vendor, installed, latest in found:
            card = ctk.CTkFrame(self.drv_body, fg_color=CARD,
                                corner_radius=12, border_width=1,
                                border_color=BORDER)
            card.pack(fill="x", pady=7)

            head = ctk.CTkFrame(card, fg_color="transparent")
            head.pack(fill="x", padx=18, pady=(16, 4))
            ctk.CTkLabel(head, text="◧", width=38, height=38, corner_radius=9,
                         fg_color="#232327", text_color=TEXT,
                         font=ctk.CTkFont(family=F_SYM, size=15)).pack(
                side="left")
            box = ctk.CTkFrame(head, fg_color="transparent")
            box.pack(side="left", padx=(12, 0))
            ctk.CTkLabel(box, text=name, text_color=TEXT, anchor="w",
                         font=ctk.CTkFont(family=F_SEMI, size=15)).pack(
                anchor="w")
            ctk.CTkLabel(box, text=vendor, text_color=MUTED, anchor="w",
                         font=ctk.CTkFont(family=F_REG, size=11)).pack(
                anchor="w")

            up_to_date = bool(latest) and latest[0] == installed
            chip_text = ("  UP TO DATE  " if up_to_date else
                         "  UPDATE AVAILABLE  " if latest else
                         "  NOT CHECKED  ")
            ctk.CTkLabel(head, text=chip_text, corner_radius=8, height=24,
                         fg_color=OK_BG if up_to_date else
                         ("#2b2411" if latest else "#1c1c20"),
                         text_color=OK_FG if up_to_date else
                         (WARN_FG if latest else FAINT),
                         font=ctk.CTkFont(family=F_SEMI, size=10)).pack(
                side="right")

            vrow = ctk.CTkFrame(card, fg_color="transparent")
            vrow.pack(fill="x", padx=18, pady=(10, 4))
            ctk.CTkLabel(vrow, text="INSTALLED", text_color=FAINT,
                         font=ctk.CTkFont(family=F_SEMI, size=9)).pack(
                anchor="w")
            ctk.CTkLabel(vrow, text=installed, text_color=TEXT,
                         font=ctk.CTkFont(family="Consolas", size=19)).pack(
                anchor="w")

            if latest:
                ctk.CTkLabel(vrow, text="LATEST", text_color=FAINT,
                             font=ctk.CTkFont(family=F_SEMI, size=9)).pack(
                    anchor="w", pady=(8, 0))
                ctk.CTkLabel(
                    vrow, text=latest[0],
                    text_color=OK_FG if up_to_date else WARN_FG,
                    font=ctk.CTkFont(family="Consolas", size=19)).pack(
                    anchor="w")

            btns = ctk.CTkFrame(card, fg_color="transparent")
            btns.pack(fill="x", padx=18, pady=(8, 16))
            prog = ctk.CTkLabel(btns, text="", text_color=MUTED,
                                font=ctk.CTkFont(family=F_REG, size=11))

            if latest and not up_to_date:
                b = ctk.CTkButton(
                    btns, text="Download Driver", width=160, height=34,
                    corner_radius=8, fg_color=ACCENT, hover_color=ACCENT_DIM,
                    font=ctk.CTkFont(family=F_SEMI, size=12))
                b.configure(command=lambda u=latest[1], v=vendor, bb=b,
                            pl=prog: self.get_driver(u, v, bb, pl))
                b.pack(side="left")

            page = drivers.vendor_page(vendor)
            ctk.CTkButton(
                btns, text="Open vendor page", width=150, height=34,
                corner_radius=8, fg_color="#232327", hover_color="#2d2d33",
                text_color=TEXT,
                font=ctk.CTkFont(family=F_REG, size=12),
                command=lambda u=page: webbrowser.open(u)).pack(
                side="left", padx=8)
            prog.pack(side="left", padx=8)

    def get_driver(self, url, vendor, btn, label):
        btn.configure(state="disabled", text="Downloading…")

        def prog(frac):
            self.after(0, lambda: label.configure(
                text=f"{frac * 100:.0f}%", text_color=MUTED))

        def work():
            try:
                path = drivers.download(url, vendor, prog)
                self.after(0, lambda: self._driver_got(btn, label, path, None))
            except Exception as e:
                self.after(0, lambda: self._driver_got(btn, label, None, e))

        threading.Thread(target=work, daemon=True).start()

    def _driver_got(self, btn, label, path, err):
        btn.configure(state="normal", text="Download Driver")
        if err:
            label.configure(text=f"Failed: {err}", text_color=WARN_FG)
            return
        label.configure(text="Saved to Downloads - opening folder",
                        text_color=OK_FG)
        drivers.reveal(path)

    # ------------------------------------------------------ system info
    def _build_sys_page(self):
        f = ctk.CTkFrame(self.body, fg_color="transparent")

        tabs = ctk.CTkFrame(f, fg_color="transparent")
        tabs.pack(fill="x", pady=(0, 12))
        self.sys_tabs = {}
        for name, icon, _fn in sysinfo.SECTIONS:
            b = ctk.CTkButton(
                tabs, text=f" {icon}  {name}", height=32, corner_radius=8,
                fg_color="#1a1a1e", hover_color="#232329", text_color=MUTED,
                font=ctk.CTkFont(family=F_REG, size=12),
                command=lambda n=name: self.load_sys(n))
            b.pack(side="left", padx=(0, 6))
            self.sys_tabs[name] = b

        self.sys_body = ctk.CTkScrollableFrame(
            f, fg_color="transparent", scrollbar_button_color="#2a2a30")
        self.sys_body.pack(fill="both", expand=True)
        self.sys_body.grid_columnconfigure(0, weight=1, uniform="s")
        self.sys_body.grid_columnconfigure(1, weight=1, uniform="s")
        return f

    def load_sys(self, name):
        self.sys_section = name
        for n, b in self.sys_tabs.items():
            b.configure(fg_color="#2a1013" if n == name else "#1a1a1e",
                        text_color=TEXT if n == name else MUTED)
        for w in self.sys_body.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.sys_body, text="Reading…", text_color=FAINT,
                     font=ctk.CTkFont(family=F_REG, size=12)).grid(
            row=0, column=0, sticky="w", padx=8, pady=8)

        fn = dict((n, f) for n, _i, f in sysinfo.SECTIONS)[name]

        def work():
            try:
                groups = fn()
            except Exception as e:
                groups = [[("Error", str(e))]]
            self.after(0, lambda: self._sys_done(name, groups))

        threading.Thread(target=work, daemon=True).start()

    def _sys_done(self, name, groups):
        if name != self.sys_section:
            return
        for w in self.sys_body.winfo_children():
            w.destroy()
        if not groups:
            ctk.CTkLabel(self.sys_body, text="Nothing reported.",
                         text_color=FAINT,
                         font=ctk.CTkFont(family=F_REG, size=12)).grid(
                row=0, column=0, sticky="w", padx=8, pady=8)
            return
        for i, rows in enumerate(groups):
            r, c = divmod(i, 2)
            card = ctk.CTkFrame(self.sys_body, fg_color=CARD,
                                corner_radius=12, border_width=1,
                                border_color=BORDER)
            card.grid(row=r, column=c, sticky="nsew", padx=8, pady=8)
            for k, v in rows:
                row = ctk.CTkFrame(card, fg_color="transparent")
                row.pack(fill="x", padx=16, pady=(10, 0))
                ctk.CTkLabel(row, text=k.upper(), text_color=FAINT,
                             anchor="w",
                             font=ctk.CTkFont(family=F_SEMI, size=9)).pack(
                    fill="x")
                ctk.CTkLabel(row, text=v, text_color=TEXT, anchor="w",
                             justify="left", wraplength=380,
                             font=ctk.CTkFont(family=F_SEMI, size=13)).pack(
                    fill="x")
            ctk.CTkFrame(card, fg_color="transparent", height=14).pack()

    # ------------------------------------------------------ disk cleanup
    def _build_clean_page(self):
        f = ctk.CTkFrame(self.body, fg_color="transparent")

        top = ctk.CTkFrame(f, fg_color=CARD, corner_radius=12,
                           border_width=1, border_color=BORDER)
        top.pack(fill="x", pady=(0, 12))
        head = ctk.CTkFrame(top, fg_color="transparent")
        head.pack(fill="x", padx=18, pady=(14, 6))
        self.clean_total = ctk.CTkLabel(
            head, text="Scanning…", text_color=TEXT, anchor="w",
            font=ctk.CTkFont(family=F_SEMI, size=20))
        self.clean_total.pack(side="left")
        self.clean_btn = ctk.CTkButton(
            head, text="Clean Up", width=130, height=34, corner_radius=8,
            fg_color=ACCENT, hover_color=ACCENT_DIM,
            font=ctk.CTkFont(family=F_SEMI, size=12), command=self.do_cleanup)
        self.clean_btn.pack(side="right")
        self.clean_rescan = ctk.CTkButton(
            head, text="Rescan", width=90, height=34, corner_radius=8,
            fg_color="#232327", hover_color="#2d2d33", text_color=TEXT,
            font=ctk.CTkFont(family=F_REG, size=12), command=self.scan_cleanup)
        self.clean_rescan.pack(side="right", padx=8)

        self.disk_bar = ctk.CTkProgressBar(top, height=8, corner_radius=4,
                                           progress_color="#7a6fd0",
                                           fg_color="#1c1c20")
        self.disk_bar.set(0)
        self.disk_bar.pack(fill="x", padx=18, pady=(4, 6))
        self.disk_lbl = ctk.CTkLabel(
            top, text="", text_color=MUTED, anchor="w",
            font=ctk.CTkFont(family=F_REG, size=11))
        self.disk_lbl.pack(fill="x", padx=18, pady=(0, 4))
        self.freed_lbl = ctk.CTkLabel(
            top, text="", text_color=OK_FG, anchor="w",
            font=ctk.CTkFont(family=F_SEMI, size=12))
        self.freed_lbl.pack(fill="x", padx=18, pady=(0, 14))
        self.session_freed = 0

        self.clean_log = ctk.CTkTextbox(
            f, fg_color="#0e0e10", text_color="#c8c8d0", corner_radius=10,
            border_width=1, border_color=BORDER, wrap="word", height=120,
            font=ctk.CTkFont(family="Consolas", size=11))
        self.clean_log_shown = False

        self.clean_body = ctk.CTkScrollableFrame(
            f, fg_color="transparent", scrollbar_button_color="#2a2a30")
        self.clean_body.pack(fill="both", expand=True)
        self.clean_vars = []
        return f

    def scan_cleanup(self):
        self.clean_btn.configure(state="disabled")
        self.clean_rescan.configure(state="disabled", text="Scanning…")
        for w in self.clean_body.winfo_children():
            w.destroy()
        self.clean_vars = []

        def work():
            items = cleanup.scan()
            total, used, free = cleanup.drive_usage("C")
            self.after(0, lambda: self._clean_done(items, total, used, free))

        threading.Thread(target=work, daemon=True).start()

    def _clean_done(self, items, total, used, free):
        self.clean_btn.configure(state="normal")
        self.clean_rescan.configure(state="normal", text="Rescan")

        reclaimable = sum(sz for (_n, _p, _k, default, _d, sz, _f) in items
                          if default)
        self.clean_total.configure(
            text=f"{cleanup.human(reclaimable)} can be freed")
        if total:
            self.disk_bar.set(used / total)
            self.disk_lbl.configure(
                text=f"Drive C:  {cleanup.human(used)} of "
                     f"{cleanup.human(total)} used  ·  "
                     f"{cleanup.human(free)} free")

        for name, path, kind, default, desc, size, files in items:
            card = ctk.CTkFrame(self.clean_body, fg_color=CARD,
                                corner_radius=10, border_width=1,
                                border_color=BORDER)
            card.pack(fill="x", pady=5)
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=(13, 2))

            var = tk.BooleanVar(value=default and size > 0)
            chk = ctk.CTkCheckBox(
                row, text="", width=24, checkbox_width=18, checkbox_height=18,
                corner_radius=5, fg_color=ACCENT, hover_color=ACCENT_DIM,
                border_color="#3a3a42", variable=var,
                command=self._recalc_clean)
            chk.pack(side="left")
            if size == 0:
                chk.configure(state="disabled")

            ctk.CTkLabel(row, text=name, text_color=TEXT, anchor="w",
                         font=ctk.CTkFont(family=F_SEMI, size=13)).pack(
                side="left", padx=(4, 0))
            ctk.CTkLabel(row, text=cleanup.human(size),
                         text_color=OK_FG if size else FAINT,
                         font=ctk.CTkFont(family=F_SEMI, size=13)).pack(
                side="right")

            sub = desc + (f"   ·   {files:,} files" if files else "")
            ctk.CTkLabel(card, text=sub, text_color=MUTED, anchor="w",
                         justify="left", wraplength=780,
                         font=ctk.CTkFont(family=F_REG, size=11)).pack(
                fill="x", padx=(46, 16), pady=(0, 13))

            self.clean_vars.append((var, name, path, kind, size))

    def _recalc_clean(self):
        total = sum(sz for var, _n, _p, _k, sz in self.clean_vars
                    if var.get())
        self.clean_total.configure(
            text=f"{cleanup.human(total)} can be freed")

    def do_cleanup(self):
        sel = [(n, p, k) for var, n, p, k, _sz in self.clean_vars if var.get()]
        if not sel:
            return
        self.clean_btn.configure(state="disabled", text="Cleaning…")
        self.clean_rescan.configure(state="disabled")

        if not self.clean_log_shown:
            self.clean_log_shown = True
            self.clean_log.pack(fill="x", pady=(10, 0))
        self._clog("\n--- Cleaning ---\n")

        def logline(name, item_freed, item_skipped):
            txt = f"{name}: freed {cleanup.human(item_freed)}"
            if item_skipped:
                txt += f", {item_skipped} in use"
            self.after(0, lambda t=txt: self._clog(t + "\n"))

        def work():
            freed, skipped, _items = cleanup.clean(sel, log=logline)
            self.after(0, lambda: self._cleanup_done(freed, skipped))

        threading.Thread(target=work, daemon=True).start()

    def _clog(self, text):
        self.clean_log.configure(state="normal")
        self.clean_log.insert("end", text)
        self.clean_log.see("end")
        self.clean_log.configure(state="disabled")

    def _cleanup_done(self, freed, skipped=0):
        self.clean_btn.configure(state="normal", text="Clean Up")
        self.clean_rescan.configure(state="normal")
        self.session_freed += freed
        msg = f"Freed {cleanup.human(self.session_freed)} this session"
        if skipped:
            msg += (f"  ·  {skipped} file(s) were locked by a running app "
                    "and left alone")
        self.freed_lbl.configure(
            text=msg, text_color=OK_FG if freed else WARN_FG)
        self._clog(f"Total: {cleanup.human(freed)} freed, {skipped} in use\n")
        self.after(1400, self.scan_cleanup)

    # --------------------------------------------------------- resources
    RES_TASKS = [
        ("System File Checker", "sfc",
         "Scans every protected Windows file and repairs anything that has "
         "been corrupted, using the local component store.",
         ["Verifies protected system files", "Repairs from local cache",
          "Usually 5-15 minutes"]),
        ("Windows Image Repair", "dism",
         "Repairs the component store itself with DISM. Run this first if "
         "SFC reports it could not fix something.",
         ["Checks component store health", "Downloads clean copies if needed",
          "Usually 10-30 minutes"]),
        ("Disk Check", "chkdsk",
         "Schedules a read-only scan of the system drive for file system "
         "errors and bad sectors.",
         ["Read-only scan, nothing is changed",
          "Reports errors without fixing", "Usually a few minutes"]),
    ]

    def _build_res_page(self):
        f = ctk.CTkScrollableFrame(self.body, fg_color="transparent",
                                   scrollbar_button_color="#2a2a30")
        self.res_widgets = {}
        for title, key, desc, bullets in self.RES_TASKS:
            card = ctk.CTkFrame(f, fg_color=CARD, corner_radius=12,
                                border_width=1, border_color=BORDER)
            card.pack(fill="x", pady=7)

            head = ctk.CTkFrame(card, fg_color="transparent")
            head.pack(fill="x", padx=18, pady=(16, 4))
            ctk.CTkLabel(head, text="⛭", width=38, height=38, corner_radius=9,
                         fg_color="#232327", text_color=TEXT,
                         font=ctk.CTkFont(family=F_SYM, size=15)).pack(
                side="left")
            box = ctk.CTkFrame(head, fg_color="transparent")
            box.pack(side="left", padx=(12, 0))
            ctk.CTkLabel(box, text=title, text_color=TEXT, anchor="w",
                         font=ctk.CTkFont(family=F_SEMI, size=15)).pack(
                anchor="w")
            ctk.CTkLabel(box, text=desc, text_color=MUTED, anchor="w",
                         justify="left", wraplength=680,
                         font=ctk.CTkFont(family=F_REG, size=11)).pack(
                anchor="w")

            for bl in bullets:
                r = ctk.CTkFrame(card, fg_color="transparent")
                r.pack(fill="x", padx=18, pady=1)
                ctk.CTkLabel(r, text="✓", text_color=OK_FG, width=18,
                             font=ctk.CTkFont(family=F_SYM, size=11)).pack(
                    side="left")
                ctk.CTkLabel(r, text=bl, text_color=MUTED, anchor="w",
                             font=ctk.CTkFont(family=F_REG, size=11)).pack(
                    side="left")

            status = ctk.CTkLabel(
                card, text="", text_color=MUTED, anchor="w", justify="left",
                wraplength=780, font=ctk.CTkFont(family=F_REG, size=11))
            status.pack(fill="x", padx=18, pady=(8, 0))

            bar = ctk.CTkProgressBar(card, height=4, corner_radius=2,
                                     progress_color=ACCENT,
                                     fg_color="#1c1c20")
            bar.set(0)

            btn = ctk.CTkButton(
                card, text="Run", width=120, height=34, corner_radius=8,
                fg_color=ACCENT, hover_color=ACCENT_DIM,
                font=ctk.CTkFont(family=F_SEMI, size=12),
                command=lambda k=key: self.run_resource(k))
            btn.pack(anchor="e", padx=18, pady=(10, 16))

            self.res_widgets[key] = (btn, status, bar)
        return f

    RES_CMDS = {
        "sfc": ["sfc", "/scannow"],
        "dism": ["dism", "/Online", "/Cleanup-Image", "/RestoreHealth"],
        "chkdsk": ["chkdsk", "C:"],
    }

    def run_resource(self, key):
        btn, status, bar = self.res_widgets[key]
        btn.configure(state="disabled", text="Running…")
        bar.pack(fill="x", padx=18, pady=(2, 0))
        bar.configure(mode="indeterminate")
        bar.start()
        status.configure(text="Starting… this window stays responsive.",
                         text_color=MUTED)

        def work():
            try:
                p = subprocess.Popen(
                    self.RES_CMDS[key], stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                    text=True, bufsize=1, encoding="utf-8", errors="replace",
                    creationflags=CREATE_NO_WINDOW)
                last = ""
                for line in p.stdout:
                    line = line.strip()
                    if line:
                        last = line
                        self.after(0, lambda t=last: status.configure(
                            text=t[:150], text_color=MUTED))
                p.wait()
                rc = p.returncode
            except Exception as e:
                last, rc = str(e), 1
            self.after(0, lambda: self._resource_done(key, last, rc))

        threading.Thread(target=work, daemon=True).start()

    def _resource_done(self, key, last, rc):
        btn, status, bar = self.res_widgets[key]
        bar.stop()
        bar.pack_forget()
        btn.configure(state="normal", text="Run")
        ok = rc == 0
        status.configure(
            text=(last or ("Finished." if ok else "Finished with errors."))[:200],
            text_color=OK_FG if ok else WARN_FG)

    # ------------------------------------------------------ restore point
    def make_restore_point(self):
        self.restore_btn.configure(text="Creating…", state="disabled")
        self.restore_status.configure(text="")

        def work():
            rc, out = run(["powershell", "-NoProfile", "-Command",
                           "Enable-ComputerRestore -Drive 'C:\\'; "
                           "Checkpoint-Computer -Description "
                           "'TechLoungeTweaks' -RestorePointType "
                           "'MODIFY_SETTINGS'"])
            msg = ("Restore point created." if rc == 0 else
                   "Could not create one - System Protection may be off "
                   "for C:, or one was made in the last 24 hours.")
            self.after(0, lambda: self._restore_done(msg, rc == 0))

        threading.Thread(target=work, daemon=True).start()

    def _restore_done(self, msg, ok):
        self.restore_btn.configure(text="Create Restore Point", state="normal")
        self.restore_status.configure(text=msg,
                                      text_color=OK_FG if ok else WARN_FG)

    # ------------------------------------------------------ boot optimiser
    def _log(self, text):
        self.boot_log.configure(state="normal")
        self.boot_log.insert("end", text)
        self.boot_log.see("end")
        self.boot_log.configure(state="disabled")

    # ---- live status helpers ----
    def _set_step(self, name):
        self._step_i = getattr(self, "_step_i", 0)
        if self._step_i < len(self.step_dots):
            self.step_dots[self._step_i].configure(text_color=ACCENT)
            self._step_i += 1
        self.boot_stepname.configure(text=name)

    def _set_activity(self, text):
        self.boot_activity.configure(text="//  " + text[:90])

    def _push_feed(self, kind, text):
        colour = {"ok": OK_FG, "plan": LOCK_FG, "warn": WARN_FG,
                  "fail": "#ef6b76"}.get(kind, FAINT)
        bullet = {"ok": "●", "plan": "»", "skip": "·",
                  "warn": "▲", "fail": "×"}.get(kind, "·")
        self._feed_buf = getattr(self, "_feed_buf", [])
        self._feed_buf.append((bullet + "  " + text[:88], colour))
        self._feed_buf = self._feed_buf[-len(self.feed_rows):]
        for row, (t, c) in zip(self.feed_rows, self._feed_buf):
            row.configure(text=t, text_color=c)
        for row in self.feed_rows[len(self._feed_buf):]:
            row.configure(text="")

    def run_boot(self, rollback, preview=False):
        for btn in (self.boot_run, self.boot_undo, self.boot_preview):
            btn.configure(state="disabled")

        self.boot_idle.pack_forget()
        self.boot_results.pack_forget()
        self.boot_log.pack_forget()
        self.raw_shown = False
        self.boot_raw_btn.configure(text="Show raw output")
        self.boot_status.pack(fill="x")

        self._step_i = 0
        self._feed_buf = []
        for d in self.step_dots:
            d.configure(text_color="#2e2e34")
        for r in self.feed_rows:
            r.configure(text="")
        self.boot_stepname.configure(
            text="Preview" if preview else ("Undo" if rollback else "Applying"))
        self._set_activity("starting…")
        self.boot_log.configure(state="normal")
        self.boot_log.delete("1.0", "end")
        self.boot_log.configure(state="disabled")

        events = []

        def work():
            try:
                folder = os.path.join(os.environ.get("LOCALAPPDATA",
                                                     tempfile.gettempdir()),
                                      "TechLoungeTweaks")
                os.makedirs(folder, exist_ok=True)
                ps1 = os.path.join(folder, "Optimize-Boot.ps1")
                # newline="" is essential: the script relies on backtick line
                # continuations, and text-mode translation turns its CRLF into
                # CRCRLF, which breaks every one of them.
                with open(ps1, "w", encoding="utf-8", newline="") as fh:
                    fh.write(base64.b64decode(boot_payload.B64).decode("utf-8"))
                rollback_file = os.path.join(folder, "boot-rollback.json")

                args = ["powershell", "-NoProfile", "-ExecutionPolicy",
                        "Bypass", "-File", ps1,
                        "-RollbackFilePath", rollback_file]
                if rollback:
                    args.append("-Rollback")
                if preview:
                    args.append("-WhatIf")

                p = subprocess.Popen(
                    args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL, text=True, bufsize=1,
                    encoding="utf-8", errors="replace",
                    creationflags=CREATE_NO_WINDOW)
                for line in p.stdout:
                    self.after(0, lambda l=line: self._log(l))
                    ev = bootparse.parse_line(line)
                    if not ev:
                        continue
                    events.append(ev)
                    kind, text, detail = ev
                    if kind == "step":
                        self.after(0, lambda t=text: self._set_step(t))
                    else:
                        shown = text + ((" → " + detail) if detail else "")
                        self.after(0, lambda t=shown: self._set_activity(t))
                        if kind in ("ok", "plan", "warn", "fail", "skip"):
                            self.after(0,
                                       lambda k=kind, t=shown:
                                       self._push_feed(k, t))
                    time.sleep(0.012)
                p.wait()
            except Exception as e:
                self.after(0, lambda: self._log(f"\nERROR: {e}\n"))
            self.after(0, lambda: self._boot_done(events, preview, rollback))

        threading.Thread(target=work, daemon=True).start()

    def _result_group(self, title, rows, colour, empty_text):
        card = ctk.CTkFrame(self.boot_results, fg_color=CARD,
                            corner_radius=10, border_width=1,
                            border_color=BORDER)
        card.pack(fill="x", pady=6)
        head = ctk.CTkFrame(card, fg_color="transparent")
        head.pack(fill="x", padx=16, pady=(13, 2))
        ctk.CTkLabel(head, text=title, text_color=TEXT,
                     font=ctk.CTkFont(family=F_SEMI, size=13)).pack(side="left")
        ctk.CTkLabel(head, text=f"  {len(rows)}  ", corner_radius=6,
                     fg_color="#232327", text_color=MUTED, height=20,
                     font=ctk.CTkFont(family=F_SEMI, size=10)).pack(
            side="left", padx=8)

        if not rows:
            ctk.CTkLabel(card, text=empty_text, text_color=FAINT, anchor="w",
                         font=ctk.CTkFont(family=F_REG, size=12)).pack(
                fill="x", padx=16, pady=(2, 14))
            return

        for text, detail in rows:
            r = ctk.CTkFrame(card, fg_color="transparent")
            r.pack(fill="x", padx=16, pady=1)
            ctk.CTkLabel(r, text="●", text_color=colour, width=14,
                         font=ctk.CTkFont(family=F_SYM, size=9)).pack(
                side="left")
            ctk.CTkLabel(r, text=text, text_color=TEXT, anchor="w",
                         font=ctk.CTkFont(family=F_REG, size=12)).pack(
                side="left")
            if detail:
                ctk.CTkLabel(r, text="  →  " + detail, text_color=OK_FG,
                             anchor="w",
                             font=ctk.CTkFont(family=F_SEMI, size=12)).pack(
                    side="left")
        ctk.CTkFrame(card, fg_color="transparent", height=10).pack()

    def _boot_done(self, events, preview, rollback):
        for btn in (self.boot_run, self.boot_undo, self.boot_preview):
            btn.configure(state="normal")
        for d in self.step_dots:
            d.configure(text_color=ACCENT)
        self.boot_status.pack_forget()

        self.boot_idle.pack_forget()
        for w in self.boot_results.winfo_children():
            w.destroy()

        planned, done, skipped, attention = bootparse.summarise(events)

        if preview:
            self.boot_stepname.configure(text="Preview")
            self._result_group(
                "Would change", planned, OK_FG,
                "Nothing to change - this machine is already optimised.")
            self._result_group(
                "Already done", skipped, FAINT,
                "Nothing was already set.")
        else:
            self._result_group(
                "Changed", done, OK_FG,
                "Nothing needed changing." if not rollback
                else "Nothing to restore.")
            self._result_group("Left alone", skipped, FAINT,
                               "Nothing was skipped.")
        if attention:
            self._result_group("Needs attention", attention, WARN_FG, "")

        self.boot_results.pack(fill="both", expand=True)


def main():
    if not is_admin():
        try:
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable,
                " ".join(f'"{a}"' for a in sys.argv), None, 1)
            return
        except Exception:
            pass
    App().mainloop()


if __name__ == "__main__":
    main()
