@echo off
echo Starting Django Development Server...
echo.
cd /d "%~dp0"
venv\Scripts\python.exe manage.py runserver
pause
