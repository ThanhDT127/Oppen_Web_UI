@echo off
echo ====================================================
echo STARTING ALL SERVICES
echo ====================================================
echo.

REM Activate virtual environment
call D:\Works\.venv\Scripts\activate.bat

REM Load environment variables from .env
for /f "tokens=1,* delims==" %%a in ('type .env ^| findstr /v "^#" ^| findstr "="') do set %%a=%%b

REM Start LiteLLM in new window with environment variables
echo [1/3] Starting LiteLLM (Port 4000)...
start "LiteLLM" cmd /k "cd D:\Works\Oppen_Web_UI_fresh && D:\Works\.venv\Scripts\activate.bat && set OPENAI_API_KEY=%OPENAI_API_KEY% && set GEMINI_API_KEY=%GEMINI_API_KEY% && litellm --config litellm/litellm_config.yaml --port 4000"
timeout /t 10 /nobreak >nul

REM Start Middleware in new window
echo [2/3] Starting Middleware (Port 5000)...
start "Middleware" cmd /k "cd D:\Works\Oppen_Web_UI_fresh\llm-mw && D:\Works\.venv\Scripts\activate.bat && set MW_SECRET=test-secret-key-for-development-only-change-in-production && set LITELLM_BASE=http://127.0.0.1:4000/v1 && set LITELLM_KEY=sk-1234 && set ADMIN_KEY=YOUR_ADMIN_KEY && python -m uvicorn main:app --host 0.0.0.0 --port 5000"
timeout /t 5 /nobreak >nul

REM Start OpenWebUI in new window
echo [3/3] Starting OpenWebUI (Port 3000)...
start "OpenWebUI" cmd /k "cd D:\Works\Oppen_Web_UI_fresh && D:\Works\.venv\Scripts\activate.bat && set DATA_DIR=D:\Works\Oppen_Web_UI_fresh\openwebui_data && set WEBUI_SECRET_KEY=your-secret-key-here && set LITELLM_API_KEY=YOUR_SUBKEY_ADMIN && open-webui serve --port 3000"
timeout /t 3 /nobreak >nul

echo.
echo ====================================================
echo ALL SERVICES STARTED
echo ====================================================
echo.
echo LiteLLM:    http://localhost:4000
echo Middleware: http://localhost:5000
echo OpenWebUI:  http://localhost:3000
echo.
echo Press any key to close this window...
pause >nul
