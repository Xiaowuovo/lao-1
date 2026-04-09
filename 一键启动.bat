@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ================================================
:: 校园事务自动提醒系统 - 一键启动脚本
:: ================================================

echo.
echo ================================================
echo 校园事务自动提醒系统 - 启动中...
echo ================================================
echo.

:: 获取脚本所在目录
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

:: 检查Python
echo [1/4] 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo       X 未找到Python，请先安装Python 3.8+
    echo.
    pause
    exit /b 1
)
echo       √ Python已安装
echo.

:: 检查配置文件
echo [2/4] 检查配置文件...
if not exist "backend\.env" (
    echo       X 配置文件不存在: backend\.env
    echo       请先配置数据库密码
    echo.
    pause
    exit /b 1
)
echo       √ 配置文件存在
echo.

:: 检查后端脚本
if not exist "backend\api_with_auth.py" (
    echo       X 后端脚本不存在
    echo.
    pause
    exit /b 1
)

:: 启动后端
echo [3/4] 启动后端服务...
start "后端服务" /MIN cmd /c "cd /d "%SCRIPT_DIR%backend" && python api_with_auth.py"
echo       √ 后端服务已启动
echo       后端地址: http://localhost:5000
echo.

:: 等待后端启动
echo       等待后端服务就绪...
timeout /t 3 /nobreak >nul

:: 启动前端
echo [4/4] 启动前端服务...
start "前端服务" /MIN cmd /c "cd /d "%SCRIPT_DIR%" && python -m http.server 8080"
echo       √ 前端服务已启动
echo       前端地址: http://localhost:8080
echo.

:: 等待前端启动
timeout /t 2 /nobreak >nul

:: 打开浏览器
echo.
echo ================================================
echo √ 系统启动成功！
echo ================================================
echo.
echo 服务信息：
echo   后端服务: http://localhost:5000
echo   前端服务: http://localhost:8080
echo.
echo 正在打开浏览器...
start http://localhost:8080/frontend/login.html

echo.
echo ================================================
echo 测试账号（密码：xtu123456）：
echo   - 202205570603 (张三)
echo   - 202205570610 (李四)
echo   - 202205580501 (王五)
echo ================================================
echo.
echo 提示：
echo   - 后端和前端服务运行在独立窗口中
echo   - 关闭对应窗口可停止服务
echo   - 或运行"停止服务.bat"一键停止
echo.
echo 按任意键关闭此窗口（服务会继续运行）...
pause >nul
