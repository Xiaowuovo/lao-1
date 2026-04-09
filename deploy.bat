@echo off
chcp 936 >nul
title Campus Reminder System - Deploy

echo ========================================
echo   Campus Reminder System v2.0
echo   One-Click Deploy
echo ========================================
echo.

echo [1/5] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo Please install Python 3.8+ from https://www.python.org/downloads/
    pause
    exit /b 1
)
echo [OK] Python installed
echo.

echo [2/5] Creating virtual environment...
cd /d "%~dp0backend"
if not exist "venv\" (
    python -m venv venv
    echo [OK] Virtual environment created
) else (
    echo [OK] Virtual environment exists
)
echo.

echo [3/5] Installing dependencies...
call venv\Scripts\activate.bat
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
echo [OK] Dependencies installed
echo.

echo [4/5] Creating config file...
if not exist ".env" (
    echo DB_HOST=localhost> .env
    echo DB_USER=root>> .env
    echo DB_PASSWORD=>> .env
    echo DB_NAME=campus_reminder_system>> .env
    echo [!] Please edit backend\.env and set DB_PASSWORD
)
echo [OK] Config file ready
echo.

echo [5/5] Database setup...
echo Please run this command manually in CMD:
echo.
echo   mysql -u root -p ^< init_database.sql
echo.

echo ========================================
echo   Deploy Complete!
echo ========================================
echo.
echo Next steps:
echo   1. Edit backend\.env - set your MySQL password
echo   2. Run: mysql -u root -p ^< init_database.sql
echo   3. Run: start.bat
echo.
echo Test account:
echo   Student ID: 202205570603
echo   Password: xtu123456
echo.
pause
