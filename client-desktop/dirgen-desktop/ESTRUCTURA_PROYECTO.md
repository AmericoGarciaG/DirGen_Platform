# Estructura del Proyecto DirGen Desktop

Este documento muestra la estructura completa de archivos del proyecto DirGen Desktop (cliente de escritorio).

## Estructura de Directorios

```
dirgen-desktop/
├── .vscode/                                    # Configuración de Visual Studio Code
│   ├── extensions.json                         # Extensiones recomendadas
│   ├── launch.json                            # Configuración de debug
│   └── tasks.json                             # Tareas automatizadas
├── src-tauri/                                 # Configuración de Tauri (aplicación de escritorio)
│   ├── capabilities/
│   │   └── default.json                       # Permisos y capacidades por defecto
│   ├── src/
│   │   ├── lib.rs                             # Librería principal de Rust
│   │   └── main.rs                            # Punto de entrada de Rust
│   ├── build.rs                               # Script de construcción
│   ├── Cargo.lock                             # Bloqueo de dependencias de Rust
│   ├── Cargo.toml                             # Configuración de Cargo/Rust
│   └── tauri.conf.json                        # Configuración de Tauri
├── src/                                       # Código fuente de Angular
│   ├── app/
│   │   ├── core/                              # Servicios centrales
│   │   │   └── services/
│   │   │       ├── api.service.ts             # Servicio de API y WebSocket
│   │   │       └── environment-detector.service.ts # Detección de entorno
│   │   ├── features/                          # Módulos de funcionalidades
│   │   │   ├── command-center/                # Centro de comando
│   │   │   │   ├── command-center.component.scss
│   │   │   │   ├── command-center.component.ts
│   │   │   │   ├── command-prompt.component.html
│   │   │   │   ├── command-prompt.component.scss
│   │   │   │   └── command-prompt.component.ts
│   │   │   ├── event-log/                     # Log de eventos (versión anterior)
│   │   │   │   └── event-log.component.ts
│   │   │   ├── monitoring/                    # Sistema de monitoreo
│   │   │   │   ├── components/
│   │   │   │   │   ├── live-event-log/        # Log de eventos en tiempo real
│   │   │   │   │   │   ├── live-event-log.component.html
│   │   │   │   │   │   ├── live-event-log.component.scss
│   │   │   │   │   │   └── live-event-log.component.ts
│   │   │   │   │   ├── plan-widget/           # Widget del plan de ejecución
│   │   │   │   │   │   ├── plan-widget.component.html
│   │   │   │   │   │   ├── plan-widget.component.scss
│   │   │   │   │   │   └── plan-widget.component.ts
│   │   │   │   │   ├── project-control/       # Control del proyecto
│   │   │   │   │   │   ├── project-control.component.html
│   │   │   │   │   │   ├── project-control.component.scss
│   │   │   │   │   │   └── project-control.component.ts
│   │   │   │   │   ├── status-bar/            # Barra de estado básica
│   │   │   │   │   │   ├── status-bar.component.html
│   │   │   │   │   │   ├── status-bar.component.scss
│   │   │   │   │   │   └── status-bar.component.ts
│   │   │   │   │   ├── status-bar-advanced/   # Barra de estado avanzada
│   │   │   │   │   │   ├── status-bar-advanced.component.html
│   │   │   │   │   │   ├── status-bar-advanced.component.scss
│   │   │   │   │   │   └── status-bar-advanced.component.ts
│   │   │   │   │   └── status-footer/         # Pie de estado
│   │   │   │   │       ├── status-footer.component.html
│   │   │   │   │       ├── status-footer.component.scss
│   │   │   │   │       └── status-footer.component.ts
│   │   │   │   ├── monitoring.component.html          # Componente principal de monitoreo
│   │   │   │   ├── monitoring.component.scss
│   │   │   │   ├── monitoring.component.ts
│   │   │   │   ├── monitoring-no-statusbar.component.ts    # Variante sin barra de estado
│   │   │   │   ├── monitoring-ultra-simple.component.ts    # Variante ultra simple
│   │   │   │   ├── monitoring-web-advanced.component.html  # Variante web avanzada
│   │   │   │   ├── monitoring-web-advanced.component.scss
│   │   │   │   └── monitoring-web-advanced.component.ts
│   │   │   ├── test-connection/               # Prueba de conexión
│   │   │   │   ├── test-connection.component.html
│   │   │   │   ├── test-connection.component.scss
│   │   │   │   └── test-connection.component.ts
│   │   │   └── workspace/                     # Espacio de trabajo
│   │   │       ├── workspace.component.html
│   │   │       ├── workspace.component.scss
│   │   │       └── workspace.component.ts
│   │   ├── shared/                            # Recursos compartidos
│   │   │   └── models/
│   │   │       └── dirgen.models.ts           # Modelos de datos de DirGen
│   │   ├── store/                             # Estado global (NgRx)
│   │   │   ├── plan/                          # Estado del plan de ejecución
│   │   │   │   ├── plan.actions.ts
│   │   │   │   ├── plan.reducer.ts
│   │   │   │   └── plan.selectors.ts
│   │   │   ├── workspace/                     # Estado del workspace
│   │   │   │   ├── workspace.actions.ts
│   │   │   │   ├── workspace.reducer.ts
│   │   │   │   └── workspace.selectors.ts
│   │   │   ├── app.actions.ts                 # Acciones principales de la app
│   │   │   ├── app.reducer.ts                 # Reducer principal
│   │   │   ├── app.selectors.ts               # Selectores principales
│   │   │   ├── effects.ts                     # Efectos secundarios (WebSocket, API)
│   │   │   ├── index.ts                       # Configuración del store
│   │   │   └── models.ts                      # Modelos de estado
│   │   ├── app.component.html                 # Componente raíz - template
│   │   ├── app.component.scss                 # Componente raíz - estilos
│   │   ├── app.component.spec.ts              # Pruebas del componente raíz
│   │   ├── app.component.ts                   # Componente raíz
│   │   ├── app.config.server.ts               # Configuración del servidor
│   │   ├── app.config.ts                      # Configuración de la app
│   │   └── app.routes.ts                      # Rutas de la aplicación
│   ├── assets/                                # Recursos estáticos
│   │   └── .gitkeep
│   ├── environments/                          # Configuraciones de entorno
│   │   └── environment.ts                     # Entorno por defecto
│   ├── favicon.ico                            # Icono de la aplicación
│   ├── index.html                             # Página principal HTML
│   ├── main.server.ts                         # Punto de entrada del servidor
│   ├── main.ts                                # Punto de entrada principal
│   └── styles.scss                            # Estilos globales
├── .editorconfig                              # Configuración del editor
├── EJECUTAR_DIRGEN.md                         # Documentación de ejecución
├── README.md                                  # Documentación principal
├── angular.json                               # Configuración de Angular
├── package.json                               # Dependencias de Node.js
├── server.ts                                  # Servidor Express
├── tsconfig.app.json                          # Configuración TypeScript para la app
├── tsconfig.json                              # Configuración TypeScript base
└── tsconfig.spec.json                         # Configuración TypeScript para tests
```

## Descripción de Componentes Principales

### Core Services
- **api.service.ts**: Maneja la comunicación con el backend, incluyendo WebSocket para tiempo real
- **environment-detector.service.ts**: Detecta si se ejecuta en web o desktop

### Features

#### Command Center
Centro de comando donde el usuario puede:
- Subir archivos SVAD
- Escribir comandos
- Aprobar/rechazar planes generados

#### Monitoring
Sistema completo de monitoreo con múltiples variantes:
- **Monitoring básico**: Vista estándar con todos los componentes
- **No Status Bar**: Sin barra de estado superior
- **Ultra Simple**: Vista minimalista
- **Web Advanced**: Optimizada para versión web

#### Store (NgRx)
Estado global de la aplicación organizado en módulos:
- **App**: Estado principal (conexión, loading, errores)
- **Plan**: Estado del plan de ejecución y aprobaciones
- **Workspace**: Estado del espacio de trabajo y archivos

### Tauri Integration
Configuración para generar la aplicación de escritorio multiplataforma usando Rust y Tauri.

## Tecnologías Utilizadas

- **Frontend**: Angular 17+ con Angular Material
- **Estado**: NgRx para gestión de estado
- **Desktop**: Tauri (Rust + WebView)
- **Comunicación**: WebSocket para tiempo real
- **Estilos**: SCSS + Angular Material
- **Build**: Angular CLI + Tauri CLI

## Patrones de Arquitectura

- **Feature-based**: Organización por funcionalidades
- **State Management**: Patrón Redux con NgRx
- **Component Communication**: Reactive patterns con RxJS
- **Service Layer**: Separación de lógica de negocio
- **Modular Design**: Componentes reutilizables y modulares