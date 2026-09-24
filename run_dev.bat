@echo off
echo ==============================================
echo Starting sch-edu-server in DEVELOPMENT MODE
echo ==============================================
echo.
echo Hot-reloading is ENABLED (auto-restarts on save).
echo Open http://localhost:5000 in your browser.
echo Press CTRL+C to stop the server.
echo.

REM Set Flask environment variables
set FLASK_APP=app.py
set FLASK_ENV=development
set FLASK_DEBUG=1

REM Run Flask development server
python -m flask run --host=0.0.0.0 --port=5000 --debug

pause
