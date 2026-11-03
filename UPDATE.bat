@echo off
setlocal
title AKS VisionX - Auto Updater

cd /d "%~dp0"

echo.
echo ==========================================
echo        AKS VisionX AUTO UPDATE
echo ==========================================
echo.

<<<<<<< HEAD
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
=======
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
>>>>>>> 32e82354c709145cb1b25fa9ae0911d3f7b8107d

if not exist ".venv-ai\Scripts\python.exe" (
    echo Creating Python environment...
    py -3.11 -m venv .venv-ai
<<<<<<< HEAD
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
=======
)

.venv-ai\Scripts\python.exe -m pip install --upgrade pip
.venv-ai\Scripts\python.exe -m pip install -r requirements.txt

>>>>>>> 32e82354c709145cb1b25fa9ae0911d3f7b8107d
if errorlevel 1 (
    echo ERROR: Python dependency update failed.
    pause
    exit /b 1
)

echo.
<<<<<<< HEAD
echo [3/4] Updating frontend...

if exist "frontend\package.json" (
    where npm >nul 2>&1
    if errorlevel 1 (
        echo ERROR: npm was not found. Install Node.js to update the frontend.
        pause
        exit /b 1
    )

=======
echo [5/6] Updating frontend...

if exist "frontend\package.json" (
>>>>>>> 32e82354c709145cb1b25fa9ae0911d3f7b8107d
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
<<<<<<< HEAD
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
=======
echo [6/6] Running Django migrations...

if exist ".venv-ai\Scripts\python.exe" (
    .venv-ai\Scripts\python.exe manage.py migrate
)
>>>>>>> 32e82354c709145cb1b25fa9ae0911d3f7b8107d

echo.
echo ==========================================
echo     AKS VisionX UPDATE COMPLETE
echo ==========================================
echo.
<<<<<<< HEAD
echo Project dependencies and database migrations are up to date.
=======
echo Latest GitHub version is installed.
>>>>>>> 32e82354c709145cb1b25fa9ae0911d3f7b8107d
echo.

pause
