"""Shared tabular helpers: forgiving file reading and column detection.

Laymen upload files with wildly varying headers ("DPD", "days_past_due",
"Overdue Days"…). ``find_col`` resolves a column by hints — exact match
first, then substring — so every engine works on real-world files
without any configuration screens.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd


def read_table(path: str | Path) -> pd.DataFrame:
    """Read a CSV/TSV/Excel file into a DataFrame."""
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix in (".csv", ".txt"):
        return pd.read_csv(p)
    if suffix == ".tsv":
        return pd.read_csv(p, sep="\t")
    if suffix in (".xlsx", ".xls"):
        return pd.read_excel(p)
    raise ValueError(f"unsupported file type: {suffix or p.name} (use a CSV or Excel file)")


def find_col(frame: pd.DataFrame, hints: tuple[str, ...]) -> str | None:
    """First column whose name matches a hint (exact match wins over contains)."""
    lowered = {str(c).strip().lower(): str(c) for c in frame.columns}
    for hint in hints:
        if hint in lowered:
            return lowered[hint]
    for hint in hints:
        for low, original in lowered.items():
            if hint in low:
                return original
    return None


def num_series(frame: pd.DataFrame, column: str | None) -> pd.Series:
    """Numeric view of a column (0.0 where missing/invalid); all zeros if absent."""
    if column is None:
        return pd.Series(0.0, index=frame.index)
    return parse_amount_series(frame[column]).fillna(0.0)


def text_series(frame: pd.DataFrame, column: str | None) -> pd.Series:
    """Stripped string view of a column ('' where missing); all '' if absent."""
    if column is None:
        return pd.Series("", index=frame.index)
    return frame[column].fillna("").astype(str).str.strip()


# ---- robust money/number coercion (the ONE money parser for this app) --------
# Real exports write amounts as text: "Rs 1,20,000.00", "INR 2,500", "(2,500)"
# accounting negatives, "1,250.00 Cr" / "500 Dr" banker suffixes and "24%".
# Plain to_numeric coerces all of these to NaN -> 0 in a report: silent,
# plausible, wrong. Identifiers ("LN50021") and prose stay NaN on purpose.
_CURRENCY_PREFIX = re.compile(
    r"^(?:rs\.?|inr|npr|bdt|usd|eur|gbp|[\u20b9$\u20ac\u00a3\u20a8])\s*(?=[\d(.\-+])",
    re.IGNORECASE,
)
_CRDR_SUFFIX = re.compile(r"\s*(cr|dr)\.?$", re.IGNORECASE)
_ALLOWED_RESIDUE = re.compile(r"^[+-]?\d*(?:\.\d+)?$")


def parse_amount(value: object) -> float:
    """Best-effort conversion of one cell to ``float`` (NaN when not a number)."""
    if value is None or isinstance(value, bool):
        return float("nan")
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value)
    text = str(value).strip()
    if not text or not any(ch.isdigit() for ch in text):
        return float("nan")
    negative = False
    suffix = _CRDR_SUFFIX.search(text)
    if suffix:  # banker suffix comes outermost: "(300) Cr", "500 Dr"
        if suffix.group(1).lower() == "dr":
            negative = not negative
        text = text[: suffix.start()].strip()
    if text.startswith("(") and text.endswith(")"):  # accounting negative
        negative, text = not negative, text[1:-1].strip()
    text = _CURRENCY_PREFIX.sub("", text)
    if text.endswith("%"):
        text = text[:-1].strip()
    text = text.replace(",", "").replace(" ", "").replace("_", "")
    if not _ALLOWED_RESIDUE.match(text):
        return float("nan")  # letters left over -> an identifier, not an amount
    try:
        number = float(text)
    except ValueError:
        return float("nan")
    return -number if negative else number


def parse_amount_series(series: pd.Series) -> pd.Series:
    """Vectorised :func:`parse_amount` with a fast path for numeric columns."""
    if pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series):
        return series.astype(float)
    return series.map(parse_amount).astype(float)
