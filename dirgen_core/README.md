# 🧠 DirGen Core - Servicios Centralizados de LLM

**DirGen Core** es el módulo central de la plataforma que proporciona servicios compartidos optimizados para la gestión de múltiples proveedores de LLM (Large Language Models). Implementa principios SOLID y patrones de diseño avanzados para garantizar escalabilidad, resiliencia y optimización de costos.

## 🎯 Objetivos

- **🏗️ Modularidad**: Servicios LLM reutilizables y desacoplados
- **💰 Optimización de Costos**: Cache inteligente y consolidación de historial
- **🛡️ Resiliencia**: Fallback automático y manejo de errores robusto
- **⚡ Performance**: Selección óptima de modelos según tipo de tarea
- **🔄 Escalabilidad**: Soporte para múltiples proveedores simultáneos

## 📦 Arquitectura del Módulo

```
dirgen_core/
├── __init__.py                 # Punto de entrada del módulo
└── llm_services/              # Servicios especializados de LLM
    ├── __init__.py            # Exportación de funciones principales
    ├── main_llm_service.py    # 🎯 Servicio principal con lógica de priorización
    ├── api_clients.py         # 🔌 Clientes para todos los proveedores LLM
    ├── local_model_manager.py # 🖥️ Gestión de modelos locales vía Docker
    └── gemini_key_rotator.py  # 🔄 Sistema de rotación de claves API Gemini
```

## 🚀 Uso Principal

### Importación Simplificada

```python
from dirgen_core.llm_services import ask_llm, get_agent_profile, select_optimal_model

# Llamada básica
response = ask_llm(
    model_id="ai/gemma3-qat",
    system_prompt="Eres un arquitecto de software experto",
    user_prompt="Diseña una API REST para un sistema financiero",
    task_type="architecture",
    use_cache=True
)

# Obtener perfil de agente desde PCCE
profile = get_agent_profile(pcce_data, "planner")

# Selección óptima de modelo
optimal_model = select_optimal_model("complex_generation", profile)
```

## 🔧 Componentes Principales

### 1. 🎯 `main_llm_service.py`

**Función principal:** `ask_llm(model_id, system_prompt, user_prompt, task_type, use_cache)`

#### Características:
- **Priorización inteligente** de proveedores LLM
- **Fallback automático** en caso de fallos
- **Cache inteligente** para tareas repetitivas
- **Rate limit detection** con candado de seguridad
- **Selección óptima** de modelos por tipo de tarea

#### Tipos de tarea soportados:
- `planning`: Planificación estratégica
- `architecture`: Diseño de arquitectura
- `complex_generation`: Generación de código complejo
- `simple_generation`: Tareas simples
- `verification`: Validación y verificación
- `general`: Tareas generales

#### Configuración:
```bash
# Variables de entorno
export LLM_PRIORITY_ORDER="gemini,local,groq,openai,anthropic,xai"
export OPENAI_API_KEY="tu-key"
export GEMINI_API_KEY="tu-key"
# ... otros proveedores
```

### 2. 🔌 `api_clients.py`

**Funciones disponibles:**
- `call_openai_llm(messages)` - Cliente OpenAI GPT
- `call_anthropic_llm(messages)` - Cliente Anthropic Claude  
- `call_groq_llm(messages)` - Cliente Groq
- `call_gemini_llm(messages)` - Cliente Google Gemini
- `call_xai_llm(messages)` - Cliente xAI Grok
- `call_local_llm(model_id, messages)` - Cliente para modelos locales

#### Características:
- **Manejo robusto de errores** con reintentos
- **Rate limiting** inteligente
- **Timeouts configurables**
- **Logging estructurado** para debugging

### 3. 🖥️ `local_model_manager.py`

**Función principal:** `ensure_model_available(model_id)`

#### Modelos locales soportados:
- `ai/qwen3-coder` - Generación de código especializada
- `ai/gemma3-qat` - Tareas generales optimizadas  
- `ai/smollm3` - Tareas simples de bajo costo
- `ai/gemma3` - Tareas generales estándar
- `ai/gemma3n` - Variante optimizada

#### Configuración DMR:
```bash
export DMR_BASE_URL="http://localhost:8080"  # Dynamic Model Router
```

### 4. 🔄 `gemini_key_rotator.py`

**Funciones principales:**
- `get_rotated_gemini_key()` - Obtiene key con load balancing
- `record_gemini_result(key, success)` - Registra resultado de uso

#### Configuración múltiples keys:
```bash
export GEMINI_API_KEY_1="key1"
export GEMINI_API_KEY_2="key2"  
export GEMINI_API_KEY_3="key3"
```

#### Características:
- **Load balancing** equitativo
- **Recovery automático** de keys bloqueadas
- **Estadísticas de uso** por key
- **Rotación inteligente** basada en performance

## 📊 Optimización de Costos

### Cache Inteligente
```python
# Cache automático para tareas repetitivas
response = ask_llm(
    model_id="ai/smollm3",
    system_prompt="Sistema de validación",
    user_prompt="Valida este JSON...",
    task_type="verification",
    use_cache=True  # ✨ Evita llamadas redundantes
)
```

### Selección Óptima de Modelos
- **Tareas simples** → Modelos locales (costo = $0)
- **Tareas complejas** → Modelos cloud (costo optimizado)
- **Verificaciones** → Cache + modelos eficientes

## 🛡️ Resiliencia y Manejo de Errores

### Fallback Automático
```python
# Si Gemini falla → Local → Groq → OpenAI → Anthropic → xAI
response = ask_llm(model_id="cualquiera", ...)  # Fallback transparente
```

### Rate Limit Detection
```python
# Detección automática de límites de API
# Activación de "candado de seguridad" con modelo local
```

### Circuit Breakers
- Evita cascadas de fallos
- Recovery automático tras período de enfriamiento
- Métricas de salud por proveedor

## 📈 Observabilidad

### Logging Estructurado
```python
logger.info(f"✅ {provider.upper()} respondió exitosamente ({len(response)} caracteres)")
logger.warning(f"❌ {provider.upper()} falló: {error_msg}")
logger.info(f"🎯 Respuesta recuperada de cache para tarea: {task_type}")
```

### Métricas Disponibles
- **Performance**: Latencia por proveedor, tokens/segundo
- **Costos**: Tokens utilizados, estimación de costos por proveedor
- **Resiliencia**: Rate de fallos, fallbacks ejecutados, cache hits
- **Usage**: Distribución de carga entre proveedores

## 🔧 Desarrollo y Extensión

### Agregar Nuevo Proveedor LLM

1. **Crear cliente en `api_clients.py`**:
```python
def call_nuevo_llm(messages: list) -> str:
    """Cliente para Nuevo Proveedor LLM"""
    # Implementación específica
    pass
```

2. **Registrar en `main_llm_service.py`**:
```python
elif provider_name == "nuevo":
    return lambda: call_nuevo_llm(messages)
```

3. **Actualizar configuración**:
```bash
export NUEVO_API_KEY="tu-key"
export LLM_PRIORITY_ORDER="nuevo,gemini,local,..."
```

### Testing

```python
# Ejemplo de test
def test_ask_llm():
    response = ask_llm(
        model_id="ai/smollm3",
        system_prompt="Eres un asistente útil",
        user_prompt="Hola",
        task_type="simple_generation"
    )
    assert len(response) > 0
    assert "Error" not in response
```

## 🏆 Principios de Diseño Aplicados

### SOLID
- **S**: Cada servicio tiene una responsabilidad única
- **O**: Extensible para nuevos proveedores sin modificar código existente
- **L**: Los clientes pueden sustituirse transparentemente
- **I**: Interfaces segregadas por funcionalidad
- **D**: Dependencias hacia abstracciones, no implementaciones concretas

### Patrones de Diseño
- **Strategy Pattern**: Selección dinámica de proveedores LLM
- **Chain of Responsibility**: Fallback entre proveedores
- **Singleton**: Cache y configuración global
- **Factory**: Creación de clientes LLM

## 🚀 Roadmap

### v2.1 (Próximo)
- [ ] Métricas avanzadas con Prometheus
- [ ] Dashboard de monitoreo en tiempo real  
- [ ] API REST para gestión externa

### v2.2 (Futuro)
- [ ] Balanceador de carga inteligente
- [ ] Predicción de costos pre-ejecución
- [ ] Optimización automática de prompts

---

**🧠 DirGen Core - La inteligencia centralizada de la plataforma DirGen**

*Optimización • Resiliencia • Escalabilidad • Performance*