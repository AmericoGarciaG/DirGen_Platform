"""
DirGen Core - LLM Services

Módulo centralizado para gestión de modelos de lenguaje (LLM) y proveedores de IA.
Proporciona una interfaz unificada para interactuar con múltiples proveedores
de LLM incluyendo:

- Proveedores en la nube: OpenAI, Anthropic, Groq, Gemini, xAI
- Modelos locales: A través de DMR (Dynamic Model Router)
- Características avanzadas: cache, rotación de claves, selección inteligente

Componentes:
- main_llm_service: Función principal ask_llm() con lógica de priorización
- api_clients: Implementaciones específicas para cada proveedor
- local_model_manager: Gestión de modelos locales via DMR
- gemini_key_rotator: Sistema de rotación de claves para Google Gemini
"""

from .main_llm_service import ask_llm, get_agent_profile, select_optimal_model
from .api_clients import (
    call_groq_llm,
    call_openai_llm,
    call_anthropic_llm,
    call_gemini_llm,
    call_xai_llm,
    call_local_llm
)
from .local_model_manager import ensure_model_available
from .gemini_key_rotator import get_rotated_gemini_key, record_gemini_result

__all__ = [
    "ask_llm",
    "get_agent_profile",
    "select_optimal_model",
    "call_groq_llm",
    "call_openai_llm", 
    "call_anthropic_llm",
    "call_gemini_llm",
    "call_xai_llm",
    "call_local_llm",
    "ensure_model_available",
    "get_rotated_gemini_key",
    "record_gemini_result"
]
