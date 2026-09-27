; MT5 Trading Workstation - Inno Setup Script
; This is a stub; the full installer is built in Phase 16 (Release).
; Build with: iscc /DAppVersion=X.Y.Z scripts/installer.iss
; build.py passes version via /DAppVersion=X.Y.Z

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppName=MT5 Trading Workstation
AppVersion={#AppVersion}
AppPublisher=MT5 Trading Workstation
DefaultDirName={localappdata}\MT5TradingWorkstation
DefaultGroupName=MT5 Trading Workstation
OutputDir=dist
OutputBaseFilename=MT5TradingWorkstation-Setup-{#AppVersion}
Compression=lzma2/ultra
SolidCompression=yes
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
WizardStyle=modern
UninstallDisplayIcon={app}\MT5TradingWorkstation.exe
SetupIconFile=

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "dist\MT5TradingWorkstation\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\MT5 Trading Workstation"; Filename: "{app}\MT5TradingWorkstation.exe"
Name: "{group}\Uninstall MT5 Trading Workstation"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\MT5TradingWorkstation.exe"; Description: "Launch MT5 Trading Workstation"; Flags: nowait postinstall skipifsilent
