@echo off
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
python custom_pack.py ..\main.py -y --name "AnyDownloaderApp" --icon ..\assets\icon.ico --add-data "..\assets;assets" --add-data "%YTMUSIC_LOCALES%;ytmusicapi/locales" --distpath "..\dist" --workpath "..\build" --specpath ".." --product-name "Any Downloader" --file-description "Any Downloader" --product-version "1.1.0.0" --file-version "1.1.0.0" --company-name "SwiftGrab" --copyright "Copyright (c) 2026 SwiftGrab"

if %errorlevel% neq 0 (
    echo Error: Flet pack failed.
    exit /b %errorlevel%
)
echo.
echo Executable built successfully in ..\dist\

echo.
echo [2/3] Building MSIX Package and Signing...
powershell -ExecutionPolicy Bypass -File build_msix.ps1

if %errorlevel% neq 0 (
    echo Error: MSIX packaging failed.
    exit /b %errorlevel%
)

echo.
echo =========================================
echo Build Complete!
echo =========================================
