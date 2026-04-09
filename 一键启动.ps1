# ================================================
# 校园事务自动提醒系统 - 一键启动脚本
# ================================================

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "校园事务自动提醒系统 - 启动中..." -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# 获取脚本所在目录
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

# 检查Python是否安装
Write-Host "[1/4] 检查Python环境..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "      ✓ Python已安装: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "      ✗ 未找到Python，请先安装Python 3.8+" -ForegroundColor Red
    Write-Host ""
    Write-Host "按任意键退出..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}

# 检查后端配置文件
Write-Host "[2/4] 检查配置文件..." -ForegroundColor Yellow
$envFile = Join-Path $scriptPath "backend\.env"
if (-Not (Test-Path $envFile)) {
    Write-Host "      ✗ 配置文件不存在: backend\.env" -ForegroundColor Red
    Write-Host "      请先配置数据库密码" -ForegroundColor Red
    Write-Host ""
    Write-Host "按任意键退出..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}
Write-Host "      ✓ 配置文件存在" -ForegroundColor Green

# 启动后端服务
Write-Host "[3/4] 启动后端服务..." -ForegroundColor Yellow
$backendPath = Join-Path $scriptPath "backend"
$backendScript = Join-Path $backendPath "api_with_auth.py"

if (-Not (Test-Path $backendScript)) {
    Write-Host "      ✗ 后端脚本不存在: $backendScript" -ForegroundColor Red
    exit 1
}

# 启动后端（新窗口）
$backendProcess = Start-Process -FilePath "python" -ArgumentList $backendScript -WorkingDirectory $backendPath -PassThru -WindowStyle Normal
Write-Host "      ✓ 后端服务已启动 (PID: $($backendProcess.Id))" -ForegroundColor Green
Write-Host "      后端地址: http://localhost:5000" -ForegroundColor Cyan

# 等待后端启动
Write-Host "      等待后端服务就绪..." -ForegroundColor Gray
Start-Sleep -Seconds 3

# 启动前端服务
Write-Host "[4/4] 启动前端服务..." -ForegroundColor Yellow
$frontendProcess = Start-Process -FilePath "python" -ArgumentList "-m", "http.server", "8080" -WorkingDirectory $scriptPath -PassThru -WindowStyle Normal
Write-Host "      ✓ 前端服务已启动 (PID: $($frontendProcess.Id))" -ForegroundColor Green
Write-Host "      前端地址: http://localhost:8080" -ForegroundColor Cyan

# 等待前端启动
Start-Sleep -Seconds 2

# 打开浏览器
Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "✓ 系统启动成功！" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "服务信息：" -ForegroundColor Cyan
Write-Host "  后端服务: http://localhost:5000 (PID: $($backendProcess.Id))" -ForegroundColor White
Write-Host "  前端服务: http://localhost:8080 (PID: $($frontendProcess.Id))" -ForegroundColor White
Write-Host ""
Write-Host "正在打开浏览器..." -ForegroundColor Yellow
Start-Process "http://localhost:8080/frontend/login.html"

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "测试账号（密码：xtu123456）：" -ForegroundColor Cyan
Write-Host "  - 202205570603 (张三)" -ForegroundColor White
Write-Host "  - 202205570610 (李四)" -ForegroundColor White
Write-Host "  - 202205580501 (王五)" -ForegroundColor White
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "提示：" -ForegroundColor Yellow
Write-Host "  - 按 Ctrl+C 停止此脚本" -ForegroundColor Gray
Write-Host "  - 关闭后端和前端窗口以完全停止服务" -ForegroundColor Gray
Write-Host "  - 或运行 停止服务.ps1 一键停止所有服务" -ForegroundColor Gray
Write-Host ""

# 保存进程ID到文件，方便后续停止
$backendProcess.Id | Out-File -FilePath (Join-Path $scriptPath ".backend.pid") -Encoding UTF8
$frontendProcess.Id | Out-File -FilePath (Join-Path $scriptPath ".frontend.pid") -Encoding UTF8

Write-Host "服务运行中，请勿关闭此窗口..." -ForegroundColor Green
Write-Host "按 Ctrl+C 或关闭窗口以停止" -ForegroundColor Green
Write-Host ""

# 保持脚本运行
try {
    while ($true) {
        # 检查进程是否还在运行
        if ($backendProcess.HasExited) {
            Write-Host ""
            Write-Host "⚠ 后端进程已退出" -ForegroundColor Red
            break
        }
        if ($frontendProcess.HasExited) {
            Write-Host ""
            Write-Host "⚠ 前端进程已退出" -ForegroundColor Red
            break
        }
        Start-Sleep -Seconds 2
    }
} catch {
    Write-Host ""
    Write-Host "正在停止服务..." -ForegroundColor Yellow
}

# 清理
Write-Host "清理进程..." -ForegroundColor Gray
if (-Not $backendProcess.HasExited) {
    Stop-Process -Id $backendProcess.Id -Force -ErrorAction SilentlyContinue
}
if (-Not $frontendProcess.HasExited) {
    Stop-Process -Id $frontendProcess.Id -Force -ErrorAction SilentlyContinue
}

# 删除PID文件
Remove-Item -Path (Join-Path $scriptPath ".backend.pid") -ErrorAction SilentlyContinue
Remove-Item -Path (Join-Path $scriptPath ".frontend.pid") -ErrorAction SilentlyContinue

Write-Host "服务已停止" -ForegroundColor Green
Write-Host ""
Write-Host "按任意键退出..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
