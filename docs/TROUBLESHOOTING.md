# LendOps Studio — Troubleshooting

## Installing & launching

**"Windows protected your PC" (SmartScreen).** Expected — the exe isn't code-signed. Click **More info → Run anyway**. Signing requires a purchased certificate; until then this prompt appears once per machine.

**Antivirus flags or quarantines the exe.** PyInstaller-packaged apps are a common false positive. Restore/allow the file, or use the portable zip. Building from source yourself (see INSTALL.md) also sidesteps it.

**`VCRUNTIME140.dll` missing.** Install the Microsoft *Visual C++ Redistributable (x64)* from Microsoft's site — one-time fix on very clean machines.

**First launch feels slow.** Normal for a one-folder PyInstaller app on first run (antivirus scans every bundled file once). Subsequent launches are fast.

## Using the app

**"Upload a file first" / nothing happens on Analyze.** The steps are ordered — the ①②③ buttons need to be used in sequence. Each page's blue card restates the order.

**My columns aren't recognised.** Columns are matched by name fragments (e.g. anything containing "dpd", "income", "pan"). Rename headers to plain words like `monthly_income`, `current_dpd`, `bank_account` and re-upload. The `sample_data` CSVs show ideal headers.

**PolicySim says it needs an outcome column.** The simulator must know how each historical loan ended. Add a column such as `defaulted` with 1/0 (or yes/no) and re-upload.

**Collecta shows "weighted risk rules" — where's the model?** The logistic-regression upgrade activates only when your file has an outcome column with both outcomes present and at least 30 rows; otherwise the transparent rules are used (by design).

**The grid shows only the first 400 rows.** A display guard for modest laptops — exports always contain every row.

**Numbers look odd in PolicySim.** Check the assumptions line under the comparison (flat interest, default interest fraction, loss-given-default). It's a directional what-if tool, not accounting.

## Building from source

**`pip install` fails.** Upgrade pip (`python -m pip install --upgrade pip`) and confirm 64-bit Python 3.10–3.12. scikit-learn wheels need 64-bit.

**PyInstaller build can't find a module.** Add it to `hiddenimports` in `LendOps.spec` and rebuild.

**Inno Setup says files not found.** Run `scripts\build_windows.bat` first — the installer packages `dist\LendOps\`.

## Data & settings

**Where are my exports?** Default folder: `%LOCALAPPDATA%\LendOps\reports` (paste in File Explorer's address bar).

**Reset the app.** Delete `%LOCALAPPDATA%\LendOps\config.json` (theme returns to dark). Deleting the whole `%LOCALAPPDATA%\LendOps` folder removes all settings and saved reports.

**Everything is stored where?** Program: where you installed/unzipped it. Your data: `%LOCALAPPDATA%\LendOps` (or `LENDOPS_HOME` if you set it). Uninstalling never deletes your data folder.
