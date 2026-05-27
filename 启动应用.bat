@echo off
chcp 65001 >nul

echo ========================================
echo   Starting Flask Server...
echo ========================================
echo.
echo [Start] Server starting...
echo [URL] http://localhost:5000
echo [Stop] Press Ctrl+C to stop
echo.

python -u frontend/app.py

echo.
pause

