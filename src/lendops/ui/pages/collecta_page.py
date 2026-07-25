"""Collecta page: upload active loans → analyze risk → export calling list."""

from __future__ import annotations

import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
import pandas as pd

from ...core.demo import sample_active_loans
from ...core.paths import reports_dir
from ...modules.collecta import RiskResult, analyze, export_calling_list
from ...modules.tabular import read_table
from ..widgets import ALERT, GOOD, WATCH, DataGrid, HelperCard, KpiCard, run_in_thread


class CollectaPage(ctk.CTkFrame):
    def __init__(self, master: tk.Misc, app) -> None:  # noqa: ANN001
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._data: pd.DataFrame | None = None
        self._result: RiskResult | None = None

        ctk.CTkLabel(
            self, text="Collecta — Delinquency Predictor", font=ctk.CTkFont(size=20, weight="bold")
        ).pack(anchor="w")
        ctk.CTkLabel(
            self,
            text="Find the loans most likely to slip into default and get a ready-to-dial "
            "calling list, worst first, with the reason for each call.",
            font=ctk.CTkFont(size=12),
            text_color=("gray35", "gray65"),
        ).pack(anchor="w", pady=(0, 8))

        HelperCard(
            self,
            "How to use — 3 steps",
            (
                "Click “Upload Active Loans” and pick your loan book (CSV or Excel). "
                "No special format needed — columns like DPD, EMI, income and outstanding "
                "are detected automatically.",
                "Click “Analyze Risk”. Every loan gets a 0–100 risk score, a High/Medium/Low "
                "band, and the main reason it is risky.",
                "Click “Export Calling List” to save an Excel file for the collections team "
                "— highest risk on top, phone numbers included.",
            ),
        ).pack(fill="x", pady=(0, 8))

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(fill="x")
        ctk.CTkButton(
            buttons, text="① Upload Active Loans…", width=190, height=34, command=self._upload
        ).pack(side="left", padx=(0, 6))
        self._analyze_btn = ctk.CTkButton(
            buttons, text="② Analyze Risk", width=150, height=34, command=self._analyze
        )
        self._analyze_btn.pack(side="left", padx=6)
        ctk.CTkButton(
            buttons,
            text="③ Export Calling List…",
            width=180,
            height=34,
            command=self._export,
        ).pack(side="left", padx=6)
        self._include_medium = ctk.CTkCheckBox(buttons, text="Include medium risk in the list")
        self._include_medium.select()
        self._include_medium.pack(side="left", padx=12)
        ctk.CTkButton(
            buttons,
            text="Try with sample data",
            width=160,
            height=34,
            fg_color="transparent",
            border_width=1,
            text_color=("gray15", "gray90"),
            command=self._load_sample,
        ).pack(side="right")

        self._file_label = ctk.CTkLabel(
            self, text="No file loaded yet.", anchor="w", text_color=("gray35", "gray65")
        )
        self._file_label.pack(fill="x", pady=(4, 0))

        cards = ctk.CTkFrame(self, fg_color="transparent")
        cards.pack(fill="x", pady=(6, 0))
        self._cards: dict[str, KpiCard] = {}
        for column, key in enumerate(("High risk", "Medium risk", "Low risk", "₹ at high risk")):
            cards.grid_columnconfigure(column, weight=1)
            card = KpiCard(cards, key)
            card.grid(row=0, column=column, padx=4, pady=4, sticky="ew")
            self._cards[key] = card

        self._model_label = ctk.CTkLabel(
            self, text="", anchor="w", font=ctk.CTkFont(size=11), text_color=("gray40", "gray65")
        )
        self._model_label.pack(fill="x")

        self._grid = DataGrid(self)
        self._grid.pack(fill="both", expand=True, pady=(6, 0))

    # ---- actions ------------------------------------------------------------
    def _upload(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose your active loans file",
            filetypes=[("Data files", "*.csv *.tsv *.xlsx *.xls"), ("All files", "*.*")],
        )
        if not path:
            return
        self.app.toast.show("Reading file…")
        run_in_thread(
            self,
            self.app.runner.submit,
            lambda: read_table(path),
            lambda df: self._loaded(df, Path(path).name),
            self._failed,
        )

    def _load_sample(self) -> None:
        self._loaded(sample_active_loans(), "sample data (400 demo loans)")

    def _loaded(self, df: pd.DataFrame, label: str) -> None:
        self._data = df
        self._result = None
        self._file_label.configure(text=f"Loaded: {label} — now click “② Analyze Risk”.")
        self._grid.show(df, note="raw file preview")
        self.app.toast.show(f"Loaded {len(df):,} rows", "ok")

    def _analyze(self) -> None:
        if self._data is None:
            self.app.toast.show("Upload a file first (step ①)", "error")
            return
        self._analyze_btn.configure(state="disabled", text="Analyzing…")
        data = self._data
        run_in_thread(
            self, self.app.runner.submit, lambda: analyze(data), self._render, self._failed
        )

    def _render(self, result: RiskResult) -> None:
        self._analyze_btn.configure(state="normal", text="② Analyze Risk")
        self._result = result
        summary = result.summary
        self._cards["High risk"].update_value(f"{summary.high:,}", "call these first", ALERT)
        self._cards["Medium risk"].update_value(f"{summary.medium:,}", "monitor / call next", WATCH)
        self._cards["Low risk"].update_value(f"{summary.low:,}", "healthy", GOOD)
        self._cards["₹ at high risk"].update_value(
            f"₹{summary.outstanding_at_risk:,.0f}", "outstanding exposure"
        )
        self._model_label.configure(text=f"Scored by: {summary.model}")
        self._grid.show(result.frame, note="worst first", tint_by="risk_band")
        self.app.toast.show("Risk analysis complete", "ok")

    def _export(self) -> None:
        if self._result is None:
            self.app.toast.show("Analyze a file first (step ②)", "error")
            return
        default = reports_dir() / f"calling_list_{date.today().isoformat()}.xlsx"
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            initialfile=default.name,
            initialdir=str(default.parent),
            filetypes=[("Excel", "*.xlsx")],
        )
        if not path:
            return
        include_medium = bool(self._include_medium.get())
        result = self._result
        run_in_thread(
            self,
            self.app.runner.submit,
            lambda: export_calling_list(result, path, include_medium=include_medium),
            lambda p: self.app.toast.show(f"Calling list saved: {p}", "ok"),
            self._failed,
        )

    def _failed(self, exc: BaseException) -> None:
        self._analyze_btn.configure(state="normal", text="② Analyze Risk")
        self.app.toast.show(f"Something went wrong: {exc}", "error")
