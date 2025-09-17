"""
Clientes API para proveedores de LLM

Este módulo contiene las implementaciones específicas para cada proveedor de LLM,
incluyendo la lógica de llamada a API, manejo de errores y transformación de formatos.
"""

import os
import logging
import requests
from typing import List, Dict

logger = logging.getLogger(__name__)

def call_groq_llm(messages: list, temperature: float = 0.1, max_tokens: int = 4096) -> str:
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

def call_openai_llm(messages: list, temperature: float = 0.1, max_tokens: int = 4096) -> str:
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

def call_anthropic_llm(messages: list, temperature: float = 0.1, max_tokens: int = 4096) -> str:
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

def call_gemini_llm(messages: list, temperature: float = 0.1, max_tokens: int = 4096) -> str:
    """Llama al LLM de Google Gemini usando sistema de rotación de claves"""
    from .gemini_key_rotator import get_rotated_gemini_key, record_gemini_result
    
    try:
        api_key = get_rotated_gemini_key()
        logger.info(f"🔄 Usando rotación de claves Gemini: {api_key[:20]}...")
    except Exception as e:
        # Fallback al sistema original
        api_key = os.getenv("GEMINI_API_KEY")
        logger.warning("⚠️ Sistema de rotación no disponible, usando clave única")
        if not api_key:
            raise ValueError("GEMINI_API_KEY no está configurada")
    
    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    
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
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        if "candidates" in result and len(result["candidates"]) > 0:
            response_text = result["candidates"][0]["content"]["parts"][0]["text"]
            
            # Registrar éxito en el sistema de rotación
            try:
                record_gemini_result(api_key, success=True)
            except Exception:
                pass  # Sistema de rotación no disponible
            
            return response_text
        else:
            error_msg = "No se recibió respuesta válida de Gemini"
            # Registrar fallo en el sistema de rotación
            try:
                record_gemini_result(api_key, success=False, error_msg=error_msg)
            except Exception:
                pass
            raise ValueError(error_msg)
    
    except Exception as e:
        error_msg = str(e)
        # Registrar fallo en el sistema de rotación
        try:
            record_gemini_result(api_key, success=False, error_msg=error_msg)
        except Exception:
            pass
        raise

def call_xai_llm(messages: list, temperature: float = 0.1, max_tokens: int = 4096) -> str:
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

def call_local_llm(model_id: str, messages: list, temperature: float = 0.1, max_tokens: int = 4096) -> str:
    """Llama al LLM local usando DMR, asegurando que el modelo esté ejecutándose"""
    from .local_model_manager import ensure_model_available
    
    # Asegurar que el modelo esté ejecutándose antes de hacer la llamada
    if not ensure_model_available(model_id):
        raise Exception(f"No se pudo iniciar el modelo local: {model_id}")
    
    endpoint = os.getenv("DMR_ENDPOINT")
    if not endpoint:
        raise ValueError("DMR_ENDPOINT no está configurado")
    
    payload = {
        "model": model_id, 
        "messages": messages, 
        "temperature": temperature, 
        "max_tokens": max_tokens
    }
    
    response = requests.post(endpoint, json=payload, timeout=900)  # 15 minutos para modelos lentos
    response.raise_for_status()
    return response.json()['choices'][0]['message']['content']