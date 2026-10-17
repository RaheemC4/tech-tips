Unicode true
!include "MUI2.nsh"
!include "FileFunc.nsh"
!include "x64.nsh"
Name "Tech Lounge Tweaks"
OutFile "${OUTPUT}"
InstallDir "$LOCALAPPDATA\Programs\TechLoungeTweaks"
InstallDirRegKey HKCU "Software\TechLoungeTweaks" "InstallRoot"
RequestExecutionLevel user
SetCompressor zlib
SetCompressionLevel 6
ShowInstDetails nevershow
!define MUI_ABORTWARNING
!define MUI_FINISHPAGE_RUN "$INSTDIR\TechLounge.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Open Tech Lounge Tweaks"
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"
Var UpdateMode
Function .onInit
  ${IfNot} ${RunningX64}
    MessageBox MB_ICONSTOP "Tech Lounge Tweaks requires 64-bit Windows."
    Abort
  ${EndIf}
  SetShellVarContext current
  ${GetParameters} $0
  ClearErrors
  ${GetOptions} $0 "/UPDATE" $1
  ${IfNot} ${Errors}
    StrCpy $UpdateMode "1"
  ${EndIf}
FunctionEnd
Section "Install"
  ${If} $UpdateMode != "1"
    IfFileExists "$INSTDIR\TechLounge.exe" 0 no_existing_install
    ExecWait '"$INSTDIR\TechLounge.exe" --prepare-install' $0
    ${If} $0 != 0
      SetErrorLevel 1
      Abort "Close the app and finish quick actions before installing."
    ${EndIf}
    Sleep 500
    no_existing_install:
  ${EndIf}
  SetOutPath "$INSTDIR\versions\${VERSION}"
  SetOverwrite ifdiff
  ClearErrors
  File /r "${PAYLOAD}\*.*"
  ${If} ${Errors}
    SetErrorLevel 1
    Abort "Could not install the app. Close Tech Lounge Tweaks and retry."
  ${EndIf}
  SetOutPath "$INSTDIR"
  File "${PAYLOAD}\TechLounge.exe"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  ; Publish the version pointer only after complete extraction. Rename is atomic.
  ClearErrors
  FileOpen $0 "$INSTDIR\current.pending" w
  FileWrite $0 "${VERSION}"
  FileClose $0
  ${If} ${Errors}
    SetErrorLevel 1
    Abort "Could not save installation metadata. Current version retained."
  ${EndIf}
  System::Call 'kernel32::MoveFileExW(w "$INSTDIR\current.pending", w "$INSTDIR\current.txt", i 9)i.r0'
  ${If} $0 == 0
    SetErrorLevel 1
    Abort "Could not finish installation. Current version retained."
  ${EndIf}
  WriteRegStr HKCU "Software\TechLoungeTweaks" "InstallRoot" "$INSTDIR"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\TechLoungeTweaks" "DisplayName" "Tech Lounge Tweaks"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\TechLoungeTweaks" "DisplayVersion" "${VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\TechLoungeTweaks" "Publisher" "The Tech Lounge"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\TechLoungeTweaks" "DisplayIcon" "$INSTDIR\TechLounge.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\TechLoungeTweaks" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\TechLoungeTweaks" "QuietUninstallString" '"$INSTDIR\Uninstall.exe" /S'
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\TechLoungeTweaks" "NoModify" 1
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\TechLoungeTweaks" "NoRepair" 1
  CreateShortcut "$SMPROGRAMS\Tech Lounge Tweaks.lnk" "$INSTDIR\TechLounge.exe"
  ExecWait '"$INSTDIR\TechLounge.exe" --install' $0
  ${If} $0 != 0
    DetailPrint "Installed. Windows could not register delayed startup. Enable Open on startup in companion settings."
  ${EndIf}
  ${If} $UpdateMode != "1"
    Exec '"$INSTDIR\TechLounge.exe" --tray'
  ${EndIf}
SectionEnd
Section "Uninstall"
  SetShellVarContext current
  ExecWait '"$INSTDIR\TechLounge.exe" --uninstall' $0
  ${If} $0 != 0
    SetErrorLevel 1
    Abort "Close the app and finish quick actions before uninstalling."
  ${EndIf}
  Sleep 500
  Delete "$SMPROGRAMS\Tech Lounge Tweaks.lnk"
  ; Remove only the known installation payload; user settings and undo data
  ; outside this directory are intentionally retained.
  RMDir /r "$INSTDIR\versions"
  Delete "$INSTDIR\TechLounge.exe"
  Delete "$INSTDIR\current.txt"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\TechLoungeTweaks"
  DeleteRegValue HKCU "Software\TechLoungeTweaks" "InstallRoot"
SectionEnd
