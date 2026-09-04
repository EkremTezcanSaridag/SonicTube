@echo off
title SonicTube Launcher
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [SonicTube] Ilk kurulum yapiliyor, lutfen bekleyin...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install -r requirements.txt
)

echo [SonicTube] Baslatiliyor...
start "" ".venv\Scripts\pythonw.exe" src\main.py
if %ERRORLEVEL% NEQ 0 (
    ".venv\Scripts\python.exe" src\main.py
)
exit
