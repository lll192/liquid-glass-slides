param(
    [string]$Workspace,
    [switch]$CheckOnly
)

$ErrorActionPreference = "Stop"
$engineRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$appDataRoot = Join-Path $env:LOCALAPPDATA "LiquidGlassSlides"
$configPath = Join-Path $appDataRoot "config.json"

if (-not (Test-Path -LiteralPath $configPath)) {
    Write-Host "首次运行，先完成安装……" -ForegroundColor Yellow
    & (Join-Path $PSScriptRoot "install_windows.ps1")
}

$config = Get-Content -Raw -LiteralPath $configPath | ConvertFrom-Json
$selectedWorkspace = if ($Workspace) { $Workspace } else { [string]$config.workspace }
New-Item -ItemType Directory -Force -Path $selectedWorkspace | Out-Null

if (-not (Test-Path -LiteralPath ([string]$config.python))) {
    throw "配置中的 Python 不存在，请删除 $configPath 后重新运行。"
}
if (-not (Test-Path -LiteralPath (Join-Path $engineRoot "scripts\api_server.py"))) {
    throw "没有找到本地控制台服务，请确认项目文件完整。"
}

if ($CheckOnly) {
    Write-Host "启动入口检查通过。" -ForegroundColor Green
    Write-Host "Python：$($config.python)"
    Write-Host "工作目录：$selectedWorkspace"
    exit 0
}

try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8765/health" -TimeoutSec 2
    if ($health.ok) {
        Write-Host "控制台已经在运行，正在打开浏览器……" -ForegroundColor Green
        Start-Process "http://127.0.0.1:8765/"
        exit 0
    }
} catch {
    # No local server is listening yet; continue with a fresh start.
}

$pythonArguments = @()
if ($config.python_arguments) { $pythonArguments = @($config.python_arguments) }
$serverArguments = $pythonArguments + @(
    (Join-Path $engineRoot "scripts\api_server.py"),
    "--workspace", $selectedWorkspace,
    "--host", "127.0.0.1",
    "--port", "8765",
    "--open"
)

Write-Host ""
Write-Host "Liquid Glass Slides 正在运行" -ForegroundColor Cyan
Write-Host "项目目录：$selectedWorkspace"
Write-Host "浏览器会自动打开。关闭此窗口即可停止服务。"
Write-Host ""
& ([string]$config.python) @serverArguments

