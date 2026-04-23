@echo off
echo Starting Campus Reminder System...

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5000" ^| findstr "LISTENING"') do taskkill /PID %%a /F >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8080" ^| findstr "LISTENING"') do taskkill /PID %%a /F >nul 2>&1

cd /d "%~dp0backend"
start "Backend" cmd /c python api_with_auth.py

cd /d "%~dp0backend"
start "Reminder Scheduler" cmd /c python reminder_scheduler.py

cd /d "%~dp0"
start "Frontend" cmd /c python -m http.server 8080

timeout /t 3 /nobreak >nul

start http://localhost:8080/frontend/login.html

echo.
echo System started successfully!
echo Backend:           http://localhost:5000
echo Frontend:          http://localhost:8080
echo Reminder Scheduler: Running (checks every minute)
echo.
echo Note: Keep all windows open for the system to work properly
echo.
pause