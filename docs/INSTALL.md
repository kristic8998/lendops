# LendOps Studio — Windows Installation & Packaging Guide

Targets **Windows 10/11, 64-bit, 16 GB RAM, integrated graphics — no GPU required.** Both packaged options bundle their own Python; **the target PC does not need Python installed.**

## Which install do I want?

| You want to… | Use | Needs Python? | Needs admin? |
|---|---|---|---|
| A normal Setup wizard with Start-menu shortcuts | **Installer** (`LendOps-Setup-1.0.0.exe`) | No | No (per-user) |
| Run from a USB stick / no install at all | **Portable** (`LendOps-1.0.0-portable.zip`) | No | No |
| Develop or build the app | **From source** (`pip install -e .`) | Yes, 3.10+ | No |

## Option A: Installer (easiest)

1. Download **`LendOps-Setup-1.0.0.exe`** from the [Releases page](https://github.com/kristic8998/lendops/releases).
2. Double-click it. If SmartScreen shows *"Windows protected your PC"*, click **More info → Run anyway** (expected — the installer isn't code-signed).
3. Follow the wizard (installs to `%LOCALAPPDATA%\Programs\LendOps`, no admin rights), optionally tick the desktop shortcut, finish, and launch from the Start menu.

## Option B: Portable (zip, no install)

1. Download **`LendOps-1.0.0-portable.zip`**, right-click → **Extract All…** to any folder.
2. Double-click **`Start LendOps.bat`** (or `LendOps\LendOps.exe`). Same SmartScreen note as above.

Nothing touches Program Files or the registry; to "uninstall," delete the folder. Your data lives separately under `%LOCALAPPDATA%\LendOps`.

## Installing on a PC with no Python

This is the normal case for both packaged options — PyInstaller bundles the complete Python runtime and every dependency inside the distributable. Copy the Setup.exe or the zip over (USB or share), run it, done. No internet connection needed.

## Verifying an install worked

Launch the app and click **“Try with sample data” → the module button** on any page; if results render, the full stack is healthy. From source you can also run the headless self-test (`lendops --selftest`), which exercises every engine in seconds — the same check CI runs on every commit.

---

# Building from source (for developers/packagers)

1. **Python 3.10–3.12 (64-bit),** 3.12 recommended; tick *"Add python.exe to PATH"* during install.
2. Get the code and set up:

   ```bat
   git clone https://github.com/kristic8998/lendops.git
   cd lendops
   python -m venv .venv
   .venv\Scripts\activate.bat
   python -m pip install --upgrade pip
   pip install -e ".[dev]"
   ```

   Runtime dependencies (from `pyproject.toml`): `customtkinter`, `numpy`, `pandas`, `scikit-learn`, `openpyxl`.
3. **Run:** `lendops` (GUI) or `lendops --selftest` (headless). No configuration needed — the only persisted setting is the theme, in `%LOCALAPPDATA%\LendOps\config.json`; set `LENDOPS_HOME` to relocate all app data.
4. **Build the exe** (Windows only — PyInstaller does not cross-compile):

   ```bat
   scripts\build_windows.bat
   ```

   → `dist\LendOps\LendOps.exe` (one-folder build; runs the self-test before freezing).
5. **Produce the distributables:**
   - Portable zip: `scripts\build_portable.bat` → `dist\LendOps-1.0.0-portable.zip`
   - Installer: install [Inno Setup 6+](https://jrsoftware.org/isdl.php), then `ISCC.exe installer\lendops.iss` (or open it and press F9) → `installer\Output\LendOps-Setup-1.0.0.exe`

## Updating after a future release

**Installer users:** run the newer Setup.exe — same `AppId`, upgrades in place, data untouched. **Portable users:** unzip the new version to a new folder, delete the old one; data carries over automatically because it lives under `%LOCALAPPDATA%\LendOps`. **From source:** `git pull`, `pip install -e ".[dev]"`, `lendops --selftest`.

## Uninstalling

**Installer:** Settings → Apps → LendOps Studio → Uninstall (or the Start-menu uninstall shortcut). **Portable:** delete the folder. Either way your data (exported reports, settings) deliberately remains in `%LOCALAPPDATA%\LendOps` — delete that folder too if you want everything gone.

## Where your data lives

| What | Location |
|---|---|
| Settings + exported reports | `%LOCALAPPDATA%\LendOps` (or `LENDOPS_HOME`) |
| Installed program (installer) | `%LOCALAPPDATA%\Programs\LendOps` |
| Portable program | wherever you unzipped it |

Problems? See **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)**.
