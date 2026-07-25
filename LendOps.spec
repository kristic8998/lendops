# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for LendOps Studio — ONE-FOLDER build (faster startup and
# friendlier with antivirus than one-file). Build on Windows only:
#   scripts\build_windows.bat        (recommended wrapper)
#   pyinstaller LendOps.spec --noconfirm --clean
# Output: dist/LendOps/LendOps.exe (+ _internal/ support folder)

from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files("customtkinter")  # CTk ships its themes as JSON assets
datas += [("sample_data", "sample_data")]  # demo CSVs available next to the exe

a = Analysis(
    ["launcher.py"],
    pathex=["src"],
    binaries=[],
    datas=datas,
    hiddenimports=[
        # scikit-learn is imported lazily inside collecta.analyze; make sure
        # the frozen build carries it even though static analysis may miss it.
        "sklearn.linear_model",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=["matplotlib", "scipy.tests", "tkinter.test"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="LendOps",
    debug=False,
    strip=False,
    upx=False,
    console=False,  # GUI app — no console window
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="LendOps",
)
