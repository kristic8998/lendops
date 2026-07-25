"""Home page: what the app does, and one-click doors into the three modules."""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from ... import APP_NAME, __version__
from ..widgets import HelperCard

_MODULES = (
    (
        "collecta",
        "☎  Collecta",
        "Delinquency predictor",
        "Which active loans are about to go bad? Upload the loan book, get a scored, "
        "phone-ready calling list — worst first, with the reason for each call.",
    ),
    (
        "policysim",
        "⚖  PolicySim",
        "Credit rule backtesting",
        "What if we had lent with stricter rules? Replay the historical book under "
        "hypothetical rules and see the profit and default-rate impact before committing.",
    ),
    (
        "kyc",
        "🛡  KYC Sentinel",
        "Identity fraud detector",
        "Scan today's applications for shared bank accounts, duplicate IDs, underage "
        "applicants and age mismatches — flagged rows, plain-English reasons.",
    ),
)


class HomePage(ctk.CTkFrame):
    def __init__(self, master: tk.Misc, app) -> None:  # noqa: ANN001
        super().__init__(master, fg_color="transparent")
        ctk.CTkLabel(
            self, text=f"Welcome to {APP_NAME}", font=ctk.CTkFont(size=24, weight="bold")
        ).pack(anchor="w")
        ctk.CTkLabel(
            self,
            text="One desktop app for the three daily jobs of a micro-lending operations team: "
            "collections targeting, policy what-ifs, and application fraud screening. "
            "Everything is click-driven — no configuration, no formulas, no terminal.",
            font=ctk.CTkFont(size=13),
            text_color=("gray35", "gray65"),
            wraplength=1050,
            justify="left",
        ).pack(anchor="w", pady=(2, 10))

        HelperCard(
            self,
            "New here? 60-second tour",
            (
                "Pick a module from the sidebar (or the buttons below).",
                "Every module has a “Try with sample data” button — click it to see a full "
                "run with realistic demo data before using your own files.",
                "When you use your own files, plain CSV or Excel exports from your LMS work "
                "as-is: columns are detected automatically by name.",
                "Use the ◐ button (or Ctrl+D) to switch between dark and light mode.",
            ),
        ).pack(fill="x", pady=(0, 10))

        for module_id, title, subtitle, blurb in _MODULES:
            card = ctk.CTkFrame(self, corner_radius=12)
            card.pack(fill="x", pady=5)
            head = ctk.CTkFrame(card, fg_color="transparent")
            head.pack(fill="x", padx=14, pady=(10, 0))
            ctk.CTkLabel(head, text=title, font=ctk.CTkFont(size=16, weight="bold")).pack(
                side="left"
            )
            ctk.CTkLabel(
                head,
                text=f"  ·  {subtitle}",
                font=ctk.CTkFont(size=12),
                text_color=("gray40", "gray65"),
            ).pack(side="left")
            ctk.CTkButton(
                head, text="Open →", width=90, command=lambda m=module_id: app.show_page(m)
            ).pack(side="right")
            ctk.CTkLabel(
                card,
                text=blurb,
                font=ctk.CTkFont(size=12),
                text_color=("gray30", "gray70"),
                wraplength=1000,
                justify="left",
            ).pack(anchor="w", padx=14, pady=(2, 12))

        ctk.CTkLabel(
            self,
            text=f"v{__version__} · your data never leaves this computer",
            font=ctk.CTkFont(size=11),
            text_color=("gray45", "gray60"),
        ).pack(anchor="w", pady=(10, 0))
