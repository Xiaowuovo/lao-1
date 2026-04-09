@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ================================================
:: 项目清理脚本 - 删除冗余文件
:: ================================================

echo.
echo ================================================
echo 开始清理项目冗余文件...
echo ================================================
echo.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo [1/2] 清理后端冗余文件...
echo.

:: 删除旧的API文件
if exist "backend\api_enhanced.py" (
    del /F /Q "backend\api_enhanced.py"
    echo    √ 已删除: backend\api_enhanced.py
)

if exist "backend\index.py" (
    del /F /Q "backend\index.py"
    echo    √ 已删除: backend\index.py
)

:: 删除旧的event文件
if exist "backend\event.py" (
    del /F /Q "backend\event.py"
    echo    √ 已删除: backend\event.py
)

:: 删除config文件（配置已在.env中）
if exist "backend\config.py" (
    del /F /Q "backend\config.py"
    echo    √ 已删除: backend\config.py
)

:: 删除重复的requirements文件
if exist "backend\requirements_enhanced.txt" (
    del /F /Q "backend\requirements_enhanced.txt"
    echo    √ 已删除: backend\requirements_enhanced.txt
)

echo.
echo [2/2] 清理前端冗余文件...
echo.

:: 删除旧的增强版JS文件（功能已整合到原文件）
if exist "frontend\index_enhanced.js" (
    del /F /Q "frontend\index_enhanced.js"
    echo    √ 已删除: frontend\index_enhanced.js
)

echo.
echo ================================================
echo √ 清理完成！
echo ================================================
echo.
echo 保留的核心文件：
echo.
echo 后端核心文件：
echo   - backend\api_with_auth.py  (主API服务，唯一入口)
echo   - backend\auth.py           (认证模块)
echo   - backend\event_enhanced.py (事件提取)
echo   - backend\location_matcher.py (地点匹配)
echo   - backend\conflict_detector.py (冲突检测)
echo   - backend\file_processor.py (文件处理)
echo   - backend\.env             (配置文件)
echo   - backend\requirements.txt (依赖清单)
echo.
echo 前端核心文件：
echo   - frontend\*.html (所有HTML页面)
echo   - frontend\*.js   (所有JS脚本)
echo   - frontend\*.css  (所有样式文件)
echo.
echo 启动脚本：
echo   - 一键启动.bat
echo   - 停止服务.bat
echo.
echo ================================================
echo 提示：
echo   - 现在只需启动 api_with_auth.py 一个文件
echo   - 使用"一键启动.bat"自动启动
echo   - 所有功能已集成到一个后端服务
echo ================================================
echo.
pause
