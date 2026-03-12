# Windows 完整部署包构建脚本
# 输出: 包含Python 3.10环境的完整部署包
# 使用: powershell -ExecutionPolicy Bypass -File build-windows.ps1

param()

Write-Host "==========================================" -ForegroundColor Green
Write-Host "  Windows完整部署包构建" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""

$ScriptDir = $PSScriptRoot
$ProjectDir = Split-Path $ScriptDir -Parent
$OutputDir = Join-Path $ScriptDir "output"
$DeployDir = Join-Path $OutputDir "baseline-checker-windows"
$EmbedPython = Join-Path $ScriptDir "python310-embed"

# 步骤1: 检查Python嵌入版
Write-Host "[1/6] 检查Python 3.10嵌入版..." -ForegroundColor Yellow
if (-not (Test-Path $EmbedPython)) {
    Write-Host "  下载Python 3.10嵌入版..." -ForegroundColor Cyan
    $url = "https://www.python.org/ftp/python/3.10.11/python-3.10.11-embed-amd64.zip"
    $zipPath = Join-Path $ScriptDir "python-3.10.11-embed.zip"
    
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $url -OutFile $zipPath -UseBasicParsing
    
    Expand-Archive -Path $zipPath -DestinationPath $EmbedPython -Force
    
    # 配置._pth文件
    $pthContent = @"
python310.zip
.
Lib/site-packages
import site
"@
    Set-Content -Path (Join-Path $EmbedPython "python310._pth") -Value $pthContent -Encoding ASCII
    
    # 创建site-packages目录
    New-Item -ItemType Directory -Path (Join-Path $EmbedPython "Lib\site-packages") -Force | Out-Null
}
Write-Host "  完成" -ForegroundColor Green

# 步骤2: 清理
Write-Host "[2/6] 清理输出目录..." -ForegroundColor Yellow
Remove-Item -Recurse -Force $OutputDir -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1
New-Item -ItemType Directory -Path "$DeployDir\app" -Force | Out-Null
New-Item -ItemType Directory -Path "$DeployDir\python3" -Force | Out-Null
Write-Host "  完成" -ForegroundColor Green

# 步骤3: 复制Python
Write-Host "[3/6] 复制Python 3.10环境..." -ForegroundColor Yellow
Copy-Item "$EmbedPython\python.exe" "$DeployDir\python3\" -Force
Copy-Item "$EmbedPython\pythonw.exe" "$DeployDir\python3\" -Force
Copy-Item "$EmbedPython\python3.dll" "$DeployDir\python3\" -Force
Copy-Item "$EmbedPython\python310.dll" "$DeployDir\python3\" -Force
Copy-Item "$EmbedPython\python310.zip" "$DeployDir\python3\" -Force
Copy-Item "$EmbedPython\python310._pth" "$DeployDir\python3\" -Force
Copy-Item "$EmbedPython\*.pyd" "$DeployDir\python3\" -Force -ErrorAction SilentlyContinue
Copy-Item "$EmbedPython\*.dll" "$DeployDir\python3\" -Force -ErrorAction SilentlyContinue
if (Test-Path "$EmbedPython\Lib") {
    Copy-Item "$EmbedPython\Lib" "$DeployDir\python3\Lib" -Recurse -Force
}
Write-Host "  完成" -ForegroundColor Green

# 步骤4: 复制应用和依赖
Write-Host "[4/6] 复制应用程序..." -ForegroundColor Yellow
Copy-Item "$ProjectDir\run.py" "$DeployDir\app\" -Force
Copy-Item "$ProjectDir\app.py" "$DeployDir\app\" -Force
Copy-Item "$ProjectDir\models.py" "$DeployDir\app\" -Force
Copy-Item "$ProjectDir\config.py" "$DeployDir\app\" -Force
Copy-Item "$ProjectDir\requirements.txt" "$DeployDir\app\" -Force

robocopy "$ProjectDir\modules" "$DeployDir\app\modules" /E /R:0 /W:0 /NP /NFL /NDL | Out-Null
robocopy "$ProjectDir\scanners" "$DeployDir\app\scanners" /E /R:0 /W:0 /NP /NFL /NDL | Out-Null
robocopy "$ProjectDir\rules" "$DeployDir\app\rules" /E /R:0 /W:0 /NP /NFL /NDL | Out-Null
robocopy "$ProjectDir\templates" "$DeployDir\app\templates" /E /R:0 /W:0 /NP /NFL /NDL | Out-Null
robocopy "$ProjectDir\static" "$DeployDir\app\static" /E /R:0 /W:0 /NP /NFL /NDL | Out-Null

# 复制依赖
$sitePackages = "$DeployDir\python3\Lib\site-packages"
$libDir = Join-Path $ProjectDir "lib"
if (Test-Path $libDir) {
    robocopy $libDir $sitePackages /E /R:0 /W:0 /NP /NFL /NDL | Out-Null
}
Write-Host "  完成" -ForegroundColor Green

# 步骤5: 创建启动脚本
Write-Host "[5/6] 创建启动脚本..." -ForegroundColor Yellow
$startBat = @'
@echo off
chcp 65001 >nul
setlocal

set SCRIPT_DIR=%~dp0
set APP_DIR=%SCRIPT_DIR%app
set PYTHON_EXE=%SCRIPT_DIR%python3\python.exe
set PORT=8000

:parse
if "%~1"=="" goto run
if /i "%~1"=="-p" (set PORT=%~2& shift & shift & goto parse)
if /i "%~1"=="-d" (start /b "" "%PYTHON_EXE%" "%APP_DIR%\run.py" --port %PORT%& echo Started on port %PORT%& exit /b 0)
shift
goto parse

:run
cd /d "%APP_DIR%"
if not exist "database" mkdir database
if not exist "logs" mkdir logs

echo.
echo ========================================
echo    Security Baseline Checker
echo ========================================
echo.
echo Port: %PORT%
echo URL: http://localhost:%PORT%
echo User: admin / admin123
echo.

"%PYTHON_EXE%" run.py --port %PORT%
'@
Set-Content "$DeployDir\start.bat" $startBat -Encoding ASCII
Write-Host "  完成" -ForegroundColor Green

# 步骤6: 打包
Write-Host "[6/6] 打包..." -ForegroundColor Yellow
$ZipPath = Join-Path $OutputDir "baseline-checker-windows.zip"
Remove-Item $ZipPath -Force -ErrorAction SilentlyContinue

Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory($DeployDir, $ZipPath)

# 统计
$files = Get-ChildItem $DeployDir -Recurse -File
$totalMB = [math]::Round(($files | Measure-Object -Property Length -Sum).Sum / 1MB, 1)
$zipMB = [math]::Round((Get-Item $ZipPath).Length / 1MB, 1)

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "  构建完成!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "输出: $ZipPath" -ForegroundColor Cyan
Write-Host "大小: $zipMB MB (解压: $totalMB MB)" -ForegroundColor Cyan
Write-Host ""
Write-Host "使用: 解压后双击 start.bat" -ForegroundColor Yellow
