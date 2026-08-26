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

start "AKS VisionX Backend" cmd /k ".venv-ai\Scripts\python.exe manage.py runserver"

timeout /t 3 /nobreak >nul

if exist "frontend\package.json" (
    start "AKS VisionX Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"
)

echo.
echo AKS VisionX started.
echo.
pause
