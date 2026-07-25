@echo off
rem ============================================================================
rem  LendOps Studio - build the Windows executable (PyInstaller one-folder).
rem
rem  Run this on a Windows machine (PyInstaller cannot cross-compile).
rem  It creates the venv if needed, installs dev extras, runs the headless
rem  self-test as a pre-flight check, then freezes the app.
rem
rem  Output: dist\LendOps\LendOps.exe  (plus an _internal\ support folder)
rem ============================================================================
setlocal
cd /d "%~dp0.."

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment ...
    python -m venv .venv || goto :error
)
call .venv\Scripts\activate.bat

echo Installing build dependencies ...
python -m pip install --upgrade pip -q || goto :error
pip install -e ".[dev]" -q || goto :error

echo Running the self-test (pre-flight) ...
lendops --selftest || goto :error

echo Cleaning previous build ...
if exist build rmdir /s /q build
if exist "dist\LendOps" rmdir /s /q "dist\LendOps"

echo Freezing with PyInstaller ...
pyinstaller LendOps.spec --noconfirm --clean || goto :error

echo(
echo ============================================================================
echo  BUILD COMPLETE:  dist\LendOps\LendOps.exe
echo  Next: scripts\build_portable.bat  (portable zip)
echo        or compile installer\lendops.iss with Inno Setup (Setup.exe)
echo ============================================================================
pause
exit /b 0

:error
echo(
echo BUILD FAILED - see the message above.
pause
exit /b 1
