"""Tests for the Collecta delinquency engine."""

from __future__ import annotations

import pandas as pd
import pytest

from lendops.core.demo import sample_active_loans
from lendops.modules.collecta import analyze, export_calling_list


def _small_book() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "loan_id": ["A", "B", "C"],
            "customer_name": ["Risky Rita", "Middling Mo", "Safe Sam"],
            "phone": ["9111111111", "9222222222", "9333333333"],
            "segment": ["student", "salaried", "salaried"],
            "monthly_income": [12_000, 40_000, 60_000],
            "loan_amount": [30_000, 30_000, 30_000],
            "outstanding": [28_000, 15_000, 2_000],
            "emi": [6_000, 3_000, 3_000],
            "current_dpd": [75, 12, 0],
            "missed_payments_3m": [3, 1, 0],
        }
    )


class TestHeuristicScoring:
    def test_orders_worst_first(self):
        result = analyze(_small_book())
        assert list(result.frame["loan_id"]) == ["A", "B", "C"]
        assert result.summary.model == "weighted risk rules"

    def test_bands_and_reasons(self):
        result = analyze(_small_book())
        worst = result.frame.iloc[0]
        assert worst["risk_band"] == "High"
        assert worst["top_risk_driver"] == "already past due"
        safest = result.frame.iloc[-1]
        assert safest["risk_band"] == "Low"

    def test_scores_bounded(self):
        result = analyze(sample_active_loans(200))
        assert result.frame["risk_score"].between(0, 100).all()
        assert result.summary.total == 200

    def test_missing_optional_columns_are_fine(self):
        df = pd.DataFrame({"loan_id": [1, 2], "current_dpd": [90, 0]})
        result = analyze(df)
        assert result.frame.iloc[0]["risk_band"] == "High"

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            analyze(pd.DataFrame())


class TestModelUpgrade:
    def test_logistic_used_when_outcome_present(self):
        rows = 60
        df = pd.DataFrame(
            {
                "current_dpd": [80] * (rows // 2) + [0] * (rows // 2),
                "missed_payments_3m": [3] * (rows // 2) + [0] * (rows // 2),
                "defaulted": [1] * (rows // 2) + [0] * (rows // 2),
            }
        )
        result = analyze(df)
        assert "logistic regression" in result.summary.model
        scored = result.frame
        bad = scored[scored["defaulted"] == 1]["risk_score"].mean()
        good = scored[scored["defaulted"] == 0]["risk_score"].mean()
        assert bad > good

    def test_small_files_stay_on_rules(self):
        df = pd.DataFrame({"current_dpd": [10, 20], "defaulted": [0, 1]})
        assert analyze(df).summary.model == "weighted risk rules"


class TestExport:
    def test_workbook_sheets(self, tmp_path):
        result = analyze(_small_book())
        out = export_calling_list(result, tmp_path / "calls.xlsx")
        assert pd.ExcelFile(out).sheet_names == ["Calling List", "All Loans Scored", "Summary"]

    def test_medium_toggle_changes_list(self, tmp_path):
        result = analyze(sample_active_loans(300))
        with_medium = result.calling_frame(include_medium=True)
        without = result.calling_frame(include_medium=False)
        assert len(without) <= len(with_medium)
        assert set(without["risk_band"]) <= {"High"}
