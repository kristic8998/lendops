"""Tests for the KYC Sentinel fraud scanner."""

from __future__ import annotations

import pandas as pd
import pytest

from lendops.core.demo import sample_daily_applications
from lendops.modules.kyc import export_report, scan


def _clean_apps() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "application_id": ["A1", "A2"],
            "applicant_name": ["Asha Rao", "Bilal Khan"],
            "dob": ["1999-04-10", "1996-08-22"],
            "age": [27, 29],
            "pan": ["ABCDE1234F", "FGHIJ5678K"],
            "bank_account": ["11111111111", "22222222222"],
            "phone": ["9111111111", "9222222222"],
            "email": ["asha@mail.example", "bilal@mail.example"],
            "monthly_income": [30_000, 40_000],
            "requested_amount": [60_000, 50_000],
        }
    )


class TestChecks:
    def test_clean_file_has_no_flags(self):
        result = scan(_clean_apps())
        assert result.alerts == 0 and result.watches == 0
        assert len(result.flagged) == 0

    def test_shared_bank_account_different_names_is_alert(self):
        df = _clean_apps()
        df.loc[1, "bank_account"] = df.loc[0, "bank_account"]
        result = scan(df)
        assert result.alerts == 2
        assert "bank account" in result.check_counts

    def test_shared_bank_same_name_is_watch(self):
        df = _clean_apps()
        df.loc[1, ["applicant_name", "bank_account"]] = [
            df.loc[0, "applicant_name"],
            df.loc[0, "bank_account"],
        ]
        result = scan(df)
        flagged = result.flagged
        assert (flagged["severity"] == "watch").all()

    def test_underage_is_alert(self):
        df = _clean_apps()
        today = pd.Timestamp.today()
        df.loc[0, "dob"] = (today - pd.DateOffset(years=16)).date().isoformat()
        df.loc[0, "age"] = 16
        result = scan(df)
        assert result.alerts == 1
        assert "underage" in result.check_counts

    def test_age_mismatch_is_alert(self):
        df = _clean_apps()
        df.loc[0, "age"] = 45  # dob says ~27
        result = scan(df)
        assert result.alerts == 1
        assert "age mismatch" in result.check_counts

    def test_invalid_pan_is_watch(self):
        df = _clean_apps()
        df.loc[0, "pan"] = "NOT-A-PAN"
        result = scan(df)
        assert "invalid PAN" in result.check_counts
        assert result.watches == 1

    def test_shared_phone_is_watch(self):
        df = _clean_apps()
        df.loc[1, "phone"] = df.loc[0, "phone"]
        result = scan(df)
        assert "phone number" in result.check_counts
        assert result.alerts == 0

    def test_missing_field_is_watch(self):
        df = _clean_apps()
        df.loc[0, "bank_account"] = ""
        result = scan(df)
        assert "missing field" in result.check_counts

    def test_absurd_ask_is_watch(self):
        df = _clean_apps()
        df.loc[0, "requested_amount"] = 30_000 * 25
        result = scan(df)
        assert "income vs ask" in result.check_counts

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            scan(pd.DataFrame())


class TestSampleAndExport:
    def test_sample_data_catches_injected_fraud(self):
        result = scan(sample_daily_applications())
        for check in ("bank account", "ID number", "underage", "age mismatch", "invalid PAN"):
            assert check in result.check_counts, f"expected {check} to fire on sample data"
        assert result.alerts >= 6

    def test_alerts_sorted_first(self):
        result = scan(sample_daily_applications())
        severities = list(result.frame["severity"])
        first_watch = severities.index("watch") if "watch" in severities else len(severities)
        assert "alert" not in severities[first_watch:]

    def test_export_sheets(self, tmp_path):
        result = scan(sample_daily_applications())
        out = export_report(result, tmp_path / "kyc.xlsx")
        assert pd.ExcelFile(out).sheet_names == ["Flagged", "All Applications", "Summary"]
