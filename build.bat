@echo off
title SonicTube EXE Olusturucu
cd /d "%~dp0"

echo [SonicTube] EXE derleme baslatiliyor...
call .venv\Scripts\activate.bat
python build_exe.py

pause
