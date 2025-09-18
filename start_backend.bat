@echo off
echo 🚀 Iniciando Backend DirGen...
echo.
echo URL del servidor: http://127.0.0.1:8000
echo Para detener el servidor: Ctrl+C
echo.

cd /d "K:\00 SW Projects\05 DirGen Platform\DirGen"
python -m uvicorn mcp_host.main:app --host 127.0.0.1 --port 8000 --reload

pause