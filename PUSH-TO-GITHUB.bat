@echo off
setlocal
color 0B
title Tech Lounge Tweaks - prepare and push
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\release.ps1" -Mode push
set "RESULT=%ERRORLEVEL%"
echo.
if not "%RESULT%"=="0" goto failed
echo Repo: https://github.com/RaheemC4/tech-tips
echo Download: https://github.com/RaheemC4/tech-tips/raw/main/TechLoungeTweaks/TechLoungeTweaks.zip
echo.
choice /c RDC /n /m "[R] Open repository  [D] Download ZIP  [C] Close: "
if errorlevel 3 exit /b 0
if errorlevel 2 goto download
start "" "https://github.com/RaheemC4/tech-tips"
exit /b 0
:download
start "" "https://github.com/RaheemC4/tech-tips/raw/main/TechLoungeTweaks/TechLoungeTweaks.zip"
exit /b 0
:failed
echo Release failed. See the error above. Nothing is force-pushed.
pause
exit /b %RESULT%
