# DirGen Desktop Client

**Cliente de escritorio para DirGen Platform** - Aplicación Tauri + Angular para validar comunicación frontend-backend y gestionar proyectos de generación de estructuras de directorios.

## 🚀 Hito 1: Prueba de Fuego Completada

Esta aplicación implementa el **Hito 1** del proyecto DirGen, validando que el ciclo completo de comunicación Frontend ↔ Backend funciona correctamente mediante una "prueba de fuego" integrada.

## 📋 Características

- ✅ **Tauri + Angular 17+**: Aplicación de escritorio híbrida
- ✅ **Angular Material**: Componentes UI modernos y responsivos
- ✅ **NgRx**: Gestión de estado reactivo (preparado para futuros hitos)
- ✅ **WebSocket Client**: Comunicación en tiempo real con el backend
- ✅ **HTTP Client**: Integración con API REST del backend
- ✅ **Prueba de Conexión**: Validación end-to-end del flujo completo

## 🛠️ Requisitos del Sistema

Antes de comenzar, asegúrate de tener instalado:

- **Node.js** (v18+) y **npm**
- **Rust** (para Tauri)
- **Sistema Operativo**: Windows, macOS o Linux

## 📦 Instalación

### 1. Navegar al directorio del proyecto

```bash
cd client-desktop/dirgen-desktop
```

### 2. Instalar dependencias

```bash
npm install
```

### 3. Verificar instalación de Tauri

```bash
npx tauri info
```

Si hay problemas con Tauri, instala las dependencias del sistema:

**Windows:**
- Instala Visual Studio Build Tools o Visual Studio Community
- Instala WebView2 (generalmente preinstalado en Windows 11)

**macOS:**
- Instala Xcode Command Line Tools: `xcode-select --install`

**Linux:**
- Instala las dependencias necesarias según tu distribución

## 🚀 Ejecución

### Modo de Desarrollo

Para ejecutar la aplicación en modo de desarrollo:

```bash
npm run tauri dev
```

Este comando:
1. Inicia el servidor de desarrollo de Angular (`ng serve`)
2. Compila y ejecuta la aplicación Tauri
3. Abre una ventana de aplicación nativa
4. Activa hot-reload para cambios en tiempo real

### Modo de Producción

Para construir la aplicación para producción:

```bash
npm run tauri build
```

Los archivos ejecutables se generarán en `src-tauri/target/release/`.

## 🧪 Prueba de Conexión

La aplicación incluye una **Prueba de Conexión integrada** que valida el ciclo completo:

### ¿Cómo usar la Prueba de Conexión?

1. **Iniciar el Backend**: Abre una **nueva terminal** y ejecuta uno de estos comandos:
   
   **Opción A (Windows CMD):**
   ```cmd
   cd K:\00 SW Projects\05 DirGen Platform\DirGen
   start_backend.bat
   ```
   
   **Opción B (PowerShell):**
   ```powershell
   cd "K:\00 SW Projects\05 DirGen Platform\DirGen"
   .\start_backend.ps1
   ```
   
   **Opción C (Manual):**
   ```bash
   cd "K:\00 SW Projects\05 DirGen Platform\DirGen"
   python -m uvicorn mcp_host.main:app --host 127.0.0.1 --port 8000 --reload
   ```

2. **Ejecutar la Aplicación** (en esta terminal):
   ```bash
   npm run tauri:dev
   ```

3. **Seleccionar Archivo**: En la interfaz, selecciona el archivo `SVAD_FinBase_v1.md` (ubicado en la raíz del proyecto principal)

4. **Iniciar Prueba**: Haz clic en "Iniciar Prueba de Conexión"

5. **Observar Resultados**:
   - ✅ Se genera un **Run ID** válido
   - ✅ La conexión **WebSocket** se establece
   - ✅ Los **mensajes en tiempo real** aparecen en formato JSON
   - ✅ El estado de conexión se actualiza correctamente

### ✅ Criterios de Éxito

La prueba es exitosa cuando:

- [x] **HTTP POST**: Se obtiene un Run ID válido del endpoint `/v1/initiate_from_svad`
- [x] **WebSocket**: La conexión se establece en `ws://127.0.0.1:8000/ws/{runId}`
- [x] **Stream en tiempo real**: Se reciben y muestran mensajes del backend
- [x] **Formato RAW**: Los mensajes se renderizan en JSON crudo para inspección
- [x] **Estados de conexión**: Se muestran claramente (Conectando, Conectado, Error, etc.)

## 🏗️ Arquitectura del Proyecto

```
src/app/
├── core/
│   ├── services/
│   │   └── api.service.ts          # Comunicación HTTP + WebSocket
│   └── state/                      # NgRx (preparado para futuros hitos)
├── features/
│   └── test-connection/            # Componente de prueba de conexión
│       ├── test-connection.component.ts
│       ├── test-connection.component.html
│       └── test-connection.component.scss
└── shared/
    └── models/
        └── dirgen.models.ts        # Interfaces TypeScript
```

## 🔧 Scripts Disponibles

```bash
# Desarrollo
npm run tauri dev          # Ejecutar en modo desarrollo
npm start                  # Solo servidor Angular (sin Tauri)

# Construcción
npm run tauri build        # Construir aplicación para producción
npm run build              # Solo build de Angular

# Testing
npm test                   # Ejecutar pruebas unitarias
npm run e2e                # Ejecutar pruebas end-to-end

# Linting y formato
npm run lint               # Verificar código con ESLint
```

## 📡 Configuración de API

Por defecto, la aplicación se conecta al backend en:

- **HTTP API**: `http://127.0.0.1:8000`
- **WebSocket**: `ws://127.0.0.1:8000`

Para cambiar estas URLs, modifica las constantes en `src/app/core/services/api.service.ts`:

```typescript
private readonly baseUrl = 'http://127.0.0.1:8000';
private readonly wsBaseUrl = 'ws://127.0.0.1:8000';
```

## 🐛 Solución de Problemas

### Error: "Backend no responde"
- ✅ Verifica que el backend DirGen esté ejecutándose
- ✅ Confirma que la URL y puerto sean correctos
- ✅ Revisa la consola del navegador para errores CORS

### Error: "WebSocket no se conecta"
- ✅ Verifica que el backend soporte conexiones WebSocket
- ✅ Confirma que no haya firewalls bloqueando la conexión
- ✅ Revisa los logs del backend para errores

### Error de compilación de Tauri
- ✅ Verifica que Rust esté instalado correctamente
- ✅ Actualiza las dependencias: `npm update`
- ✅ Limpia y reinstala: `rm -rf node_modules && npm install`

## 📚 Tecnologías Utilizadas

| Tecnología | Versión | Propósito |
|------------|---------|-----------||
| Angular | 17+ | Framework frontend |
| Tauri | Latest | Framework de aplicación nativa |
| Angular Material | 17+ | Componentes UI |
| NgRx | 17+ | Gestión de estado |
| TypeScript | 5+ | Tipado estático |
| RxJS | 7+ | Programación reactiva |

## 🎯 Próximos Pasos (Futuros Hitos)

El **Hito 1** está completo. Los próximos desarrollos incluirán:

- **Hito 2**: Interfaz completa de gestión de proyectos
- **Hito 3**: Visualización avanzada del progreso de generación
- **Hito 4**: Gestión de configuraciones y plantillas
- **Hito 5**: Sincronización y colaboración en tiempo real

## 💡 Contribuir

Este es un proyecto en desarrollo activo. Para contribuir:

1. Haz fork del repositorio
2. Crea una rama para tu feature: `git checkout -b feature/nueva-caracteristica`
3. Commit tus cambios: `git commit -am 'Añadir nueva característica'`
4. Push a la rama: `git push origin feature/nueva-caracteristica`
5. Crea un Pull Request

## 📞 Soporte

Si encuentras problemas o tienes preguntas:

1. Revisa la sección de **Solución de Problemas**
2. Verifica que el backend esté ejecutándose correctamente
3. Consulta la documentación del backend DirGen
4. Abre un issue en el repositorio del proyecto

---

**¡La prueba de fuego del Hito 1 está completa y funcionando! 🎉**

La aplicación DirGen Desktop Client está lista para validar la comunicación completa entre frontend y backend.
