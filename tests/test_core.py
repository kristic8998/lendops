"""Tests for config, demo generators, and tabular helpers."""

from __future__ import annotations

import pandas as pd

from lendops.core.config import AppConfig, load_config, save_config
from lendops.core.demo import (
    sample_active_loans,
    sample_daily_applications,
    sample_historical_loans,
    write_sample_files,
)
from lendops.modules.tabular import find_col, num_series, read_table, text_series


class TestConfig:
    def test_roundtrip(self, tmp_path):
        path = tmp_path / "config.json"
        save_config(AppConfig(theme="light", start_page="kyc"), path)
        loaded = load_config(path)
        assert loaded.theme == "light" and loaded.start_page == "kyc"

    def test_missing_file_gives_defaults(self, tmp_path):
        config = load_config(tmp_path / "nope.json")
        assert config.theme == "dark"

    def test_corrupt_file_gives_defaults(self, tmp_path):
        path = tmp_path / "config.json"
        path.write_text("{not json", encoding="utf-8")
        assert load_config(path).theme == "dark"

    def test_bad_theme_normalised(self, tmp_path):
        path = tmp_path / "config.json"
        path.write_text('{"theme": "neon", "start_page": "home"}', encoding="utf-8")
        assert load_config(path).theme == "dark"


class TestDemo:
    def test_shapes_and_determinism(self):
        a1, a2 = sample_active_loans(100), sample_active_loans(100)
        pd.testing.assert_frame_equal(a1, a2)
        assert len(sample_historical_loans(50)) == 50
        assert len(sample_daily_applications(60)) == 60

    def test_historical_has_both_outcomes(self):
        hist = sample_historical_loans(300)
        assert 0 < hist["defaulted"].sum() < len(hist)

    def test_write_sample_files(self, tmp_path):
        written = write_sample_files(tmp_path)
        assert [p.name for p in written] == [
            "active_loans.csv",
            "historical_loans.csv",
            "daily_applications.csv",
        ]
        assert all(p.is_file() for p in written)


class TestTabular:
    def test_find_col_prefers_exact(self):
        df = pd.DataFrame(columns=["dpd_bucket", "dpd"])
        assert find_col(df, ("dpd",)) == "dpd"

    def test_find_col_contains_fallback(self):
        df = pd.DataFrame(columns=["Current DPD Days"])
        assert find_col(df, ("dpd",)) == "Current DPD Days"

    def test_series_helpers_handle_absent_columns(self):
        df = pd.DataFrame({"x": [1, 2]})
        assert num_series(df, None).eq(0.0).all()
        assert text_series(df, None).eq("").all()

    def test_read_table_csv_and_excel(self, tmp_path):
        df = pd.DataFrame({"a": [1, 2]})
        csv = tmp_path / "t.csv"
        xlsx = tmp_path / "t.xlsx"
        df.to_csv(csv, index=False)
        df.to_excel(xlsx, index=False)
        assert len(read_table(csv)) == 2
        assert len(read_table(xlsx)) == 2
