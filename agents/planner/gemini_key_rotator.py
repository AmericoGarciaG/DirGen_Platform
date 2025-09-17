#!/usr/bin/env python3
"""
Sistema de Rotación Automática de API Keys para Gemini
Permite alternar entre múltiples claves API para evitar rate limiting
"""

import os
import logging
import time
import threading
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class ApiKeyStatus:
    """Estado de una API Key"""
    key_id: str
    key_value: str
    is_active: bool = True
    last_used: Optional[datetime] = None
    consecutive_failures: int = 0
    rate_limit_until: Optional[datetime] = None
    total_requests: int = 0
    successful_requests: int = 0
    
    @property
    def success_rate(self) -> float:
        """Calcula la tasa de éxito de esta clave"""
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests
    
    @property
    def is_available(self) -> bool:
        """Verifica si la clave está disponible para uso"""
        if not self.is_active:
            return False
        if self.rate_limit_until and datetime.now() < self.rate_limit_until:
            return False
        return True
    
    def record_success(self):
        """Registra un uso exitoso"""
        self.last_used = datetime.now()
        self.total_requests += 1
        self.successful_requests += 1
        self.consecutive_failures = 0
    
    def record_failure(self, is_rate_limit: bool = False):
        """Registra una falla"""
        self.last_used = datetime.now()
        self.total_requests += 1
        self.consecutive_failures += 1
        
        if is_rate_limit:
            # Cooldown de 5 minutos para rate limit
            self.rate_limit_until = datetime.now() + timedelta(minutes=5)
            logger.warning(f"🚨 Clave {self.key_id} en cooldown hasta {self.rate_limit_until}")

class GeminiKeyRotator:
    """Sistema de rotación automática de claves API de Gemini"""
    
    def __init__(self):
        self._keys: Dict[str, ApiKeyStatus] = {}
        self._current_key_index = 0
        self._lock = threading.Lock()
        self._load_keys()
        self._stats_start_time = datetime.now()
    
    def _load_keys(self):
        """Carga las claves API desde variables de entorno"""
        # Cargar archivo de configuración de claves si existe
        env_file = os.path.join(os.path.dirname(__file__), "..", "..", ".env.api_keys")
        if os.path.exists(env_file):
            try:
                from dotenv import load_dotenv
                load_dotenv(env_file)
                logger.info(f"✅ Configuración de claves cargada desde {env_file}")
            except ImportError:
                logger.warning("dotenv no disponible, leyendo variables de entorno directamente")
        
        # Buscar claves numeradas (GEMINI_API_KEY_1, GEMINI_API_KEY_2, etc.)
        for i in range(1, 10):  # Buscar hasta 9 claves
            key_var = f"GEMINI_API_KEY_{i}"
            key_value = os.getenv(key_var)
            
            if key_value and key_value not in ["", "..."]:
                # No registrar claves que son placeholders
                if not key_value.startswith("..."):
                    key_status = ApiKeyStatus(
                        key_id=f"gemini_key_{i}",
                        key_value=key_value
                    )
                    self._keys[f"key_{i}"] = key_status
                    logger.info(f"✅ Clave Gemini #{i} registrada: {key_value[:20]}...")
        
        # Fallback: usar clave única si no hay múltiples
        if not self._keys:
            single_key = os.getenv("GEMINI_API_KEY")
            if single_key:
                key_status = ApiKeyStatus(
                    key_id="gemini_key_single",
                    key_value=single_key
                )
                self._keys["key_single"] = key_status
                logger.info("✅ Usando clave única de Gemini como fallback")
        
        if not self._keys:
            logger.error("❌ No se encontraron claves API de Gemini configuradas")
            raise ValueError("No hay claves API de Gemini disponibles")
        
        logger.info(f"🔑 Sistema de rotación inicializado con {len(self._keys)} claves")
    
    def get_current_key(self) -> str:
        """Obtiene la clave API actual para usar"""
        with self._lock:
            # Si solo hay una clave, devolverla
            if len(self._keys) == 1:
                return list(self._keys.values())[0].key_value
            
            # Buscar la mejor clave disponible
            available_keys = [
                (key_id, status) for key_id, status in self._keys.items() 
                if status.is_available
            ]
            
            if not available_keys:
                # No hay claves disponibles, usar la que tenga menor cooldown
                logger.warning("⚠️ Todas las claves en cooldown, usando la de menor tiempo restante")
                best_key = min(
                    self._keys.values(),
                    key=lambda k: k.rate_limit_until or datetime.min
                )
                return best_key.key_value
            
            # Seleccionar clave por rotación round-robin
            if self._current_key_index >= len(available_keys):
                self._current_key_index = 0
            
            selected_key_id, selected_status = available_keys[self._current_key_index]
            self._current_key_index = (self._current_key_index + 1) % len(available_keys)
            
            logger.info(f"🔄 Usando clave: {selected_status.key_id}")
            return selected_status.key_value
    
    def record_request_result(self, api_key: str, success: bool, error_msg: str = ""):
        """Registra el resultado de una petición"""
        with self._lock:
            # Encontrar la clave correspondiente
            key_status = None
            for status in self._keys.values():
                if status.key_value == api_key:
                    key_status = status
                    break
            
            if not key_status:
                logger.warning(f"⚠️ No se pudo encontrar estado para la clave API")
                return
            
            if success:
                key_status.record_success()
                logger.info(f"✅ Petición exitosa con {key_status.key_id}")
            else:
                # Detectar si es rate limit
                is_rate_limit = any(indicator in error_msg.lower() for indicator in [
                    "rate limit", "too many requests", "quota exceeded", "429"
                ])
                
                key_status.record_failure(is_rate_limit=is_rate_limit)
                
                if is_rate_limit:
                    logger.warning(f"🚨 Rate limit detectado en {key_status.key_id}")
                else:
                    logger.warning(f"❌ Error en {key_status.key_id}: {error_msg[:100]}...")
    
    def get_rotation_stats(self) -> Dict:
        """Obtiene estadísticas del sistema de rotación"""
        with self._lock:
            total_requests = sum(status.total_requests for status in self._keys.values())
            successful_requests = sum(status.successful_requests for status in self._keys.values())
            
            key_stats = {}
            for key_id, status in self._keys.items():
                key_stats[key_id] = {
                    "total_requests": status.total_requests,
                    "successful_requests": status.successful_requests,
                    "success_rate": status.success_rate,
                    "consecutive_failures": status.consecutive_failures,
                    "is_available": status.is_available,
                    "last_used": status.last_used.isoformat() if status.last_used else None,
                    "rate_limit_until": status.rate_limit_until.isoformat() if status.rate_limit_until else None
                }
            
            return {
                "total_keys": len(self._keys),
                "available_keys": sum(1 for status in self._keys.values() if status.is_available),
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "overall_success_rate": successful_requests / total_requests if total_requests > 0 else 1.0,
                "uptime_minutes": (datetime.now() - self._stats_start_time).total_seconds() / 60,
                "key_details": key_stats
            }
    
    def reset_key_status(self, key_id: str = None):
        """Resetea el estado de una clave específica o todas"""
        with self._lock:
            if key_id:
                if key_id in self._keys:
                    status = self._keys[key_id]
                    status.rate_limit_until = None
                    status.consecutive_failures = 0
                    status.is_active = True
                    logger.info(f"🔄 Estado de {key_id} reseteado")
            else:
                for status in self._keys.values():
                    status.rate_limit_until = None
                    status.consecutive_failures = 0
                    status.is_active = True
                logger.info("🔄 Estado de todas las claves reseteado")

# Instancia global del rotador
_key_rotator = None

def get_gemini_key_rotator() -> GeminiKeyRotator:
    """Obtiene la instancia global del rotador de claves"""
    global _key_rotator
    if _key_rotator is None:
        _key_rotator = GeminiKeyRotator()
    return _key_rotator

def get_rotated_gemini_key() -> str:
    """Función de conveniencia para obtener una clave rotada"""
    rotator = get_gemini_key_rotator()
    return rotator.get_current_key()

def record_gemini_result(api_key: str, success: bool, error_msg: str = ""):
    """Función de conveniencia para registrar resultado de petición"""
    rotator = get_gemini_key_rotator()
    rotator.record_request_result(api_key, success, error_msg)