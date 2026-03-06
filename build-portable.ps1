# CivSim Portable Builder - PowerShell Version
# Run: powershell -ExecutionPolicy Bypass -File build-portable.ps1

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  CivSim Portable Builder" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

$SourceDir = $PSScriptRoot
$ReleaseDir = Join-Path $SourceDir "target\release"
$PortableDir = Join-Path $SourceDir "CivSim-Portable"
$FrontendDir = Join-Path $SourceDir "frontend"

# Step 1: Check Frontend
Write-Host "[Step 1] Checking frontend build..." -ForegroundColor Yellow
if (-not (Test-Path (Join-Path $FrontendDir "dist"))) {
    Write-Host "Frontend not built! Building..." -ForegroundColor Red
    Set-Location $FrontendDir
    
    # Detect package manager
    if (Test-Path (Join-Path $FrontendDir "pnpm-lock.yaml")) {
        $PkgCmd = "pnpm"
    } elseif (Test-Path (Join-Path $FrontendDir "yarn.lock")) {
        $PkgCmd = "yarn"
    } else {
        $PkgCmd = "npm"
    }
    
    Write-Host "Using: $PkgCmd" -ForegroundColor Green
    & $PkgCmd install
    & $PkgCmd run build
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Frontend build failed!" -ForegroundColor Red
        pause
        exit 1
    }
    Set-Location $SourceDir
} else {
    Write-Host "Frontend already built ✓" -ForegroundColor Green
}

# Step 2: Build Rust
Write-Host ""
Write-Host "[Step 2] Building Rust backend (this may take a few minutes)..." -ForegroundColor Yellow
Set-Location $SourceDir
cargo build --release 2>&1 | ForEach-Object { Write-Host $_ }

if ($LASTEXITCODE -ne 0) {
    Write-Host "Rust build failed!" -ForegroundColor Red
    pause
    exit 1
}
Write-Host "Rust build complete ✓" -ForegroundColor Green

# Step 3: Create Directory
Write-Host ""
Write-Host "[Step 3] Creating portable directory..." -ForegroundColor Yellow
if (Test-Path $PortableDir) {
    Remove-Item -Recurse -Force $PortableDir
}
New-Item -ItemType Directory -Force -Path $PortableDir | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $PortableDir "data") | Out-Null
Write-Host "Directory created ✓" -ForegroundColor Green

# Step 4: Copy Files
Write-Host ""
Write-Host "[Step 4] Copying files..." -ForegroundColor Yellow

# Copy EXE
Copy-Item (Join-Path $ReleaseDir "CivSim.exe") $PortableDir -Force
Write-Host "  - CivSim.exe" -ForegroundColor Gray

# Copy DLLs
$DllFiles = Get-ChildItem (Join-Path $ReleaseDir "*.dll") -ErrorAction SilentlyContinue
$DllCount = 0
foreach ($dll in $DllFiles) {
    Copy-Item $dll.FullName $PortableDir -Force
    Write-Host "  - $($dll.Name)" -ForegroundColor Gray
    $DllCount++
}
Write-Host "Copied $DllCount DLL files ✓" -ForegroundColor Green

# Step 5: Create Launchers
Write-Host ""
Write-Host "[Step 5] Creating launchers..." -ForegroundColor Yellow

# Start.bat
$StartBat = @"
@echo off
echo Starting CivSim...
start CivSim.exe
"@
Set-Content -Path (Join-Path $PortableDir "Start.bat") -Value $StartBat -Encoding ASCII

# README.txt
$Readme = @"
========================================
CivSim Portable Edition
========================================

QUICK START:
1. Rename .env.example to .env
2. Edit .env and add your API key
3. Double-click Start.bat to run

API Key: https://dashscope.console.aliyun.com/

FEATURES:
- No installation required
- No registry changes
- Saves in data/ folder
- Can run from USB drive
"@
Set-Content -Path (Join-Path $PortableDir "README.txt") -Value $Readme -Encoding ASCII

# .env.example
$EnvExample = @"
# Add your DashScope API key here
# Get it from: https://dashscope.console.aliyun.com/
DASHSCOPE_API_KEY=sk-your-api-key-here
"@
Set-Content -Path (Join-Path $PortableDir ".env.example") -Value $EnvExample -Encoding ASCII

Write-Host "Launchers created ✓" -ForegroundColor Green

# Final Summary
Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "  BUILD COMPLETE!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Output: $PortableDir" -ForegroundColor Cyan
Write-Host ""
Write-Host "Files:" -ForegroundColor Yellow
Get-ChildItem $PortableDir | ForEach-Object {
    $size = if ($_.Length -gt 1MB) { "{0:N1} MB" -f ($_.Length / 1MB) } else { "{0:N1} KB" -f ($_.Length / 1KB) }
    Write-Host "  - $($_.Name) ($size)" -ForegroundColor Gray
}
Write-Host ""
Write-Host "NEXT STEPS:" -ForegroundColor Yellow
Write-Host "1. Copy CivSim-Portable folder to any location" -ForegroundColor White
Write-Host "2. Rename .env.example to .env" -ForegroundColor White
Write-Host "3. Edit .env and add your API key" -ForegroundColor White
Write-Host "4. Double-click Start.bat to run" -ForegroundColor White
Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
