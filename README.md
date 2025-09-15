# 🏗️ DirGen Platform

**DirGen** es una plataforma inteligente de generación automática de proyectos de software que utiliza agentes de IA especializados para crear estructuras de código completas y funcionales basadas en especificaciones de alto nivel.

## 🎯 Descripción General

DirGen transforma **PCCE** (Project Context, Components, and Expectations) en proyectos de software completamente funcionales mediante un sistema multi-agente que incluye:

- **🤖 Agente Planificador**: Genera la arquitectura y diseño del proyecto
- **✅ Agente Validador**: Valida la calidad y completitud de los artefactos generados
- **🎭 Agentes Especializados**: Implementan código específico por tecnología
- **🎯 Orquestador**: Coordina todo el flujo de trabajo
- **🖥️ Cliente TUI**: Interfaz de usuario terminal interactiva

## 🏛️ Arquitectura

```
DirGen Platform
├── 🖥️ client/          # Interfaz de usuario (CLI + TUI)
├── 🎯 mcp_host/         # Coordinador central del sistema
├── 🤖 agents/          # Agentes de IA especializados
│   ├── planner/        # Generación de diseño y arquitectura
│   ├── validator/      # Validación de calidad
│   └── specialized/    # Agentes por tecnología
├── 📋 pcce_finbase.yml # PCCE de ejemplo para FinBase
└── 📊 logs/            # Sistema de logging distribuido
```

## 🚀 Inicio Rápido

### Prerrequisitos

- **Python 3.8+**
- **Conexión a Internet** (para LLM API)
- **Variables de entorno** configuradas para el LLM

### Instalación

```bash
# Clonar el repositorio
git clone <repository-url>
cd DirGen

# Instalar dependencias
cd client && pip install -r requirements.txt
cd ../mcp_host && pip install -r requirements.txt

# Los agentes se descargan/configuran automáticamente
```

### Configuración

1. **Configurar variables de entorno para LLM**:
```bash
# Ejemplo para OpenAI (ajustar según tu proveedor)
export OPENAI_API_KEY="tu-api-key"
export LLM_MODEL="gpt-4"
```

2. **Crear o seleccionar un PCCE**:
```bash
# PCCE de ejemplo incluido: pcce_finbase.yml
# Personalizar según necesidades del proyecto
```

### Ejecución

#### Opción 1: Interfaz TUI Interactiva
```bash
cd client
python tui.py
```

#### Opción 2: CLI Directo
```bash
cd client
python cli.py execute ../pcce_finbase.yml
```

El sistema iniciará automáticamente el MCP Host y coordinará todos los agentes necesarios.

## 📋 Formato PCCE

Los PCCE (Project Context, Components, and Expectations) definen qué se debe generar en formato YAML:

```yaml
rol: "Plataforma DirGen: Descripción del rol del sistema"

contexto:
  nombre_proyecto: "Mi Proyecto"
  descripcion: "Descripción detallada del sistema"
  stack_tecnologico:
    lenguaje: "Python 3.11+"
    frameworks: ["FastAPI", "Pydantic"]

entradas:
  requerimientos_funcionales:
    - "FR-01: Descripción del requerimiento"
  arquitectura_propuesta:
    patron: "Microservicios"
    componentes: ["servicio-1", "servicio-2"]

salidas_esperadas:
  - "Diagramas de arquitectura"
  - "Código fuente completo"
  - "Configuración de despliegue"

fases:
  diseno:
    salidas_esperadas:
      - "design/architecture.puml"
      - "design/api/*.yml"
```

## 🔄 Flujo de Trabajo

1. **📤 Envío de PCCE**: El cliente envía la especificación al orquestador
2. **🏗️ Fase de Diseño**: 
   - Agente Planificador genera arquitectura y APIs
   - Quality Gate 1 valida completitud del diseño
3. **👨‍💻 Fase de Implementación**:
   - Agentes especializados generan código por componente
   - Quality Gate 2 valida funcionalidad del código
4. **🚀 Fase de Despliegue**:
   - Generación de configuraciones de infraestructura
   - Quality Gate 3 valida preparación para despliegue

## 🛠️ Componentes Principales

### 🎯 MCP Host (`mcp_host/`)
- **`main.py`**: Coordinador central y punto de entrada
- Maneja la orquestación de agentes
- Proporciona API REST para el cliente
- Gestiona el ciclo de vida de las ejecuciones

### 🖥️ Cliente (`client/`)
- **`cli.py`**: Interfaz de línea de comandos
- **`tui.py`**: Interfaz de usuario terminal interactiva
- **`tui.css`**: Estilos para la interfaz TUI
- **`requirements.txt`**: Dependencias del cliente

### 🤖 Agentes (`agents/`)

#### Agente Planificador (`agents/planner/`)
- Genera diagramas de arquitectura (PlantUML)
- Crea especificaciones OpenAPI
- Define estructura de proyecto
- Implementa bucle de corrección inteligente

#### Agente Validador (`agents/validator/`)
- Valida completitud de artefactos
- Verifica calidad del código generado
- Ejecuta quality gates
- Proporciona feedback para correcciones

### 📋 PCCE de Ejemplo
- **`pcce_finbase.yml`**: Especificación completa para sistema FinBase
- Incluye requerimientos funcionales y no funcionales
- Define arquitectura de microservicios
- Especifica quality gates y políticas de gobernanza

## 📊 Monitoreo y Logs

### Logs del Sistema
- **MCP Host**: `mcp_host/logs/`
- **Agentes**: `agents/*/logs/`
- **Cliente**: `client/logs/`

### Formato de Logs
```
TIMESTAMP - COMPONENT - LEVEL - MESSAGE
2025-09-15 14:00:01,132 - DirGenTUI - INFO - Quality Gate APROBADO
```

### Comunicación en Tiempo Real
- **WebSocket**: Streaming de progreso en tiempo real
- **Mensajes estructurados**: Pensamientos, acciones, errores
- **Reintentos inteligentes**: Sistema de corrección automática

## 🔧 Desarrollo y Extensión

### Agregar Nuevos Agentes

1. Crear directorio en `agents/nuevo_agente/`
2. Implementar interfaz base del agente
3. Registrar en el orquestador
4. Definir quality gates específicos

### Personalizar Quality Gates

Editar el PCCE con las validaciones deseadas:

```yaml
fases:
  diseno:
    descripcion: "Generar artefactos de diseño"
    salidas_esperadas:
      - "design/architecture.puml"
      - "design/api/*.yml"

politicas_de_gobernanza:
  - "qual-test-coverage-80"
  - "std-python-black-isort"
  - "sec-no-hardcoded-secrets"
```

## 🤝 Contribución

1. Fork el repositorio
2. Crear rama feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para detalles.

## 🆘 Soporte

Para reportar bugs o solicitar funcionalidades:
- **Issues**: Usar el sistema de issues del repositorio
- **Logs**: Incluir logs relevantes del componente afectado
- **PCCE**: Proporcionar el PCCE que causó el problema (si aplica)

## 🎉 Ejemplos

### Ejemplo: Plataforma de Datos Financieros (FinBase)

```bash
# Usar el PCCE incluido
cd client
python cli.py execute ../pcce_finbase.yml

# El sistema generará:
# ├── design/architecture.puml
# ├── design/api/collector.yml
# ├── design/api/quality.yml
# ├── design/api/storage.yml
# ├── design/api/api.yml
# ├── design/api/backfill.yml
# └── [fases posteriores con código fuente]
```

### Ejemplo: Modo Interactivo

```bash
# Interfaz TUI interactiva
cd client
python tui.py

# Seleccionar PCCE y monitorear progreso en tiempo real
```

---

**🚀 DirGen - Transformando ideas en código funcional**

*Desarrollado con ❤️ por el equipo DirGen*