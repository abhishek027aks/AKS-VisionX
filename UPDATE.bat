@echo off
setlocal
title AKS VisionX - Auto Updater

cd /d "%~dp0"

echo.
echo ==========================================
echo        AKS VisionX AUTO UPDATE
echo ==========================================
echo.

echo [1/6] Checking Git...
git --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Git is not installed.
    pause
    exit /b 1
)

echo.
echo [2/6] Getting latest GitHub code...
git fetch origin

if errorlevel 1 (
    echo ERROR: Could not connect to GitHub.
    pause
    exit /b 1
)

echo.
echo [3/6] Updating source code...
git pull --ff-only origin main

if errorlevel 1 (
    echo.
    echo ERROR: Update failed.
    echo Local changes may be present.
    pause
    exit /b 1
)

echo.
echo [4/6] Updating Python environment...

if not exist ".venv-ai\Scripts\python.exe" (
    echo Creating Python environment...
    py -3.11 -m venv .venv-ai
)

.venv-ai\Scripts\python.exe -m pip install --upgrade pip
.venv-ai\Scripts\python.exe -m pip install -r requirements.txt

if errorlevel 1 (
    echo ERROR: Python dependency update failed.
    pause
    exit /b 1
)

echo.
echo [5/6] Updating frontend...

if exist "frontend\package.json" (
    cd frontend
    call npm install

    if errorlevel 1 (
        echo ERROR: npm install failed.
        cd ..
        pause
        exit /b 1
    )

    call npm run build

    if errorlevel 1 (
        echo ERROR: Frontend build failed.
        cd ..
        pause
        exit /b 1
    )

    cd ..
)

echo.
echo [6/6] Running Django migrations...

if exist ".venv-ai\Scripts\python.exe" (
    .venv-ai\Scripts\python.exe manage.py migrate
)

echo.
echo ==========================================
echo     AKS VisionX UPDATE COMPLETE
echo ==========================================
echo.
echo Latest GitHub version is installed.
echo.

pause
