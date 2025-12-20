@echo off
REM ====================================================
REM  KHOI CHAY NHANH - OPPEN WEB UI
REM  Usage: scripts\start.bat
REM ====================================================

echo.
echo ====================================================
echo   STARTING ALL SERVICES
echo ====================================================
echo.

REM Set working directory
cd /d "%~dp0.."

REM Load environment variables from .env file
if exist .env (
    echo [+] Loading environment variables...
    for /f "tokens=1,* delims==" %%a in ('type .env ^| findstr /v "^#" ^| findstr "="') do set %%a=%%b
)

REM Activate virtual environment
echo [+] Activating virtual environment...
call D:\Works\.venv\Scripts\activate.bat
if errorlevel 1 (
    echo [!] Failed to activate venv
    pause
    exit /b 1
)

REM Start LiteLLM in new window
echo.
echo [1/3] Starting LiteLLM (Port 4000)...
start "LiteLLM - Port 4000" cmd /k "call D:\Works\.venv\Scripts\activate.bat && cd /d %CD% && litellm --config litellm/litellm_config.yaml --port 4000"
timeout /t 8 /nobreak >nul

REM Start Middleware in new window
echo [2/3] Starting Middleware (Port 5000)...
start "Middleware - Port 5000" cmd /k "call D:\Works\.venv\Scripts\activate.bat && cd /d %CD%\llm-mw && python main.py"
timeout /t 5 /nobreak >nul

REM Start OpenWebUI in new window
echo [3/3] Starting OpenWebUI (Port 3000)...
start "OpenWebUI - Port 3000" cmd /k "call D:\Works\.venv\Scripts\activate.bat && cd /d %CD% && set DATA_DIR=%CD%\openwebui_data && set WEBUI_SECRET_KEY=your-secret-key-here && open-webui serve --port 3000"
timeout /t 3 /nobreak >nul

echo.
echo ====================================================
echo   ALL SERVICES STARTED SUCCESSFULLY!
echo ====================================================
echo.
echo   LiteLLM:    http://localhost:4000
echo   Middleware: http://localhost:5000
echo   OpenWebUI:  http://localhost:3000
echo.
echo   Press Ctrl+C in each terminal to stop services
echo ====================================================
echo.
pause
