@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo.
echo  ========================================
echo   Rhys's Home - Git Push
echo  ========================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0push.ps1"

echo.
pause
endlocal