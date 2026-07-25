# LendOps Studio

One desktop app for the three daily jobs of a micro-lending operations team — built for analysts serving students and young professionals, and simple enough for a non-technical user: pick a file, click a button, get a result. Windows-native (CustomTkinter), offline-first, dark/light mode.

## Install it

Grab either artifact from the [Releases page](https://github.com/kristic8998/lendops/releases):

- **`LendOps-Setup-1.0.0.exe`** — normal Windows installer (Start-menu shortcuts, uninstaller, no admin needed)
- **`LendOps-1.0.0-portable.zip`** — unzip anywhere and run, nothing installed

Neither requires Python on the target PC. Full instructions (including building from source): **[docs/INSTALL.md](docs/INSTALL.md)**.

## The three modules

| Module | What it answers | Flow |
|---|---|---|
| **☎ Collecta** — delinquency predictor | *Which active loans are about to go bad, and whom do we call first?* | Upload Active Loans → Analyze Risk → Export Calling List. 0–100 risk score per loan, High/Medium/Low bands, plain-English reason per call. Auto-upgrades from weighted rules to a logistic regression when your file carries an outcome column. |
| **⚖ PolicySim** — credit rule backtesting | *What if we had lent with stricter rules?* | Upload historical book → tick rules (loan cap, min income, loan-to-income, exclude students, reprice APR) with sliders → Run Simulation. Actual vs simulated profit, losses and default rate, with every economic assumption stated on screen. |
| **🛡 KYC Sentinel** — identity fraud detector | *Which of today's applications are fraudulent?* | Upload Daily Applications → Scan for Fraud → Export Report. Detects shared bank accounts and IDs across different names, duplicate phones/emails, underage applicants, age/DOB mismatches, invalid PAN formats, missing critical fields, absurd ask-to-income. Red = alert, orange = review. |

Design promises kept everywhere: every page shows a **"How to use" card** on screen, every page has a **"Try with sample data"** button, every heavy operation runs on a **background thread** (the UI never freezes), and files need **no special format** — columns are detected by name from plain CSV/Excel exports.

## Quickstart from source

```bat
git clone https://github.com/kristic8998/lendops.git
cd lendops
python -m venv .venv && .venv\Scripts\activate.bat
pip install -e ".[dev]"
lendops              :: launches the app
lendops --selftest   :: verifies all engines headlessly
pytest               :: 44 engine/core tests
scripts\build_windows.bat   :: freeze LendOps.exe (Windows only)
```

## Project structure

```
├── src/lendops/
│   ├── core/        # paths, JSON config, background TaskRunner, demo data
│   ├── modules/     # collecta, policysim, kyc, tabular — pure services, no UI imports
│   ├── ui/          # CustomTkinter shell, widgets (HelperCard, DataGrid…), 4 pages
│   ├── app.py       # composition root + window shell
│   └── selftest.py  # `lendops --selftest`
├── tests/           # 44 tests over every engine
├── sample_data/     # the three demo CSVs (also embedded in the app)
├── scripts/         # build_windows.bat, build_portable.bat
├── installer/       # Inno Setup script (lendops.iss) -> Setup.exe
├── LendOps.spec     # PyInstaller one-folder spec
└── .github/workflows/ci.yml
```

## Documentation

- **[Install Guide](docs/INSTALL.md)** — installer & portable, building from source, updating, uninstalling
- **[User Guide](docs/USER_GUIDE.md)** — each module step by step, written for a non-programmer
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** — SmartScreen, antivirus, file-format questions, logs

## Honest limitations

PolicySim uses simplified flat-interest economics (stated on screen and in exports) — it is a directional what-if tool, not an accounting system. Collecta's rule weights are transparent heuristics unless your file provides outcomes to train on. KYC checks are pattern-based screening, not a verification service. The installer/exe are not code-signed, so SmartScreen shows a first-run prompt (see Troubleshooting).

## License

MIT — see [LICENSE](LICENSE).
