@echo off
chcp 936 >nul
title Campus Reminder System

echo ========================================
echo   Starting Campus Reminder System...
echo ========================================
echo.

echo [1] Starting backend server (port 5000)...
cd /d "%~dp0backend"
start "Backend-5000" cmd /k "venv\Scripts\activate.bat && python api_with_auth.py"

timeout /t 3 /nobreak >nul

echo [2] Starting frontend server (port 8080)...
cd /d "%~dp0"
start "Frontend-8080" cmd /k "python -m http.server 8080"

timeout /t 2 /nobreak >nul

echo [3] Opening browser...
start http://localhost:8080/frontend/login.html

echo.
echo ========================================
echo   System Started!
echo ========================================
echo.
echo Frontend: http://localhost:8080/frontend/login.html
echo Backend:  http://localhost:5000
echo.
echo Test account:
echo   Student ID: 202205570603
echo   Password: xtu123456
echo.
echo To stop: close the Backend and Frontend windows
echo.
pause
