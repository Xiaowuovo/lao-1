# ================================================
# 校园事务自动提醒系统 - 停止服务脚本
# ================================================

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "停止系统服务..." -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# 获取脚本所在目录
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

$stopped = $false

# 尝试从PID文件读取并停止
$backendPidFile = Join-Path $scriptPath ".backend.pid"
$frontendPidFile = Join-Path $scriptPath ".frontend.pid"

if (Test-Path $backendPidFile) {
    $backendPid = Get-Content $backendPidFile -ErrorAction SilentlyContinue
    if ($backendPid) {
        try {
            Stop-Process -Id $backendPid -Force -ErrorAction SilentlyContinue
            Write-Host "✓ 已停止后端服务 (PID: $backendPid)" -ForegroundColor Green
            $stopped = $true
        } catch {
            Write-Host "✗ 停止后端服务失败" -ForegroundColor Red
        }
    }
    Remove-Item $backendPidFile -ErrorAction SilentlyContinue
}

if (Test-Path $frontendPidFile) {
    $frontendPid = Get-Content $frontendPidFile -ErrorAction SilentlyContinue
    if ($frontendPid) {
        try {
            Stop-Process -Id $frontendPid -Force -ErrorAction SilentlyContinue
            Write-Host "✓ 已停止前端服务 (PID: $frontendPid)" -ForegroundColor Green
            $stopped = $true
        } catch {
            Write-Host "✗ 停止前端服务失败" -ForegroundColor Red
        }
    }
    Remove-Item $frontendPidFile -ErrorAction SilentlyContinue
}

# 如果没有找到PID文件，尝试按进程名停止
if (-Not $stopped) {
    Write-Host "未找到PID文件，尝试按进程名停止..." -ForegroundColor Yellow
    
    # 停止所有Python进程（谨慎使用）
    $pythonProcesses = Get-Process -Name "python" -ErrorAction SilentlyContinue
    if ($pythonProcesses) {
        Write-Host ""
        Write-Host "发现以下Python进程：" -ForegroundColor Cyan
        foreach ($proc in $pythonProcesses) {
            Write-Host "  PID: $($proc.Id), 路径: $($proc.Path)" -ForegroundColor Gray
        }
        
        Write-Host ""
        $confirm = Read-Host "是否停止所有Python进程? (y/n)"
        if ($confirm -eq "y" -or $confirm -eq "Y") {
            Stop-Process -Name "python" -Force -ErrorAction SilentlyContinue
            Write-Host "✓ 已停止所有Python进程" -ForegroundColor Green
            $stopped = $true
        } else {
            Write-Host "已取消" -ForegroundColor Yellow
        }
    }
}

if ($stopped) {
    Write-Host ""
    Write-Host "================================================" -ForegroundColor Green
    Write-Host "✓ 服务已停止" -ForegroundColor Green
    Write-Host "================================================" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "================================================" -ForegroundColor Yellow
    Write-Host "未找到运行中的服务" -ForegroundColor Yellow
    Write-Host "================================================" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "按任意键退出..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
