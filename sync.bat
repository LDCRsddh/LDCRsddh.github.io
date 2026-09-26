@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo.
echo  ========================================
echo   Rhys's Home - Sync
echo  ========================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0sync.ps1"

echo.
pause
endlocal