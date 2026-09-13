@echo off
cd /d "%~dp0"
echo RESIDUAL / COMMAND STATION
docker info >nul 2>&1
if %errorlevel% equ 0 (
    if not exist projects mkdir projects
    docker compose up --build -d
    if errorlevel 1 goto failed
    start "" http://localhost:8765
    echo Open http://localhost:8765
    echo Stop with: docker compose stop
    pause
    exit /b 0
)
where git >nul 2>&1
if errorlevel 1 goto requirements
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if not errorlevel 1 (
    py -3 -m residual.station.server --open
    pause
    exit /b
)
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if errorlevel 1 goto requirements
python -m residual.station.server --open
pause
exit /b
:requirements
echo Install Docker Desktop for the complete runtime, or Python 3.11+ and Git for native mode.
echo See START-HERE.md for the two launch options.
pause
exit /b 1
:failed
echo Docker could not build or start the station. Check the error above and retry.
pause
exit /b 1
