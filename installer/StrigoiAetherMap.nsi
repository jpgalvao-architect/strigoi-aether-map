; SPDX-License-Identifier: GPL-3.0-only
Unicode true
!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"
!include "x64.nsh"

!ifndef PAYLOAD
  !error "Define PAYLOAD as the complete prepared portable folder."
!endif
!ifndef OUTPUT
  !define OUTPUT "StrigoiAetherMap-Setup-0.9.0-beta.2.exe"
!endif
!ifndef UNINSTALL_MANIFEST
  !error "Generate the exact installed-file removal manifest first."
!endif
!ifndef TERMS_HASH
  !error "Define TERMS_HASH from both versioned terms files."
!endif
!ifdef TEST_BUILD
  !define REGKEY "Software\StrigoiAetherMapInstallerTest"
  !define UNINSTALLKEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\StrigoiAetherMapInstallerTest"
!else
  !define REGKEY "Software\StrigoiAetherMap"
  !define UNINSTALLKEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\StrigoiAetherMap"
!endif

Name "Strigoi Aether Map"
OutFile "${OUTPUT}"
InstallDir "$LOCALAPPDATA\Programs\StrigoiAetherMap"
InstallDirRegKey HKCU "${REGKEY}" "InstallDir"
RequestExecutionLevel user
ManifestDPIAware true
SetCompressor /SOLID lzma
SetCompressorDictSize 32
BrandingText "Strigoi Aether Map · 0.9.0-beta.2"
VIProductVersion "0.9.0.2"
VIAddVersionKey /LANG=1033 "ProductName" "Strigoi Aether Map"
VIAddVersionKey /LANG=1033 "FileDescription" "Strigoi Aether Map installer"
VIAddVersionKey /LANG=1033 "FileVersion" "0.9.0-beta.2"
VIAddVersionKey /LANG=1033 "LegalCopyright" "2026 Strigoi Aether Map contributors"
!define MUI_ICON "..\app\assets\aether.ico"
!define MUI_UNICON "..\app\assets\aether.ico"
!define MUI_ABORTWARNING
!define MUI_WELCOMEPAGE_TEXT "$(WelcomeText)"
!insertmacro MUI_PAGE_WELCOME
!define MUI_PAGE_HEADER_TEXT "$(TermsTitle)"
!define MUI_PAGE_HEADER_SUBTEXT "$(TermsSubtitle)"
!define MUI_LICENSEPAGE_CHECKBOX
!define MUI_LICENSEPAGE_CHECKBOX_TEXT "$(AcceptText)"
!insertmacro MUI_PAGE_LICENSE "$(TermsFile)"
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN "$INSTDIR\StrigoiAetherMap.exe"
!define MUI_FINISHPAGE_RUN_NOTCHECKED
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH
!insertmacro MUI_LANGUAGE "PortugueseBR"
!insertmacro MUI_LANGUAGE "English"

LicenseLangString TermsFile ${LANG_PORTUGUESEBR} "terms-pt_BR.rtf"
LicenseLangString TermsFile ${LANG_ENGLISH} "terms-en_US.rtf"
LangString WelcomeText ${LANG_PORTUGUESEBR} "Seu companheiro de exploração: atlas, coletas, cubos e eventos.$\r$\n$\r$\nA instalação inclui o aplicativo, as licenças e o código-fonte. Suas visitas e preferências serão preservadas.$\r$\n$\r$\nO idioma escolhido também será o padrão da primeira abertura. Depois, você pode mudá-lo em Configurações."
LangString WelcomeText ${LANG_ENGLISH} "Your exploration companion: atlas, gatherables, cubes and events.$\r$\n$\r$\nSetup includes the application, licenses and source code. Your visits and preferences will be preserved.$\r$\n$\r$\nThe selected language will be the default on first launch. You can change it later in Settings."
LangString TermsTitle ${LANG_PORTUGUESEBR} "Termos de uso"
LangString TermsTitle ${LANG_ENGLISH} "Terms of use"
LangString TermsSubtitle ${LANG_PORTUGUESEBR} "Leia os termos antes de continuar."
LangString TermsSubtitle ${LANG_ENGLISH} "Read the terms before continuing."
LangString AcceptText ${LANG_PORTUGUESEBR} "Li e aceito os termos de uso"
LangString AcceptText ${LANG_ENGLISH} "I have read and accept the terms of use"
LangString AppSection ${LANG_PORTUGUESEBR} "Aplicativo, licenças e código-fonte"
LangString AppSection ${LANG_ENGLISH} "Application, licenses and source code"
LangString DesktopSection ${LANG_PORTUGUESEBR} "Atalho na área de trabalho"
LangString DesktopSection ${LANG_ENGLISH} "Desktop shortcut"
LangString NpcapSection ${LANG_PORTUGUESEBR} "Npcap · componente do medidor de dano"
LangString NpcapSection ${LANG_ENGLISH} "Npcap · damage meter component"
LangString NpcapExplain ${LANG_PORTUGUESEBR} "O instalador verificará se Npcap já está disponível. Caso necessário, baixará a cópia oficial verificada e abrirá o assistente do fabricante, que pode solicitar permissão do Windows. Conclua esse assistente para usar o medidor de dano."
LangString NpcapExplain ${LANG_ENGLISH} "Setup checks whether Npcap is already available. If needed, it downloads the verified official copy and opens the publisher's wizard, which may request Windows permission. Complete that wizard to use the damage meter."
LangString NpcapMissing ${LANG_PORTUGUESEBR} "Npcap não foi instalado. O Atlas e o Sonar continuam disponíveis; o medidor de dano precisará do componente. Tentar novamente?"
LangString NpcapMissing ${LANG_ENGLISH} "Npcap was not installed. Atlas and Sonar remain available; the damage meter needs this component. Try again?"
LangString Unsupported ${LANG_PORTUGUESEBR} "Este aplicativo requer Windows 10/11 de 64 bits."
LangString Unsupported ${LANG_ENGLISH} "This application requires 64-bit Windows 10/11."
LangString SilentTerms ${LANG_PORTUGUESEBR} "A instalação silenciosa exige /ACCEPTTERMS após a leitura dos termos."
LangString SilentTerms ${LANG_ENGLISH} "Silent installation requires /ACCEPTTERMS after reviewing the terms."
LangString CloseApp ${LANG_PORTUGUESEBR} "Feche o Strigoi Aether Map e tente novamente."
LangString CloseApp ${LANG_ENGLISH} "Close Strigoi Aether Map and try again."
Var DefaultLanguage
Var SeedDirectory

Function .onInit
  SetShellVarContext current
  StrCpy $LANGUAGE ${LANG_PORTUGUESEBR}
  IfSilent silent_mode interactive_mode
  interactive_mode:
    !insertmacro MUI_LANGDLL_DISPLAY
    Goto language_ready
  silent_mode:
    ${GetOptions} $CMDLINE "/LANG=" $0
    ${If} $0 == "en_US"
      StrCpy $LANGUAGE ${LANG_ENGLISH}
    ${EndIf}
    ClearErrors
    ${GetOptions} $CMDLINE "/ACCEPTTERMS" $0
    ${If} ${Errors}
      DetailPrint "$(SilentTerms)"
      SetErrorLevel 2
      Quit
    ${EndIf}
  language_ready:
  ${IfNot} ${RunningX64}
    MessageBox MB_OK|MB_ICONSTOP "$(Unsupported)" /SD IDOK
    SetErrorLevel 3
    Quit
  ${EndIf}
  ${If} $LANGUAGE == ${LANG_ENGLISH}
    StrCpy $DefaultLanguage "en_US"
  ${Else}
    StrCpy $DefaultLanguage "pt_BR"
  ${EndIf}
  !ifdef TEST_BUILD
    StrCpy $SeedDirectory "$INSTDIR\test-user-data"
  !else
    StrCpy $SeedDirectory "$LOCALAPPDATA\StrigoiAetherMap"
  !endif
FunctionEnd

Section "$(AppSection)" Core
  SectionIn RO
  SetOutPath "$INSTDIR"
  SetOverwrite on
  ClearErrors
  File /r "${PAYLOAD}\*.*"
  ${If} ${Errors}
    MessageBox MB_OK|MB_ICONSTOP "$(CloseApp)" /SD IDOK
    SetErrorLevel 4
    Abort
  ${EndIf}
  FileOpen $0 "$INSTDIR\.strigoi-install-owned" w
  FileWrite $0 "StrigoiAetherMap-0.9.0-beta.2"
  FileClose $0
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  WriteRegStr HKCU "${REGKEY}" "InstallDir" "$INSTDIR"
  WriteRegStr HKCU "${REGKEY}" "TermsVersion" "1.1"
  WriteRegStr HKCU "${REGKEY}" "TermsSHA256" "${TERMS_HASH}"
  WriteRegStr HKCU "${REGKEY}" "InstallerLanguage" "$DefaultLanguage"
  WriteRegStr HKCU "${UNINSTALLKEY}" "DisplayName" "Strigoi Aether Map"
  WriteRegStr HKCU "${UNINSTALLKEY}" "DisplayVersion" "0.9.0-beta.2"
  WriteRegStr HKCU "${UNINSTALLKEY}" "Publisher" "Strigoi Aether Map"
  WriteRegStr HKCU "${UNINSTALLKEY}" "DisplayIcon" "$INSTDIR\StrigoiAetherMap.exe"
  WriteRegStr HKCU "${UNINSTALLKEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${UNINSTALLKEY}" "UninstallString" '$\"$INSTDIR\Uninstall.exe$\"'
  WriteRegDWORD HKCU "${UNINSTALLKEY}" "NoModify" 1
  WriteRegDWORD HKCU "${UNINSTALLKEY}" "NoRepair" 1
  ; Only a default-language seed: never overwrite preferences or exploration data.
  !ifdef TEST_BUILD
    StrCpy $SeedDirectory "$INSTDIR\test-user-data"
  !endif
  CreateDirectory "$SeedDirectory"
  FileOpen $0 "$SeedDirectory\installation.json" w
  FileWrite $0 '{$\"default_language$\":$\"$DefaultLanguage$\",$\"terms_version$\":$\"1.1$\",$\"terms_sha256$\":$\"${TERMS_HASH}$\"}'
  FileClose $0
  !ifndef TEST_BUILD
    CreateDirectory "$SMPROGRAMS\Strigoi Aether Map"
    CreateShortcut "$SMPROGRAMS\Strigoi Aether Map\Strigoi Aether Map.lnk" "$INSTDIR\StrigoiAetherMap.exe"
    CreateShortcut "$SMPROGRAMS\Strigoi Aether Map\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
  !endif
SectionEnd

Section "$(NpcapSection)" Npcap
  SectionIn RO
  !ifdef TEST_BUILD
    DetailPrint "Npcap integration skipped in isolated installer tests"
  !else
    IfSilent npcap_done 0
    InitPluginsDir
    SetOutPath "$PLUGINSDIR"
    File /oname=install-npcap.ps1 "install-npcap.ps1"
    DetailPrint "$(NpcapExplain)"
    npcap_retry:
      nsExec::ExecToStack '"$WINDIR\Sysnative\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "$PLUGINSDIR\install-npcap.ps1" -Language "$DefaultLanguage"'
      Pop $0
      Pop $1
      DetailPrint "$1"
      ${If} $0 == "3010"
        SetRebootFlag true
      ${ElseIf} $0 != "0"
        MessageBox MB_RETRYCANCEL|MB_ICONEXCLAMATION "$(NpcapMissing)" IDRETRY npcap_retry
      ${EndIf}
    npcap_done:
  !endif
SectionEnd

Section /o "$(DesktopSection)" Desktop
  !ifndef TEST_BUILD
    CreateShortcut "$DESKTOP\Strigoi Aether Map.lnk" "$INSTDIR\StrigoiAetherMap.exe"
  !endif
SectionEnd

Function un.onInit
  SetShellVarContext current
  ReadRegStr $0 HKCU "${REGKEY}" "InstallDir"
  ${If} $0 != $INSTDIR
    SetErrorLevel 5
    Abort
  ${EndIf}
  IfFileExists "$INSTDIR\.strigoi-install-owned" +3 0
    SetErrorLevel 5
    Abort
FunctionEnd

Section "Uninstall"
  ; Exact file list, never recursively delete a user-selected directory.
  !include "${UNINSTALL_MANIFEST}"
  Delete "$INSTDIR\.strigoi-install-owned"
  Delete "$INSTDIR\Uninstall.exe"
  !ifndef TEST_BUILD
    Delete "$DESKTOP\Strigoi Aether Map.lnk"
    Delete "$SMPROGRAMS\Strigoi Aether Map\Strigoi Aether Map.lnk"
    Delete "$SMPROGRAMS\Strigoi Aether Map\Uninstall.lnk"
    RMDir "$SMPROGRAMS\Strigoi Aether Map"
  !endif
  DeleteRegKey HKCU "${UNINSTALLKEY}"
  DeleteRegKey HKCU "${REGKEY}"
  RMDir "$INSTDIR"
  ; Intentionally preserve LOCALAPPDATA\StrigoiAetherMap and unknown files.
SectionEnd
