@echo off
cd /d "%~dp0frontend"
echo === Starting AgentFlow-Eval Frontend ===
echo Port: 5173
echo.
npx vite --host 127.0.0.1 --port 5173
