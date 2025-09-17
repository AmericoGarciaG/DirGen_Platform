"""
DirGen Core - Módulo central de servicios compartidos para la plataforma DirGen.

Este módulo contiene los servicios fundamentales que son utilizados por múltiples
componentes de la plataforma, incluyendo la gestión de modelos de lenguaje (LLM),
proveedores de IA, y otras capacidades centrales.

Arquitectura:
- llm_services: Gestión completa de proveedores de LLM y modelos locales
- Futuras expansiones: cache, logging, configuración, etc.
"""

__version__ = "1.0.0"
__author__ = "DirGen Platform"

# Importaciones principales del módulo
from .llm_services.main_llm_service import ask_llm

__all__ = ["ask_llm"]