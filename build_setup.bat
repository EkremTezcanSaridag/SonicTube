@echo off
title SonicTube Setup Derleyici
cd /d "%~dp0"

echo ========================================
echo    SonicTube Setup (.exe) Uretici
echo ========================================

if not exist "dist\SonicTube\SonicTube.exe" (
    echo [1/2] Uygulama binaryleri bulunamadi, once derleniyor...
    call .venv\Scripts\activate.bat
    python build_exe.py
) else (
    echo [1/2] Uygulama binaryleri hazir.
)

set "ISCC_PATH=C:\Users\%USERNAME%\AppData\Local\Programs\Inno Setup 6\ISCC.exe"
if not exist "%ISCC_PATH%" (
    set "ISCC_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
)
if not exist "%ISCC_PATH%" (
    set "ISCC_PATH=C:\Program Files\Inno Setup 6\ISCC.exe"
)

if not exist "%ISCC_PATH%" (
    echo [HATA] Inno Setup derleyicisi bulunamadi!
    echo Lutfen Inno Setup 6 yuklu oldugundan emin olun.
    pause
    exit /b 1
)

echo [2/2] Setup dosyasi olusturuluyor...
"%ISCC_PATH%" installer.iss

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo [OK] TEBRIKLER! Setup Basariyla Uretildi!
    echo Konum: dist\installer\SonicTube-Setup-v1.0.exe
    echo ========================================
) else (
    echo.
    echo [HATA] Setup olusturulurken bir hata olustu.
)

pause
