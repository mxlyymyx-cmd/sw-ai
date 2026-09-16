@echo off
rem SWAI API server launcher - Flask on 127.0.0.1:5757 (windowless background)
cd /d "%~dp0"
netstat -ano | findstr ":5757" | findstr "LISTENING" >nul && (
  echo [SWAI] Server already running on port 5757. Nothing to do.
  timeout /t 2 >nul
  exit /b 0
)
start "" pythonw "%~dp0api.py" --port 5757
echo [SWAI] Starting API server in background (no window)...
timeout /t 4 /nobreak >nul
netstat -ano | findstr ":5757" | findstr "LISTENING" >nul && (
  echo [SWAI] Service ready: http://127.0.0.1:5757
) || (
  echo [SWAI] WARNING: port 5757 not listening yet, wait a few seconds and retry.
)
echo.
echo Server runs in background with no window - closing this window never stops it.
echo To stop: double-click stop-AI-service.bat (stop AI service.bat)
pause
