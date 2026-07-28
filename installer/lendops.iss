; ============================================================================
;  LendOps Studio - Inno Setup installer script
;
;  Produces a standard Windows Setup.exe: per-user install (no admin),
;  Start-menu + optional desktop shortcut, registered uninstaller, and
;  in-place upgrades on future versions (fixed AppId).
;
;  Build steps (on Windows):
;   1. Run scripts\build_windows.bat
;      -> produces dist\LendOps\LendOps.exe (one-folder build)
;   2. Install Inno Setup 6+ :  https://jrsoftware.org/isdl.php
;   3. Open this file in the Inno Setup Compiler and press Build (F9),
;      or from a terminal:      ISCC.exe installer\lendops.iss
;   -> produces installer\Output\LendOps-Setup-<version>.exe
; ============================================================================

#define AppName "LendOps Studio"
#define AppVersion "1.1.0"
#define AppPublisher "Kristi Chakraborty"
#define AppExeName "LendOps.exe"
#define AppURL "https://github.com/kristic8998/lendops"

[Setup]
AppId={{9C5E4B76-1D3A-4F2C-8E0B-LEND0PS2026}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
DefaultDirName={localappdata}\Programs\LendOps
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=Output
OutputBaseFilename=LendOps-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName={#AppName} {#AppVersion}
UninstallDisplayIcon={app}\{#AppExeName}

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
; Ship the entire PyInstaller one-folder output.
Source: "..\dist\LendOps\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion
; Documentation for offline reading.
Source: "..\README.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\docs\USER_GUIDE.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\docs\TROUBLESHOOTING.md"; DestDir: "{app}\docs"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent
