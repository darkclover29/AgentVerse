@echo off
REM AgentVerse backend launcher — stays open so you can see any errors.
cd /d "%~dp0backend"

REM pick a Python launcher
where py >nul 2>&1 && (set PY=py) || (set PY=python)
%PY% --version >nul 2>&1 || (
    echo.
    echo [ERROR] Python was not found on PATH. Install Python 3.10+ from python.org
    echo and make sure "Add to PATH" is checked, then run this again.
    echo.
    pause & exit /b 1
)

if not exist ".venv" (
    echo Creating virtual environment...
    %PY% -m venv .venv || (echo [ERROR] venv creation failed & pause & exit /b 1)
)

call .venv\Scripts\activate.bat

echo Installing backend dependencies...
pip install -q -r requirements.txt || (echo [ERROR] pip install failed & pause & exit /b 1)

if not exist "agentverse.db" (
    echo Seeding the city ^(100 agents + grid^)...
    python -m app.seed || (echo [ERROR] seed failed & pause & exit /b 1)
)

echo.
echo Backend running at http://localhost:8000   ^(docs at /docs^)
echo Close this window to stop the backend.
echo.
uvicorn app.main:app --reload

echo.
echo [Backend stopped] If this was unexpected, read the error above.
pause
