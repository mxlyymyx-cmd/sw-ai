@echo off
rem Stop SWAI API server (Flask on 127.0.0.1:5757)
set "found=0"
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":5757" ^| findstr "LISTENING"') do (
  taskkill /pid %%p /f >nul 2>&1 && set "found=1"
)
if "%found%"=="1" (
  echo [SWAI] API server stopped.
) else (
  echo [SWAI] No running server found on port 5757.
)
timeout /t 2 >nul
