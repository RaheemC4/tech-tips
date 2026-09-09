"""Hover tooltips - plain-English explanations of what each number means."""

import tkinter as tk

BG = "#17171b"
BORDER = "#33333c"
TITLE = "#f4f4f5"
BODY = "#a8a8b2"
GOOD = "#57d98a"

_active = {"win": None, "job": None}


def _destroy():
    win = _active.get("win")
    if win is not None:
        try:
            win.destroy()
        except Exception:
            pass
    _active["win"] = None


def attach(widget, title, body, good=None, font_semi="Segoe UI",
           font_reg="Segoe UI", delay=350):
    """Show a tooltip after hovering `widget`.

    title - what the thing is
    body  - what it means in plain language
    good  - what a decent value looks like (shown in green)
    """
    def show(event=None):
        _destroy()
        try:
            win = tk.Toplevel(widget)
            win.wm_overrideredirect(True)
            win.attributes("-topmost", True)
            try:
                win.attributes("-alpha", 0.0)
            except Exception:
                pass

            frame = tk.Frame(win, bg=BORDER, bd=0)
            frame.pack(fill="both", expand=True)
            inner = tk.Frame(frame, bg=BG, bd=0)
            inner.pack(fill="both", expand=True, padx=1, pady=1)

            tk.Label(inner, text=title, bg=BG, fg=TITLE, anchor="w",
                     justify="left", font=(font_semi, 10, "bold")).pack(
                anchor="w", padx=12, pady=(10, 2))
            tk.Label(inner, text=body, bg=BG, fg=BODY, anchor="w",
                     justify="left", wraplength=300,
                     font=(font_reg, 9)).pack(anchor="w", padx=12,
                                              pady=(0, 4))
            if good:
                tk.Label(inner, text=good, bg=BG, fg=GOOD, anchor="w",
                         justify="left", wraplength=300,
                         font=(font_reg, 9)).pack(anchor="w", padx=12,
                                                  pady=(0, 10))
            else:
                tk.Frame(inner, bg=BG, height=6).pack()

            win.update_idletasks()
            x = widget.winfo_rootx() + 18
            y = widget.winfo_rooty() + widget.winfo_height() + 8
            sw = widget.winfo_screenwidth()
            sh = widget.winfo_screenheight()
            if x + win.winfo_width() > sw - 12:
                x = sw - win.winfo_width() - 12
            if y + win.winfo_height() > sh - 12:
                y = widget.winfo_rooty() - win.winfo_height() - 8
            win.geometry(f"+{max(8, x)}+{max(8, y)}")
            _active["win"] = win
            _fade_in(win, 0.0)
        except Exception:
            _destroy()

    def enter(event=None):
        cancel()
        _active["job"] = widget.after(delay, show)

    def cancel(event=None):
        job = _active.get("job")
        if job is not None:
            try:
                widget.after_cancel(job)
            except Exception:
                pass
            _active["job"] = None

    def leave(event=None):
        cancel()
        _destroy()

    widget.bind("<Enter>", enter, add="+")
    widget.bind("<Leave>", leave, add="+")
    widget.bind("<Button-1>", leave, add="+")


def _fade_in(win, alpha):
    if win is not _active.get("win"):
        return
    alpha = min(1.0, alpha + 0.2)
    try:
        win.attributes("-alpha", alpha)
    except Exception:
        return
    if alpha < 1.0:
        win.after(16, lambda: _fade_in(win, alpha))


def attach_all(widgets, title, body, good=None, **kw):
    for w in widgets:
        attach(w, title, body, good, **kw)
