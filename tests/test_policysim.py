"""Tests for the PolicySim backtesting engine."""

from __future__ import annotations

import pandas as pd
import pytest

from lendops.core.demo import sample_historical_loans
from lendops.modules.policysim import PolicyRules, export_simulation, simulate


def _history() -> pd.DataFrame:
    # Two defaulters, both low-income; two good loans, both high-income.
    return pd.DataFrame(
        {
            "loan_amount": [50_000, 40_000, 30_000, 20_000],
            "monthly_income": [8_000, 9_000, 50_000, 60_000],
            "interest_rate": [30, 30, 24, 24],
            "tenure_months": [12, 12, 12, 12],
            "segment": ["student", "student", "salaried", "salaried"],
            "defaulted": [1, 1, 0, 0],
        }
    )


class TestRules:
    def test_min_income_declines_the_defaulters(self):
        result = simulate(_history(), PolicyRules(min_monthly_income=15_000))
        assert result.approved == 2 and result.declined == 2
        declined = result.frame[result.frame["simulated_decision"] == "Decline"]
        assert (declined["defaulted"] == 1).all()
        assert "income below" in declined["decline_reason"].iloc[0]

    def test_declining_defaulters_improves_profit(self):
        result = simulate(_history(), PolicyRules(min_monthly_income=15_000))
        assert result.simulated.net_profit > result.actual.net_profit
        assert result.simulated.default_rate_pct == 0.0

    def test_no_rules_means_everyone_approved(self):
        result = simulate(_history(), PolicyRules())
        assert result.approved == 4 and result.declined == 0
        assert result.simulated.net_profit == pytest.approx(result.actual.net_profit)

    def test_exclude_students(self):
        result = simulate(_history(), PolicyRules(exclude_students=True))
        assert result.declined == 2
        assert "student" in result.frame["decline_reason"].iloc[0].lower() or (
            result.frame["decline_reason"].str.contains("student").any()
        )

    def test_rate_override_scales_interest(self):
        base = simulate(_history(), PolicyRules())
        repriced = simulate(_history(), PolicyRules(interest_rate_pct=48.0))
        assert repriced.simulated.interest_income > base.simulated.interest_income

    def test_max_loan_to_income(self):
        result = simulate(_history(), PolicyRules(max_loan_to_income=2.0))
        declined = result.frame[result.frame["simulated_decision"] == "Decline"]
        assert len(declined) == 2  # the two low-income loans are > 2x income


class TestValidation:
    def test_requires_outcome_column(self):
        df = _history().drop(columns=["defaulted"])
        with pytest.raises(ValueError, match="outcome column"):
            simulate(df, PolicyRules())

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            simulate(pd.DataFrame(), PolicyRules())


class TestPortfolioMath:
    def test_flat_interest_formula(self):
        df = pd.DataFrame(
            {
                "loan_amount": [10_000],
                "interest_rate": [24],
                "tenure_months": [12],
                "defaulted": [0],
            }
        )
        result = simulate(df, PolicyRules())
        assert result.actual.interest_income == pytest.approx(2_400.0)
        assert result.actual.default_losses == 0.0

    def test_default_economics(self):
        df = pd.DataFrame(
            {
                "loan_amount": [10_000],
                "interest_rate": [24],
                "tenure_months": [12],
                "defaulted": [1],
            }
        )
        result = simulate(df, PolicyRules(), loss_given_default=0.5, default_interest_fraction=0.5)
        assert result.actual.interest_income == pytest.approx(1_200.0)
        assert result.actual.default_losses == pytest.approx(5_000.0)

    def test_sample_data_runs_end_to_end(self, tmp_path):
        result = simulate(
            sample_historical_loans(400),
            PolicyRules(min_monthly_income=15_000, max_loan_to_income=4.0),
        )
        assert 0 < result.approval_rate_pct < 100
        out = export_simulation(result, tmp_path / "sim.xlsx")
        assert pd.ExcelFile(out).sheet_names == ["Comparison", "Declined Loans", "All Decisions"]
