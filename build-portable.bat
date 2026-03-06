@echo off
chcp 936 >nul
echo ==========================================
echo CivSim Portable Builder
echo ==========================================
echo.

set "SOURCE_DIR=%~dp0"
set "RELEASE_DIR=%SOURCE_DIR%target\release"
set "PORTABLE_DIR=%SOURCE_DIR%CivSim-Portable"
set "FRONTEND_DIR=%SOURCE_DIR%frontend"

echo [Step 0] Checking package manager...
cd /d "%FRONTEND_DIR%"

if exist "pnpm-lock.yaml" (
    set "PKG_CMD=pnpm"
    echo Found: pnpm
) else if exist "yarn.lock" (
    set "PKG_CMD=yarn"
    echo Found: yarn
) else if exist "package-lock.json" (
    set "PKG_CMD=npm"
    echo Found: npm
) else (
    echo No lock file found, defaulting to pnpm
    set "PKG_CMD=pnpm"
)

echo.
echo [Step 1] Checking prerequisites...

if not exist "%FRONTEND_DIR%\dist" (
    echo Frontend not built! Building now...
    echo.
    cd /d "%FRONTEND_DIR%"
    
    call %PKG_CMD% install
    if errorlevel 1 (
        echo Install failed! Trying npm...
        call npm install
    )
    
    call %PKG_CMD% run build
    if errorlevel 1 (
        echo Build failed!
        pause
        exit /b 1
    )
    echo Build complete
) else (
    echo Frontend already built
)

echo.
echo [Step 2] Building Rust backend...
cd /d "%SOURCE_DIR%"
cargo build --release

if errorlevel 1 (
    echo Rust build failed!
    pause
    exit /b 1
)

echo.
echo [Step 3] Creating portable directory...
if exist "%PORTABLE_DIR%" rmdir /s /q "%PORTABLE_DIR%"
mkdir "%PORTABLE_DIR%"
mkdir "%PORTABLE_DIR%\data"

echo.
echo [Step 4] Copying files...
copy "%RELEASE_DIR%\CivSim.exe" "%PORTABLE_DIR%\" >nul
echo   - CivSim.exe

for %%%%f in ("%RELEASE_DIR%\*.dll") do (
    copy "%%%%f" "%PORTABLE_DIR%\" >nul 2>&1
)

echo.
echo [Step 5] Creating launchers...

echo @echo off > "%PORTABLE_DIR%\Start.bat"
echo start CivSim.exe >> "%PORTABLE_DIR%\Start.bat"

echo ========================================== > "%PORTABLE_DIR%\README.txt"
echo CivSim Portable Edition >> "%PORTABLE_DIR%\README.txt"
echo ========================================== >> "%PORTABLE_DIR%\README.txt"
echo. >> "%PORTABLE_DIR%\README.txt"
echo QUICK START: >> "%PORTABLE_DIR%\README.txt"
echo 1. Rename .env.example to .env >> "%PORTABLE_DIR%\README.txt"
echo 2. Edit .env and add your API key >> "%PORTABLE_DIR%\README.txt"
echo 3. Double-click Start.bat to run >> "%PORTABLE_DIR%\README.txt"
echo. >> "%PORTABLE_DIR%\README.txt"
echo API Key: https://dashscope.console.aliyun.com/ >> "%PORTABLE_DIR%\README.txt"

echo # Add your API key here > "%PORTABLE_DIR%\.env.example"
echo DASHSCOPE_API_KEY=sk-your-key-here >> "%PORTABLE_DIR%\.env.example"

echo.
echo ==========================================
echo Build Complete!
echo ==========================================
echo.
echo Output: %PORTABLE_DIR%
echo.
echo Files:
dir /b "%PORTABLE_DIR%" 2>nul
echo.
echo Next steps:
echo 1. Copy folder to any location
echo 2. Setup API key in .env file
echo 3. Run Start.bat
echo.
pause
