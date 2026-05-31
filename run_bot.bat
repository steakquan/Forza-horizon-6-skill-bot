@echo off
title Forza Horizon 6 Skill Bot
echo ===================================================
echo   Forza Horizon 6 Skill Bot Starting...
echo ===================================================
echo.
cd /d "%~dp0"
"C:\Users\a0985\AppData\Local\Programs\Python\Python312\python.exe" gui.py
if errorlevel 1 (
    echo.
    echo   An error occurred.
    echo   Please verify you are running as Administrator.
    echo.
    pause
)
