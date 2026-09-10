@echo off
setlocal
title Tech Lounge Tweaks - prepare personal ZIP
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\release.ps1" -Mode prepare
set "RESULT=%ERRORLEVEL%"
echo.
if not "%RESULT%"=="0" echo Release failed. See the error above.
pause
exit /b %RESULT%
