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

start "AKS VisionX Backend" /D "%~dp0backend" "%ComSpec%" /k ""%~dp0.venv-ai\Scripts\python.exe" manage.py runserver"

timeout /t 3 /nobreak >nul

if exist "frontend\package.json" (
    where npm >nul 2>&1
    if errorlevel 1 (
        echo ERROR: npm was not found. Install Node.js to start the frontend.
        pause
        exit /b 1
    )
    start "AKS VisionX Frontend" /D "%~dp0frontend" "%ComSpec%" /k "npm run dev"
)

echo.
echo AKS VisionX started.
echo.
pause
