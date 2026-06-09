@echo off
title Forza Horizon 6 Skill Bot
cd /d "%~dp0"

:: 1. Find Python executable
set PYTHON_EXE=python
set PYTHONW_EXE=pythonw

:: Test if system python works
python --version >nul 2>nul
if %errorlevel% equ 0 goto :python_found

:: Fallback check local path 3.14 (pythoncore)
if exist "%LocalAppData%\Python\pythoncore-3.14-64\python.exe" (
    set PYTHON_EXE="%LocalAppData%\Python\pythoncore-3.14-64\python.exe"
    set PYTHONW_EXE="%LocalAppData%\Python\pythoncore-3.14-64\pythonw.exe"
    goto :python_found
)

:: Fallback check local path 3.12
if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
    set PYTHON_EXE="%LocalAppData%\Programs\Python\Python312\python.exe"
    set PYTHONW_EXE="%LocalAppData%\Programs\Python\Python312\pythonw.exe"
    goto :python_found
)

:: Fallback check local path 3.13
if exist "%LocalAppData%\Programs\Python\Python313\python.exe" (
    set PYTHON_EXE="%LocalAppData%\Programs\Python\Python313\python.exe"
    set PYTHONW_EXE="%LocalAppData%\Programs\Python\Python313\pythonw.exe"
    goto :python_found
)

:: Fallback check local path 3.14
if exist "%LocalAppData%\Programs\Python\Python314\python.exe" (
    set PYTHON_EXE="%LocalAppData%\Programs\Python\Python314\python.exe"
    set PYTHONW_EXE="%LocalAppData%\Programs\Python\Python314\pythonw.exe"
    goto :python_found
)

echo ===================================================
echo [錯誤 / ERROR] 系統找不到 Python 執行檔！
echo.
echo 1. 請確認您的電腦已安裝 Python 3.12 或以上版本。
echo 2. 安裝時務必勾選「Add Python to PATH」選項。
echo ===================================================
pause
exit /b 1

:python_found

:: 2. Check dependencies by attempting imports
%PYTHON_EXE% -c "import cv2, PIL, win32gui" >nul 2>nul
if %errorlevel% neq 0 (
    echo ===================================================
    echo [警告 / WARNING] 偵測到遺失必要的 Python 套件！
    echo 正在使用主控台模式啟動以顯示詳細錯誤訊息：
    echo ---------------------------------------------------
    %PYTHON_EXE% gui.py
    echo ---------------------------------------------------
    echo.
    echo 請執行 'install_requirements.bat' 以安裝所有必要套件。
    echo ===================================================
    pause
    exit /b 1
)

:: 3. Run the GUI silently using pythonw
echo 正在啟動小助手...
start "" %PYTHONW_EXE% gui.py
exit /b 0
