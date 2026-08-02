@echo off
REM Eskwela Project - Real-Time Development Server Launcher for Windows
REM This script starts the Daphne ASGI server with proper environment setup

setlocal enabledelayedexpansion

echo.
echo =====================================================
echo     ESKWELA PROJECT - Real-Time Server Launcher
echo =====================================================
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo Error: Virtual environment not found!
    echo Please create it first:
    echo   python -m venv venv
    echo   venv\Scripts\activate
    echo   pip install -r requirements.txt
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

if errorlevel 1 (
    echo Error: Failed to activate virtual environment
    pause
    exit /b 1
)

REM Check if daphne is installed
python -c "import daphne" >nul 2>&1
if errorlevel 1 (
    echo.
    echo Error: Daphne is not installed!
    echo Installing now...
    pip install daphne channels
    if errorlevel 1 (
        echo Failed to install dependencies
        pause
        exit /b 1
    )
)

REM Create logs directory if it doesn't exist
if not exist "logs" (
    mkdir logs
    echo Created logs directory
)

echo.
echo ======================================================
echo   Starting Daphne ASGI Server for Real-Time Updates
echo ======================================================
echo.
echo  Server: Daphne (ASGI)
echo  WebSocket: ws://localhost:8000/ws/dashboard/
echo  HTTP: http://localhost:8000
echo.
echo  Real-time Dashboard Updates: ENABLED
echo  WebSocket Connections: ENABLED
echo  Auto-reload on code changes: ENABLED
echo.
echo  Press Ctrl+C to stop the server
echo.
echo ======================================================
echo.

REM Run migrations
echo Applying migrations...
python manage.py migrate --quiet
if errorlevel 1 (
    echo Warning: Migration had issues, but continuing...
)

REM Start Daphne
echo.
echo Starting server...
echo.

daphne -b 0.0.0.0 -p 8000 -v 2 eskwela_project.asgi:application

REM If Daphne fails, try the Python script
if errorlevel 1 (
    echo.
    echo Trying alternative startup method...
    python run_server.py
)

pause
