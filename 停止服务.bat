@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ================================================
:: 校园事务自动提醒系统 - 停止服务脚本
:: ================================================

echo.
echo ================================================
echo 停止系统服务...
echo ================================================
echo.

:: 停止所有Python进程
set "found=0"

:: 检查是否有Python进程
tasklist /FI "IMAGENAME eq python.exe" 2>NUL | find /I /N "python.exe">NUL
if "%ERRORLEVEL%"=="0" (
    set "found=1"
    echo 发现Python进程，正在停止...
    taskkill /F /IM python.exe >nul 2>&1
    if errorlevel 1 (
        echo    X 停止失败，请以管理员身份运行
    ) else (
        echo    √ 已停止所有Python进程
    )
)

if "%found%"=="0" (
    echo 未发现运行中的Python进程
)

echo.
echo ================================================
echo √ 服务停止完成
echo ================================================
echo.
echo 提示：
echo   - 如果服务窗口仍然存在，请手动关闭
echo   - 或在任务管理器中结束python.exe进程
echo.
pause
