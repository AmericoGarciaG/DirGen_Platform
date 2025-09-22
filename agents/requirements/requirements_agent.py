import argparse
import json
import logging
import os
import sys
import tempfile
import re
import unicodedata
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv

# --- Configuración y Herramientas ---
# Intentar usar logging centralizado, fallback a configuración básica
try:
    import sys
    from pathlib import Path
    project_root = Path(__file__).parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    from dirgen_core.logging_config import get_agent_logger, LogicBookLogger, LogLevel
    logger = get_agent_logger("requirements", LogLevel.DEBUG)
    logic_logger = LogicBookLogger()
except ImportError:
    # Fallback a configuración básica
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - AGENT(Requirements) - %(message)s')
    logger = logging.getLogger("REQUIREMENTS_AGENT")
    logic_logger = None
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
    """Reporta progreso al Orquestador"""
    try:
        requests.post(f"{HOST}/v1/agent/{run_id}/report", 
                     json={"source": "Requirements Agent", "type": type, "data": data}, timeout=5)
    except requests.RequestException:
        logger.warning(f"No se pudo reportar el progreso al Orquestador para el run_id {run_id}")

def use_tool(tool_name: str, args: dict) -> str:
    """Usa herramientas del orquestador - Conformidad Logic Book Capítulo 2.2"""
    toolbelt_endpoints = {
        "writeFile": f"{HOST}/v1/tools/filesystem/writeFile",
        "readFile": f"{HOST}/v1/tools/filesystem/readFile", 
        "listFiles": f"{HOST}/v1/tools/filesystem/listFiles"
    }
    
    if tool_name in toolbelt_endpoints:
        try:
            response = requests.post(toolbelt_endpoints[tool_name], json=args, timeout=10)
            response.raise_for_status()
            return json.dumps(response.json())
        except requests.RequestException as e:
            logger.error(f"Error llamando herramienta {tool_name}: {str(e)}")
            return json.dumps({"success": False, "error": f"Error de conexión con {tool_name}: {str(e)}"})
    
    return json.dumps({"success": False, "error": f"Herramienta '{tool_name}' no disponible. Herramientas disponibles: {list(toolbelt_endpoints.keys())}"})

def call_llm_service(system_prompt: str, user_prompt: str, task_type: str = "general", model_id: str = None) -> str:
    """Interfaz simplificada para llamar al servicio central de LLM"""
    if not LLM_SERVICE_AVAILABLE:
        raise Exception("Servicio central de LLM no disponible. Verifique la instalación de dirgen_core.")
    
    try:
        return ask_llm(
            model_id=model_id or "ai/gemma3-qat", 
            system_prompt=system_prompt, 
            user_prompt=user_prompt, 
            task_type=task_type, 
            use_cache=False
        )
    except Exception as e:
        logger.error(f"Error en servicio central de LLM: {str(e)}")
        raise

def task_complete(run_id: str, status: str = "success", summary: str = None, reason: str = None):
    """Notifica completación de tarea al Orquestador"""
    payload = {"role": "requirements", "status": status}
    if summary:
        payload["summary"] = summary
    if reason:
        payload["reason"] = reason
    
    try:
        response = requests.post(f"{HOST}/v1/agent/{run_id}/task_complete", json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"✅ Task completion notificada: {status}")
    except requests.RequestException as e:
        logger.error(f"❌ Error notificando task completion: {e}")

# Utilidades de saneamiento de YAML
FENCE_PATTERN = re.compile(r"^```[a-zA-Z]*\s*\n|\n```\s*$", re.MULTILINE)
CODE_BLOCK_EXTRACT_PATTERN = re.compile(r"```(?:yaml|yml)?\s*\n(.*?)\n```", re.DOTALL | re.IGNORECASE)

def clean_yaml_output(text: str) -> str:
    """Limpia la salida del LLM para garantizar YAML válido.
    - Extrae contenido entre ```yaml ... ``` si existe
    - Elimina cercas de código y backticks sueltos
    - Normaliza comillas "inteligentes" a ASCII
    - Elimina caracteres de ancho cero y BOM
    - Convierte tabs a 2 espacios y normaliza saltos de línea
    """
    if not text:
        return ""

    # Intentar extraer el bloque YAML si viene cercado
    m = CODE_BLOCK_EXTRACT_PATTERN.search(text)
    if m:
        text = m.group(1)
    else:
        # Si empieza con ```yaml o ``` eliminar cercas
        text = FENCE_PATTERN.sub("", text)

    # Quitar BOM y caracteres invisibles problemáticos
    text = text.lstrip("\ufeff")
    text = text.replace("\u200b", "").replace("\u200c", "").replace("\u200d", "")

    # Normalizar comillas tipográficas a ASCII
    translations = {
        ord('“'): '"', ord('”'): '"', ord('„'): '"', ord('‟'): '"',
        ord('’'): "'", ord('‘'): "'", ord('‚'): "'",
        ord('«'): '"', ord('»'): '"'
    }
    text = text.translate(translations)

    # Sustituir backticks accidentales al inicio de línea
    text = re.sub(r"^`+\s*", "", text, flags=re.MULTILINE)

    # Tabs -> espacios y normalización de fin de línea
    text = text.replace("\t", "  ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Trim final
    return text.strip()

# === PLANTILLA DE VALIDACIÓN SVAD ===
SVAD_TEMPLATE = {
    "required_sections": [
        "## 1. Resumen Ejecutivo",
        "### 1.1 Visión del Producto", 
        "### 1.2 Objetivos de Negocio",
        "### 1.3 Alcance del Proyecto",
        "## 2. Actores y Casos de Uso",
        "## 3. Requerimientos Funcionales (FRs)",
        "## 4. Requerimientos No Funcionales (NFRs)",
        "## 6. Visión de la Arquitectura de la Solución",
        "## 7. Stack Tecnológico Propuesto"
    ],
    "optional_sections": [
        "## 5. Políticas de Gobernanza y Cumplimiento",
        "## 8. Glosario de Términos"
    ]
}

def validate_svad_structure(svad_content: str, run_id: str = None) -> dict:
    """Valida la estructura del documento SVAD"""
    validation_result = {
        "valid": True,
        "missing_sections": [],
        "warnings": [],
        "quality_score": 0
    }
    
    # Log inicio de validación según Logic Book
    if logic_logger and run_id:
        logic_logger.log_agent_action(
            logger, run_id, "Requirements", "SVAD_VALIDATION_START", 
            {'sections_to_check': len(SVAD_TEMPLATE["required_sections"])}
        )
    
    # Verificar secciones requeridas
    for section in SVAD_TEMPLATE["required_sections"]:
        if section not in svad_content:
            validation_result["missing_sections"].append(section)
            validation_result["valid"] = False
    
    # Verificar secciones opcionales (advertencias)
    for section in SVAD_TEMPLATE["optional_sections"]:
        if section not in svad_content:
            validation_result["warnings"].append(f"Sección opcional faltante: {section}")
    
    # Calcular puntaje de calidad
    total_sections = len(SVAD_TEMPLATE["required_sections"]) + len(SVAD_TEMPLATE["optional_sections"])
    found_sections = total_sections - len(validation_result["missing_sections"]) - len(validation_result["warnings"])
    validation_result["quality_score"] = int((found_sections / total_sections) * 100)
    
    # Log resultado de validación según Logic Book
    if logic_logger and run_id:
        result_status = "PASSED" if validation_result["valid"] else "FAILED"
        logic_logger.log_quality_gate(
            logger, run_id, "SVAD_STRUCTURE_VALIDATION", result_status,
            f"Calidad: {validation_result['quality_score']}%, Secciones faltantes: {len(validation_result['missing_sections'])}"
        )
    
    return validation_result

def extract_project_info(svad_content: str) -> dict:
    """Extrae información del proyecto del SVAD"""
    try:
        # Buscar nombre del proyecto
        project_name = "Sistema Generado"
        if "## FinBase Data Pipeline" in svad_content:
            project_name = "FinBase Data Pipeline"
        elif "###" in svad_content:
            # Buscar en headers de nivel 3
            lines = svad_content.split('\n')
            for line in lines:
                if line.startswith("## ") and " v" not in line.lower() and "resumen" not in line.lower():
                    project_name = line.replace("## ", "").strip()
                    break
        
        # Buscar descripción (primer párrafo después de visión del producto)
        description = "Sistema desarrollado a partir de documento SVAD"
        if "### 1.1 Visión del Producto" in svad_content:
            vision_section = svad_content.split("### 1.1 Visión del Producto")[1]
            first_paragraph = vision_section.split("\n\n")[1] if "\n\n" in vision_section else vision_section.split("\n")[1]
            if first_paragraph and len(first_paragraph) > 50:
                description = first_paragraph.strip()
        
        return {
            "nombre_proyecto": project_name,
            "descripcion": description,
            "objetivo": "Implementar sistema según especificaciones SVAD"
        }
    except Exception as e:
        logger.warning(f"Error extrayendo información del proyecto: {e}")
        return {
            "nombre_proyecto": "Sistema Generado",
            "descripcion": "Sistema desarrollado a partir de documento SVAD",
            "objetivo": "Implementar sistema según especificaciones SVAD"
        }

def main():
    """Función principal del RequirementsAgent"""
    parser = argparse.ArgumentParser(description="RequirementsAgent - Análisis de SVAD y generación de PCCE")
    parser.add_argument("--run-id", required=True, help="ID de la ejecución")
    parser.add_argument("--svad-path", required=True, help="Ruta al archivo SVAD")
    
    args = parser.parse_args()
    run_id = args.run_id
    svad_path = args.svad_path
    
    logger.info(f"🚀 RequirementsAgent iniciado para {run_id}")
    logger.info(f"📋 Archivo SVAD: {svad_path}")
    
    # Log inicio del agente según Logic Book
    if logic_logger:
        logic_logger.log_agent_action(
            logger, run_id, "Requirements", "AGENT_START", 
            {'svad_path': svad_path, 'chapter': 'CAP-2'}
        )
    
    try:
        # PASO 1: Leer y analizar el documento SVAD
        report_progress(run_id, "thought", {
            "content": "Iniciando análisis del documento SVAD. Primero voy a leer el archivo y examinar su estructura para validar que cumple con los estándares de calidad."
        })
        
        report_progress(run_id, "action", {
            "tool": "readFile",
            "args": {"path": svad_path}
        })
        
        with open(svad_path, 'r', encoding='utf-8') as f:
            svad_content = f.read()
        
        logger.info(f"✅ Archivo SVAD leído: {len(svad_content)} caracteres")
        
        # PASO 2: Validar la estructura del SVAD
        report_progress(run_id, "thought", {
            "content": "Validando la estructura del documento SVAD contra la plantilla estándar. Verificaré que contenga todas las secciones obligatorias: Resumen Ejecutivo, Actores y Casos de Uso, Requerimientos Funcionales, NFRs, Arquitectura y Stack Tecnológico."
        })
        
        validation_result = validate_svad_structure(svad_content, run_id)
        
        if not validation_result["valid"]:
            # SVAD inválido - reportar error y terminar
            missing_sections = ", ".join(validation_result["missing_sections"])
            error_message = f"El documento SVAD no cumple con los estándares requeridos. Secciones faltantes: {missing_sections}"
            
            report_progress(run_id, "error", {"message": error_message})
            logger.error(error_message)
            
            # Log falla de validación según Logic Book
            if logic_logger:
                logic_logger.log_phase_transition(
                    logger, run_id, "REQUIREMENTS", "FAILED", "CAP-2"
                )
            
            task_complete(run_id, status="failed", reason=error_message)
            return
        
        # SVAD válido - continuar con generación
        report_progress(run_id, "info", {
            "message": f"✅ SVAD validado exitosamente. Puntaje de calidad: {validation_result['quality_score']}%"
        })
        
        # Log validación exitosa según Logic Book
        if logic_logger:
            logic_logger.log_phase_transition(
                logger, run_id, "VALIDATION", "PCCE_GENERATION", "CAP-2"
            )
        
        if validation_result["warnings"]:
            warnings_msg = "; ".join(validation_result["warnings"])
            report_progress(run_id, "info", {"message": f"⚠️ Advertencias: {warnings_msg}"})
        
        # PASO 3: Extraer información estructurada y generar PCCE
        report_progress(run_id, "thought", {
            "content": "El SVAD es válido. Ahora procederé a extraer la información estructurada y transformarla en el formato PCCE YAML que la plataforma DirGen puede procesar."
        })
        
        # Extraer información del proyecto
        project_info = extract_project_info(svad_content)
        
        # Generar PCCE usando LLM
        pcce_generation_prompt = f"""Eres un experto en análisis de requerimientos y arquitectura de software.

Tu tarea es transformar este documento SVAD (Software Vision and Requirements Document) en un archivo PCCE (Project Context, Components, and Expectations) en formato YAML.

REQUISITOS DE SALIDA IMPORTANTES:
- Devuelve UNICAMENTE el YAML plano, sin explicaciones ni comentarios previos o posteriores.
- NO incluyas cercas de código de Markdown. No uses ```yaml ni ```.
- Usa exclusivamente caracteres ASCII seguros en claves y valores. No utilices comillas tipográficas.
- Asegúrate de que el YAML sea válido para yaml.safe_load.

DOCUMENTO SVAD A TRANSFORMAR:
{svad_content}

ESTRUCTURA YAML OBJETIVO:
Debes generar un archivo YAML con la siguiente estructura:

# PCCE: [nombre del proyecto]
rol: "Plataforma DirGen: Orquestador de agentes para generar [descripción del sistema]."

contexto:
  nombre_proyecto: "[extraer del SVAD]"
  descripcion: "[extraer visión del producto]"
  objetivo: "[extraer objetivo principal]"
  entorno_despliegue_local: "Docker Compose"

entradas:
  requerimientos_funcionales:
    - "[convertir cada FR del SVAD]"
  
  requerimientos_no_funcionales:
    - "[convertir cada NFR del SVAD]"
  
  arquitectura_propuesta:
    patron: "[extraer patrón arquitectónico]"
    componentes:
      - "[lista de componentes/servicios]"
    comunicacion_asincrona: "[tecnología de messaging si aplica]"
    persistencia: "[base de datos propuesta]"
  
  stack_tecnologico:
    lenguaje: "[lenguaje principal]"
    frameworks: ["[lista de frameworks]"]
    infraestructura_local: ["Docker", "Docker Compose"]

salidas_esperadas:
  - "Diagrama C4 de la arquitectura en formato PlantUML."
  - "Contratos OpenAPI v3 para APIs."
  - "Código fuente para los componentes."
  - "Dockerfile para cada componente."
  - "Archivo docker-compose.yml para orquestación local."
  - "Reportes de pruebas unitarias y cobertura."

fases:
  diseno:
    descripcion: "Generar los artefactos de diseño de alto nivel."
    salidas_esperadas:
      - "design/architecture.puml"
      - "design/api/[componente].yml"

perfiles_agentes:
  - rol_agente: "planner"
    descripcion: "Agente para planificación estratégica y diseño de arquitectura."
    modelo_id: "ai/gemma3-qat"
    fallback_modelo: "ai/smollm3"
    configuracion:
      temperatura: 0.2
      max_tokens: 10000

politicas_de_gobernanza:
  - "qual-test-coverage-80"
  - "std-python-black-isort"
  - "sec-no-hardcoded-secrets"
  - "sec-no-known-critical-cves"

trazabilidad:
  requerido: true
  campos: ["run_id", "agent_id", "prompt_version", "artifact_hash", "timestamp"]

INSTRUCCIONES ESPECÍFICAS:
1. Extrae la información del SVAD y mápela correctamente a la estructura YAML
2. Convierte los requerimientos funcionales y no funcionales al formato de lista YAML
3. Identifica el patrón arquitectónico y los componentes del sistema
4. Extrae las tecnologías del stack tecnológico propuesto
5. Mantén el formato YAML válido y la estructura completa
6. Si alguna información no está disponible en el SVAD, usa valores por defecto razonables

Genera ÚNICAMENTE el contenido YAML, sin explicaciones adicionales:"""
        
        report_progress(run_id, "action", {
            "tool": "llm_query", 
            "args": {"prompt_type": "pcce_generation", "content_length": len(pcce_generation_prompt)}
        })
        
        pcce_yaml_content = call_llm_service(
            system_prompt="Eres un experto en transformación de requerimientos de negocio a especificaciones técnicas. Generas archivos PCCE YAML perfectamente estructurados.",
            user_prompt=pcce_generation_prompt,
            task_type="architecture",
            model_id="ai/gemma3-qat"
        )
        
        logger.info(f"✅ PCCE generado: {len(pcce_yaml_content)} caracteres")
        
        # Log generación de PCCE según Logic Book
        if logic_logger:
            logic_logger.log_agent_action(
                logger, run_id, "Requirements", "PCCE_GENERATED",
                {'pcce_size': len(pcce_yaml_content), 'model': 'ai/gemma3-qat'}
            )

        # Saneamiento del contenido YAML devuelto por el LLM (eliminar ```yaml, etc.)
        cleaned_yaml = clean_yaml_output(pcce_yaml_content)
        if cleaned_yaml != pcce_yaml_content:
            logger.info("🧹 YAML limpiado de cercas de código y caracteres no ASCII problemáticos")
        
        # PASO 4: Validar YAML generado y guardarlo
        try:
            # Validar que el YAML es válido
            yaml.safe_load(cleaned_yaml)
            logger.info("✅ YAML generado es válido")
        except yaml.YAMLError as e:
            logger.error(f"❌ YAML inválido generado: {e}")
            report_progress(run_id, "error", {"message": f"Error en YAML generado: {str(e)}"})
            task_complete(run_id, status="failed", reason=f"YAML inválido: {str(e)}")
            return
        
        # Guardar PCCE en archivo temporal (CORREGIDO: usar ruta relativa del proyecto)
        # Usar ruta relativa en lugar de ruta absoluta temporal para cumplir con sandboxing
        pcce_relative_path = f"temp/{run_id}_pcce.yml"
        
        report_progress(run_id, "action", {
            "tool": "writeFile",
            "args": {"path": pcce_relative_path, "content_length": len(pcce_yaml_content)}
        })
        
        tool_result = use_tool("writeFile", {
            "path": pcce_relative_path,
            "content": cleaned_yaml
        })
        
        result_data = json.loads(tool_result)
        if not result_data.get("success"):
            error_msg = f"Error guardando PCCE: {result_data.get('error', 'Unknown error')}"
            logger.error(error_msg)
            report_progress(run_id, "error", {"message": error_msg})
            task_complete(run_id, status="failed", reason=error_msg)
            return
        
        logger.info(f"✅ PCCE guardado en: {pcce_relative_path}")
        
        # Log generación exitosa de artefacto según Logic Book
        if logic_logger:
            logic_logger.log_artifact_generation(
                logger, run_id, "PCCE", pcce_relative_path, success=True
            )
        
        # PASO 5: Generar resumen ejecutivo
        summary = f"""📋 ANÁLISIS DE REQUERIMIENTOS COMPLETADO

🎯 DOCUMENTO SVAD PROCESADO:
- Archivo: {os.path.basename(svad_path)}
- Tamaño: {len(svad_content):,} caracteres
- Calidad: {validation_result['quality_score']}%

✅ VALIDACIÓN EXITOSA:
- Estructura SVAD: ✓ Completa
- Secciones obligatorias: ✓ Todas presentes
- Formato: ✓ Válido

🏗️ PCCE GENERADO:
- Archivo: {os.path.basename(pcce_relative_path)}
- Proyecto: {project_info['nombre_proyecto']}
- Tamaño: {len(cleaned_yaml):,} caracteres
- Estado: ✓ Listo para Fase 1

🚀 TRANSICIÓN: Fase 0 → Fase 1
El sistema procederá automáticamente con el diseño arquitectónico usando el PCCE generado."""
        
        report_progress(run_id, "info", {
            "message": f"✅ RequirementsAgent completado. PCCE generado exitosamente en {pcce_relative_path}"
        })
        
        # Notificar completación exitosa
        task_complete(run_id, status="success", summary=summary)
        logger.info("🎉 RequirementsAgent completado exitosamente")
        
        # Log completación exitosa según Logic Book
        if logic_logger:
            logic_logger.log_phase_transition(
                logger, run_id, "REQUIREMENTS", "COMPLETED", "CAP-2"
            )
        
    except FileNotFoundError:
        error_msg = f"Archivo SVAD no encontrado: {svad_path}"
        logger.error(error_msg)
        report_progress(run_id, "error", {"message": error_msg})
        task_complete(run_id, status="failed", reason=error_msg)
        
    except Exception as e:
        error_msg = f"Error crítico en RequirementsAgent: {str(e)}"
        logger.error(error_msg)
        
        # Log error crítico según Logic Book
        if logic_logger:
            logic_logger.log_agent_action(
                logger, run_id, "Requirements", "CRITICAL_ERROR",
                {'error': str(e), 'chapter': 'CAP-2'}
            )
        
        report_progress(run_id, "error", {"message": error_msg})
        task_complete(run_id, status="failed", reason=error_msg)

if __name__ == "__main__":
    main()