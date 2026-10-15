$ErrorActionPreference = "Stop"
$engineRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$appDataRoot = Join-Path $env:LOCALAPPDATA "LiquidGlassSlides"
$defaultWorkspace = Join-Path ([Environment]::GetFolderPath("MyDocuments")) "Liquid Glass Slides Projects"

function Test-PythonCandidate([string]$Executable, [string[]]$Arguments) {
    if (-not $Executable -or -not (Test-Path -LiteralPath $Executable)) { return $false }
    try {
        $ErrorActionPreference = "Continue"
        & $Executable @Arguments -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" *> $null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Find-Python {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py -and (Test-PythonCandidate $py.Source @("-3"))) {
        return @{ Executable = $py.Source; Arguments = @("-3") }
    }

    $candidates = @()
    foreach ($name in @("python", "python3")) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command) { $candidates += $command.Source }
    }
    $condaPython = if ($env:CONDA_PREFIX) { Join-Path $env:CONDA_PREFIX "python.exe" } else { $null }
    $candidates += @(
        $condaPython,
        (Join-Path $env:USERPROFILE "anaconda3\python.exe"),
        (Join-Path $env:USERPROFILE "miniconda3\python.exe"),
        "C:\ProgramData\anaconda3\python.exe",
        "D:\Anaconda3\python.exe"
    )
    foreach ($candidate in ($candidates | Where-Object { $_ } | Select-Object -Unique)) {
        if (Test-PythonCandidate $candidate @()) {
            return @{ Executable = $candidate; Arguments = @() }
        }
    }
    throw "未找到可用的 Python 3。请先从 https://www.python.org/downloads/ 安装 Python，并勾选 Add Python to PATH。"
}

Write-Host ""
Write-Host "Liquid Glass Slides · Windows 安装" -ForegroundColor Cyan
Write-Host "正在检查运行环境……"
$python = Find-Python
New-Item -ItemType Directory -Force -Path $appDataRoot, $defaultWorkspace | Out-Null

$doctorArgs = @($python.Arguments) + @((Join-Path $engineRoot "scripts\slides.py"), "--json", "doctor")
& $python.Executable @doctorArgs
if ($LASTEXITCODE -ne 0) { throw "生成引擎自检失败。" }

$skillArgs = @($python.Arguments) + @((Join-Path $engineRoot "scripts\install_plugin.py"), "--target", "codex", "--update")
& $python.Executable @skillArgs
if ($LASTEXITCODE -ne 0) { throw "Codex Skill 安装失败。" }

$config = [ordered]@{
    engine_root = $engineRoot
    workspace = $defaultWorkspace
    python = $python.Executable
    python_arguments = $python.Arguments
}
$config | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $appDataRoot "config.json") -Encoding UTF8

$launcher = Join-Path $engineRoot "打开控制台.cmd"
$desktop = [Environment]::GetFolderPath("Desktop")
if ($desktop -and (Test-Path -LiteralPath $launcher)) {
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut((Join-Path $desktop "Liquid Glass Slides.lnk"))
    $shortcut.TargetPath = $env:ComSpec
    $shortcut.Arguments = "/c `"`"$launcher`"`""
    $shortcut.WorkingDirectory = $engineRoot
    $shortcut.Description = "打开 Liquid Glass Slides 控制台"
    $shortcut.Save()
}

Write-Host ""
Write-Host "安装完成。" -ForegroundColor Green
Write-Host "默认项目目录：$defaultWorkspace"
Write-Host "桌面快捷方式：Liquid Glass Slides"
Write-Host "下一步：双击桌面快捷方式，或运行“打开控制台.cmd”。"
Write-Host "如果使用 Codex，请重启 Codex 后再开始。"

