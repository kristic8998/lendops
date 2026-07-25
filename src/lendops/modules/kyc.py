"""KYC Sentinel — identity-fraud pattern detection on daily applications.

Pure pandas, no UI. :func:`scan` runs every check and annotates each
application with ``flags`` (plain-English reasons), ``flag_count`` and a
``severity`` ("alert" for likely fraud, "watch" for review-worthy).

Checks:
* same **bank account** on multiple applications — *alert* when the
  names differ (classic mule pattern), *watch* when they match
  (probable resubmission);
* same **ID / PAN** across applications — same alert/watch logic;
* same **phone** or **email** across applications — *watch*;
* **underage** applicant (<18 from DOB or stated age) — *alert*;
* **age mismatch** (stated age vs DOB differ by >1 year) — *alert*;
* **invalid PAN format** (when the ID column is a PAN) — *watch*;
* **missing critical field** (name / ID / bank / phone) — *watch*;
* **requested amount over 20× monthly income** — *watch*.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .tabular import find_col, num_series, text_series

_PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
_INCOME_MULTIPLE_CAP = 20.0


@dataclass
class KycResult:
    frame: pd.DataFrame  # original columns + flags / flag_count / severity
    flagged: pd.DataFrame
    check_counts: dict[str, int] = field(default_factory=dict)
    alerts: int = 0
    watches: int = 0

    def summary_text(self) -> str:
        clean = len(self.frame) - len(self.flagged)
        return (
            f"{len(self.frame):,} applications scanned · {self.alerts:,} alert(s), "
            f"{self.watches:,} to review · {clean:,} clean"
        )


def scan(frame: pd.DataFrame) -> KycResult:
    """Run all fraud checks; returns annotated frame + flagged subset."""
    if frame is None or frame.empty:
        raise ValueError("the file has no rows to scan")
    df = frame.copy().reset_index(drop=True)
    df.columns = [str(c).strip() for c in df.columns]

    name_col = find_col(df, ("applicant_name", "name", "applicant"))
    id_col = find_col(df, ("pan", "id_number", "aadhaar", "national_id", "document_id"))
    bank_col = find_col(df, ("bank_account", "account_number", "account", "bank"))
    phone_col = find_col(df, ("phone", "mobile", "contact"))
    email_col = find_col(df, ("email",))
    dob_col = find_col(df, ("dob", "date_of_birth", "birth"))
    age_col = find_col(df, ("age",))
    income_col = find_col(df, ("income", "salary"))
    ask_col = find_col(df, ("requested_amount", "requested", "loan_amount", "amount"))

    names = text_series(df, name_col)
    flags: list[list[tuple[str, str, str]]] = [[] for _ in range(len(df))]  # (sev, check, text)

    def add(position: int, severity: str, check: str, text: str) -> None:
        flags[position].append((severity, check, text))

    # ---- cross-row duplicates ----------------------------------------------
    def flag_shared(column: str | None, check: str, *, alert_on_name_clash: bool) -> None:
        if column is None:
            return
        values = text_series(df, column)
        mask = values.ne("") & values.duplicated(keep=False)
        for _value, group in values[mask].groupby(values[mask]):
            positions = list(group.index)
            distinct_names = names.loc[positions].str.lower().replace("", pd.NA).nunique()
            clash = alert_on_name_clash and distinct_names > 1
            severity = "alert" if clash else "watch"
            text = f"{check} shared across {len(positions)} applications" + (
                " with different names" if clash else ""
            )
            for position in positions:
                add(position, severity, check, text)

    flag_shared(bank_col, "bank account", alert_on_name_clash=True)
    flag_shared(id_col, "ID number", alert_on_name_clash=True)
    flag_shared(phone_col, "phone number", alert_on_name_clash=False)
    flag_shared(email_col, "email", alert_on_name_clash=False)

    # ---- age & DOB -----------------------------------------------------------
    stated_age = num_series(df, age_col)
    derived_age = pd.Series(float("nan"), index=df.index)
    if dob_col is not None:
        dob = pd.to_datetime(df[dob_col], errors="coerce", dayfirst=True)
        derived_age = (pd.Timestamp.today() - dob).dt.days / 365.25
    for position in df.index:
        derived = derived_age.iloc[position]
        stated = stated_age.iloc[position]
        if pd.notna(derived):
            if derived < 18:
                add(position, "alert", "underage", "applicant is under 18 (from date of birth)")
            elif stated > 0 and abs(stated - derived) > 1.5:
                add(
                    position,
                    "alert",
                    "age mismatch",
                    f"stated age {stated:.0f} but DOB implies {derived:.0f}",
                )
        elif 0 < stated < 18:
            add(position, "alert", "underage", "stated age is under 18")

    # ---- per-row field checks -------------------------------------------------
    id_is_pan = id_col is not None and "pan" in id_col.lower()
    id_values = text_series(df, id_col)
    incomes = num_series(df, income_col)
    asks = num_series(df, ask_col)
    critical = [
        (c, label)
        for c, label in (
            (name_col, "name"),
            (id_col, "ID number"),
            (bank_col, "bank account"),
            (phone_col, "phone"),
        )
        if c is not None
    ]
    for position in df.index:
        if id_is_pan:
            value = id_values.iloc[position].upper()
            if value and not _PAN_RE.match(value):
                add(position, "watch", "invalid PAN", "PAN format looks invalid")
        for column, label in critical:
            if text_series(df, column).iloc[position] == "":
                add(position, "watch", "missing field", f"missing {label}")
        if incomes.iloc[position] > 0 and asks.iloc[position] > (
            _INCOME_MULTIPLE_CAP * incomes.iloc[position]
        ):
            add(
                position,
                "watch",
                "income vs ask",
                f"requested amount is over {_INCOME_MULTIPLE_CAP:.0f}× monthly income",
            )

    # ---- assemble --------------------------------------------------------------
    out = df.copy()
    out["flags"] = ["; ".join(t for _s, _c, t in row) for row in flags]
    out["flag_count"] = [len(row) for row in flags]
    out["severity"] = [
        "alert" if any(s == "alert" for s, _c, _t in row) else ("watch" if row else "")
        for row in flags
    ]
    order = out["severity"].map({"alert": 0, "watch": 1, "": 2})
    out = (
        out.assign(_order=order)
        .sort_values(["_order", "flag_count"], ascending=[True, False])
        .drop(columns="_order")
        .reset_index(drop=True)
    )

    check_counts: dict[str, int] = {}
    for row in flags:
        for _severity, check, _text in row:
            check_counts[check] = check_counts.get(check, 0) + 1
    flagged = out[out["flag_count"] > 0].reset_index(drop=True)
    return KycResult(
        frame=out,
        flagged=flagged,
        check_counts=dict(sorted(check_counts.items(), key=lambda kv: -kv[1])),
        alerts=int((out["severity"] == "alert").sum()),
        watches=int((out["severity"] == "watch").sum()),
    )


def export_report(result: KycResult, path: str | Path) -> Path:
    """Write the fraud workbook: Flagged / All Applications / Summary."""
    out = Path(path)
    summary = pd.DataFrame(
        {
            "check": list(result.check_counts.keys()) + ["TOTAL alerts", "TOTAL to review"],
            "hits": list(result.check_counts.values()) + [result.alerts, result.watches],
        }
    )
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        result.flagged.to_excel(writer, sheet_name="Flagged", index=False)
        result.frame.to_excel(writer, sheet_name="All Applications", index=False)
        summary.to_excel(writer, sheet_name="Summary", index=False)
    return out
