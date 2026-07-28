@echo off
rem ============================================================================
rem  LendOps Studio - build the PORTABLE distribution (a self-contained .zip).
rem
rem  No installer, no admin rights: unzip anywhere and double-click.
rem  Python is bundled inside, so the target PC needs no Python.
rem
rem  Prereq: run scripts\build_windows.bat first (creates dist\LendOps).
rem  Output: dist\LendOps-1.1.0-portable.zip
rem ============================================================================
setlocal
cd /d "%~dp0.."
set "VERSION=1.1.0"
set "PKG=LendOps-%VERSION%-portable"

if not exist "dist\LendOps\LendOps.exe" (
    echo dist\LendOps\LendOps.exe not found.
    echo Run scripts\build_windows.bat first, then re-run this script.
    pause
    exit /b 1
)

echo Staging portable folder ...
if exist "dist\%PKG%" rmdir /s /q "dist\%PKG%"
xcopy "dist\LendOps" "dist\%PKG%\LendOps\" /e /i /q || goto :error

rem A friendly launcher at the top level of the zip.
> "dist\%PKG%\Start LendOps.bat" echo @echo off
>>"dist\%PKG%\Start LendOps.bat" echo start "" "%%~dp0LendOps\LendOps.exe"

rem A short readme so a non-technical recipient knows what to do.
> "dist\%PKG%\READ ME FIRST.txt" echo LendOps Studio %VERSION% - Portable edition
>>"dist\%PKG%\READ ME FIRST.txt" echo -------------------------------------------
>>"dist\%PKG%\READ ME FIRST.txt" echo(
>>"dist\%PKG%\READ ME FIRST.txt" echo No installation required. No Python required.
>>"dist\%PKG%\READ ME FIRST.txt" echo(
>>"dist\%PKG%\READ ME FIRST.txt" echo 1. Unzip this whole folder anywhere (Desktop is fine).
>>"dist\%PKG%\READ ME FIRST.txt" echo 2. Double-click "Start LendOps.bat" (or LendOps\LendOps.exe).
>>"dist\%PKG%\READ ME FIRST.txt" echo 3. Your data is stored under %%LOCALAPPDATA%%\LendOps.
>>"dist\%PKG%\READ ME FIRST.txt" echo(
>>"dist\%PKG%\READ ME FIRST.txt" echo If Windows SmartScreen warns you: More info -^> Run anyway.
>>"dist\%PKG%\READ ME FIRST.txt" echo Full guide: docs\USER_GUIDE.md at github.com/kristic8998/lendops

echo Compressing to dist\%PKG%.zip ...
if exist "dist\%PKG%.zip" del /q "dist\%PKG%.zip"
powershell -NoProfile -Command ^
  "Compress-Archive -Path 'dist\%PKG%\*' -DestinationPath 'dist\%PKG%.zip' -Force" || goto :error

echo(
echo ============================================================================
echo  PORTABLE BUILD COMPLETE
echo    dist\%PKG%.zip
echo  Share that single .zip. The recipient unzips and runs it.
echo ============================================================================
pause
exit /b 0

:error
echo(
echo Portable packaging FAILED - see the message above.
pause
exit /b 1
