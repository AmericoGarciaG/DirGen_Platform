@echo off
echo 🎯 DirGen Desktop - Inicio Rápido
echo ===================================
echo.

echo 🔥 Paso 1: Iniciando Backend...
start "DirGen Backend" cmd /k "cd /d \"K:\00 SW Projects\05 DirGen Platform\DirGen\" && python -m uvicorn mcp_host.main:app --host 127.0.0.1 --port 8000 --reload"

echo ⏳ Esperando que el backend se inicie...
timeout /t 3 /nobreak > nul

echo 🚀 Paso 2: Iniciando Frontend Tauri...
cd /d "K:\00 SW Projects\05 DirGen Platform\DirGen\client-desktop\dirgen-desktop"
npm run tauri:dev

echo.
echo ✅ DirGen iniciado completamente!
pause