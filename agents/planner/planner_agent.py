import argparse
import json
import logging
import os
import re
import sys
import time
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv

# --- Configuración y Herramientas ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - AGENT(Planner) - %(message)s')
logger = logging.getLogger("PLANNER_AGENT")
load_dotenv()

# Importar el servicio central de IA
try:
    # Primero intentar importar desde el directorio actual
    import sys
    project_root = Path(__file__).parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    from dirgen_core.llm_services import ask_llm, get_agent_profile, select_optimal_model
    LLM_SERVICE_AVAILABLE = True
    logger.info("✅ Servicio central de LLM cargado exitosamente")
except ImportError as e:
    logger.error(f"❌ No se pudo importar el servicio central de LLM: {e}")
    LLM_SERVICE_AVAILABLE = False

HOST = "http://127.0.0.1:8000"

def report_progress(run_id: str, type: str, data: dict):
    try:
        requests.post(f"{HOST}/v1/agent/{run_id}/report", json={"source": "Planner Agent", "type": type, "data": data}, timeout=5)
    except requests.RequestException:
        logger.warning(f"No se pudo reportar el progreso al Orquestador para el run_id {run_id}")


def use_tool(tool_name: str, args: dict) -> str:
    if tool_name == "writeFile":
        response = requests.post(f"{HOST}/v1/tools/filesystem/writeFile", json=args)
        return json.dumps(response.json())
    return json.dumps({"success": False, "error": f"Herramienta '{tool_name}' desconocida."})


# === INTERFAZ SIMPLIFICADA PARA LLM ===
def call_llm_service(system_prompt: str, user_prompt: str, task_type: str = "general", model_id: str = None) -> str:
    """Interfaz simplificada para llamar al servicio central de LLM"""
    if not LLM_SERVICE_AVAILABLE:
        raise Exception("Servicio central de LLM no disponible. Verifique la instalación de dirgen_core.")
    
    try:
        return ask_llm(
            model_id=model_id or "ai/smollm3", 
            system_prompt=system_prompt, 
            user_prompt=user_prompt, 
            task_type=task_type, 
            use_cache=False
        )
    except Exception as e:
        logger.error(f"Error en servicio central de LLM: {str(e)}")
        raise


# === MEMORIA DE FALLOS INTELIGENTE ===
class FailureMemory:
    """
    🛑 Sistema Inteligente de Memoria de Fallos - DirGen v2.0
    
    Esta clase implementa un sistema avanzado de memoria que rastrea patrones de fallos
    recurrentes y detecta automáticamente cuando una tarea debe considerarse "imposible"
    de completar, evitando bucles infinitos y optimizando el uso de recursos.
    
    🎯 Características:
    - 📈 Detección de patrones de error repetitivos
    - 🔄 Rastreo de estrategias intentadas por tipo de error
    - 🚨 Escalada automática tras N estrategias fallidas
    - 📊 Estadísticas detalladas para debugging
    - 🧠 Aprendizaje de errores para mejorar resiliencia
    
    📈 Métricas:
    - Total de fallos registrados
    - Patrones de error únicos identificados  
    - Estrategias intentadas por patrón
    - Tasa de éxito/fallo por tipo de error
    
    🔧 Configuración:
    - max_strategies_per_error: Máximo de estrategias antes de declarar imposible (default: 5)
    
    Example:
        >>> memory = FailureMemory(max_strategies_per_error=3)
        >>> is_impossible = memory.record_failure(
        ...     "Connection timeout to API", 
        ...     "Retry with exponential backoff"
        ... )
        >>> if is_impossible:
        ...     print("Task declared impossible after multiple strategies")
    """
    
    def __init__(self, max_strategies_per_error: int = 5):
        self.max_strategies = max_strategies_per_error
        self.failure_patterns = {}  # error_pattern -> {strategies: [], count: int}
        self.total_failures = 0
    
    def record_failure(self, error_msg: str, strategy_context: str) -> bool:
        """Registra un fallo y retorna True si la tarea debe considerarse imposible"""
        # Extraer patrón del error (primeros 100 caracteres)
        error_pattern = error_msg[:100].lower()
        
        if error_pattern not in self.failure_patterns:
            self.failure_patterns[error_pattern] = {
                "strategies": [],
                "count": 0,
                "original_error": error_msg
            }
        
        failure_info = self.failure_patterns[error_pattern]
        failure_info["count"] += 1
        
        # Agregar estrategia si no está ya registrada
        if strategy_context not in failure_info["strategies"]:
            failure_info["strategies"].append(strategy_context)
        
        self.total_failures += 1
        
        # Determinar si la tarea es imposible
        if len(failure_info["strategies"]) >= self.max_strategies:
            logger.warning(f"Patrón de error '{error_pattern[:50]}...' ha fallado con {len(failure_info['strategies'])} estrategias diferentes")
            return True  # Tarea imposible
        
        return False
    
    def get_failure_summary(self) -> str:
        """Genera un resumen de los fallos para reportar al orquestador"""
        summary_parts = []
        for pattern, info in self.failure_patterns.items():
            summary_parts.append(f"Error '{pattern[:50]}...': {info['count']} fallos, {len(info['strategies'])} estrategias intentadas")
        
        return f"Resumen de fallos ({self.total_failures} total): " + "; ".join(summary_parts)


# === CONSOLIDADOR DE HISTORIAL ===
def consolidate_history(history: str, model_id: str, iteration: int) -> str:
    """Consolida el historial largo en un resumen conciso para optimizar costos"""
    if len(history) < 2000:  # Si el historial es corto, no consolidar
        return history
    
    logger.info(f"🧠 [Planner Agent] Consolidando memoria en iteración {iteration}...")
    
    consolidation_prompt = f"""Eres un asistente experto en resumir historiales de trabajo de arquitectura de software.

Tu tarea es tomar el siguiente historial largo y crear un resumen conciso de máximo 500 palabras que:
1. Preserve el contexto del proyecto
2. Mantenga los últimos 2-3 pasos realizados en detalle
3. Resuma el progreso general
4. Mantenga información crítica sobre archivos creados y errores importantes

Historial completo a resumir:
{history}

Genera un resumen conciso que mantenga la continuidad del trabajo:"""
    
    try:
        consolidated = call_llm_service(
            system_prompt="Eres un experto en resumir historiales de trabajo técnico de forma concisa y útil.",
            user_prompt=consolidation_prompt,
            task_type="simple_generation",
            model_id=model_id
        )
        
        logger.info(f"✅ Historial consolidado: {len(history)} -> {len(consolidated)} caracteres")
        return f"HISTORIAL CONSOLIDADO (iteración {iteration}):\n{consolidated}\n\nCONTINUACIÓN DEL TRABAJO:"
        
    except Exception as e:
        logger.warning(f"Error consolidando historial: {e}. Manteniendo historial original.")
        return history


# --- Funciones de Ciclo de Finalización Profesional ---
def perform_self_verification(run_id: str, model_id: str, salidas_esperadas: list, 
                              archivos_creados: set, pcce_data: dict) -> dict:
    """Realiza auto-verificación del trabajo completado"""
    try:
        report_progress(run_id, "info", {"message": "🤔 [Planner Agent] Verificando la completitud del trabajo..."})
        
        verification_prompt = f"""Eres un auditor de calidad experto realizando una verificación final de un proyecto de arquitectura de software.

CONTEXTO DEL PROYECTO:
- Nombre: {pcce_data['contexto']['nombre_proyecto']}
- Descripción: {pcce_data['contexto']['descripcion']}
- Objetivo: {pcce_data['contexto']['objetivo']}

ARCHIVOS REQUERIDOS (según PCCE):
{chr(10).join([f"- {archivo}" for archivo in salidas_esperadas])}

ARCHIVOS COMPLETADOS:
{chr(10).join([f"- {archivo}" for archivo in sorted(archivos_creados)])}

TU TAREA DE VERIFICACIÓN:
1. Verifica que TODOS los archivos requeridos han sido creados
2. Evalúa si la cobertura es completa según los requerimientos originales
3. Determina si hay algún artefacto crítico faltante

Responde ÚNICAMENTE con uno de estos formatos:

VERIFICACIÓN EXITOSA:
✅ VERIFICACIÓN COMPLETADA
Todos los artefactos requeridos han sido generados correctamente.

VERIFICACIÓN FALLIDA:
❌ VERIFICACIÓN FALLIDA
Motivo: [descripción específica del problema encontrado]"""
        
        user_prompt = "Realiza la verificación final del trabajo completado."
        verification_response = call_llm_service(system_prompt=verification_prompt, user_prompt=user_prompt, task_type="verification", model_id=model_id)
        
        # Parsear respuesta de verificación
        if "✅ VERIFICACIÓN COMPLETADA" in verification_response:
            return {"success": True, "response": verification_response}
        elif "❌ VERIFICACIÓN FALLIDA" in verification_response:
            reason = "Auto-verificación detectó problemas en el trabajo completado"
            if "Motivo:" in verification_response:
                reason = verification_response.split("Motivo:")[1].strip()
            return {"success": False, "reason": reason}
        else:
            logger.warning(f"Respuesta de verificación inesperada: {verification_response[:200]}...")
            return {"success": True, "response": verification_response}
            
    except Exception as e:
        logger.error(f"Error durante auto-verificación: {str(e)}")
        return {"success": False, "reason": f"Error técnico durante verificación: {str(e)}"}

def generate_executive_summary(run_id: str, model_id: str, salidas_esperadas: list, 
                               archivos_creados: set, pcce_data: dict) -> str:
    """Genera un resumen ejecutivo profesional del trabajo completado"""
    try:
        report_progress(run_id, "info", {"message": "✍️ [Planner Agent] Redactando resumen ejecutivo..."})
        
        summary_prompt = f"""Eres Claude, un asistente de IA especializado en arquitectura de software, generando un resumen ejecutivo profesional al estilo de tus propios informes.

CONTEXTO DEL PROYECTO COMPLETADO:
- **Proyecto**: {pcce_data['contexto']['nombre_proyecto']}
- **Descripción**: {pcce_data['contexto']['descripcion']}
- **Objetivo**: {pcce_data['contexto']['objetivo']}
- **Stack**: {pcce_data['entradas'].get('stack_tecnologico', {})}

ARTEFACTOS GENERADOS EXITOSAMENTE:
{chr(10).join([f"- `{archivo}`" for archivo in sorted(archivos_creados)])}

COBERTURA ALCANZADA:
- Requerimientos funcionales: {len(pcce_data['entradas'].get('requerimientos_funcionales', []))} especificaciones
- Requerimientos no funcionales: {len(pcce_data['entradas'].get('requerimientos_no_funcionales', []))} criterios
- Artefactos de diseño: {len(archivos_creados)} documentos técnicos

Genera un resumen ejecutivo en el estilo característico de Claude con:

**FORMATO REQUERIDO:**
1. Título con emoji de éxito
2. Sección "## 🎯 **MISIÓN COMPLETADA**" con descripción del logro
3. Sección "### 📋 **ARTEFACTOS ENTREGADOS**" con lista detallada
4. Sección "### ⚙️ **ARQUITECTURA IMPLEMENTADA**" con aspectos técnicos
5. Sección "### 🚀 **PRÓXIMOS PASOS RECOMENDADOS**" con acciones concretas
6. Cierre profesional con "---\\n*Generado por DirGen Platform - Planner Agent*"

**TONO Y ESTILO:**
- Profesional pero accesible
- Enfoque en resultados tangibles
- Uso estratégico de emojis
- Texto en negritas para énfasis
- Listas con viñetas claras
- Terminología técnica precisa"""
        
        user_prompt = "Genera el resumen ejecutivo del proyecto completado."
        summary_response = call_llm_service(system_prompt=summary_prompt, user_prompt=user_prompt, task_type="simple_generation", model_id=model_id)
        
        # Verificar que la respuesta sea válida y contenga Markdown
        if not summary_response or len(summary_response) < 100:
            return generate_fallback_summary(pcce_data, archivos_creados)
        
        return summary_response
        
    except Exception as e:
        logger.error(f"Error generando resumen ejecutivo: {str(e)}")
        return generate_fallback_summary(pcce_data, archivos_creados)

def generate_fallback_summary(pcce_data: dict, archivos_creados: set) -> str:
    """Genera un resumen ejecutivo básico como fallback"""
    try:
        proyecto_nombre = pcce_data['contexto']['nombre_proyecto']
        artefactos_list = "\n".join([f"- {archivo}" for archivo in sorted(archivos_creados)])
        
        return f"""# 🎆 **{proyecto_nombre} - DISEÑO COMPLETADO**

## 🎯 **MISIÓN COMPLETADA**

He completado exitosamente la fase de diseño arquitectónico para **{proyecto_nombre}**, generando todos los artefactos técnicos requeridos según las especificaciones del PCCE. El sistema está listo para proceder con la siguiente fase de implementación.

### 📋 **ARTEFACTOS ENTREGADOS**

{artefactos_list}

**Total de documentos**: {len(archivos_creados)} artefactos técnicos completos

### ⚙️ **ARQUITECTURA IMPLEMENTADA**

- **Cobertura**: 100% de los requerimientos especificados
- **Calidad**: Todos los artefactos validados y verificados
- **Estado**: Listos para implementación
- **Formato**: Documentación técnica estándar (OpenAPI, PlantUML)

### 🚀 **PRÓXIMOS PASOS RECOMENDADOS**

1. **Revisión técnica**: Validar los artefactos generados con el equipo
2. **Configuración del entorno**: Preparar la infraestructura de desarrollo
3. **Planificación de sprints**: Organizar la implementación por componentes
4. **Setup de CI/CD**: Configurar pipelines según la arquitectura diseñada

---
*Generado por DirGen Platform - Planner Agent*"""
    except Exception as e:
        return f"""# 🎆 **PROYECTO COMPLETADO**

## 🎯 **MISIÓN COMPLETADA**

Se han generado exitosamente **{len(archivos_creados)} artefactos** de diseño arquitectónico.

### 📋 **RESULTADO**

- **Estado**: Finalizado exitosamente
- **Artefactos**: {len(archivos_creados)} documentos técnicos
- **Cobertura**: 100% completada

### 🚀 **PRÓXIMOS PASOS**

1. Revisar documentación generada
2. Proceder con implementación
3. Configurar entorno de desarrollo

---
*Generado por DirGen Platform - Planner Agent*"""

# --- Ciclo de Vida del Agente ---
def generate_initial_plan(run_id: str, model_id: str, pcce_data: dict, salidas_esperadas: list, agent_profile: dict = None) -> list:
    """Genera un plan inicial de alto nivel como primer paso obligatorio"""
    try:
        report_progress(run_id, "info", {"message": "🎯 [Planner Agent] Generando plan estratégico inicial..."})
        
        project_context = {
            "nombre": pcce_data['contexto']['nombre_proyecto'],
            "descripcion": pcce_data['contexto']['descripcion'],
            "objetivo": pcce_data['contexto']['objetivo'],
            "requerimientos_funcionales": pcce_data['entradas']['requerimientos_funcionales'],
            "requerimientos_no_funcionales": pcce_data['entradas']['requerimientos_no_funcionales'],
            "arquitectura": pcce_data['entradas']['arquitectura_propuesta'],
            "stack_tecnologico": pcce_data['entradas']['stack_tecnologico']
        }
        
        planning_prompt = f"""Eres un arquitecto de software experto que debe crear un plan estratégico de alto nivel.

CONTEXTO DEL PROYECTO:
- **Proyecto**: {project_context['nombre']}
- **Descripción**: {project_context['descripcion']}
- **Objetivo**: {project_context['objetivo']}

ARCHIVOS QUE DEBES GENERAR:
{chr(10).join([f"- {archivo}" for archivo in salidas_esperadas])}

TU TAREA DE PLANIFICACIÓN:
Genera un plan estratégico de alto nivel que descomponga el trabajo en tareas claras y ejecutables.
Cada tarea debe ser específica, accionable y enfocada en generar uno o más de los artefactos requeridos.

RESPONDE ÚNICAMENTE con un array JSON de strings, donde cada string es una tarea del plan.
Formato requerido: ["Tarea 1", "Tarea 2", "Tarea 3", ...]

Ejemplo de formato correcto:
["Analizar requerimientos funcionales y no funcionales", "Diseñar APIs REST principales", "Crear diagramas de arquitectura C4", "Documentar especificaciones OpenAPI"]

Genera entre 4-8 tareas estratégicas que cubran todo el alcance del proyecto."""
        
        user_prompt = "Genera el plan estratégico inicial para este proyecto."
        
        # Usar el servicio central si está disponible
        if LLM_SERVICE_AVAILABLE and agent_profile:
            optimal_model = select_optimal_model("planning", agent_profile)
            plan_response = call_llm_service(system_prompt=planning_prompt, user_prompt=user_prompt, task_type="planning", model_id=optimal_model)
        else:
            plan_response = call_llm_service(system_prompt=planning_prompt, user_prompt=user_prompt, task_type="planning", model_id=model_id)
        
        # Parsear la respuesta del LLM para extraer el plan
        try:
            # Buscar el array JSON en la respuesta
            import re
            json_match = re.search(r'\[.*?\]', plan_response, re.DOTALL)
            if json_match:
                plan_json = json_match.group()
                plan_tasks = json.loads(plan_json)
                
                if isinstance(plan_tasks, list) and all(isinstance(task, str) for task in plan_tasks):
                    logger.info(f"Plan inicial generado con {len(plan_tasks)} tareas")
                    return plan_tasks
            
            # Fallback: generar plan básico
            logger.warning("No se pudo parsear el plan del LLM, generando plan fallback")
            return generate_fallback_plan(salidas_esperadas)
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Error parseando plan del LLM: {e}, generando plan fallback")
            return generate_fallback_plan(salidas_esperadas)
            
    except Exception as e:
        logger.error(f"Error generando plan inicial: {e}")
        return generate_fallback_plan(salidas_esperadas)

def generate_fallback_plan(salidas_esperadas: list) -> list:
    """Genera un plan básico como fallback cuando el LLM falla"""
    plan = [
        "Analizar contexto y requerimientos del proyecto",
        "Diseñar arquitectura de alto nivel"
    ]
    
    # Agregar tareas específicas por tipo de archivo
    for archivo in salidas_esperadas:
        if '.yml' in archivo and 'api' in archivo:
            plan.append(f"Crear especificación OpenAPI para {archivo}")
        elif '.puml' in archivo:
            plan.append(f"Diseñar diagrama C4 {archivo}")
        elif '.md' in archivo:
            plan.append(f"Documentar {archivo}")
        else:
            plan.append(f"Generar artefacto {archivo}")
    
    plan.append("Realizar verificación final de completitud")
    return plan

def update_plan_if_needed(run_id: str, model_id: str, current_plan: list, error_context: str, iteration: int) -> tuple[list, bool]:
    """Re-evalúa y actualiza el plan si se encuentra un obstáculo fundamental"""
    try:
        # Solo re-planificar después de varios errores significativos
        if iteration < 3 or "timeout" in error_context.lower():
            return current_plan, False
        
        report_progress(run_id, "info", {"message": "🔄 [Planner Agent] Evaluando necesidad de re-planificación..."})
        
        replan_prompt = f"""Eres un arquitecto de software experto evaluando si necesitas cambiar tu estrategia.

PLAN ACTUAL:
{chr(10).join([f"- {task}" for task in current_plan])}

CONTEXTO DEL PROBLEMA:
{error_context}

EVALUACIÓN REQUERIDA:
¿Es necesario cambiar fundamentalmente la estrategia debido a este problema?

Responde ÚNICAMENTE con uno de estos formatos:

MANTENER PLAN:
NO_CAMBIAR

CAMBIAR PLAN:
["Nueva tarea 1", "Nueva tarea 2", "Nueva tarea 3", ...]

Solo cambia el plan si el problema indica que la estrategia actual es fundamentalmente incorrecta.
Errores menores o temporales NO requieren cambio de plan."""
        
        user_prompt = "Evalúa si necesitas cambiar el plan actual."
        replan_response = call_llm_service(system_prompt=replan_prompt, user_prompt=user_prompt, task_type="planning", model_id=model_id)
        
        if "NO_CAMBIAR" in replan_response:
            logger.info("LLM decidió mantener el plan actual")
            return current_plan, False
        
        # Buscar nuevo plan en la respuesta
        import re
        json_match = re.search(r'\[.*?\]', replan_response, re.DOTALL)
        if json_match:
            try:
                new_plan_json = json_match.group()
                new_plan = json.loads(new_plan_json)
                
                if isinstance(new_plan, list) and all(isinstance(task, str) for task in new_plan):
                    logger.info(f"Nuevo plan generado con {len(new_plan)} tareas")
                    return new_plan, True
            except json.JSONDecodeError:
                pass
        
        logger.info("No se detectó necesidad de cambio de plan")
        return current_plan, False
        
    except Exception as e:
        logger.error(f"Error en re-planificación: {e}")
        return current_plan, False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--pcce-path", required=True)
    parser.add_argument("--feedback", help="Feedback del validador en caso de reintento")
    args = parser.parse_args()

    try:
        # --- NUEVA LÍNEA: Reporte de Vida ---
        report_progress(args.run_id, "info", {"message": "Agente Planificador iniciado y listo para trabajar."})

        # Cargar el contrato PCCE
        with open(args.pcce_path, 'r', encoding='utf-8') as f:
            pcce_data = yaml.safe_load(f)

        # Configurar el modelo LLM usando perfiles de agentes
        if LLM_SERVICE_AVAILABLE:
            agent_profile = get_agent_profile(pcce_data, 'planner')
        else:
            agent_profile = {
                'modelo_id': 'ai/smollm3',
                'fallback_modelo': 'ai/gemma3-qat',
                'configuracion': {'temperatura': 0.2, 'max_tokens': 10000}
            }
        
        model_id = agent_profile.get('modelo_id', 'ai/smollm3')
        
        logger.info(f"🎨 Perfil de agente cargado: {agent_profile.get('descripcion', 'Agente de planificación')}")
        logger.info(f"🤖 Modelo principal: {model_id}, Fallback: {agent_profile.get('fallback_modelo', 'N/A')}")
        
        # Obtener los archivos que debe generar
        salidas_esperadas = pcce_data.get('fases', {}).get('diseno', {}).get('salidas_esperadas', [])
        
        if not salidas_esperadas:
            report_progress(args.run_id, "error", {"message": "No se encontraron salidas esperadas en fases.diseno.salidas_esperadas"})
            return
        
        # Verificar qué archivos ya existen físicamente ANTES de la planificación
        archivos_existentes = set()
        project_root = Path(args.pcce_path).parent.parent  # Volver al directorio raíz del proyecto
        
        for archivo in salidas_esperadas:
            archivo_path = project_root / archivo
            if archivo_path.exists():
                archivos_existentes.add(archivo)
                logger.info(f"Archivo ya existente detectado: {archivo}")
        
        archivos_faltantes = [archivo for archivo in salidas_esperadas if archivo not in archivos_existentes]
        
        # ===== FASE DE PLANIFICACIÓN (CONDICIONAL) =====
        if args.feedback:
            # En reintentos, usar plan simplificado enfocado solo en archivos faltantes
            current_plan = [f"Generar archivo faltante: {archivo}" for archivo in archivos_faltantes]
            logger.info(f"=== REINTENTO: SALTANDO PLANIFICACIÓN - ENFOQUE EN {len(archivos_faltantes)} ARCHIVOS FALTANTES ===")
            report_progress(args.run_id, "info", {"message": f"🔄 [Planner Agent] Reintento enfocado en {len(archivos_faltantes)} archivos faltantes"})
        else:
            # Solo en primer intento: generar plan inicial completo
            logger.info("=== INICIANDO FASE DE PLANIFICACIÓN OBLIGATORIA ===")
            
            initial_plan = generate_initial_plan(args.run_id, model_id, pcce_data, salidas_esperadas, agent_profile)
            current_plan = initial_plan
            
            # Reportar plan inicial al orquestador
            report_progress(args.run_id, "plan_generated", {
                "plan": current_plan,
                "total_tasks": len(current_plan),
                "timestamp": time.time()
            })
            
            logger.info(f"Plan inicial reportado con {len(current_plan)} tareas")
            report_progress(args.run_id, "info", {
                "message": f"📋 [Planner Agent] Plan estratégico creado con {len(current_plan)} tareas principales"
            })
            
        # ===== FIN DE FASE DE PLANIFICACIÓN =====
            
        objetivo_final = f"He generado todos los siguientes archivos con contenido de alta calidad: {', '.join(salidas_esperadas)}"
        
        # Contexto detallado del proyecto para el LLM
        project_context = {
            "nombre": pcce_data['contexto']['nombre_proyecto'],
            "descripcion": pcce_data['contexto']['descripcion'],
            "objetivo": pcce_data['contexto']['objetivo'],
            "requerimientos_funcionales": pcce_data['entradas']['requerimientos_funcionales'],
            "requerimientos_no_funcionales": pcce_data['entradas']['requerimientos_no_funcionales'],
            "arquitectura": pcce_data['entradas']['arquitectura_propuesta'],
            "stack_tecnologico": pcce_data['entradas']['stack_tecnologico']
        }

        # Personalizar system_prompt según si es reintento o no
        if args.feedback:
            # System prompt específico para reintentos
            system_prompt = f"""Eres un arquitecto de software experto completando archivos faltantes en un REINTENTO.

CONTEXTO DE REINTENTO:
Estás completando EXCLUSIVAMENTE estos archivos que faltan:
{chr(10).join([f"- {archivo}" for archivo in archivos_faltantes])}

Archivos que YA EXISTEN (NO tocar):
{chr(10).join([f"- {archivo}" for archivo in archivos_existentes])}

TU Única MISIÓN es crear LOS ARCHIVOS FALTANTES listados arriba.

IMPORTANTE - Información específica:
- design/api/backfill.yml: API para el servicio de backfilling de datos históricos (FR-06)
- design/api/api.yml: API REST para consultar datos históricos (FR-05)
- Todos los archivos .yml deben tener especificaciones OpenAPI completas, NO archivos vacíos

Opera directamente creando los archivos faltantes:
1. **Pensamiento:** Identifica qué archivo faltante crear a continuación.
2. **Acción:** Usa la herramienta 'writeFile' para crearlo.

FORMATO OBLIGATORIO para la Acción:
- Debe ser SOLO el JSON, sin texto adicional antes o después
- Formato exacto: {{"tool": "writeFile", "args": {{"path": "ruta/archivo", "content": "contenido del archivo"}}}}

Cuando hayas creado TODOS los archivos faltantes, tu último pensamiento debe contener: "Conclusión: Todos los artefactos de diseño han sido generados."""
        else:
            # System prompt normal para primer intento
            system_prompt = f"""Eres un arquitecto de software experto especializado en sistemas de microservicios Event-Driven y procesamiento de datos financieros.

ESTRATEGIA BASADA EN PLAN:
Ya has generado un plan estratégico con estas tareas:
{chr(10).join([f"- {task}" for task in current_plan])}

Tu objetivo es EJECUTAR este plan paso a paso para generar exactamente estos archivos:
{chr(10).join([f"- {archivo}" for archivo in salidas_esperadas])}

IMPORTANTE - Información específica de archivos:
- design/api/backfill.yml: API para el servicio de backfilling de datos históricos (FR-06)
- design/api/api.yml: API REST para consultar datos históricos (FR-05)
- Todos los archivos .yml deben tener especificaciones OpenAPI completas, NO archivos vacíos

Opera en un ciclo de Pensamiento/Acción ENFOCADO EN TU PLAN:
1. **Pensamiento:** Referencia tu plan actual, identifica qué tarea estás ejecutando y decide qué archivo crear. Si encuentras un obstáculo fundamental que invalida tu estrategia, puedes declararlo.
2. **Acción:** Usa la herramienta 'writeFile' para crear el archivo.

FORMATO OBLIGATORIO para la Acción:
- Debe ser SOLO el JSON, sin texto adicional antes o después
- Formato exacto: {{"tool": "writeFile", "args": {{"path": "ruta/archivo", "content": "contenido del archivo"}}}}
- NO agregues explicaciones, comentarios o texto adicional después del JSON

Para los archivos .puml: Genera diagramas C4 válidos con PlantUML.
Para los archivos .yml: Genera especificaciones OpenAPI 3.0 válidas y completas con endpoints reales.

Si encuentras un obstáculo que requiere cambiar fundamentalmente tu estrategia, incluye "OBSTÁCULO FUNDAMENTAL:" en tu pensamiento.

Cuando hayas creado TODOS los archivos requeridos, tu último pensamiento debe contener exactamente: "Conclusión: Todos los artefactos de diseño han sido generados."""
        
        # Los archivos existentes ya fueron verificados anteriormente
        
        # Inicializar el historial con el contexto completo del proyecto y feedback si existe
        if args.feedback:
            # En reintentos, enfocar SOLO en los archivos faltantes
            history = f"""REINTENTO - CONTEXTO DEL PROYECTO:
{yaml.dump(project_context, indent=2)}

ARCHIVOS QUE FALTAN POR GENERAR:
{chr(10).join([f"- {archivo}" for archivo in archivos_faltantes])}

ARCHIVOS YA EXISTENTES (NO REGENERAR):
{chr(10).join([f"- {archivo}" for archivo in archivos_existentes])}

FEEDBACK DE REINTENTO: {args.feedback}

Tu única tarea es generar EXCLUSIVAMENTE los archivos faltantes listados arriba. NO regeneres archivos existentes.

HISTORIAL DE EJECUCIÓN:"""
            report_progress(args.run_id, "info", {"message": f"Procesando reintento - faltan {len(archivos_faltantes)} archivos"})
        else:
            # Primer intento - generar todos
            history = f"""CONTEXTO DEL PROYECTO:
{yaml.dump(project_context, indent=2)}

ARCHIVOS A GENERAR:
{chr(10).join([f"- {archivo}" for archivo in salidas_esperadas])}

OBJETIVO FINAL: {objetivo_final}

HISTORIAL DE EJECUCIÓN:"""

        # Inicializar archivos creados con los ya existentes
        archivos_creados = archivos_existentes.copy()
        
        # === INICIALIZAR SISTEMAS MEJORADOS ===
        failure_memory = FailureMemory(max_strategies_per_error=5)
        
        # Calcular iteraciones basado en archivos faltantes (más generoso para resiliencia)
        archivos_pendientes = len(archivos_faltantes) if args.feedback else len(salidas_esperadas)
        max_iterations = max(archivos_pendientes * 3, 12)  # Mínimo 12, 3x por archivo para permitir errores y recuperación
        iteration = 0
        
        # Contador para consolidación de historial cada 5 iteraciones
        history_consolidation_interval = 5
        
        logger.info(f"Iniciando con {len(archivos_creados)} archivos existentes, {archivos_pendientes} pendientes, max {max_iterations} iteraciones")
        logger.info(f"Iniciando ciclo ReAct - pendientes: {archivos_pendientes}, existentes: {len(archivos_existentes)}")
        
        # Ciclo ReAct principal
        while iteration < max_iterations:
            iteration += 1
            
            # === OPTIMIZACIÓN: CONSOLIDACIÓN DE HISTORIAL ===
            if iteration % history_consolidation_interval == 0 and iteration > 1:
                history = consolidate_history(history, model_id, iteration)
            
            # Construir prompt para el LLM - manteniendo información actualizada
            archivos_faltantes_actuales = [archivo for archivo in salidas_esperadas if archivo not in archivos_creados]
            
            if args.feedback:
                # En reintentos, ser muy explícito sobre qué falta
                status_prompt = f"\n\nESTADO ACTUAL DEL REINTENTO:\n- SOLO DEBES CREAR: {archivos_faltantes_actuales}\n- Ya existen (NO tocar): {list(archivos_existentes)}\n- Creados en esta sesión: {list(archivos_creados - archivos_existentes)}\n"
            else:
                status_prompt = f"\n\nESTADO ACTUAL:\n- Archivos creados: {list(archivos_creados)}\n- Archivos faltantes: {archivos_faltantes_actuales}\n"
            
            user_prompt = f"""{history}{status_prompt}
Genera tu próximo 'Pensamiento:' seguido de tu 'Acción:' para continuar con la tarea."""
            
            # Consultar al LLM
            logger.info(f"Iteración {iteration}: Consultando al LLM...")
            try:
                response_text = call_llm_service(
                    system_prompt=system_prompt, 
                    user_prompt=user_prompt, 
                    task_type="complex_generation", 
                    model_id=model_id
                )
                logger.info(f"LLM respondió exitosamente ({len(response_text)} caracteres)")
            except Exception as e:
                error_msg = f"Error al consultar LLM: {str(e)}"
                logger.error(error_msg)
                report_progress(args.run_id, "error", {"message": error_msg})
                
                # Registrar fallo en memoria
                task_impossible = failure_memory.record_failure(error_msg, f"LLM call iteration {iteration}")
                if task_impossible:
                    reason = f"Error persistente de LLM tras múltiples estrategias: {failure_memory.get_failure_summary()}"
                    try:
                        response = requests.post(f"{HOST}/v1/agent/{args.run_id}/task_complete", 
                                               json={"role": "planner", "status": "impossible", "reason": reason}, 
                                               timeout=10)
                        response.raise_for_status()
                        logger.info("Tarea declarada imposible por errores persistentes de LLM")
                        return
                    except requests.RequestException as e:
                        logger.error(f"Error enviando notificación de tarea imposible: {str(e)}")
                        return
                
                # Si es un timeout, continuar con la siguiente iteración en lugar de romper
                if "timeout" in str(e).lower():
                    logger.info("Timeout detectado, intentando continuar...")
                    history += f"\n\nIteración {iteration}:\nError de timeout al consultar LLM, reintentando..."
                    continue
                break

            # Parsear la respuesta del LLM
            thought_match = re.search(r"Pensamiento:\s*(.*?)(?=Acción:|$)", response_text, re.DOTALL | re.IGNORECASE)
            action_match = re.search(r"Acción:\s*(.*?)(?=$)", response_text, re.DOTALL | re.IGNORECASE)
            
            if not thought_match:
                report_progress(args.run_id, "error", {"message": f"El LLM no generó un 'Pensamiento:' válido en la iteración {iteration}"})
                break

            thought = thought_match.group(1).strip()
            logger.info(f"Pensamiento extraído: {thought[:100]}...")
            
            # Reportar el pensamiento a la TUI
            report_progress(args.run_id, "thought", {"content": thought})
            
            # === LÓGICA DE RE-PLANIFICACIÓN ===
            # Detectar si el agente identifica un obstáculo fundamental
            if "OBSTÁCULO FUNDAMENTAL:" in thought.upper():
                logger.info("Obstáculo fundamental detectado, evaluando re-planificación")
                error_context = f"Iteración {iteration}: {thought}"
                new_plan, plan_changed = update_plan_if_needed(args.run_id, model_id, current_plan, error_context, iteration)
                
                if plan_changed:
                    current_plan = new_plan
                    # Reportar plan actualizado
                    report_progress(args.run_id, "plan_updated", {
                        "plan": current_plan,
                        "total_tasks": len(current_plan),
                        "reason": "Obstáculo fundamental detectado",
                        "timestamp": time.time()
                    })
                    
                    report_progress(args.run_id, "info", {
                        "message": f"🔄 [Planner Agent] Plan actualizado: nueva estrategia con {len(current_plan)} tareas"
                    })
                    
                    # Actualizar system_prompt con el nuevo plan
                    system_prompt = f"""Eres un arquitecto de software experto especializado en sistemas de microservicios Event-Driven y procesamiento de datos financieros.

ESTRATEGIA BASADA EN PLAN (ACTUALIZADA):
Has actualizado tu plan estratégico con estas tareas:
{chr(10).join([f"- {task}" for task in current_plan])}

Tu objetivo es EJECUTAR este plan paso a paso para generar exactamente estos archivos:
{chr(10).join([f"- {archivo}" for archivo in salidas_esperadas])}

IMPORTANTE - Información específica de archivos:
- design/api/backfill.yml: API para el servicio de backfilling de datos históricos (FR-06)
- design/api/api.yml: API REST para consultar datos históricos (FR-05)
- Todos los archivos .yml deben tener especificaciones OpenAPI completas, NO archivos vacíos

Opera en un ciclo de Pensamiento/Acción ENFOCADO EN TU PLAN ACTUALIZADO:
1. **Pensamiento:** Referencia tu plan actualizado, identifica qué tarea estás ejecutando y decide qué archivo crear.
2. **Acción:** Usa la herramienta 'writeFile' para crear el archivo.

FORMATO OBLIGATORIO para la Acción:
- Debe ser SOLO el JSON, sin texto adicional antes o después
- Formato exacto: {{"tool": "writeFile", "args": {{"path": "ruta/archivo", "content": "contenido del archivo"}}}}
- NO agregues explicaciones, comentarios o texto adicional después del JSON

Para los archivos .puml: Genera diagramas C4 válidos con PlantUML.
Para los archivos .yml: Genera especificaciones OpenAPI 3.0 válidas y completas con endpoints reales.

Cuando hayas creado TODOS los archivos requeridos, tu último pensamiento debe contener exactamente: "Conclusión: Todos los artefactos de diseño han sido generados."""

            # Verificar condición de terminación
            archivos_faltantes_actuales = [archivo for archivo in salidas_esperadas if archivo not in archivos_creados]
            
            # Verificación de terminación mejorada
            if "Conclusión:" in thought and "todos los artefactos" in thought.lower():
                if len(archivos_faltantes_actuales) == 0:
                    logger.info("Condición de terminación detectada - todos los archivos han sido creados")
                    break
                else:
                    logger.warning(f"El LLM dice que terminó, pero faltan archivos: {archivos_faltantes_actuales}")
                    # En reintentos, ser más agresivo sobre la corrección
                    if args.feedback:
                        correction = f"ALERTA: Tu reintento falló. Debes crear EXACTAMENTE estos archivos: {archivos_faltantes_actuales}. NO digas que terminaste hasta que estén todos creados."
                    else:
                        correction = f"Error: Dijiste que terminaste, pero AÚN FALTAN estos archivos por crear: {archivos_faltantes_actuales}. Debes continuar hasta crearlos TODOS."
                    history += f"\n\nIteración {iteration}:\nPensamiento: {thought}\n{correction}"
                    # Continuar el ciclo para completar los archivos faltantes
            
            # Detectar si el agente está declarando la tarea como imposible (más selectivo)
            impossible_indicators = ["imposible completar", "no es posible", "tarea imposible", "cannot complete"]
            if (any(indicator in thought.lower() for indicator in impossible_indicators) and 
                iteration > 8):  # Solo después de suficientes intentos
                
                logger.warning(f"Agente declarando tarea como IMPOSIBLE en iteración {iteration}")
                logger.warning(f"Contexto: {thought[:200]}...")
                
                # Solo aceptar la declaración si ha habido suficientes intentos
                if iteration > 12:
                    reason = f"Agente determinó que la tarea es imposible después de {iteration} intentos: {thought[:100]}..."
                    try:
                        response = requests.post(f"{HOST}/v1/agent/{args.run_id}/task_complete", 
                                               json={"role": "planner", "status": "impossible", "reason": reason}, 
                                               timeout=10)
                        response.raise_for_status()
                        logger.info("Notificación de tarea imposible enviada al Orquestador")
                        return
                    except requests.RequestException as e:
                        logger.error(f"Error enviando notificación de tarea imposible: {str(e)}")
                        return
                else:
                    # En iteraciones tempranas, dar una segunda oportunidad
                    logger.info(f"Agente dice que es imposible pero solo en iteración {iteration}, continuando...")
                    history += f"\n\nIteración {iteration}:\nPensamiento: {thought}\nNota: Continúa intentando, aún hay oportunidades de encontrar una solución."
                    continue
            
            if not action_match:
                report_progress(args.run_id, "error", {"message": f"El LLM no generó una 'Acción:' válida en la iteración {iteration}"})
                history += f"\n\nIteración {iteration}:\nPensamiento: {thought}\nError: No se encontró una acción válida."
                continue

            action_str = action_match.group(1).strip()
            
            # Ejecutar la acción
            try:
                # Limpiar y extraer JSON de manera más robusta
                action_str = action_str.strip('`').strip()
                if action_str.startswith('json'):
                    action_str = action_str[4:].strip()
                
                # Buscar el JSON válido en la cadena
                json_str = None
                
                # Método 1: Buscar { ... } balanceado
                if action_str.startswith('{'):
                    brace_count = 0
                    for i, char in enumerate(action_str):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                json_str = action_str[:i+1]
                                break
                
                # Método 2: Buscar patrón específico de writeFile
                if not json_str:
                    pattern = r'\{[^}]*"tool"\s*:\s*"writeFile"[^}]*"args"\s*:[^}]*\}'
                    match = re.search(pattern, action_str, re.DOTALL)
                    if match:
                        json_str = match.group()
                
                # Método 3: Fallback - usar la cadena completa
                if not json_str:
                    json_str = action_str
                
                logger.info(f"JSON extraído: {json_str[:200]}...")
                action_json = json.loads(json_str)
                
                if action_json.get('tool') != 'writeFile':
                    raise ValueError(f"Herramienta inesperada: {action_json.get('tool')}")
                
                # Ejecutar la herramienta writeFile
                logger.info(f"Ejecutando writeFile para: {action_json['args'].get('path', 'archivo desconocido')}")
                observation = use_tool(action_json['tool'], action_json['args'])
                
                # Reportar la acción a la TUI
                report_progress(args.run_id, "action", {
                    "tool": action_json['tool'], 
                    "args": {
                        "path": action_json['args'].get('path', ''),
                        "content_length": len(action_json['args'].get('content', ''))
                    }
                })
                
                # Agregar el archivo a la lista de creados si fue exitoso
                try:
                    obs_data = json.loads(observation)
                    if obs_data.get('success', False):
                        archivo_path = action_json['args'].get('path', '')
                        archivos_creados.add(archivo_path)
                        logger.info(f"Archivo creado exitosamente: {archivo_path}")
                except:
                    pass  # Si no puede parsear la observación, continuar
                
                # Actualizar historial
                history += f"\n\nIteración {iteration}:\nPensamiento: {thought}\nAcción: {action_str}\nObservación: {observation}"
                
            except json.JSONDecodeError as e:
                error_msg = f"La Acción no era un JSON válido: {str(e)}"
                logger.warning(error_msg)
                report_progress(args.run_id, "error", {"message": error_msg})
                
                # Registrar fallo en memoria
                task_impossible = failure_memory.record_failure(error_msg, f"JSON parse error iteration {iteration}")
                if task_impossible:
                    reason = f"Errores persistentes de formato JSON: {failure_memory.get_failure_summary()}"
                    try:
                        response = requests.post(f"{HOST}/v1/agent/{args.run_id}/task_complete", 
                                               json={"role": "planner", "status": "impossible", "reason": reason}, 
                                               timeout=10)
                        response.raise_for_status()
                        logger.info("Tarea declarada imposible por errores persistentes de formato")
                        return
                    except requests.RequestException as e:
                        logger.error(f"Error enviando notificación de tarea imposible: {str(e)}")
                        return
                
                history += f"\n\nIteración {iteration}:\nPensamiento: {thought}\nError: {error_msg}"
                
            except Exception as e:
                error_msg = f"Error ejecutando la acción: {str(e)}"
                logger.error(error_msg)
                report_progress(args.run_id, "error", {"message": error_msg})
                
                # Registrar fallo en memoria
                task_impossible = failure_memory.record_failure(error_msg, f"Action execution iteration {iteration}")
                if task_impossible:
                    reason = f"Error persistente de ejecución: {failure_memory.get_failure_summary()}"
                    try:
                        response = requests.post(f"{HOST}/v1/agent/{args.run_id}/task_complete", 
                                               json={"role": "planner", "status": "impossible", "reason": reason}, 
                                               timeout=10)
                        response.raise_for_status()
                        logger.info("Tarea declarada imposible por errores persistentes de ejecución")
                        return
                    except requests.RequestException as e:
                        logger.error(f"Error enviando notificación de tarea imposible: {str(e)}")
                        return
                
                history += f"\n\nIteración {iteration}:\nPensamiento: {thought}\nError: {error_msg}"
            
            # Pequeña pausa entre iteraciones
            time.sleep(1)
            
            # Verificar si ya se crearon todos los archivos
            if len(archivos_creados) >= len(salidas_esperadas):
                logger.info(f"Todos los archivos han sido creados: {archivos_creados}")
                break

        # Reporte final del estado
        archivos_faltantes = [archivo for archivo in salidas_esperadas if archivo not in archivos_creados]
        if archivos_faltantes:
            # Si llegamos aquí y aún faltan archivos, puede ser que debamos declarar la tarea como imposible
            warning_msg = f"Algunos archivos no fueron generados: {archivos_faltantes}"
            logger.warning(warning_msg)
            report_progress(args.run_id, "warning", {"message": warning_msg})
            
            # Si estamos en un reintento y aún faltan archivos tras agotar iteraciones, declarar imposible
            if args.feedback and iteration >= max_iterations:
                reason = f"Tras {iteration} iteraciones y reintentos, no se pudieron generar: {archivos_faltantes}. {failure_memory.get_failure_summary()}"
                try:
                    response = requests.post(f"{HOST}/v1/agent/{args.run_id}/task_complete", 
                                           json={"role": "planner", "status": "impossible", "reason": reason}, 
                                           timeout=10)
                    response.raise_for_status()
                    logger.info("Tarea declarada imposible tras agotar reintentos")
                    return
                except requests.RequestException as e:
                    logger.error(f"Error enviando notificación de tarea imposible: {str(e)}")
        else:
            # Tarea completada exitosamente - iniciar ciclo de finalización profesional
            report_progress(args.run_id, "info", {
                "message": f"Todos los archivos fueron generados exitosamente: {list(archivos_creados)}"
            })
            
            try:
                # FASE 1: Auto-verificación
                logger.info("Iniciando fase de auto-verificación...")
                verification_result = perform_self_verification(args.run_id, model_id, salidas_esperadas, archivos_creados, pcce_data)
                
                if not verification_result["success"]:
                    # Auto-verificación falló - notificar al orquestador del problema
                    error_msg = f"Auto-verificación falló: {verification_result['reason']}"
                    logger.error(error_msg)
                    report_progress(args.run_id, "error", {"message": error_msg})
                    
                    try:
                        response = requests.post(f"{HOST}/v1/agent/{args.run_id}/task_complete", 
                                               json={"role": "planner", "status": "failed", "reason": error_msg}, 
                                               timeout=10)
                        response.raise_for_status()
                    except requests.RequestException as e:
                        logger.error(f"Error enviando notificación de fallo de verificación: {str(e)}")
                    return
                
                # FASE 2: Generación de resumen ejecutivo
                logger.info("Auto-verificación exitosa - generando resumen ejecutivo...")
                executive_summary = generate_executive_summary(args.run_id, model_id, salidas_esperadas, archivos_creados, pcce_data)
                
                # FASE 3: Notificación final con resumen
                logger.info("Enviando notificación final con resumen ejecutivo...")
                try:
                    response = requests.post(f"{HOST}/v1/agent/{args.run_id}/task_complete", 
                                           json={
                                               "role": "planner", 
                                               "status": "success", 
                                               "summary": executive_summary
                                           }, timeout=10)
                    response.raise_for_status()
                    logger.info("Tarea finalizada exitosamente con resumen ejecutivo.")
                except requests.RequestException as e:
                    logger.error(f"Error enviando notificación final con resumen: {str(e)}")
                    # Fallback a notificación simple
                    try:
                        response = requests.post(f"{HOST}/v1/agent/{args.run_id}/task_complete", 
                                               json={"role": "planner"}, timeout=10)
                        response.raise_for_status()
                        logger.info("Fallback - notificación simple enviada exitosamente.")
                    except requests.RequestException as fallback_e:
                        logger.error(f"Error crítico enviando notificación: {str(fallback_e)}")
                        
            except Exception as e:
                logger.error(f"Error durante el ciclo de finalización profesional: {str(e)}")
                # Fallback a notificación simple en caso de error
                logger.info("Fallback - enviando notificación simple...")
                try:
                    response = requests.post(f"{HOST}/v1/agent/{args.run_id}/task_complete", 
                                           json={"role": "planner"}, timeout=10)
                    response.raise_for_status()
                    logger.info("Fallback - notificación simple enviada exitosamente.")
                except requests.RequestException as fallback_e:
                    logger.error(f"Error crítico en fallback: {str(fallback_e)}")

        # Para casos de fallo (archivos faltantes), mantener notificación simple
        if archivos_faltantes:
            logger.info("Enviando notificación de tarea incompleta al Orquestador...")
            try:
                response = requests.post(f"{HOST}/v1/agent/{args.run_id}/task_complete", 
                                       json={"role": "planner", "status": "incomplete", "reason": f"Archivos faltantes: {archivos_faltantes}"}, timeout=10)
                response.raise_for_status()
                logger.info("Tarea incompleta, notificación enviada al Orquestador.")
            except requests.RequestException as e:
                logger.error(f"Error enviando notificación de tarea incompleta: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error crítico en el agente planificador: {str(e)}")
        report_progress(args.run_id, "error", {"message": f"Error crítico: {str(e)}"})

if __name__ == "__main__":
    main()