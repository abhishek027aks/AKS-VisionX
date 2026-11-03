@echo off
<<<<<<< HEAD
setlocal
title AKS VisionX - GitHub Auto Update
cd /d "%~dp0"
=======
title AKS VisionX - GitHub Auto Update
cd /d "E:\AKS VisionX"
>>>>>>> 32e82354c709145cb1b25fa9ae0911d3f7b8107d

echo.
echo ==========================================
echo       AKS VisionX - GitHub Updater
echo ==========================================
echo.

<<<<<<< HEAD
git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
    echo ERROR: This project folder is not a Git checkout.
    echo Clone the repository before using the GitHub updater.
    pause
    exit /b 1
)

for /f "delims=" %%B in ('git branch --show-current') do set CURRENT_BRANCH=%%B
if not "%CURRENT_BRANCH%"=="main" (
    echo ERROR: Switch to the main branch before publishing.
    pause
    exit /b 1
)

=======
>>>>>>> 32e82354c709145cb1b25fa9ae0911d3f7b8107d
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
