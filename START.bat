@echo off
setlocal
title AKS VisionX

cd /d "%~dp0"

echo ==========================================
echo          AKS VisionX STARTING
echo ==========================================
echo.

if not exist ".venv-ai\Scripts\python.exe" (
    echo Python environment not found.
    echo Please run UPDATE.bat first.
    pause
    exit /b 1
)

<<<<<<< HEAD
start "AKS VisionX Backend" /D "%~dp0backend" "%ComSpec%" /k ""%~dp0.venv-ai\Scripts\python.exe" manage.py runserver"
=======
start "AKS VisionX Backend" cmd /k ".venv-ai\Scripts\python.exe manage.py runserver"
>>>>>>> 32e82354c709145cb1b25fa9ae0911d3f7b8107d

timeout /t 3 /nobreak >nul

if exist "frontend\package.json" (
<<<<<<< HEAD
    where npm >nul 2>&1
    if errorlevel 1 (
        echo ERROR: npm was not found. Install Node.js to start the frontend.
        pause
        exit /b 1
    )
    start "AKS VisionX Frontend" /D "%~dp0frontend" "%ComSpec%" /k "npm run dev"
=======
    start "AKS VisionX Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"
>>>>>>> 32e82354c709145cb1b25fa9ae0911d3f7b8107d
)

echo.
echo AKS VisionX started.
echo.
pause
