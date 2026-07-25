"""Collecta — delinquency prediction and calling-list generation.

Pure pandas/scikit-learn, no UI. :func:`analyze` scores every active
loan 0–100 for delinquency risk:

* **Weighted rules (default):** days past due, recent missed payments,
  EMI burden vs income, outstanding utilisation, and a small student-
  segment adjustment — fully transparent.
* **Logistic regression (automatic upgrade):** if the file carries an
  outcome column (e.g. ``defaulted`` from a past cycle) with both
  classes and ≥30 rows, a model is trained *on that file* so scores
  reflect the caller's own book.

Every row also gets a human-readable ``top_risk_driver`` so a
collections agent knows *why* they are calling.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .tabular import find_col, num_series, text_series

WEIGHTS = {"dpd": 0.40, "missed": 0.25, "burden": 0.20, "util": 0.10, "student": 0.05}

_REASON_TEXT = {
    "dpd": "already past due",
    "missed": "recent missed payments",
    "burden": "EMI is heavy vs income",
    "util": "high outstanding balance",
    "student": "student segment",
}

_TRUTHY = {"1", "y", "yes", "true", "default", "defaulted", "npa", "bad", "charged_off"}


@dataclass
class RiskSummary:
    total: int
    high: int
    medium: int
    low: int
    outstanding_at_risk: float
    model: str

    def as_text(self) -> str:
        return (
            f"{self.total:,} loans scored · {self.high:,} high / {self.medium:,} medium / "
            f"{self.low:,} low risk · ₹{self.outstanding_at_risk:,.0f} outstanding at high risk "
            f"· scored by {self.model}"
        )


@dataclass
class RiskResult:
    frame: pd.DataFrame  # original columns + risk_score / risk_band / top_risk_driver
    summary: RiskSummary

    def calling_frame(self, include_medium: bool = True) -> pd.DataFrame:
        bands = ("High", "Medium") if include_medium else ("High",)
        return self.frame[self.frame["risk_band"].isin(bands)]


def _truthy(series: pd.Series) -> pd.Series:
    text = series.fillna("").astype(str).str.strip().str.lower()
    return text.isin(_TRUTHY).astype(int)


def _safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """numerator/denominator with 0 where the denominator is not positive."""
    out = np.where(denominator > 0, numerator / denominator.where(denominator > 0, 1.0), 0.0)
    return pd.Series(out, index=numerator.index)


def analyze(
    frame: pd.DataFrame,
    *,
    high_threshold: float = 60.0,
    medium_threshold: float = 35.0,
) -> RiskResult:
    """Score every loan; returns the scored frame + a summary."""
    if frame is None or frame.empty:
        raise ValueError("the file has no rows to analyze")
    df = frame.copy()
    df.columns = [str(c).strip() for c in df.columns]

    dpd = num_series(df, find_col(df, ("dpd", "past_due", "overdue")))
    missed = num_series(df, find_col(df, ("missed", "late", "bounce")))
    income = num_series(df, find_col(df, ("income", "salary")))
    emi = num_series(df, find_col(df, ("emi", "installment", "instalment", "repayment")))
    outstanding = num_series(df, find_col(df, ("outstanding", "balance")))
    amount = num_series(df, find_col(df, ("loan_amount", "principal", "amount", "disbursed")))
    segment = text_series(
        df, find_col(df, ("segment", "occupation", "employment", "profile"))
    ).str.lower()

    factors = pd.DataFrame(
        {
            "dpd": (dpd / 60.0).clip(0.0, 1.0),
            "missed": (missed / 4.0).clip(0.0, 1.0),
            "burden": (_safe_ratio(emi, income) / 0.6).clip(0.0, 1.0),
            "util": _safe_ratio(outstanding, amount).clip(0.0, 1.0),
            "student": segment.str.contains("student").astype(float),
        },
        index=df.index,
    )
    contributions = pd.DataFrame({k: WEIGHTS[k] * factors[k] for k in WEIGHTS}, index=df.index)
    score = (100.0 * contributions.sum(axis=1)).clip(0.0, 100.0)
    # Severe delinquency floor: 60+ days past due is high risk regardless of
    # what the other columns say (or whether they exist at all).
    score = score.where(dpd < 60, other=score.clip(lower=75.0))
    model_used = "weighted risk rules"

    label_col = find_col(df, ("defaulted", "default", "npa", "charged_off", "bad_loan"))
    if label_col is not None:
        y = _truthy(df[label_col])
        if 0 < int(y.sum()) < len(y) and len(df) >= 30:
            from sklearn.linear_model import LogisticRegression

            model = LogisticRegression(max_iter=1000)
            model.fit(factors.to_numpy(), y.to_numpy())
            score = pd.Series(model.predict_proba(factors.to_numpy())[:, 1] * 100.0, index=df.index)
            model_used = f"logistic regression (trained on this file's '{label_col}' column)"

    band = pd.Series(
        np.select(
            [score >= high_threshold, score >= medium_threshold],
            ["High", "Medium"],
            default="Low",
        ),
        index=df.index,
    )
    driver = contributions.idxmax(axis=1).map(_REASON_TEXT)
    driver[contributions.max(axis=1) < 0.05] = "no single strong risk driver"

    out = df.copy()
    out["risk_score"] = score.round(1)
    out["risk_band"] = band
    out["top_risk_driver"] = driver
    out = out.sort_values("risk_score", ascending=False).reset_index(drop=True)

    summary = RiskSummary(
        total=len(out),
        high=int((band == "High").sum()),
        medium=int((band == "Medium").sum()),
        low=int((band == "Low").sum()),
        outstanding_at_risk=float(outstanding[band == "High"].sum()),
        model=model_used,
    )
    return RiskResult(frame=out, summary=summary)


def export_calling_list(
    result: RiskResult, path: str | Path, *, include_medium: bool = True
) -> Path:
    """Write the collections workbook: Calling List / All Loans Scored / Summary."""
    out = Path(path)
    calls = result.calling_frame(include_medium=include_medium)
    summary = pd.DataFrame(
        {
            "metric": [
                "Loans scored",
                "High risk",
                "Medium risk",
                "Low risk",
                "Outstanding at high risk",
                "Scoring model",
                "Calling list size",
            ],
            "value": [
                result.summary.total,
                result.summary.high,
                result.summary.medium,
                result.summary.low,
                round(result.summary.outstanding_at_risk, 2),
                result.summary.model,
                len(calls),
            ],
        }
    )
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        calls.to_excel(writer, sheet_name="Calling List", index=False)
        result.frame.to_excel(writer, sheet_name="All Loans Scored", index=False)
        summary.to_excel(writer, sheet_name="Summary", index=False)
    return out
