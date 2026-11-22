@echo off
cd /d "%~dp0"
echo Stopping any old CodeTutor instance on port 7860...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :7860 ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1
call venv\Scripts\activate.bat
echo Starting CodeTutor v1.2.0...
python app.py
