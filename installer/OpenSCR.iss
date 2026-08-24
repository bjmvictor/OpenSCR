#ifndef MyAppVersion
  #define MyAppVersion "2.0.5"
#endif
#ifndef SourceDir
  #error SourceDir must point to the OpenSCR onedir release
#endif
#ifndef OutputDir
  #define OutputDir "..\release"
#endif
#ifndef MyMinVersion
  #define MyMinVersion "10.0.14393"
#endif
#ifndef OutputSuffix
  #define OutputSuffix ""
#endif

[Setup]
AppId={{7CB585D1-B9B7-48BA-931C-825529224202}
AppName=OpenSCR
AppVersion={#MyAppVersion}
AppPublisher=Benjamin Victor
AppPublisherURL=https://github.com/bjmvictor/OpenSCR
AppSupportURL=https://github.com/bjmvictor/OpenSCR/issues
DefaultDirName={autopf}\OpenSCR
DefaultGroupName=OpenSCR
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion={#MyMinVersion}
PrivilegesRequired=admin
OutputDir={#OutputDir}
OutputBaseFilename=OpenSCR-{#MyAppVersion}-Windows-x64{#OutputSuffix}-Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\assets\OpenSCR.ico
UninstallDisplayIcon={app}\OpenSCR.exe
CloseApplications=yes

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"
#ifdef ChineseLanguage
Name: "chinesesimplified"; MessagesFile: "{#ChineseLanguage}"
#endif

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\OpenSCR"; Filename: "{app}\OpenSCR.exe"
Name: "{autodesktop}\OpenSCR"; Filename: "{app}\OpenSCR.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Criar um atalho na área de trabalho"; GroupDescription: "Atalhos adicionais:"

[Run]
Filename: "{app}\OpenSCR.exe"; Description: "Abrir o OpenSCR"; Flags: nowait postinstall skipifsilent
