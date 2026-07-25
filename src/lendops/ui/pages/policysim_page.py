"""PolicySim page: set hypothetical rules with sliders → run → compare P&L."""

from __future__ import annotations

import tkinter as tk
from datetime import date
from tkinter import filedialog

import customtkinter as ctk
import pandas as pd

from ...core.demo import sample_historical_loans
from ...core.paths import reports_dir
from ...modules.policysim import PolicyRules, SimulationResult, export_simulation, simulate
from ...modules.tabular import read_table
from ..widgets import ALERT, GOOD, DataGrid, HelperCard, Section, run_in_thread


class _RuleSlider:
    """A checkbox-gated slider with a live value label (layman-friendly rule input)."""

    def __init__(
        self,
        parent: tk.Misc,
        text: str,
        low: float,
        high: float,
        initial: float,
        fmt,  # noqa: ANN001 - callable(float) -> str
        steps: int = 100,
    ) -> None:
        self._fmt = fmt
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=3)
        self.checkbox = ctk.CTkCheckBox(row, text=text, width=260, command=self._toggle)
        self.checkbox.pack(side="left")
        self.slider = ctk.CTkSlider(
            row, from_=low, to=high, number_of_steps=steps, command=self._moved, width=280
        )
        self.slider.set(initial)
        self.slider.pack(side="left", padx=10)
        self.value_label = ctk.CTkLabel(row, text=fmt(initial), width=120, anchor="w")
        self.value_label.pack(side="left")
        self._toggle()

    def _moved(self, value: float) -> None:
        self.value_label.configure(text=self._fmt(value))

    def _toggle(self) -> None:
        state = "normal" if self.checkbox.get() else "disabled"
        self.slider.configure(state=state)

    def value(self) -> float | None:
        return float(self.slider.get()) if self.checkbox.get() else None


class PolicySimPage(ctk.CTkFrame):
    def __init__(self, master: tk.Misc, app) -> None:  # noqa: ANN001
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._data: pd.DataFrame | None = None
        self._result: SimulationResult | None = None

        ctk.CTkLabel(
            self,
            text="PolicySim — Credit Rule Backtesting",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            self,
            text="Ask “what if we had lent with stricter rules?” — replay your historical book "
            "under hypothetical rules and see the profit and default-rate impact before "
            "changing policy for real.",
            font=ctk.CTkFont(size=12),
            text_color=("gray35", "gray65"),
        ).pack(anchor="w", pady=(0, 8))

        HelperCard(
            self,
            "How to use",
            (
                "Upload your historical loans file (must include how each loan ended, "
                "e.g. a “defaulted” yes/no column) — or click “Try with sample data”.",
                "Tick the rules you want to test and drag the sliders. Unticked rules are off.",
                "Click “Run Simulation”. The table compares the real book with the "
                "rule-filtered one; “Export Report” saves the full comparison to Excel.",
            ),
        ).pack(fill="x", pady=(0, 8))

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        top = ctk.CTkFrame(scroll, fg_color="transparent")
        top.pack(fill="x")
        ctk.CTkButton(
            top, text="Upload Historical Loans…", width=200, height=34, command=self._upload
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            top,
            text="Try with sample data",
            width=160,
            height=34,
            fg_color="transparent",
            border_width=1,
            text_color=("gray15", "gray90"),
            command=self._load_sample,
        ).pack(side="left")
        self._file_label = ctk.CTkLabel(
            top, text="No file loaded yet.", anchor="w", text_color=("gray35", "gray65")
        )
        self._file_label.pack(side="left", padx=12)

        rules = Section(scroll, "Rules to test (tick to enable)")
        rules.pack(fill="x", pady=(8, 0))
        rupee = lambda v: f"₹{v:,.0f}"  # noqa: E731
        self._max_amount = _RuleSlider(
            rules.body, "Cap loan amount at", 5_000, 200_000, 50_000, rupee, steps=195
        )
        self._min_income = _RuleSlider(
            rules.body,
            "Require monthly income of at least",
            5_000,
            100_000,
            15_000,
            rupee,
            steps=95,
        )
        self._max_lti = _RuleSlider(
            rules.body, "Cap loan at N × monthly income", 1, 12, 4, lambda v: f"{v:,.0f}×", steps=11
        )
        self._rate = _RuleSlider(
            rules.body,
            "Re-price interest rate (APR) to",
            6,
            48,
            24,
            lambda v: f"{v:,.0f}%",
            steps=42,
        )
        self._exclude_students = ctk.CTkCheckBox(rules.body, text="Exclude the student segment")
        self._exclude_students.pack(anchor="w", pady=3)

        actions = ctk.CTkFrame(scroll, fg_color="transparent")
        actions.pack(fill="x", pady=(8, 0))
        self._run_btn = ctk.CTkButton(
            actions, text="▶ Run Simulation", width=170, height=36, command=self._run
        )
        self._run_btn.pack(side="left")
        ctk.CTkButton(
            actions,
            text="Export Report…",
            width=150,
            height=36,
            fg_color="transparent",
            border_width=1,
            text_color=("gray15", "gray90"),
            command=self._export,
        ).pack(side="left", padx=8)
        self._headline = ctk.CTkLabel(
            actions, text="", anchor="w", font=ctk.CTkFont(size=13, weight="bold")
        )
        self._headline.pack(side="left", padx=12)

        compare = Section(scroll, "Actual book  vs  with your rules")
        compare.pack(fill="x", pady=(8, 0))
        self._table = ctk.CTkFrame(compare.body, fg_color="transparent")
        self._table.pack(fill="x")
        self._assumptions = ctk.CTkLabel(
            compare.body,
            text="",
            anchor="w",
            justify="left",
            wraplength=1050,
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray65"),
        )
        self._assumptions.pack(fill="x", pady=(6, 0))

        declined = Section(scroll, "Loans your rules would have declined")
        declined.pack(fill="both", expand=True, pady=(8, 0))
        self._declined_grid = DataGrid(declined.body, page_size=300)
        self._declined_grid.pack(fill="both", expand=True)

    # ---- actions ------------------------------------------------------------
    def _upload(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose your historical loans file",
            filetypes=[("Data files", "*.csv *.tsv *.xlsx *.xls"), ("All files", "*.*")],
        )
        if not path:
            return
        self.app.toast.show("Reading file…")
        run_in_thread(
            self,
            self.app.runner.submit,
            lambda: read_table(path),
            lambda df: self._loaded(df, path.rsplit("/", 1)[-1]),
            self._failed,
        )

    def _load_sample(self) -> None:
        self._loaded(sample_historical_loans(), "sample data (800 closed loans)")

    def _loaded(self, df: pd.DataFrame, label: str) -> None:
        self._data = df
        self._result = None
        self._file_label.configure(text=f"Loaded: {label} ({len(df):,} loans)")
        self.app.toast.show(f"Loaded {len(df):,} rows", "ok")

    def _rules(self) -> PolicyRules:
        return PolicyRules(
            max_loan_amount=self._max_amount.value(),
            min_monthly_income=self._min_income.value(),
            max_loan_to_income=self._max_lti.value(),
            exclude_students=bool(self._exclude_students.get()),
            interest_rate_pct=self._rate.value(),
        )

    def _run(self) -> None:
        if self._data is None:
            self.app.toast.show("Upload a historical file first", "error")
            return
        self._run_btn.configure(state="disabled", text="Simulating…")
        data, rules = self._data, self._rules()
        run_in_thread(
            self, self.app.runner.submit, lambda: simulate(data, rules), self._render, self._failed
        )

    def _render(self, result: SimulationResult) -> None:
        self._run_btn.configure(state="normal", text="▶ Run Simulation")
        self._result = result
        delta = result.profit_delta
        pct = (100.0 * delta / abs(result.actual.net_profit)) if result.actual.net_profit else 0.0
        self._headline.configure(
            text=(
                f"Net profit impact: {'+' if delta >= 0 else '−'}₹{abs(delta):,.0f} "
                f"({pct:+.1f}%) · rules approve {result.approval_rate_pct:.0f}% of applicants"
            ),
            text_color=GOOD if delta >= 0 else ALERT,
        )

        for child in self._table.winfo_children():
            child.destroy()
        headers = ("Metric", "Actual book", "With your rules", "Change")
        for column, header in enumerate(headers):
            self._table.grid_columnconfigure(column, weight=1)
            ctk.CTkLabel(
                self._table, text=header, font=ctk.CTkFont(size=12, weight="bold"), anchor="w"
            ).grid(row=0, column=column, sticky="w", padx=8, pady=2)
        rows = (
            ("Loans booked", "{:,.0f}", result.actual.loans, result.simulated.loans),
            ("Disbursed", "₹{:,.0f}", result.actual.disbursed, result.simulated.disbursed),
            (
                "Interest income",
                "₹{:,.0f}",
                result.actual.interest_income,
                result.simulated.interest_income,
            ),
            (
                "Default losses",
                "₹{:,.0f}",
                result.actual.default_losses,
                result.simulated.default_losses,
            ),
            ("Net profit", "₹{:,.0f}", result.actual.net_profit, result.simulated.net_profit),
            (
                "Default rate",
                "{:,.1f}%",
                result.actual.default_rate_pct,
                result.simulated.default_rate_pct,
            ),
        )
        for r, (label, fmt, actual, simulated) in enumerate(rows, start=1):
            bold = label == "Net profit"
            font = ctk.CTkFont(size=12, weight="bold" if bold else "normal")
            change = simulated - actual
            for column, text in enumerate(
                (label, fmt.format(actual), fmt.format(simulated), f"{change:+,.0f}")
            ):
                ctk.CTkLabel(self._table, text=text, font=font, anchor="w").grid(
                    row=r, column=column, sticky="w", padx=8, pady=1
                )
        self._assumptions.configure(text=f"Assumptions: {result.assumptions}")
        declined = result.frame[result.frame["simulated_decision"] == "Decline"]
        self._declined_grid.show(declined, note="with the first rule each loan failed")
        self.app.toast.show("Simulation complete", "ok")

    def _export(self) -> None:
        if self._result is None:
            self.app.toast.show("Run a simulation first", "error")
            return
        default = reports_dir() / f"policy_simulation_{date.today().isoformat()}.xlsx"
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
            lambda: export_simulation(result, path),
            lambda p: self.app.toast.show(f"Report saved: {p}", "ok"),
            self._failed,
        )

    def _failed(self, exc: BaseException) -> None:
        self._run_btn.configure(state="normal", text="▶ Run Simulation")
        self.app.toast.show(f"Something went wrong: {exc}", "error")
