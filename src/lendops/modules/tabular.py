"""Shared tabular helpers: forgiving file reading and column detection.

Laymen upload files with wildly varying headers ("DPD", "days_past_due",
"Overdue Days"…). ``find_col`` resolves a column by hints — exact match
first, then substring — so every engine works on real-world files
without any configuration screens.
"""

from __future__ import annotations

from pathlib import Path

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
    return pd.to_numeric(frame[column], errors="coerce").fillna(0.0).astype(float)


def text_series(frame: pd.DataFrame, column: str | None) -> pd.Series:
    """Stripped string view of a column ('' where missing); all '' if absent."""
    if column is None:
        return pd.Series("", index=frame.index)
    return frame[column].fillna("").astype(str).str.strip()
