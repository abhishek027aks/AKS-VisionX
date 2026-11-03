@echo off
setlocal
title AKS VisionX - Auto Updater

cd /d "%~dp0"

echo.
echo ==========================================
echo        AKS VisionX AUTO UPDATE
echo ==========================================
echo.

git rev-parse --is-inside-work-tree >nul 2>&1
if not errorlevel 1 (
    echo [1/4] Updating Git checkout...
    git pull --ff-only origin main
    if errorlevel 1 (
        echo ERROR: Git update failed.
        pause
        exit /b 1
    )
) else (
    echo [1/4] Standalone project copy detected. Skipping Git update.
)

echo.
echo [2/4] Updating Python environment...

if not exist ".venv-ai\Scripts\python.exe" (
    echo Creating Python environment...
    py -3.11 -m venv .venv-ai
    if errorlevel 1 (
        echo ERROR: Python 3.11 is required to create the environment.
        pause
        exit /b 1
    )
)

if not exist ".venv-ai\Scripts\python.exe" (
    echo ERROR: Python environment was not created.
    pause
    exit /b 1
)

.venv-ai\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 (
    echo ERROR: pip could not be upgraded.
    pause
    exit /b 1
)

.venv-ai\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Python dependency update failed.
    pause
    exit /b 1
)

echo.
echo [3/4] Updating frontend...

if exist "frontend\package.json" (
    where npm >nul 2>&1
    if errorlevel 1 (
        echo ERROR: npm was not found. Install Node.js to update the frontend.
        pause
        exit /b 1
    )

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
echo [4/4] Running Django migrations...

pushd backend
..\.venv-ai\Scripts\python.exe manage.py migrate
if errorlevel 1 (
    popd
    echo ERROR: Django migrations failed.
    pause
    exit /b 1
)
popd

echo.
echo ==========================================
echo     AKS VisionX UPDATE COMPLETE
echo ==========================================
echo.
echo Project dependencies and database migrations are up to date.
echo.

pause
