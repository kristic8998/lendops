"""Headless end-to-end self-test: ``lendops --selftest``.

Exercises every engine against the deterministic sample data and writes
each export to a temp folder — the same check CI runs on every commit
and the Windows build script runs before freezing the exe.
"""

from __future__ import annotations

import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

from . import __version__
from .core import demo
from .core.config import AppConfig, load_config, save_config


def _utf8_console() -> None:
    """Make stdout/stderr UTF-8 so ₹/·/— print fine on Windows pipes (cp1252)."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:  # noqa: BLE001 - console cosmetics must never break the test
                pass


def run() -> int:
    _utf8_console()
    print(f"LendOps Studio v{__version__} — self-test")
    checks: list[tuple[str, Callable[[], str]]] = []
    tmp = Path(tempfile.mkdtemp(prefix="lendops_selftest_"))

    def check_config() -> str:
        path = tmp / "config.json"
        save_config(AppConfig(theme="light", start_page="kyc"), path)
        loaded = load_config(path)
        assert loaded.theme == "light" and loaded.start_page == "kyc"
        return "round-trip ok"

    checks.append(("config", check_config))

    def check_collecta() -> str:
        from .modules.collecta import analyze, export_calling_list

        result = analyze(demo.sample_active_loans())
        assert result.summary.high > 0
        out = export_calling_list(result, tmp / "calling_list.xlsx")
        assert out.is_file()
        return result.summary.as_text()

    checks.append(("collecta", check_collecta))

    def check_policysim() -> str:
        from .modules.policysim import PolicyRules, export_simulation, simulate

        rules = PolicyRules(min_monthly_income=15_000, max_loan_to_income=4.0)
        result = simulate(demo.sample_historical_loans(), rules)
        assert 0 < result.approved < result.approved + result.declined
        out = export_simulation(result, tmp / "policy_simulation.xlsx")
        assert out.is_file()
        return (
            f"approval {result.approval_rate_pct:.0f}% · net profit "
            f"₹{result.actual.net_profit:,.0f} → ₹{result.simulated.net_profit:,.0f}"
        )

    checks.append(("policysim", check_policysim))

    def check_kyc() -> str:
        from .modules.kyc import export_report, scan

        result = scan(demo.sample_daily_applications())
        assert result.alerts > 0 and result.watches > 0
        out = export_report(result, tmp / "kyc_report.xlsx")
        assert out.is_file()
        return result.summary_text()

    checks.append(("kyc sentinel", check_kyc))

    failures = 0
    for name, fn in checks:
        try:
            detail = fn()
            print(f"  OK    {name:<12} {detail}")
        except Exception as exc:  # noqa: BLE001 - report every failure, keep going
            failures += 1
            print(f"  FAIL  {name:<12} {exc}")
    print("ALL CHECKS PASSED" if failures == 0 else f"{failures} CHECK(S) FAILED")
    return 0 if failures == 0 else 1
