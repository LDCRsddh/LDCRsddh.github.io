@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo Scanning for .inside files on external devices...
echo Please ensure all USB drives/external disks are connected...
echo.

:: Create temp file with Unicode support
set "tempFile=%temp%\.inside_files_%random%.txt"
echo Found .inside files: > "%tempFile%"

:: Scan removable drives (USB) and network drives (external HDD)
set deviceCount=0
for /f "tokens=1-2" %%a in ('wmic logicaldisk where "DriveType=2 or DriveType=4" get DeviceID^,DriveType 2^>nul ^| findstr ":"') do (
    set /a deviceCount+=1
    set "drive=%%a"
    set "type=%%b"
    
    vol !drive! >nul 2>&1
    if not errorlevel 1 (
        echo.
        echo [Device Found] !drive! [Type:!type!]
        
        :: Search and list all .inside files
        set fileCount=0
        for /f "delims=" %%f in ('dir /a /s /b "!drive!\*.inside" "!drive!\.inside" 2^>nul') do (
            set /a fileCount+=1
            echo   - %%f
            >> "%tempFile%" echo %%f
        )
        
        if !fileCount! gtr 0 (
            echo    Found !fileCount! .inside file(s)
        ) else (
            echo    No .inside files found
        )
    )
)

:: Display scan results
echo.
echo ========================================
type "%tempFile%"
echo ========================================
echo.

if !deviceCount! == 0 (
    echo No external storage devices found!
    timeout /t 5 >nul
    del "%tempFile%" >nul 2>&1
    exit /b
)

:: User confirmation
:confirm
set /p choice="Delete ALL listed files? (y/n): "
if /i "!choice!"=="y" (
    goto delete_files
) else if /i "!choice!"=="n" (
    echo Operation cancelled
) else (
    echo Please enter y or n
    goto confirm
)

:delete_files
echo.
echo Deleting files...
set deletedCount=0

for /f "usebackq delims=" %%f in ("%tempFile%") do (
    if exist "%%f" (
        attrib -h -s "%%f" >nul 2>&1
        del /f /q "%%f" >nul 2>&1
        if exist "%%f" (
            echo  [FAILED] %%f
        ) else (
            echo  [DELETED] %%f
            set /a deletedCount+=1
        )
    )
)

echo.
echo Operation complete! Deleted !deletedCount! file(s)
del "%tempFile%" >nul 2>&1
timeout /t 10 >nul