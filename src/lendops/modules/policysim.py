"""PolicySim — backtest hypothetical credit rules on a historical book.

Pure pandas, no UI. The historical file must contain an outcome column
(e.g. ``defaulted``); each rule declines a slice of the historical
applicants, and the engine compares the *actual* portfolio (everything
that was really booked) with the *simulated* one (only what the new
rules would have approved).

Economics are simple and stated openly (see ``SimulationResult.assumptions``):
flat interest = amount × APR × (tenure/12); defaulters pay a fraction of
their scheduled interest before defaulting and lose a fraction of
principal (loss-given-default). It is a directional what-if tool, not an
accounting system.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .tabular import find_col, num_series, text_series

_DEFAULT_APR = 24.0
_DEFAULT_TENURE_MONTHS = 12.0
_TRUTHY = {"1", "y", "yes", "true", "default", "defaulted", "npa", "bad", "charged_off"}


@dataclass(frozen=True)
class PolicyRules:
    """The hypothetical lending policy being tested. ``None`` = rule off."""

    max_loan_amount: float | None = None
    min_monthly_income: float | None = None
    max_loan_to_income: float | None = None  # amount must be <= ratio × monthly income
    exclude_students: bool = False
    interest_rate_pct: float | None = None  # override APR on the simulated book


@dataclass
class PortfolioMetrics:
    loans: int
    disbursed: float
    interest_income: float
    default_losses: float
    net_profit: float
    default_rate_pct: float


@dataclass
class SimulationResult:
    actual: PortfolioMetrics
    simulated: PortfolioMetrics
    approved: int
    declined: int
    approval_rate_pct: float
    frame: pd.DataFrame  # original columns + simulated_decision / decline_reason
    assumptions: str

    @property
    def profit_delta(self) -> float:
        return self.simulated.net_profit - self.actual.net_profit


def simulate(
    frame: pd.DataFrame,
    rules: PolicyRules,
    *,
    loss_given_default: float = 0.65,
    default_interest_fraction: float = 0.5,
) -> SimulationResult:
    """Replay the historical book under ``rules`` and compare outcomes."""
    if frame is None or frame.empty:
        raise ValueError("the file has no rows to simulate")
    df = frame.copy()
    df.columns = [str(c).strip() for c in df.columns]

    label_col = find_col(df, ("defaulted", "default", "npa", "charged_off", "bad_loan"))
    if label_col is None:
        raise ValueError(
            "the historical file needs an outcome column (e.g. 'defaulted' with yes/no) "
            "so the simulator knows how each loan actually ended"
        )
    defaulted = df[label_col].fillna("").astype(str).str.strip().str.lower().isin(
        _TRUTHY
    ) | pd.to_numeric(df[label_col], errors="coerce").fillna(0).astype(int).eq(1)

    amount = num_series(df, find_col(df, ("loan_amount", "principal", "amount", "disbursed")))
    income = num_series(df, find_col(df, ("income", "salary")))
    rate_col = find_col(df, ("interest_rate", "rate", "apr"))
    rate = num_series(df, rate_col)
    rate = rate.where(rate > 0, _DEFAULT_APR)
    tenure = num_series(df, find_col(df, ("tenure", "term", "months")))
    tenure = tenure.where(tenure > 0, _DEFAULT_TENURE_MONTHS)
    segment = text_series(
        df, find_col(df, ("segment", "occupation", "employment", "profile"))
    ).str.lower()

    # ---- apply rules: first failing rule wins as the decline reason --------
    reason = pd.Series("", index=df.index)

    def decline(mask: pd.Series, text: str) -> None:
        reason.loc[(reason == "") & mask] = text

    if rules.max_loan_amount is not None:
        decline(amount > rules.max_loan_amount, f"loan above cap ₹{rules.max_loan_amount:,.0f}")
    if rules.min_monthly_income is not None:
        decline(
            income < rules.min_monthly_income,
            f"income below ₹{rules.min_monthly_income:,.0f}/month",
        )
    if rules.max_loan_to_income is not None:
        decline(
            (income <= 0) | (amount > rules.max_loan_to_income * income),
            f"loan above {rules.max_loan_to_income:g}× monthly income",
        )
    if rules.exclude_students:
        decline(segment.str.contains("student"), "student segment excluded")

    approved = reason == ""

    # ---- portfolio economics ----------------------------------------------
    def metrics(mask: pd.Series, rate_series: pd.Series) -> PortfolioMetrics:
        n = int(mask.sum())
        if n == 0:
            return PortfolioMetrics(0, 0.0, 0.0, 0.0, 0.0, 0.0)
        amt = amount[mask]
        scheduled = amt * (rate_series[mask] / 100.0) * (tenure[mask] / 12.0)
        bad = defaulted[mask]
        earned = np.where(bad, default_interest_fraction * scheduled, scheduled)
        losses = np.where(bad, loss_given_default * amt, 0.0)
        return PortfolioMetrics(
            loans=n,
            disbursed=float(amt.sum()),
            interest_income=float(earned.sum()),
            default_losses=float(losses.sum()),
            net_profit=float(earned.sum() - losses.sum()),
            default_rate_pct=float(100.0 * bad.mean()),
        )

    everything = pd.Series(True, index=df.index)
    actual = metrics(everything, rate)
    sim_rate = (
        rate
        if rules.interest_rate_pct is None
        else pd.Series(rules.interest_rate_pct, index=df.index)
    )
    simulated = metrics(approved, sim_rate)

    out = df.copy()
    out["simulated_decision"] = np.where(approved, "Approve", "Decline")
    out["decline_reason"] = reason

    notes = [
        f"Flat interest: amount × APR × (tenure/12); defaulters assumed to pay "
        f"{default_interest_fraction:.0%} of scheduled interest and lose "
        f"{loss_given_default:.0%} of principal.",
    ]
    if rate_col is None:
        notes.append(f"No interest-rate column found — assumed {_DEFAULT_APR:.0f}% APR.")
    if rules.interest_rate_pct is not None:
        notes.append(f"Simulated book repriced to {rules.interest_rate_pct:g}% APR.")

    return SimulationResult(
        actual=actual,
        simulated=simulated,
        approved=int(approved.sum()),
        declined=int((~approved).sum()),
        approval_rate_pct=float(100.0 * approved.mean()),
        frame=out,
        assumptions=" ".join(notes),
    )


def export_simulation(result: SimulationResult, path: str | Path) -> Path:
    """Write the what-if workbook: Comparison / Declined Loans / All Decisions."""
    out = Path(path)
    rows = []
    for name, a, s in (
        ("Loans booked", result.actual.loans, result.simulated.loans),
        ("Disbursed", result.actual.disbursed, result.simulated.disbursed),
        ("Interest income", result.actual.interest_income, result.simulated.interest_income),
        ("Default losses", result.actual.default_losses, result.simulated.default_losses),
        ("Net profit", result.actual.net_profit, result.simulated.net_profit),
        ("Default rate %", result.actual.default_rate_pct, result.simulated.default_rate_pct),
    ):
        rows.append(
            {
                "metric": name,
                "actual": round(float(a), 2),
                "with_rules": round(float(s), 2),
                "change": round(float(s) - float(a), 2),
            }
        )
    comparison = pd.DataFrame(rows)
    declined = result.frame[result.frame["simulated_decision"] == "Decline"]
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        comparison.to_excel(writer, sheet_name="Comparison", index=False)
        declined.to_excel(writer, sheet_name="Declined Loans", index=False)
        result.frame.to_excel(writer, sheet_name="All Decisions", index=False)
    return out
