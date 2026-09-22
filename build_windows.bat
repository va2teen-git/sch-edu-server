@echo off
echo ==============================================
echo Building sch-edu-server for Windows (Zero-Dependency)
echo ==============================================

:: Ensure PyInstaller is installed
pip install pyinstaller flask flask-sqlalchemy waitress

:: Clean previous builds
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist server.spec del /q server.spec

:: Compile using PyInstaller
:: --onefile means pack everything into a single .exe
:: --add-data "folder;folder" includes the static and template files
pyinstaller --onefile --name server --add-data "templates;templates" --add-data "static;static" app.py

echo ==============================================
echo Build Complete! 
echo You can find the executable at: dist\server.exe
echo ==============================================
pause
