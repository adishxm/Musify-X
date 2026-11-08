@echo off
setlocal enabledelayedexpansion
title Musify-X - Android Emulator Test Runner
color 0B

echo ========================================================
echo        Musify-X - Android Emulator Test Runner
echo        Target: Android Emulator (API 36, x86_64)
echo        Privacy Shields, Ad Blocking ^& Media Validation
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

if not exist "%EMULATOR_EXE%" (
    echo [ERROR] Android Emulator not found at: %EMULATOR_EXE%
    pause
    exit /b 1
)

if not exist "%ADB_EXE%" (
    echo [ERROR] ADB not found at: %ADB_EXE%
    pause
    exit /b 1
)

set "PACKAGE_NAME=com.brave.browser_nightly"
set "MAIN_ACTIVITY=com.google.android.apps.chrome.Main"
set "APK_PATH=%SCRIPT_DIR%Musify-X.apk"

if not exist "!APK_PATH!" (
    echo [INFO] Musify-X.apk not found. Running build pipeline...
    python "%SCRIPT_DIR%build.py"
    if !errorlevel! neq 0 (
        echo [ERROR] Build pipeline failed.
        pause
        exit /b 1
    )
)

echo.
echo [1/5] Checking Android Emulator status...
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
echo [2/5] Waiting for Android system boot completion...
:wait_boot
for /f "tokens=*" %%a in ('"%ADB_EXE%" shell getprop sys.boot_completed 2^>nul') do (
    set "BOOT_DONE=%%a"
)
set "BOOT_DONE=!BOOT_DONE:~0,1!"
if not "!BOOT_DONE!"=="1" (
    timeout /t 2 /nobreak >nul
    goto wait_boot
)
echo Android system booted successfully!

echo.
echo [3/5] Installing Musify-X APK...
"%ADB_EXE%" install -r -d "!APK_PATH!"
if !errorlevel! neq 0 (
    echo [WARN] Direct install failed, attempting clean reinstall...
    "%ADB_EXE%" uninstall "!PACKAGE_NAME!" >nul 2>&1
    "%ADB_EXE%" install "!APK_PATH!"
)

echo.
echo [4/5] Launching Musify-X...
"%ADB_EXE%" shell am force-stop "!PACKAGE_NAME!" >nul 2>&1
timeout /t 1 /nobreak >nul
"%ADB_EXE%" shell am start -n "!PACKAGE_NAME!/!MAIN_ACTIVITY!"
timeout /t 3 /nobreak >nul

echo.
echo [5/5] Verifying application state...
"%ADB_EXE%" shell pidof "!PACKAGE_NAME!" >nul 2>&1
if !errorlevel! equ 0 (
    echo [SUCCESS] Musify-X is active and running on emulator!
) else (
    echo [ERROR] Musify-X process not detected.
)

echo.
echo ========================================================
echo  Test Runner Complete.
echo ========================================================
pause
