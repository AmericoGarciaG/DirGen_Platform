# 🚀 Guía de Ejecución - DirGen Platform

Esta guía explica cómo ejecutar tanto la **versión web** como la **versión desktop** de DirGen Platform.

## 📋 Requisitos Previos

- **Node.js** v18 o superior
- **Python** 3.10+ con pip
- **Rust** (para la versión desktop con Tauri)
- **PowerShell** en Windows

## 🎯 Estructura del Proyecto

```
K:\00 SW Projects\05 DirGen Platform\DirGen\
├── client-desktop/dirgen-desktop/    # 🖥️ Aplicación Desktop (Angular + Tauri)
├── mcp_host/                         # 🔧 Backend FastAPI
├── start_backend.ps1                 # 🚀 Script para iniciar backend
└── ...otros archivos
```

---

## 🌐 VERSIÓN WEB

### 1️⃣ Iniciar Backend

**Terminal 1** - Ejecutar desde la carpeta raíz:
```powershell
cd "K:\00 SW Projects\05 DirGen Platform\DirGen"
.\start_backend.ps1
```

**Salida esperada:**
```
🚀 Iniciando Backend DirGen...

URL del servidor: http://127.0.0.1:8000
Para detener el servidor: Ctrl+C
```

### 2️⃣ Iniciar Frontend Web

**Terminal 2** - Ejecutar desde la carpeta cliente:
```powershell
cd "K:\00 SW Projects\05 DirGen Platform\DirGen\client-desktop\dirgen-desktop"
npm start
```

**Salida esperada:**
```
Server bundles
...
Application bundle generation complete.
Watch mode enabled.
  ➜  Local:   http://localhost:4200/
```

### 3️⃣ Acceder a la Aplicación Web

- URL Base: http://localhost:4200/
- Ruta recomendada para pruebas (Web Avanzado): http://localhost:4200/monitoring-web-advanced
  - Incluye el nuevo Event Log reactivo (NgRx) y el Command Center (NgRx)
  - Adjunta un archivo SVAD (.md/.txt), pulsa Enviar y verifica el flujo end-to-end
- StatusBar: Completamente funcional en modo web
- Conectividad: WebSocket con backend en tiempo real

### 4️⃣ Flujo de prueba rápido (validación)

1. Abre DevTools (F12) → pestaña Network
2. Adjunta un archivo SVAD en el Centro de Mando y pulsa Enviar
3. Debes ver:
   - POST /v1/initiate_from_svad → 200 con un JSON que incluye `run_id`
   - WS ws://127.0.0.1:8000/ws/<run_id> → 101 Switching Protocols
4. La UI debe mostrar:
   - `runId` en el estado de conexión del Centro de Mando
   - El archivo en la pestaña «Contexto» (panel izquierdo)
   - Eventos en tiempo real en el «Log de Eventos»

---

## 🖥️ VERSIÓN DESKTOP

### 1️⃣ Iniciar Backend (Igual que versión web)

**Terminal 1**:
```powershell
cd "K:\00 SW Projects\05 DirGen Platform\DirGen"
.\start_backend.ps1
```

### 2️⃣ Iniciar Aplicación Desktop

**Terminal 2** - Ejecutar desde la carpeta cliente desktop:
```powershell
cd "K:\00 SW Projects\05 DirGen Platform\DirGen\client-desktop\dirgen-desktop"
npm run tauri:dev
```

**Salida esperada:**
```
> dirgen-desktop@0.0.0 tauri:dev
> tauri dev

Running BeforeDevCommand (`npm run start:tauri`)
...
Application bundle generation complete.
Running DevCommand (`cargo run`)
Finished `dev` profile target(s)
Running `target\debug\app.exe`
```

### 3️⃣ Usar la Aplicación Desktop

- **Ventana**: Se abre automáticamente una ventana nativa de Windows
- **Título**: "DirGen Desktop" 
- **Tamaño**: 1200x800 pixels
- **Funcionalidades**: Interfaz completa (StatusBar simplificado)

---

## ⚙️ Configuraciones Específicas

> Importante: usa SIEMPRE procesos en terminales separadas (una para backend y otra para frontend). No ejecutes ambos en la misma terminal para evitar bloqueos u ocultar errores.

### 🔧 Configuración Desktop vs Web

| Aspecto | Web (Puerto 4200) | Desktop (Puerto 127.0.0.1:4200) |
|---------|-------------------|-----------------------------------|
| **StatusBar** | ✅ Completo con todas las funciones | ⚠️ Versión simplificada (evita problemas) |
| **Conectividad** | `localhost:4200` | `127.0.0.1:4200` (evita firewalls/VPNs) |
| **Host Check** | Habilitado | `--disable-host-check` |
| **Polling** | No | `--poll 2000` (para VPNs/Firewalls) |

### 🛠️ Scripts NPM Utilizados

```json
{
  "start": "ng serve --host 0.0.0.0 --disable-host-check",
  "start:tauri": "ng serve --host 127.0.0.1 --port 4200 --disable-host-check --poll 2000",
  "tauri:dev": "tauri dev",
  "tauri:build": "tauri build"
}
```

---

## 🚨 Problemas Comunes y Soluciones

### ❌ Problema: "localhost rechazó la conexión"

**Causa**: Firewalls, VPNs, o software antivirus bloquean conexiones
**Solución**: La configuración actual usa `127.0.0.1` y `--disable-host-check`

### ❌ Problema: Pantalla en blanco en Desktop

**Causa**: El StatusBar original causa problemas en entorno Tauri
**Solución**: Se usa versión simplificada (`MonitoringNoStatusbarComponent`)

### ❌ Problema: Puertos ocupados

**Web**: Cambiar puerto con `ng serve --port 4201`
**Desktop**: La configuración maneja automáticamente los puertos

### ❌ Problema: Backend no responde

**Verificar**:
1. Backend ejecutándose en http://127.0.0.1:8000
2. Python y uvicorn funcionando correctamente
3. Puerto 8000 libre

---

## 📊 Características de Cada Versión

### 🌐 **Versión Web**
- ✅ StatusBar completo con todas las funcionalidades
- ✅ Todas las animaciones y transiciones
- ✅ DevTools de navegador disponibles
- ✅ Recarga automática (hot reload)
- ✅ Ideal para desarrollo y debugging

### 🖥️ **Versión Desktop**  
- ✅ Aplicación nativa de Windows
- ✅ No requiere navegador
- ✅ Integración con OS (menús nativos, notificaciones)
- ✅ Mejor rendimiento (motor nativo)
- ✅ StatusBar simplificado pero funcional
- ✅ Ideal para producción y usuarios finales

---

## 🎯 Comandos Rápidos

### Para desarrolladores:
```powershell
# Terminal A (Backend):
cd "K:\\00 SW Projects\\05 DirGen Platform\\DirGen"
.\\start_backend.ps1

# Terminal B (Frontend Web):
cd "K:\\00 SW Projects\\05 DirGen Platform\\DirGen\\client-desktop\\dirgen-desktop"
npm start  # abre http://localhost:4200/ (recomendado: /monitoring-web-advanced)

# Terminal B (Desktop) en lugar de Web:
cd "K:\\00 SW Projects\\05 DirGen Platform\\DirGen\\client-desktop\\dirgen-desktop"
npm run tauri:dev
```

### Para producción:
```powershell
# Build desktop:
npm run tauri:build

# Build web:
npm run build
```

---

## ✅ Validación de Funcionamiento

### Backend funcionando correctamente:
- [ ] Terminal muestra: `Uvicorn running on http://127.0.0.1:8000`
- [ ] http://127.0.0.1:8000/docs accesible (documentación API)

### Frontend Web funcionando:
- [ ] http://localhost:4200/monitoring-web-advanced accesible
- [ ] Centro de Mando visible y sin desbordes (input a ancho completo)
- [ ] Al adjuntar archivo, el botón «Enviar» se mantiene visible
- [ ] Al Enviar, se ve el `runId`, el archivo en «Contexto» y eventos en el log

### Frontend Desktop funcionando:
- [ ] Ventana nativa de Windows se abre
- [ ] StatusBar simplificado visible
- [ ] Todos los paneles cargados correctamente  
- [ ] Comunicación con backend establecida
- [ ] Log de eventos en tiempo real

---

## 📞 Soporte

Si encuentras problemas:

1. **Revisar terminales** para mensajes de error
2. **Verificar puertos** con `netstat -an | findstr ":4200"`
3. **Limpiar caché** con `npm start` en nueva terminal
4. **Reiniciar servicios** si es necesario

---

**✨ ¡Ambas versiones están completamente funcionales y listas para usar!**