@echo off
title AKS VisionX - Stop

echo Stopping AKS VisionX...

taskkill /FI "WINDOWTITLE eq AKS VisionX Backend*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq AKS VisionX Frontend*" /T /F >nul 2>&1

echo.
echo AKS VisionX stopped.
pause
