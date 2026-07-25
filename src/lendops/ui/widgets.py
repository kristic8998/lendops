"""Shared UI building blocks: helper cards, KPI cards, data grid, toasts.

Every page is click-driven and self-explaining: :class:`HelperCard`
renders the mandatory in-app "How to use" steps at the top of each
module, and :class:`DataGrid` can tint rows by severity so risk jumps
out visually without reading numbers.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable, Sequence
from tkinter import ttk

import customtkinter as ctk
import pandas as pd

ACCENT = "#2E7BE6"
GOOD = "#2E7D32"
WATCH = "#EF6C00"
ALERT = "#C62828"

_TINT_TAGS = {
    "high": "alert",
    "alert": "alert",
    "medium": "watch",
    "watch": "watch",
    "decline": "watch",
}


class HelperCard(ctk.CTkFrame):
    """Always-visible 'How to use' card with numbered steps."""

    def __init__(self, master: tk.Misc, title: str, steps: Sequence[str], **kwargs: object) -> None:
        super().__init__(master, corner_radius=12, border_width=1, border_color=ACCENT, **kwargs)
        ctk.CTkLabel(
            self,
            text=f"ⓘ  {title}",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=ACCENT,
        ).pack(anchor="w", padx=14, pady=(10, 2))
        for number, step in enumerate(steps, start=1):
            ctk.CTkLabel(
                self,
                text=f"{number}.  {step}",
                font=ctk.CTkFont(size=12),
                anchor="w",
                justify="left",
                wraplength=1050,
            ).pack(anchor="w", padx=18, pady=1)
        ctk.CTkLabel(self, text="").pack(pady=(0, 4))  # bottom breathing room


class KpiCard(ctk.CTkFrame):
    """Rounded metric card: small label, big value, optional sub-line."""

    def __init__(self, master: tk.Misc, title: str, **kwargs: object) -> None:
        super().__init__(master, corner_radius=12, **kwargs)
        ctk.CTkLabel(
            self, text=title, font=ctk.CTkFont(size=12), text_color=("gray40", "gray70")
        ).pack(anchor="w", padx=14, pady=(10, 0))
        self._value = ctk.CTkLabel(self, text="—", font=ctk.CTkFont(size=22, weight="bold"))
        self._value.pack(anchor="w", padx=14)
        self._sub = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=11), text_color=("gray45", "gray65")
        )
        self._sub.pack(anchor="w", padx=14, pady=(0, 10))

    def update_value(self, value: str, sub: str = "", color: str | None = None) -> None:
        self._value.configure(text=value, text_color=color if color else None)
        self._sub.configure(text=sub)


class Section(ctk.CTkFrame):
    """Titled rounded container."""

    def __init__(self, master: tk.Misc, title: str, **kwargs: object) -> None:
        super().__init__(master, corner_radius=12, **kwargs)
        ctk.CTkLabel(self, text=title, font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", padx=14, pady=(10, 4)
        )
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=10, pady=(0, 10))


class DataGrid(ctk.CTkFrame):
    """DataFrame viewer on ttk.Treeview, with optional severity row tinting.

    Shows up to ``page_size`` rows with a count banner — a deliberate
    guard for 16 GB laptops; exports always use the full frame.
    """

    def __init__(self, master: tk.Misc, page_size: int = 400, **kwargs: object) -> None:
        super().__init__(master, corner_radius=8, **kwargs)
        self._page_size = page_size
        self._frame: pd.DataFrame = pd.DataFrame()

        self._banner = ctk.CTkLabel(
            self, text="", anchor="w", font=ctk.CTkFont(size=11), text_color=("gray40", "gray70")
        )
        self._banner.pack(fill="x", padx=8, pady=(6, 0))

        container = tk.Frame(self, highlightthickness=0, bd=0)
        container.pack(fill="both", expand=True, padx=6, pady=6)
        self._tree = ttk.Treeview(container, show="headings", height=12)
        vsb = ttk.Scrollbar(container, orient="vertical", command=self._tree.yview)
        hsb = ttk.Scrollbar(container, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

    def show(self, frame: pd.DataFrame, note: str = "", tint_by: str | None = None) -> None:
        self._frame = frame
        self._tree.delete(*self._tree.get_children())
        dark = ctk.get_appearance_mode().lower() == "dark"
        self._tree.tag_configure("alert", background="#4a1f1f" if dark else "#fde2e0")
        self._tree.tag_configure("watch", background="#4a3620" if dark else "#fff0d6")

        columns = [str(c) for c in frame.columns]
        self._tree.configure(columns=columns)
        for column in columns:
            self._tree.heading(column, text=column)
            self._tree.column(column, width=max(90, min(240, 11 * len(column))), anchor="w")
        for _, row in frame.head(self._page_size).iterrows():
            tags: tuple[str, ...] = ()
            if tint_by is not None and tint_by in frame.columns:
                tag = _TINT_TAGS.get(str(row[tint_by]).strip().lower())
                if tag:
                    tags = (tag,)
            self._tree.insert("", "end", values=[_fmt(v) for v in row.tolist()], tags=tags)
        extra = f" (showing first {self._page_size:,})" if len(frame) > self._page_size else ""
        banner = f"{len(frame):,} row(s) × {len(columns)} column(s){extra}"
        if note:
            banner = f"{banner} — {note}"
        self._banner.configure(text=banner)


def _fmt(value: object) -> str:
    if isinstance(value, float):
        return f"{value:,.2f}"
    return "" if value is None else str(value)


class Toast:
    """Transient status message in the shell's status bar."""

    def __init__(self, label: ctk.CTkLabel) -> None:
        self._label = label
        self._token = 0

    def show(self, message: str, kind: str = "info", ms: int = 6000) -> None:
        color = {"info": ("gray25", "gray80"), "ok": GOOD, "error": ALERT}.get(kind, ALERT)
        self._label.configure(text=message, text_color=color)
        self._token += 1
        token = self._token

        def clear() -> None:
            if self._token == token:
                self._label.configure(text="")

        self._label.after(ms, clear)


def style_treeview(dark: bool) -> None:
    """Make ttk.Treeview match the CTk theme (ttk has its own styling)."""
    style = ttk.Style()
    style.theme_use("clam")
    bg, fg, field = ("#23272e", "#e8e8e8", "#2b3038") if dark else ("#ffffff", "#1c2733", "#f4f6f9")
    style.configure(
        "Treeview", background=bg, foreground=fg, fieldbackground=bg, rowheight=26, borderwidth=0
    )
    style.configure(
        "Treeview.Heading",
        background=field,
        foreground=fg,
        borderwidth=0,
        font=("Segoe UI", 9, "bold"),
    )
    style.map("Treeview", background=[("selected", ACCENT)], foreground=[("selected", "#ffffff")])


def run_in_thread(
    widget: tk.Misc,
    runner: Callable[..., object],
    func: Callable[[], object],
    on_done: Callable[[object], None],
    on_error: Callable[[BaseException], None],
) -> None:
    """Submit work to the TaskRunner, marshalling callbacks onto the Tk thread."""
    runner(  # type: ignore[operator]
        func,
        on_done=lambda result: widget.after(0, lambda: on_done(result)),
        on_error=lambda exc: widget.after(0, lambda: on_error(exc)),
    )
