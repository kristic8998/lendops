"""Deterministic sample data for demos, tests, and the self-test.

Every page has a "Try with sample data" button backed by these
generators, so a layman can experience each module in one click before
touching their own files. Seeded — identical output on every machine.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

_FIRST = [
    "Aarav",
    "Isha",
    "Rohan",
    "Priya",
    "Kabir",
    "Ananya",
    "Dev",
    "Meera",
    "Arjun",
    "Sana",
    "Vikram",
    "Tara",
    "Nikhil",
    "Zoya",
    "Rahul",
    "Divya",
]
_LAST = ["Sharma", "Patel", "Iyer", "Khan", "Das", "Nair", "Gupta", "Bose", "Rao", "Singh"]


def _names(rng: np.random.Generator, n: int) -> list[str]:
    return [f"{rng.choice(_FIRST)} {rng.choice(_LAST)}" for _ in range(n)]


def _phones(rng: np.random.Generator, n: int) -> list[str]:
    return [f"9{rng.integers(10**8, 10**9 - 1)}" for _ in range(n)]


def sample_active_loans(n: int = 400, seed: int = 42) -> pd.DataFrame:
    """Active loan book for Collecta (no outcome column → rules scoring)."""
    rng = np.random.default_rng(seed)
    segment = rng.choice(["student", "salaried"], size=n, p=[0.45, 0.55])
    income = np.where(
        segment == "student",
        rng.normal(16_000, 4_000, n),
        rng.normal(45_000, 12_000, n),
    ).clip(6_000, 120_000)
    amount = (income * rng.uniform(0.5, 3.0, n)).clip(5_000, 90_000).round(-2)
    tenure = rng.choice([3, 6, 9, 12, 18, 24], size=n)
    emi = (amount * 1.12 / tenure).round(0)
    outstanding = (amount * rng.uniform(0.05, 1.0, n)).round(0)
    dpd = np.where(rng.random(n) < 0.72, 0, rng.integers(1, 120, n))
    missed = rng.poisson(0.35, n) + (dpd > 30).astype(int) + (dpd > 60).astype(int)
    return pd.DataFrame(
        {
            "loan_id": [f"L{i:05d}" for i in range(1, n + 1)],
            "customer_name": _names(rng, n),
            "phone": _phones(rng, n),
            "segment": segment,
            "monthly_income": income.round(0),
            "loan_amount": amount,
            "outstanding": outstanding,
            "emi": emi,
            "tenure_months": tenure,
            "current_dpd": dpd,
            "missed_payments_3m": missed,
        }
    )


def sample_historical_loans(n: int = 800, seed: int = 7) -> pd.DataFrame:
    """Closed-book history for PolicySim (includes the `defaulted` outcome)."""
    rng = np.random.default_rng(seed)
    segment = rng.choice(["student", "salaried"], size=n, p=[0.4, 0.6])
    income = np.where(
        segment == "student",
        rng.normal(15_000, 5_000, n),
        rng.normal(42_000, 14_000, n),
    ).clip(4_000, 150_000)
    amount = (income * rng.uniform(0.4, 6.0, n)).clip(5_000, 200_000).round(-2)
    rate = rng.uniform(18, 36, n).round(1)
    tenure = rng.choice([3, 6, 9, 12, 18, 24], size=n)
    # Default risk rises with loan-to-income and is a bit higher for students.
    lti = amount / income
    logits = -4.2 + 0.62 * lti + 0.5 * (segment == "student")
    p_default = 1 / (1 + np.exp(-logits))
    defaulted = (rng.random(n) < p_default).astype(int)
    return pd.DataFrame(
        {
            "loan_id": [f"H{i:05d}" for i in range(1, n + 1)],
            "segment": segment,
            "monthly_income": income.round(0),
            "loan_amount": amount,
            "interest_rate": rate,
            "tenure_months": tenure,
            "defaulted": defaulted,
        }
    )


def sample_daily_applications(n: int = 120, seed: int = 11) -> pd.DataFrame:
    """Daily application batch for KYC Sentinel, with injected fraud patterns."""
    rng = np.random.default_rng(seed)
    letters = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

    def pan() -> str:
        return (
            "".join(rng.choice(letters, 5))
            + f"{rng.integers(0, 9999):04d}"
            + str(rng.choice(letters))
        )

    names = _names(rng, n)
    ages = rng.integers(19, 34, n)
    today = pd.Timestamp.today().normalize()
    dob = [
        (today - pd.DateOffset(years=int(a), days=int(rng.integers(30, 330)))).date().isoformat()
        for a in ages
    ]
    income = rng.normal(28_000, 9_000, n).clip(8_000, 90_000).round(0)
    requested = (income * rng.uniform(0.5, 6.0, n)).round(-2)
    df = pd.DataFrame(
        {
            "application_id": [f"A{i:04d}" for i in range(1, n + 1)],
            "applicant_name": names,
            "dob": dob,
            "age": ages,
            "pan": [pan() for _ in range(n)],
            "bank_account": [f"{rng.integers(10**10, 10**11 - 1)}" for _ in range(n)],
            "phone": _phones(rng, n),
            "email": [f"user{i}@mail.example" for i in range(1, n + 1)],
            "monthly_income": income,
            "requested_amount": requested,
        }
    )

    # ---- inject fraud patterns (positions are stable thanks to the seed; each
    # injection is skipped gracefully when n is too small to hold it) ----------
    def has(*positions: int) -> bool:
        return all(p < n for p in positions)

    if has(5, 17):
        df.loc[17, "bank_account"] = df.loc[5, "bank_account"]  # shared bank, diff names
    if has(23, 41):
        df.loc[41, "pan"] = df.loc[23, "pan"]  # shared PAN, different names
    if has(30):
        df.loc[30, "dob"] = (today - pd.DateOffset(years=16, days=100)).date().isoformat()
        df.loc[30, "age"] = 16  # underage
    if has(33):
        df.loc[33, "dob"] = (today - pd.DateOffset(years=40, days=50)).date().isoformat()
        df.loc[33, "age"] = 25  # age mismatch
    if has(44, 45):
        df.loc[[44, 45], "pan"] = ["ABC123", "12345XYZ9"]  # invalid PAN format
    if has(50, 51, 52):
        df.loc[51, "phone"] = df.loc[50, "phone"]
        df.loc[52, "phone"] = df.loc[50, "phone"]  # phone shared by 3 apps
    if has(60):
        df.loc[60, "requested_amount"] = float(df.loc[60, "monthly_income"]) * 30  # absurd ask
    if has(70, 71):
        df.loc[70, "bank_account"] = ""  # missing critical fields
        df.loc[71, "phone"] = ""
    return df


def write_sample_files(directory: str | Path) -> list[Path]:
    """Write the three sample CSVs (shipped in the repo's sample_data/)."""
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=True)
    written = []
    for name, frame in (
        ("active_loans.csv", sample_active_loans()),
        ("historical_loans.csv", sample_historical_loans()),
        ("daily_applications.csv", sample_daily_applications()),
    ):
        path = target / name
        frame.to_csv(path, index=False)
        written.append(path)
    return written
