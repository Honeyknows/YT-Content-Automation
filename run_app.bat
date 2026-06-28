@echo off
title Run YT Content automation App

if not exist venv\Scripts\activate.bat (
    echo [ERROR] Environment not found! Please run setup_app.bat first.
    pause
    exit /b
)

if "%~1"=="hidden" goto :run
echo CreateObject("WScript.Shell").Run """%~f0"" hidden", 0, False > "%temp%\hide.vbs"
cscript //nologo "%temp%\hide.vbs"
del "%temp%\hide.vbs"
exit /b

:run
cd /d "%~dp0"
call venv\Scripts\activate.bat
python main.py
