@echo off
cd /d "%~dp0"
echo ====================================================
echo TESTING MIDDLEWARE ENDPOINTS
echo ====================================================
echo.

echo [1/7] Testing /health endpoint...
curl -s http://localhost:5000/health
echo.
echo.

echo [2/7] Testing /v1/models endpoint...
curl -s http://localhost:5000/v1/models -H "Authorization: Bearer YOUR_SUBKEY_ADMIN"
echo.
echo.

echo [3/7] Testing /admin/usage endpoint...
curl -s http://localhost:5000/admin/usage -H "Authorization: Bearer YOUR_ADMIN_KEY"
echo.
echo.

echo [4/7] Testing /v1/_mw/summary endpoint...
curl -s "http://localhost:5000/v1/_mw/summary?minutes=60" -H "Authorization: Bearer YOUR_ADMIN_KEY"
echo.
echo.

echo [5/7] Testing /v1/chat/completions endpoint (non-streaming)...
curl -s http://localhost:5000/v1/chat/completions ^
  -H "Authorization: Bearer YOUR_SUBKEY_ADMIN" ^
  -H "Content-Type: application/json" ^
  -d "{\"model\":\"gpt-4o-mini\",\"messages\":[{\"role\":\"user\",\"content\":\"Say 'Hello from modular middleware!'\"}],\"stream\":false}"
echo.
echo.

echo [6/7] Testing /v1/images/generations endpoint...
curl -s http://localhost:5000/v1/images/generations ^
  -H "Authorization: Bearer YOUR_SUBKEY_ADMIN" ^
  -H "Content-Type: application/json" ^
  -d "{\"model\":\"gemini-2.5-flash-image\",\"prompt\":\"A cute cat\",\"n\":1}"
echo.
echo.

echo [7/7] Checking service health status...
curl -s http://localhost:5000/health | findstr "ok"
echo.

echo ====================================================
echo TESTS COMPLETE
echo ====================================================
pause
