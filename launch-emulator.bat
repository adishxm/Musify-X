@echo off
setlocal enabledelayedexpansion
title Musify-X - Launch Android Emulator
color 0B

echo ========================================================
echo          Musify-X Android Emulator Launcher
echo          Target: Medium_Phone (API 36, x86_64)
echo ========================================================
echo.

set "SCRIPT_DIR=%~dp0"
if defined LOCALAPPDATA (
    set "SDK_DIR=%LOCALAPPDATA%\Android\Sdk"
) else (
    set "SDK_DIR=C:\Users\adity\AppData\Local\Android\Sdk"
)
if not exist "%SDK_DIR%" set "SDK_DIR=C:\Users\adity\AppData\Local\Android\Sdk"

set "EMULATOR_DIR=%SDK_DIR%\emulator"
set "EMULATOR_EXE=%EMULATOR_DIR%\emulator.exe"
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
    echo [ERROR] Android emulator executable not found at:
    echo %EMULATOR_EXE%
    echo Please verify Android SDK installation.
    echo.
    pause
    exit /b 1
)

:: Check if an existing emulator or QEMU process is running
tasklist /fi "imagename eq qemu-system-x86_64.exe" 2>nul | findstr /i "qemu" >nul
set "IS_QEMU_RUNNING=%errorlevel%"

if %IS_QEMU_RUNNING% equ 0 (
    echo [NOTICE] An emulator process is already detected running on your system.
    echo.
    set /p "CHOICE=Do you want to restart it fresh? [Y/N, default N]: "
    if "!CHOICE!"=="" set "CHOICE=N"
    if /i "!CHOICE!"=="Y" (
        echo Terminating existing emulator process...
        "%ADB_EXE%" emu kill >nul 2>&1
        taskkill /f /im qemu-system-x86_64.exe >nul 2>&1
        taskkill /f /im emulator.exe >nul 2>&1
        timeout /t 2 >nul
    ) else (
        echo Keeping running emulator. Checking Musify-X launch status...
        goto launch_app
    )
)

:: Auto-clean stale AVD lock files if process is not running
del /f /q /a "%USERPROFILE%\.android\avd\Medium_Phone.avd\*.lock" >nul 2>&1
rd /s /q "%USERPROFILE%\.android\avd\Medium_Phone.avd\hardware-qemu.ini.lock" >nul 2>&1
del /f /q /a "%USERPROFILE%\.android\avd\Medium_Phone.avd\multiinstance.lock" >nul 2>&1
del /f /q /a "%USERPROFILE%\.android\avd\Medium_Phone_API_36.1.avd\*.lock" >nul 2>&1
rd /s /q "%USERPROFILE%\.android\avd\Medium_Phone_API_36.1.avd\hardware-qemu.ini.lock" >nul 2>&1
del /f /q /a "%USERPROFILE%\.android\avd\Medium_Phone_API_36.1.avd\multiinstance.lock" >nul 2>&1

if exist "%USERPROFILE%\.android\avd\Medium_Phone.avd\snapshots\default_boot\ram.img.dirty" (
    rd /s /q "%USERPROFILE%\.android\avd\Medium_Phone.avd\snapshots\default_boot" >nul 2>&1
)
if exist "%USERPROFILE%\.android\avd\Medium_Phone_API_36.1.avd\snapshots\default_boot\ram.img.dirty" (
    rd /s /q "%USERPROFILE%\.android\avd\Medium_Phone_API_36.1.avd\snapshots\default_boot" >nul 2>&1
)

echo.
echo Starting Android Emulator '%AVD_NAME%'...
pushd "%EMULATOR_DIR%"

start "Medium Phone - Musify-X Emulator" emulator.exe -avd "%AVD_NAME%" -no-snapshot-load

popd

echo Waiting for emulator process to initialize...
timeout /t 4 >nul

echo [1/2] Waiting for ADB device connection...
"%ADB_EXE%" wait-for-device

echo [2/2] Waiting for Android system boot completion...
:wait_boot
for /f "tokens=*" %%a in ('"%ADB_EXE%" shell getprop sys.boot_completed 2^>nul') do set "BOOT_STATUS=%%a"
if not "!BOOT_STATUS!"=="1" (
    timeout /t 2 >nul
    goto wait_boot
)

:launch_app
echo.
echo ========================================================
echo  [SUCCESS] Android Emulator is booted and ready!
echo  Checking and launching Musify-X...
echo ========================================================

set "MUSIFYX_PKG="
for /f "tokens=2 delims=:" %%p in ('"%ADB_EXE%" shell pm list packages com.brave.browser_nightly 2^>nul') do (
    set "MUSIFYX_PKG=%%p"
)
if not defined MUSIFYX_PKG (
    for /f "tokens=2 delims=:" %%p in ('"%ADB_EXE%" shell pm list packages musifyx 2^>nul') do (
        set "MUSIFYX_PKG=%%p"
    )
)

if not defined MUSIFYX_PKG (
    if exist "%SCRIPT_DIR%Musify-X.apk" (
        echo Installing Musify-X build...
        "%ADB_EXE%" install -r -d -g "%SCRIPT_DIR%Musify-X.apk"
        for /f "tokens=2 delims=:" %%p in ('"%ADB_EXE%" shell pm list packages musifyx 2^>nul') do (
            set "MUSIFYX_PKG=%%p"
        )
    )
)

if defined MUSIFYX_PKG (
    echo Found installed Musify-X package: !MUSIFYX_PKG!
    echo Launching Musify-X on emulator...
    "%ADB_EXE%" shell monkey -p !MUSIFYX_PKG! -c android.intent.category.LAUNCHER 1 >nul 2>&1
    echo Musify-X launched successfully!
) else (
    echo Musify-X is not yet installed on the emulator.
    echo Run 'test-on-emulator.bat' to install and test Musify-X.
)

echo.
pause
