@echo off
echo ==============================================
echo Starting sch-edu-server in DEVELOPMENT MODE
echo ==============================================
echo.
echo Hot-reloading is ENABLED (auto-restarts on save).
echo Open http://localhost:5000 in your browser.
echo Press CTRL+C to stop the server.
echo.

:: Устанавливаем переменные окружения для Flask в режиме отладки
set FLASK_APP=app.py
set FLASK_DEBUG=1

:: Запуск встроенного dev-сервера (вместо Waitress, чтобы работала горячая перезагрузка)
python -m flask run --host=0.0.0.0 --port=5000

pause
