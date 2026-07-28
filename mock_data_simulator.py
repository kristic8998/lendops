"""Standalone mock-data simulator for LendOps Studio.

Generates one edge-case-filled dataset per pillar so anyone can exercise
Collecta, PolicySim and KYC Sentinel without real customer data.

Run it from the repository root (no LendOps install required):

    python mock_data_simulator.py

Outputs (written to ./mock_data/):
    active_loans.xlsx        -- Collecta: scoring + calling list
    active_loans_sparse.csv  -- Collecta stress: only 3 columns present
    historical_loans.xlsx    -- PolicySim: has a defaulted outcome column
    daily_applications.xlsx  -- KYC Sentinel: planted fraud patterns

Only pandas / numpy / openpyxl are required. Seeded and reproducible.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 20260726
OUT_DIR = Path(__file__).resolve().parent / "mock_data"

NAMES = [
    "Riya Ghosh",
    "Arjun Paul",
    "Sneha Banerjee",
    "Imran Ali",
    "Tanmay Dutta",
    "Priya Sharma",
    "Sourav Mondal",
    "Ayesha Khatun",
    "Debojit Nag",
    "Mou Sinha",
]
OCCUPATIONS = ["student", "salaried", "self-employed", "gig worker"]


def build_active_loans(n: int = 250) -> pd.DataFrame:
    """Active book for Collecta — includes the severe-DPD floor test case."""
    rng = np.random.default_rng(SEED)
    amount = rng.choice([5000, 10000, 20000, 35000, 50000], n).astype(float)
    df = pd.DataFrame(
        {
            "loan_id": [f"LN{50000 + i}" for i in range(n)],
            "customer_name": rng.choice(NAMES, n),
            "phone": [f"9{rng.integers(100000000, 999999999)}" for _ in range(n)],
            "loan_amount": amount,
            "outstanding": (amount * rng.uniform(0.05, 1.0, n)).round(0),
            "dpd": rng.choice([0, 0, 0, 5, 15, 30, 45, 59, 60, 61, 90, 120], n).astype(
                float
            ),
            "missed_payments": rng.integers(0, 6, n).astype(float),
            "monthly_income": rng.choice([8000, 12000, 18000, 25000, 40000], n).astype(
                float
            ),
            "emi": (amount / 12).round(0),
            "occupation": rng.choice(OCCUPATIONS, n),
        }
    )
    # --- planted edge cases ---
    # Row 0: dpd 90 but everything else rosy -> severe-DPD floor MUST force High.
    df.loc[0, ["dpd", "missed_payments", "outstanding", "monthly_income"]] = [
        90,
        0,
        500,
        90000,
    ]
    df.loc[1, "monthly_income"] = 0.0  # zero income -> burden ratio guard
    df.loc[2, "outstanding"] = np.nan  # missing numeric
    df.loc[3, "dpd"] = np.nan  # missing DPD
    df.loc[4, "customer_name"] = "রিয়া ঘোষ"  # unicode must survive to Excel
    return df


def build_historical_loans(n: int = 300) -> pd.DataFrame:
    """Closed book for PolicySim — outcome column with BOTH classes present."""
    rng = np.random.default_rng(SEED + 1)
    amount = rng.choice([5000, 10000, 20000, 35000, 50000, 80000], n).astype(float)
    income = rng.choice([8000, 12000, 18000, 25000, 40000], n).astype(float)
    risk = (amount / (income * 6)).clip(0, 1)
    defaulted = (rng.uniform(0, 1, n) < (0.05 + 0.45 * risk)).astype(int)
    df = pd.DataFrame(
        {
            "loan_id": [f"HL{90000 + i}" for i in range(n)],
            "loan_amount": amount,
            "monthly_income": income,
            "tenure_months": rng.choice([6, 9, 12, 18, 24], n),
            "interest_rate": rng.choice([18.0, 22.0, 24.0, 28.0], n),
            "occupation": rng.choice(OCCUPATIONS, n),
            "defaulted": defaulted,
        }
    )
    df.loc[0, "interest_rate"] = np.nan  # missing rate -> 24% APR fallback path
    return df


def build_daily_applications(n: int = 80) -> pd.DataFrame:
    """Fresh applications for KYC Sentinel with planted fraud patterns."""
    rng = np.random.default_rng(SEED + 2)
    income = rng.choice([9000, 15000, 22000, 30000], n).astype(float)
    # age must be CONSISTENT with DOB (the mismatch check fires above 1.5y),
    # so generate DOB first and derive the stated age from it.
    dobs = [
        f"{rng.integers(1, 29):02d}/{rng.integers(1, 13):02d}/{rng.integers(1975, 2007)}"
        for _ in range(n)
    ]
    today = pd.Timestamp("2026-07-26")
    ages = [
        float(int((today - pd.to_datetime(d, dayfirst=True)).days / 365.25))
        for d in dobs
    ]
    df = pd.DataFrame(
        {
            "application_id": [f"APP{7000 + i}" for i in range(n)],
            "applicant_name": rng.choice(NAMES, n),
            "date_of_birth": dobs,
            "age": ages,
            "pan_number": [f"ABCDE{rng.integers(1000, 9999)}F" for _ in range(n)],
            "bank_account": [f"ACC{rng.integers(10**9, 10**10)}" for _ in range(n)],
            "phone": [f"9{rng.integers(100000000, 999999999)}" for _ in range(n)],
            "monthly_income": income,
            "requested_amount": (income * rng.uniform(0.5, 4.0, n)).round(0),
        }
    )
    # --- planted fraud (documented so testers know what MUST be flagged) ---
    df.loc[0, "bank_account"] = df.loc[1, "bank_account"]  # shared account,
    df.loc[0, "applicant_name"] = "Riya Ghosh"  # ...different names
    df.loc[1, "applicant_name"] = "Imran Ali"  # -> ALERT (mule)
    df.loc[2, "date_of_birth"] = "15/03/2010"  # underage -> ALERT
    df.loc[2, "age"] = 22.0  # + age/DOB mismatch
    df.loc[3, "pan_number"] = "AB123CD45"  # invalid PAN -> watch
    df.loc[4, "requested_amount"] = df.loc[4, "monthly_income"] * 25  # absurd ask
    df.loc[5, "phone"] = df.loc[6, "phone"]  # shared phone -> watch
    df.loc[7, "bank_account"] = ""  # missing critical field
    return df


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    frames = {
        "active_loans.xlsx": build_active_loans(),
        "historical_loans.xlsx": build_historical_loans(),
        "daily_applications.xlsx": build_daily_applications(),
    }
    for filename, frame in frames.items():
        with pd.ExcelWriter(OUT_DIR / filename, engine="openpyxl") as writer:
            frame.to_excel(writer, sheet_name="Data", index=False)
    sparse = build_active_loans().loc[:, ["loan_id", "customer_name", "dpd"]]
    sparse.to_csv(OUT_DIR / "active_loans_sparse.csv", index=False)

    print("Mock data written to:", OUT_DIR)
    for filename, frame in frames.items():
        print(f"  {filename:<26} {len(frame)} rows")
    print(f"  active_loans_sparse.csv    {len(sparse)} rows (3 columns only)")
    print("Next: open LendOps Studio and upload these on the matching pages.")


if __name__ == "__main__":
    main()
