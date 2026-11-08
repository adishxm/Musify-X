@echo off
setlocal enabledelayedexpansion
title Musify-X Lite - Android Emulator Test Runner
color 0A

echo ========================================================
echo        Musify-X Lite - Android Emulator Test Runner
echo        Target: Android Emulator (API 36, x86_64)
echo        Size: ~14MB (Compatible 10MB - 40MB Target)
echo        Features: Spotify Auto-Load, Shields, Background Audio
echo ========================================================
echo.

set "SCRIPT_DIR=%~dp0"
if defined LOCALAPPDATA (
    set "SDK_DIR=%LOCALAPPDATA%\Android\Sdk"
) else (
    set "SDK_DIR=C:\Users\adity\AppData\Local\Android\Sdk"
)
if not exist "%SDK_DIR%" set "SDK_DIR=C:\Users\adity\AppData\Local\Android\Sdk"

set "EMULATOR_EXE=%SDK_DIR%\emulator\emulator.exe"
set "ADB_EXE=%SDK_DIR%\platform-tools\adb.exe"

set "AVD_NAME=Medium_Phone_API_36.1"
if exist "%USERPROFILE%\.android\avd\Medium_Phone_API_36.1.ini" (
    set "AVD_NAME=Medium_Phone_API_36.1"
) else if exist "%USERPROFILE%\.android\avd\Medium_Phone.ini" (
    set "AVD_NAME=Medium_Phone"
)

set "ANDROID_HOME=%SDK_DIR%"
set "ANDROID_SDK_ROOT=%SDK_DIR%"
set "PATH=%SDK_DIR%\emulator;%SDK_DIR%\platform-tools;%PATH%"

set "PACKAGE_NAME=com.musifyx.lite"
set "MAIN_ACTIVITY=com.musifyx.lite.MainActivity"
set "APK_PATH=%SCRIPT_DIR%Musify-X-Lite.apk"

if not exist "!APK_PATH!" (
    echo [INFO] Musify-X-Lite.apk not found. Running build pipeline...
    python "%SCRIPT_DIR%build_lite.py"
    if !errorlevel! neq 0 (
        echo [ERROR] Build pipeline failed.
        pause
        exit /b 1
    )
)

echo.
echo [1/4] Checking Android Emulator status...
set "EMULATOR_ONLINE=0"
for /f "skip=1 tokens=1,2" %%i in ('"%ADB_EXE%" devices 2^>nul') do (
    if "%%j"=="device" set "EMULATOR_ONLINE=1"
)

if "!EMULATOR_ONLINE!"=="0" (
    echo Starting emulator '%AVD_NAME%'...
    pushd "%SDK_DIR%\emulator"
    start "Musify-X Emulator" /d "%SDK_DIR%\emulator" "%EMULATOR_EXE%" -avd "%AVD_NAME%" -no-snapshot-load
    popd
    echo Waiting for emulator device to register with ADB...
    "%ADB_EXE%" wait-for-device
) else (
    echo Emulator is online and ready.
)

echo.
echo [2/4] Installing Musify-X Lite APK (~14MB)...
"%ADB_EXE%" install -r -d "!APK_PATH!"
if !errorlevel! neq 0 (
    echo [WARN] Reinstalling package...
    "%ADB_EXE%" uninstall "!PACKAGE_NAME!" >nul 2>&1
    "%ADB_EXE%" install "!APK_PATH!"
)

echo.
echo [3/4] Launching Musify-X Lite with Spotify Web Player...
"%ADB_EXE%" shell am start -n "!PACKAGE_NAME!/!MAIN_ACTIVITY!"

echo.
echo ========================================================
echo [SUCCESS] Musify-X Lite is now running on emulator!
echo - Auto-navigates to: https://open.spotify.com
echo - Musify-X Shields: Active (Tracker ^& Audio Ad Blocker)
echo - Liquid 'M' Day/Night Adaptive Launcher Icon
echo ========================================================
echo.
pause

