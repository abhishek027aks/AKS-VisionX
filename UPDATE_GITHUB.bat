@echo off
title AKS VisionX - GitHub Auto Update
cd /d "E:\AKS VisionX"

echo.
echo ==========================================
echo       AKS VisionX - GitHub Updater
echo ==========================================
echo.

echo [1/5] Checking repository...
git status

echo.
echo [2/5] Adding project changes...
git add .

echo.
echo [3/5] Creating commit...
git diff --cached --quiet
if %errorlevel%==0 (
    echo No new changes to commit.
    goto PUSH
)

for /f "tokens=1-2 delims= " %%A in ('powershell -NoProfile -Command "Get-Date -Format 'yyyy-MM-dd HH:mm'"') do set NOW=%%A %%B
git commit -m "Auto update - %NOW%"

:PUSH
echo.
echo [4/5] Updating local branch...
git pull --rebase origin main

if errorlevel 1 (
    echo.
    echo ==========================================
    echo ERROR: Pull/Rebase failed.
    echo Please resolve the Git conflict manually.
    echo ==========================================
    pause
    exit /b 1
)

echo.
echo [5/5] Uploading to GitHub...
git push origin main

if errorlevel 1 (
    echo.
    echo ==========================================
    echo ERROR: GitHub push failed.
    echo Check your GitHub login/remote/branch.
    echo ==========================================
    pause
    exit /b 1
)

echo.
echo ==========================================
echo       SUCCESS - GitHub Updated!
echo ==========================================
echo.
pause
