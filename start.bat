@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo Starting API Key Manager...
start "API Key Manager" cmd /k python app.py

timeout /t 3 /nobreak >nul
start "" http://localhost:5000

exit
