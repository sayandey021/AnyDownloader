@echo off
cd /d "%~dp0"
:menu
cls
echo =========================================
echo Any Downloader Build Tools
echo =========================================
echo.
echo Please select an option:
echo 1. Update Version
echo 2. Build and Package (EXE ^& MSIX)
echo 3. Exit
echo.
set /p choice="Enter choice (1-3): "

if "%choice%"=="1" goto update_version
if "%choice%"=="2" goto build_msix
if "%choice%"=="3" goto end

goto menu

:update_version
echo.
set /p new_version="Enter new version (e.g. 2.0.8): "
python update_version.py %new_version%
echo.
pause
goto menu

:build_msix
echo.
echo =========================================
echo Building Any Downloader
echo =========================================

echo.
echo [0/3] Patching flet.exe to fix taskbar metadata...
python patch_flet_exe.py

echo.
echo [1/3] Packaging Python App with Flet...
set "FLET_VIEW_PATH=%CD%\..\.flet_view"
FOR /F "tokens=*" %%g IN ('python -c "import ytmusicapi, os; print(os.path.join(os.path.dirname(ytmusicapi.__file__), 'locales'))"') do (SET "YTMUSIC_LOCALES=%%g")
python custom_pack.py ..\main.py -y --name "AnyDownloaderApp" --icon ..\assets\icon.ico --add-data "..\assets;assets" --add-data "%YTMUSIC_LOCALES%;ytmusicapi/locales" --distpath "..\dist" --product-name "Any Downloader" --file-description "Any Downloader" --product-version "1.6.0.0" --file-version "1.6.0.0" --company-name "SwiftGrab" --copyright "Copyright (c) 2026 SwiftGrab"

if %errorlevel% neq 0 (
    echo Error: Flet pack failed.
    pause
    exit /b %errorlevel%
)
echo.
echo Executable built successfully in ..\dist\

echo.
echo [2/3] Building MSIX Package and Signing...
powershell -ExecutionPolicy Bypass -File build_msix.ps1

if %errorlevel% neq 0 (
    echo Error: MSIX packaging failed.
    pause
    exit /b %errorlevel%
)

echo.
echo =========================================
echo Build Complete!
echo =========================================
pause
goto menu

:end
exit /b 0
