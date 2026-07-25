"""LendOps Studio application shell.

Sidebar navigation + lazily-built pages + status bar. All heavy work
(file reads, scoring, simulations, scans, exports) runs on the
TaskRunner worker threads; the Tk thread only ever draws, so the UI
stays responsive on modest hardware.
"""

from __future__ import annotations

import logging
import sys

import customtkinter as ctk

from . import APP_NAME, __version__
from .core.config import AppConfig, load_config, save_config
from .core.tasks import TaskRunner
from .ui.widgets import Toast, style_treeview

logger = logging.getLogger(__name__)

_PAGES: tuple[tuple[str, str, str], ...] = (
    # (module id, title, glyph)
    ("home", "Home", "⌂"),
    ("collecta", "Collecta", "☎"),
    ("policysim", "PolicySim", "⚖"),
    ("kyc", "KYC Sentinel", "🛡"),
)


class LendOpsApp(ctk.CTk):
    """Main window."""

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self.config_data = config
        self.runner = TaskRunner(max_workers=4)

        ctk.set_appearance_mode(config.theme)
        ctk.set_default_color_theme("blue")
        style_treeview(dark=config.theme != "light")

        self.title(f"{APP_NAME} — Micro-Lending Operations")
        self.geometry("1320x820")
        self.minsize(1080, 680)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self._pages: dict[str, ctk.CTkFrame] = {}
        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        self._build_sidebar()

        self._host = ctk.CTkFrame(self, fg_color="transparent")
        self._host.grid(row=0, column=1, sticky="nsew", padx=(0, 12), pady=12)

        status = ctk.CTkFrame(self, height=30, corner_radius=0)
        status.grid(row=1, column=0, columnspan=2, sticky="ew")
        self._status_label = ctk.CTkLabel(status, text="", anchor="w", font=ctk.CTkFont(size=11))
        self._status_label.pack(side="left", padx=12)
        ctk.CTkLabel(
            status,
            text=f"v{__version__} · Ctrl+D theme · Ctrl+1..4 pages",
            font=ctk.CTkFont(size=11),
            text_color=("gray45", "gray60"),
        ).pack(side="right", padx=12)
        self.toast = Toast(self._status_label)

        self.bind("<Control-d>", lambda _e: self.toggle_theme())
        for index, (module_id, _title, _glyph) in enumerate(_PAGES, start=1):
            self.bind(f"<Control-Key-{index}>", lambda _e, m=module_id: self.show_page(m))

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        start = (
            config.start_page
            if config.start_page in dict.fromkeys(p[0] for p in _PAGES)
            else "home"
        )
        self.show_page(start)

    # ---- construction ---------------------------------------------------------
    def _build_sidebar(self) -> None:
        sidebar = ctk.CTkFrame(self, width=210, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsw", padx=(0, 12))
        sidebar.grid_propagate(False)

        ctk.CTkLabel(sidebar, text="LendOps", font=ctk.CTkFont(size=22, weight="bold")).pack(
            anchor="w", padx=18, pady=(18, 0)
        )
        ctk.CTkLabel(
            sidebar,
            text="Studio",
            font=ctk.CTkFont(size=11),
            text_color=("gray45", "gray60"),
        ).pack(anchor="w", padx=18, pady=(0, 16))

        for module_id, title, glyph in _PAGES:
            button = ctk.CTkButton(
                sidebar,
                text=f"  {glyph}  {title}",
                anchor="w",
                fg_color="transparent",
                hover_color=("gray85", "gray25"),
                text_color=("gray15", "gray90"),
                height=36,
                corner_radius=8,
                command=lambda m=module_id: self.show_page(m),
            )
            button.pack(fill="x", padx=8, pady=1)
            self._nav_buttons[module_id] = button

        ctk.CTkFrame(sidebar, fg_color="transparent").pack(fill="both", expand=True)
        ctk.CTkButton(
            sidebar,
            text="◐  Dark / light mode",
            height=30,
            fg_color="transparent",
            border_width=1,
            text_color=("gray15", "gray90"),
            command=self.toggle_theme,
        ).pack(fill="x", padx=12, pady=12)

    # ---- page management --------------------------------------------------------
    def show_page(self, module_id: str) -> None:
        from .ui.pages import PAGE_FACTORIES

        if module_id not in PAGE_FACTORIES:
            return
        if module_id not in self._pages:
            self._pages[module_id] = PAGE_FACTORIES[module_id](self._host, self)
        for shown_id, page in self._pages.items():
            if shown_id != module_id:
                page.pack_forget()
        self._pages[module_id].pack(fill="both", expand=True)
        for nav_id, button in self._nav_buttons.items():
            button.configure(
                fg_color=("gray80", "gray28") if nav_id == module_id else "transparent"
            )

    # ---- global actions ------------------------------------------------------------
    def toggle_theme(self) -> None:
        new_mode = "light" if ctk.get_appearance_mode().lower() == "dark" else "dark"
        ctk.set_appearance_mode(new_mode)
        style_treeview(dark=new_mode == "dark")
        self.config_data.theme = new_mode
        save_config(self.config_data)

    def _on_close(self) -> None:
        try:
            self.runner.shutdown()
            save_config(self.config_data)
        except Exception as exc:  # closing must never hang the window
            logger.warning("shutdown housekeeping failed: %s", exc)
        self.destroy()


def create_app() -> LendOpsApp:
    """Composition root: config → window."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    return LendOpsApp(load_config())


def main() -> int:
    if "--selftest" in sys.argv:
        from .selftest import run

        return run()
    app = create_app()
    app.mainloop()
    return 0
