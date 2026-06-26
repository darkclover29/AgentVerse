@echo off
REM AgentVerse frontend launcher — stays open so you can see any errors.
cd /d "%~dp0frontend"

where npm >nul 2>&1 || (
    echo.
    echo [ERROR] npm was not found on PATH. Install Node.js LTS from nodejs.org,
    echo then run this again.
    echo.
    pause & exit /b 1
)

if not exist "node_modules" (
    echo Installing frontend dependencies ^(first run, may take a minute^)...
    call npm install || (echo [ERROR] npm install failed & pause & exit /b 1)
)

echo.
echo Frontend running at http://localhost:5173
echo Close this window to stop the frontend.
echo.
call npm run dev

echo.
echo [Frontend stopped] If this was unexpected, read the error above.
pause
