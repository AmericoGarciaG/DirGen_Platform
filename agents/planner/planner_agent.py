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

def _call_groq_llm(messages: list, temperature: float = 0.1, max_tokens: int = 4096) -> str:
    """Llama al LLM de Groq usando la API compatible con OpenAI"""
    import openai
    api_key = os.getenv("GROQ_API_KEY")
    base_url = os.getenv("GROQ_BASE_URL")
    model = os.getenv("GROQ_MODEL")
    
    if not api_key:
        raise ValueError("GROQ_API_KEY no está configurada")
    
    client = openai.OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens
    )
    return response.choices[0].message.content

def _call_openai_llm(messages: list, temperature: float = 0.1, max_tokens: int = 4096) -> str:
    """Llama al LLM de OpenAI"""
    import openai
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("OPENAI_MODEL")
    
    if not api_key:
        raise ValueError("OPENAI_API_KEY no está configurada")
    
    client = openai.OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens
    )
    return response.choices[0].message.content

def _call_anthropic_llm(messages: list, temperature: float = 0.1, max_tokens: int = 4096) -> str:
    """Llama al LLM de Anthropic"""
    import anthropic
    api_key = os.getenv("ANTHROPIC_API_KEY")
    model = os.getenv("ANTHROPIC_MODEL")
    
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY no está configurada")
    
    client = anthropic.Anthropic(api_key=api_key)
    
    # Convertir formato de mensajes de OpenAI a Anthropic
    system_message = ""
    user_messages = []
    for msg in messages:
        if msg["role"] == "system":
            system_message = msg["content"]
        else:
            user_messages.append(msg)
    
    response = client.messages.create(
        model=model,
        system=system_message,
        messages=user_messages,
        temperature=temperature,
        max_tokens=max_tokens
    )
    return response.content[0].text

def _call_gemini_llm(messages: list, temperature: float = 0.1, max_tokens: int = 4096) -> str:
    """Llama al LLM de Google Gemini usando su API nativa"""
    api_key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    
    if not api_key:
        raise ValueError("GEMINI_API_KEY no está configurada")
    
    # Convertir mensajes de formato OpenAI a formato Gemini
    gemini_contents = []
    for msg in messages:
        if msg["role"] == "system":
            # Gemini no tiene "system" role, lo agregamos como contexto al primer mensaje user
            continue
        elif msg["role"] == "user":
            # Si hay un mensaje de system, lo agregamos como contexto
            system_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
            content = f"{system_msg}\n\n{msg['content']}" if system_msg else msg["content"]
            gemini_contents.append({
                "parts": [{"text": content}]
            })
            break  # Solo usar el primer mensaje user con contexto
    
    # Llamada a Gemini API
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": api_key
    }
    payload = {
        "contents": gemini_contents,
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens
        }
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    
    result = response.json()
    if "candidates" in result and len(result["candidates"]) > 0:
        return result["candidates"][0]["content"]["parts"][0]["text"]
    else:
        raise ValueError("No se recibió respuesta válida de Gemini")

def _call_xai_llm(messages: list, temperature: float = 0.1, max_tokens: int = 4096) -> str:
    """Llama al LLM de xAI (Grok) usando la API compatible con OpenAI"""
    import openai
    api_key = os.getenv("XAI_API_KEY")
    base_url = os.getenv("XAI_BASE_URL")
    model = os.getenv("XAI_MODEL")
    
    if not api_key:
        raise ValueError("XAI_API_KEY no está configurada")
    
    client = openai.OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens
    )
    return response.choices[0].message.content

def _call_local_llm(model_id: str, messages: list, temperature: float = 0.1, max_tokens: int = 4096) -> str:
    """Llama al LLM local usando DMR"""
    endpoint = os.getenv("DMR_ENDPOINT")
    if not endpoint:
        raise ValueError("DMR_ENDPOINT no está configurado")
    
    payload = {
        "model": model_id, 
        "messages": messages, 
        "temperature": temperature, 
        "max_tokens": max_tokens
    }
    
    response = requests.post(endpoint, json=payload, timeout=600)
    response.raise_for_status()
    return response.json()['choices'][0]['message']['content']

def ask_llm(model_id: str, system_prompt: str, user_prompt: str) -> str:
    """Función principal que intenta múltiples proveedores LLM según prioridad configurada"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    # Obtener orden de prioridad desde .env
    priority_order = os.getenv("LLM_PRIORITY_ORDER", "groq,openai,local").split(",")
    priority_order = [p.strip().lower() for p in priority_order]
    
    # Mapear proveedores a sus funciones
    llm_providers = {
        "groq": lambda: _call_groq_llm(messages),
        "openai": lambda: _call_openai_llm(messages),
        "anthropic": lambda: _call_anthropic_llm(messages),
        "xai": lambda: _call_xai_llm(messages),
        "gemini": lambda: _call_gemini_llm(messages),
        "local": lambda: _call_local_llm(model_id, messages)
    }
    
    last_error = None
    
    # Intentar cada proveedor según el orden de prioridad
    for provider in priority_order:
        if provider not in llm_providers:
            logger.warning(f"Proveedor LLM desconocido: {provider}")
            continue
            
        try:
            logger.info(f"Intentando consultar LLM: {provider.upper()}")
            response = llm_providers[provider]()
            logger.info(f"✅ {provider.upper()} respondió exitosamente ({len(response)} caracteres)")
            return response
            
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"❌ {provider.upper()} falló: {error_msg}")
            last_error = e
            
            # No intentar otros proveedores si es un problema de API key
            if "api" in error_msg.lower() and "key" in error_msg.lower():
                logger.info(f"Problema de API key en {provider}, probando siguiente proveedor...")
                continue
            
            # Para timeouts o errores de conectividad, intentar siguiente proveedor
            if any(word in error_msg.lower() for word in ["timeout", "connection", "network"]):
                logger.info(f"Error de conectividad en {provider}, probando siguiente proveedor...")
                continue
                
            # Para otros errores, también continuar
            logger.info(f"Error en {provider}, probando siguiente proveedor...")
            continue
    
    # Si todos los proveedores fallaron
    raise Exception(f"Todos los proveedores LLM fallaron. Último error: {str(last_error)}")

# --- Ciclo de Vida del Agente ---
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

        # Configurar el modelo LLM
        planner_profile = next((p for p in pcce_data.get('perfiles_agentes', []) if p.get('rol_agente') == 'planner'), {})
        model_id = planner_profile.get('modelo_id', 'ai/gemma3-qat')
        
        # Obtener los archivos que debe generar
        salidas_esperadas = pcce_data.get('fases', {}).get('diseno', {}).get('salidas_esperadas', [])
        
        if not salidas_esperadas:
            report_progress(args.run_id, "error", {"message": "No se encontraron salidas esperadas en fases.diseno.salidas_esperadas"})
            return
            
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

        system_prompt = f"""Eres un arquitecto de software experto especializado en sistemas de microservicios Event-Driven y procesamiento de datos financieros. 

Tu tarea es generar los artefactos de diseño para el proyecto FinBase según los requerimientos proporcionados.

DEBES generar exactamente estos archivos:
{chr(10).join([f"- {archivo}" for archivo in salidas_esperadas])}

IMPORTANTE - Información específica de archivos:
- design/api/backfill.yml: API para el servicio de backfilling de datos históricos (FR-06)
- design/api/api.yml: API REST para consultar datos históricos (FR-05)
- Todos los archivos .yml deben tener especificaciones OpenAPI completas, NO archivos vacíos

Opera en un ciclo de Pensamiento/Acción:
1. **Pensamiento:** Analiza el contexto, los requerimientos y decide qué archivo crear a continuación. Explica tu razonamiento.
2. **Acción:** Usa la herramienta 'writeFile' para crear el archivo.

FORMATO OBLIGATORIO para la Acción:
- Debe ser SOLO el JSON, sin texto adicional antes o después
- Formato exacto: {{"tool": "writeFile", "args": {{"path": "ruta/archivo", "content": "contenido del archivo"}}}}
- NO agregues explicaciones, comentarios o texto adicional después del JSON

Para los archivos .puml: Genera diagramas C4 válidos con PlantUML.
Para los archivos .yml: Genera especificaciones OpenAPI 3.0 válidas y completas con endpoints reales.

Cuando hayas creado TODOS los archivos requeridos, tu último pensamiento debe contener exactamente: "Conclusión: Todos los artefactos de diseño han sido generados."""
        
        # Verificar qué archivos ya existen físicamente
        archivos_existentes = set()
        project_root = Path(args.pcce_path).parent.parent  # Volver al directorio raíz del proyecto
        
        for archivo in salidas_esperadas:
            archivo_path = project_root / archivo
            if archivo_path.exists():
                archivos_existentes.add(archivo)
                logger.info(f"Archivo ya existente detectado: {archivo}")
        
        archivos_faltantes = [archivo for archivo in salidas_esperadas if archivo not in archivos_existentes]
        
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
        
        # Calcular iteraciones basado en archivos faltantes
        archivos_pendientes = len(archivos_faltantes) if args.feedback else len(salidas_esperadas)
        max_iterations = max(archivos_pendientes + 2, 8)  # Mínimo 8, máximo necesarios + buffer
        iteration = 0
        
        # Contador de estrategias fallidas para detectar si la tarea es imposible
        repeated_failures = 0
        last_error_pattern = None
        last_thoughts = []  # Para detectar bucles de pensamiento
        
        logger.info(f"Iniciando con {len(archivos_creados)} archivos existentes, {archivos_pendientes} pendientes, max {max_iterations} iteraciones")

        logger.info(f"Iniciando ciclo ReAct - pendientes: {archivos_pendientes}, existentes: {len(archivos_existentes)}")
        
        # Ciclo ReAct principal
        while iteration < max_iterations:
            iteration += 1
            
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
                response_text = ask_llm(model_id, system_prompt, user_prompt)
                logger.info(f"LLM respondió exitosamente ({len(response_text)} caracteres)")
            except Exception as e:
                error_msg = f"Error al consultar LLM: {str(e)}"
                logger.error(error_msg)
                report_progress(args.run_id, "error", {"message": error_msg})
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

            # Verificar condición de terminación
            # Solo terminar si realmente se han creado TODOS los archivos requeridos
            archivos_faltantes_actuales = [archivo for archivo in salidas_esperadas if archivo not in archivos_creados]
            
            # Detectar bucles de pensamiento (mismo pensamiento repetido)
            last_thoughts.append(thought[:100])  # Primeros 100 caracteres
            if len(last_thoughts) > 3:
                last_thoughts.pop(0)
            
            # Si los últimos 3 pensamientos son muy similares, declarar imposible
            if len(last_thoughts) == 3 and len(set(last_thoughts)) <= 1:
                logger.warning("Bucle de pensamiento detectado - mismos pensamientos repetidos")
                reason = f"Bucle infinito detectado: el agente repite el mismo razonamiento sin progresar"
                try:
                    response = requests.post(f"{HOST}/v1/agent/{args.run_id}/task_complete", 
                                           json={"role": "planner", "status": "impossible", "reason": reason}, 
                                           timeout=10)
                    response.raise_for_status()
                    logger.info("Notificación de bucle infinito enviada al Orquestador")
                    return
                except requests.RequestException as e:
                    logger.error(f"Error enviando notificación de bucle infinito: {str(e)}")
                    return
            
            # Detectar si el agente está declarando la tarea como imposible
            if "IMPOSIBLE" in thought.upper() and ("no puedo" in thought.lower() or "imposible" in thought.lower()):
                logger.warning("Agente declarando tarea como IMPOSIBLE")
                reason = f"Agente determinó que la tarea es imposible: {thought}"
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
                history += f"\n\nIteración {iteration}:\nPensamiento: {thought}\nError: {error_msg}"
            except Exception as e:
                error_msg = f"Error ejecutando la acción: {str(e)}"
                logger.error(error_msg)
                report_progress(args.run_id, "error", {"message": error_msg})
                history += f"\n\nIteración {iteration}:\nPensamiento: {thought}\nError: {error_msg}"
                
                # Detectar patrones de errores repetidos
                current_error_pattern = str(e)[:50]  # Primeros 50 caracteres del error
                if current_error_pattern == last_error_pattern:
                    repeated_failures += 1
                else:
                    repeated_failures = 1
                    last_error_pattern = current_error_pattern
                
                # Si el mismo error se repite muchas veces, considerar declarar la tarea imposible
                if repeated_failures >= 3:
                    logger.warning(f"Error repetido {repeated_failures} veces: {current_error_pattern}")
                    reason = f"Error repetido múltiples veces: {error_msg}. No se puede resolver automáticamente."
                    try:
                        response = requests.post(f"{HOST}/v1/agent/{args.run_id}/task_complete", 
                                               json={"role": "planner", "status": "impossible", "reason": reason}, 
                                               timeout=10)
                        response.raise_for_status()
                        logger.info("Notificación de tarea imposible enviada por errores repetidos")
                        return
                    except requests.RequestException as req_e:
                        logger.error(f"Error enviando notificación de tarea imposible: {str(req_e)}")
                        return
            
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
                reason = f"Tras {iteration} iteraciones y reintentos, no se pudieron generar: {archivos_faltantes}"
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
            report_progress(args.run_id, "info", {
                "message": f"Todos los archivos fueron generados exitosamente: {list(archivos_creados)}"
            })

        # Notificación de finalización al orquestador
        logger.info("Enviando notificación de tarea completada al Orquestador...")
        try:
            response = requests.post(f"{HOST}/v1/agent/{args.run_id}/task_complete", 
                                   json={"role": "planner"}, timeout=10)
            response.raise_for_status()
            logger.info("Tarea finalizada, notificación enviada al Orquestador exitosamente.")
        except requests.RequestException as e:
            logger.error(f"Error enviando notificación de finalización: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error crítico en el agente planificador: {str(e)}")
        report_progress(args.run_id, "error", {"message": f"Error crítico: {str(e)}"})

if __name__ == "__main__":
    main()