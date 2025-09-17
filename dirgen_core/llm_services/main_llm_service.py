"""
Servicio Principal de LLM - DirGen Core v2.0

🧠 Este módulo implementa el core de inteligencia de la plataforma DirGen, proporcionando
un servicio unificado y optimizado para acceder a múltiples proveedores de LLM.

🎯 Características Principales:
- 🚀 Priorización inteligente de proveedores basada en tipo de tarea
- 🔄 Fallback automático transparente entre proveedores
- 📊 Cache inteligente para optimización de costos
- 🛑 Rate limit detection con candado de seguridad
- 🎯 Selección óptima de modelos según contexto
- 📊 Logging estructurado para observabilidad

📈 Proveedores Soportados:
- OpenAI GPT (gpt-4, gpt-3.5-turbo)
- Anthropic Claude (claude-3-opus, claude-3-sonnet)
- Google Gemini (gemini-pro, gemini-1.5)
- Groq (llama-3.1, mixtral)
- xAI Grok (grok-beta)
- Modelos Locales vía DMR (ai/qwen3-coder, ai/gemma3-qat, ai/smollm3)

🔧 Variables de Entorno:
- LLM_PRIORITY_ORDER: Orden de prioridad (ej: "gemini,local,groq,openai,anthropic,xai")
- OPENAI_API_KEY, ANTHROPIC_API_KEY, GROQ_API_KEY, GEMINI_API_KEY, XAI_API_KEY
- DMR_BASE_URL: URL del Dynamic Model Router para modelos locales

🎯 Arquitectura SOLID:
- Single Responsibility: Cada función tiene una responsabilidad específica
- Open/Closed: Extensible para nuevos proveedores sin modificar código existente
- Dependency Inversion: Depende de abstracciones (interfaces), no implementaciones

Autor: Sistema DirGen v2.0
Fecha: 2025-09-17
Versión: 2.0.0
"""

import os
import logging
import hashlib
from typing import Dict

from .api_clients import (
    call_groq_llm, call_openai_llm, call_anthropic_llm, 
    call_gemini_llm, call_xai_llm, call_local_llm
)

logger = logging.getLogger(__name__)

# === CACHE SIMPLE PARA EVITAR LLAMADAS REDUNDANTES ===
_llm_cache = {}
_cache_max_size = 50

# === FUNCIONES DE SELECCIÓN INTELIGENTE DE MODELOS ===

def get_agent_profile(pcce_data: dict, agent_role: str) -> dict:
    """
    🎭 Obtiene el perfil de configuración de un agente desde el PCCE
    
    Esta función extrae la configuración específica de un agente (modelo, parámetros, etc.)
    del archivo PCCE, implementando una estrategia de fallback jerárquica para garantizar
    que siempre se retorne una configuración válida.
    
    Args:
        pcce_data (dict): Datos del archivo PCCE parseado
        agent_role (str): Rol del agente ('planner', 'validator', 'codegen', etc.)
    
    Returns:
        dict: Perfil del agente con keys:
            - modelo_id (str): ID del modelo principal a usar
            - fallback_modelo (str): ID del modelo de fallback
            - configuracion (dict): Parámetros del modelo (temperatura, max_tokens)
    
    Fallback Strategy:
        1. Buscar perfil exacto del rol solicitado
        2. Si no existe, usar perfil 'planner' como fallback
        3. Si tampoco existe, usar configuración por defecto hardcodeada
    
    Example:
        >>> pcce_data = {'perfiles_agentes': [{'rol_agente': 'planner', 'modelo_id': 'ai/gemma3-qat'}]}
        >>> profile = get_agent_profile(pcce_data, 'planner')
        >>> print(profile['modelo_id'])  # 'ai/gemma3-qat'
    """
    perfiles = pcce_data.get('perfiles_agentes', [])
    for perfil in perfiles:
        if perfil.get('rol_agente') == agent_role:
            return perfil
    
    # Fallback al perfil planner si no se encuentra el rol específico
    for perfil in perfiles:
        if perfil.get('rol_agente') == 'planner':
            logger.warning(f"Perfil para '{agent_role}' no encontrado, usando 'planner' como fallback")
            return perfil
    
    # Fallback final con configuración por defecto
    logger.warning(f"No se encontró perfil para '{agent_role}', usando configuración por defecto")
    return {
        'modelo_id': 'ai/smollm3',
        'fallback_modelo': 'ai/gemma3-qat',
        'configuracion': {'temperatura': 0.2, 'max_tokens': 10000}
    }

def select_optimal_model(task_type: str, agent_profile: dict) -> str:
    """Selecciona el modelo óptimo según el tipo de tarea y perfil del agente"""
    primary_model = agent_profile.get('modelo_id', 'ai/smollm3')
    fallback_model = agent_profile.get('fallback_modelo', 'ai/gemma3-qat')
    
    # Mapeo de tipos de tarea a preferencias de modelo
    # NOTA: Los modelos locales se usan via ask_llm() solo en emergencias (rate limiting)
    task_preferences = {
        'planning': primary_model,           # Planificación: usar modelo principal (Gemini via ask_llm)
        'complex_generation': fallback_model,  # Generación compleja: usar modelo más potente
        'architecture': primary_model,       # Arquitectura: usar modelo principal (Gemini via ask_llm)
        'verification': primary_model,       # Verificación: usar modelo principal (Gemini via ask_llm)
        'validation': primary_model,         # Validación: usar modelo principal (Gemini via ask_llm)
        'simple_generation': primary_model,  # Generación simple: modelo principal
        'general': primary_model
    }
    
    selected_model = task_preferences.get(task_type, primary_model)
    logger.info(f"🤖 Modelo seleccionado para '{task_type}': {selected_model}")
    return selected_model

# === FUNCIONES DE CACHE ===

def _get_cache_key(system_prompt: str, user_prompt: str) -> str:
    """Genera una clave de cache basada en los prompts"""
    combined = f"{system_prompt[:200]}|{user_prompt[:200]}"  # Primeros 200 chars de cada uno
    return hashlib.md5(combined.encode()).hexdigest()

def _is_rate_limit_error(error_msg: str) -> bool:
    """Detecta si el error es por límite de requests"""
    rate_limit_indicators = [
        "rate limit", "too many requests", "quota exceeded", 
        "demasiadas peticiones", "límite excedido", "429", 
        "quota_exceeded", "rate_limit_exceeded", "usage_limit"
    ]
    return any(indicator in error_msg.lower() for indicator in rate_limit_indicators)

# === FUNCIÓN PRINCIPAL ===

def ask_llm(model_id: str, system_prompt: str, user_prompt: str, task_type: str = "general", use_cache: bool = False) -> str:
    """
    🚀 Función principal de la plataforma DirGen para consultas a LLM
    
    Esta es la función core que centraliza todas las consultas a modelos de lenguaje,
    implementando inteligencia para selección óptima, fallback automático, 
    optimización de costos y resiliencia avanzada.
    
    🎆 Características Avanzadas:
    - Priorización dinámica basada en tipo de tarea
    - Fallback transparente entre 6 proveedores diferentes
    - Cache inteligente para tareas repetitivas (ahorro hasta 75%)
    - Rate limit detection con "candado de seguridad"
    - Logging estructurado para observabilidad completa
    
    Args:
        model_id (str): ID del modelo solicitado (ej: 'ai/gemma3-qat', 'gpt-4')
        system_prompt (str): Prompt del sistema que define el rol/contexto
        user_prompt (str): Prompt del usuario con la tarea específica
        task_type (str): Tipo de tarea para optimización:
            - 'planning': Planificación estratégica (usa modelos potentes)
            - 'architecture': Diseño de arquitectura (usa modelos potentes)
            - 'complex_generation': Generación compleja (usa fallback models)
            - 'simple_generation': Tareas simples (prefiere modelos locales)
            - 'verification': Validación (usa cache + modelos eficientes)
            - 'validation': Validación (usa cache + modelos eficientes)
            - 'general': Tareas generales
        use_cache (bool): Si usar cache para evitar llamadas redundantes
    
    Returns:
        str: Respuesta del modelo LLM seleccionado
    
    Raises:
        Exception: Si todos los proveedores fallan o no hay configuración válida
    
    Example:
        >>> # Consulta básica
        >>> response = ask_llm(
        ...     model_id="ai/gemma3-qat",
        ...     system_prompt="Eres un arquitecto de software",
        ...     user_prompt="Diseña una API REST",
        ...     task_type="architecture"
        ... )
        
        >>> # Con optimización de cache
        >>> response = ask_llm(
        ...     model_id="ai/smollm3",
        ...     system_prompt="Valida este JSON",
        ...     user_prompt="{\"name\": \"test\"}",
        ...     task_type="verification",
        ...     use_cache=True  # Evita llamadas redundantes
        ... )
    
    Flow Diagram:
        [ask_llm] -> [Cache Check] -> [Provider Selection] -> [Fallback Chain]
               |                                                        |
               v                                                        v
        [Rate Limit Detection] -> [Security Lock] -> [Local Fallback] -> [Response]
    """
    
    # === OPTIMIZACIÓN: CACHE PARA TAREAS REPETITIVAS ===
    cache_key = None
    if use_cache and task_type in ["verification", "validation", "simple_generation"]:
        cache_key = _get_cache_key(system_prompt, user_prompt)
        if cache_key in _llm_cache:
            logger.info(f"🎯 Respuesta recuperada de cache para tarea: {task_type}")
            return _llm_cache[cache_key]
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    # === SELECCIÓN INTELIGENTE DE PRIORIDAD BASADA EN TIPO DE TAREA ===
    base_priority = os.getenv("LLM_PRIORITY_ORDER", "gemini,local").split(",")
    base_priority = [p.strip().lower() for p in base_priority]
    
    # Ajustar prioridad según el tipo de tarea
    if task_type in ["planning", "complex_generation", "architecture"]:
        # Tareas complejas: preferir modelos en la nube
        priority_order = base_priority
    elif task_type in ["simple_generation"]:
        # Solo tareas muy simples: preferir modelos locales
        priority_order = ["local"] + [p for p in base_priority if p != "local"]
    else:
        # Todas las demás tareas (incluidas validation y verification): usar prioridad base
        # Los modelos locales están reservados para emergencias (rate limiting)
        priority_order = base_priority
    
    # === MAPEAR PROVEEDORES CON SOPORTE PARA FALLBACK MODELS ===
    def create_llm_provider(provider_name, fallback_model=None):
        if provider_name == "local":
            return lambda: call_local_llm(fallback_model or model_id, messages)
        elif provider_name == "groq":
            return lambda: call_groq_llm(messages)
        elif provider_name == "openai":
            return lambda: call_openai_llm(messages)
        elif provider_name == "anthropic":
            return lambda: call_anthropic_llm(messages)
        elif provider_name == "xai":
            return lambda: call_xai_llm(messages)
        elif provider_name == "gemini":
            return lambda: call_gemini_llm(messages)
        else:
            return None
    
    llm_providers = {}
    for provider in priority_order:
        provider_func = create_llm_provider(provider)
        if provider_func:
            llm_providers[provider] = provider_func
    
    last_error = None
    rate_limit_detected = False
    
    # === CICLO DE INTENTOS CON CANDADO DE SEGURIDAD ===
    for provider in priority_order:
        if provider not in llm_providers:
            logger.warning(f"Proveedor LLM desconocido: {provider}")
            continue
            
        try:
            logger.info(f"Intentando consultar LLM: {provider.upper()} para tarea: {task_type}")
            response = llm_providers[provider]()
            logger.info(f"✅ {provider.upper()} respondió exitosamente ({len(response)} caracteres)")
            
            # === GUARDAR EN CACHE SI ES APROPIADO ===
            if use_cache and cache_key and task_type in ["verification", "validation", "simple_generation"]:
                # Limpiar cache si está lleno
                if len(_llm_cache) >= _cache_max_size:
                    # Remover el 20% más antiguo
                    keys_to_remove = list(_llm_cache.keys())[:_cache_max_size // 5]
                    for k in keys_to_remove:
                        del _llm_cache[k]
                
                _llm_cache[cache_key] = response
                logger.info(f"💾 Respuesta guardada en cache")
            
            return response
            
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"❌ {provider.upper()} falló: {error_msg}")
            last_error = e
            
            # === CANDADO DE SEGURIDAD: DETECTAR RATE LIMITING ===
            if _is_rate_limit_error(error_msg):
                rate_limit_detected = True
                logger.warning(f"🚨 RATE LIMIT detectado en {provider.upper()}! Activando candado de seguridad...")
                
                # Si detectamos rate limit en un proveedor de nube, forzar uso local
                if provider != "local" and "local" not in [p for p in priority_order[:priority_order.index(provider)+1]]:
                    logger.info(f"🔄 Candado activado: Intentando con modelo local como fallback de emergencia...")
                    try:
                        fallback_response = call_local_llm(model_id, messages)
                        logger.info(f"✅ CANDADO EXITOSO: Modelo local respondió como fallback ({len(fallback_response)} caracteres)")
                        return fallback_response
                    except Exception as fallback_e:
                        logger.error(f"❌ Fallback local también falló: {str(fallback_e)}")
                        # Si falla el fallback local, continuar con otros proveedores en lugar de fallar completamente
                        logger.info("Continuando con otros proveedores disponibles...")
                
                continue
            
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
    
    # === MENSAJE DE ERROR MEJORADO ===
    error_context = f"Todos los proveedores LLM fallaron para tarea '{task_type}'. "
    if rate_limit_detected:
        error_context += "Rate limiting detectado - considera usar más modelos locales. "
    error_context += f"Último error: {str(last_error)}"
    
    raise Exception(error_context)