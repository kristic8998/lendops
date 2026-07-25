"""KYC Sentinel page: upload applications → scan for fraud → export report."""

from __future__ import annotations

import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
import pandas as pd

from ...core.demo import sample_daily_applications
from ...core.paths import reports_dir
from ...modules.kyc import KycResult, export_report, scan
from ...modules.tabular import read_table
from ..widgets import ALERT, GOOD, WATCH, DataGrid, HelperCard, KpiCard, run_in_thread


class KycPage(ctk.CTkFrame):
    def __init__(self, master: tk.Misc, app) -> None:  # noqa: ANN001
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._data: pd.DataFrame | None = None
        self._result: KycResult | None = None

        ctk.CTkLabel(
            self,
            text="KYC Sentinel — Identity Fraud Detector",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            self,
            text="Catch identity fraud before disbursal: shared bank accounts, duplicate IDs, "
            "underage applicants, age/DOB mismatches and more — in one click.",
            font=ctk.CTkFont(size=12),
            text_color=("gray35", "gray65"),
        ).pack(anchor="w", pady=(0, 8))

        HelperCard(
            self,
            "How it works",
            (
                "Click “Upload Daily Applications” and pick today’s application file "
                "(CSV or Excel). Columns like name, DOB, PAN, bank account and phone are "
                "detected automatically.",
                "Click “Scan for Fraud”. Red rows are likely fraud (call them alerts); "
                "orange rows need a manual review. The “flags” column says exactly why.",
                "Click “Export Report” to save the flagged list for the risk team.",
            ),
        ).pack(fill="x", pady=(0, 8))

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(fill="x")
        ctk.CTkButton(
            buttons,
            text="① Upload Daily Applications…",
            width=210,
            height=34,
            command=self._upload,
        ).pack(side="left", padx=(0, 6))
        self._scan_btn = ctk.CTkButton(
            buttons, text="② Scan for Fraud", width=150, height=34, command=self._scan
        )
        self._scan_btn.pack(side="left", padx=6)
        ctk.CTkButton(
            buttons, text="③ Export Report…", width=150, height=34, command=self._export
        ).pack(side="left", padx=6)
        self._flagged_only = ctk.CTkCheckBox(
            buttons, text="Show flagged rows only", command=self._refresh_grid
        )
        self._flagged_only.pack(side="left", padx=12)
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
        for column, key in enumerate(("Applications", "Fraud alerts", "To review", "Clean")):
            cards.grid_columnconfigure(column, weight=1)
            card = KpiCard(cards, key)
            card.grid(row=0, column=column, padx=4, pady=4, sticky="ew")
            self._cards[key] = card

        self._grid = DataGrid(self)
        self._grid.pack(fill="both", expand=True, pady=(6, 0))

    # ---- actions ------------------------------------------------------------
    def _upload(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose today's applications file",
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
        self._loaded(sample_daily_applications(), "sample data (120 demo applications)")

    def _loaded(self, df: pd.DataFrame, label: str) -> None:
        self._data = df
        self._result = None
        self._file_label.configure(text=f"Loaded: {label} — now click “② Scan for Fraud”.")
        self._grid.show(df, note="raw file preview")
        self.app.toast.show(f"Loaded {len(df):,} rows", "ok")

    def _scan(self) -> None:
        if self._data is None:
            self.app.toast.show("Upload a file first (step ①)", "error")
            return
        self._scan_btn.configure(state="disabled", text="Scanning…")
        data = self._data
        run_in_thread(self, self.app.runner.submit, lambda: scan(data), self._render, self._failed)

    def _render(self, result: KycResult) -> None:
        self._scan_btn.configure(state="normal", text="② Scan for Fraud")
        self._result = result
        clean = len(result.frame) - len(result.flagged)
        self._cards["Applications"].update_value(f"{len(result.frame):,}")
        self._cards["Fraud alerts"].update_value(
            f"{result.alerts:,}", "likely fraud — act now", ALERT if result.alerts else GOOD
        )
        self._cards["To review"].update_value(
            f"{result.watches:,}", "manual review", WATCH if result.watches else GOOD
        )
        self._cards["Clean"].update_value(f"{clean:,}", "no flags", GOOD)
        self._refresh_grid()
        self.app.toast.show(result.summary_text(), "ok")

    def _refresh_grid(self) -> None:
        if self._result is None:
            return
        frame = self._result.flagged if self._flagged_only.get() else self._result.frame
        self._grid.show(frame, note="alerts first — see the flags column", tint_by="severity")

    def _export(self) -> None:
        if self._result is None:
            self.app.toast.show("Scan a file first (step ②)", "error")
            return
        default = reports_dir() / f"kyc_fraud_report_{date.today().isoformat()}.xlsx"
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            initialfile=default.name,
            initialdir=str(default.parent),
            filetypes=[("Excel", "*.xlsx")],
        )
        if not path:
            return
        result = self._result
        run_in_thread(
            self,
            self.app.runner.submit,
            lambda: export_report(result, path),
            lambda p: self.app.toast.show(f"Fraud report saved: {p}", "ok"),
            self._failed,
        )

    def _failed(self, exc: BaseException) -> None:
        self._scan_btn.configure(state="normal", text="② Scan for Fraud")
        self.app.toast.show(f"Something went wrong: {exc}", "error")
