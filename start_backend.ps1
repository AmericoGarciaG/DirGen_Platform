#!/usr/bin/env pwsh

Write-Host "🚀 Iniciando Backend DirGen..." -ForegroundColor Green
Write-Host ""
Write-Host "URL del servidor: " -NoNewline
Write-Host "http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "Para detener el servidor: Ctrl+C"
Write-Host ""

Set-Location "K:\00 SW Projects\05 DirGen Platform\DirGen"

# Verificar que Python esté disponible
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Error: Python no está disponible en el PATH" -ForegroundColor Red
    exit 1
}

# Ejecutar el servidor
python -m uvicorn mcp_host.main:app --host 127.0.0.1 --port 8000 --reload