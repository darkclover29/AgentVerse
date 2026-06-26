@echo off
REM AgentVerse one-click launcher.
REM Opens the backend and frontend in their own windows (each stays open and shows
REM errors), then opens the dashboard in your browser.
cd /d "%~dp0"

echo Launching AgentVerse...
start "AgentVerse Backend"  cmd /k "%~dp0run_backend.bat"
start "AgentVerse Frontend" cmd /k "%~dp0run_frontend.bat"

echo Waiting for servers to start, then opening the dashboard...
timeout /t 8 >nul
start "" http://localhost:5173
exit /b 0
