@echo off
setlocal
title Tech Lounge Tweaks - prepare and push
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\release.ps1" -Mode push
set "RESULT=%ERRORLEVEL%"
echo.
if not "%RESULT%"=="0" echo Release failed. See the error above. Nothing is force-pushed.
pause
exit /b %RESULT%
