@echo off
REM Quick start script for Windows
REM Make sure you have MongoDB, Redis, and Neo4j running before executing this

echo.
echo ====================================================================
echo  SECURITY BANKING APP - BACKEND STARTUP
echo ====================================================================
echo.

cd /d "%~dp0backend" || exit /b 1

echo Checking database connectivity...
python check_databases.py

if errorlevel 1 (
    echo.
    echo WARNING: Some databases are not available!
    echo Please ensure MongoDB, Redis, and Neo4j are running.
    echo.
    pause
)

echo.
echo Starting Flask backend server...
python app.py

pause
