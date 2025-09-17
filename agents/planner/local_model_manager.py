#!/usr/bin/env python3
"""
Gestor Dinámico de Modelos Locales para DirGen Platform

Este módulo maneja automáticamente el inicio, monitoreo y parada de modelos locales
ejecutándose en Docker, optimizando el uso de recursos del sistema.
"""

import json
import logging
import os
import subprocess
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)

class LocalModelManager:
    """Gestor dinámico para modelos LLM locales ejecutándose en Docker"""
    
    def __init__(self, 
                 idle_timeout: int = 300,  # 5 minutos sin uso
                 startup_timeout: int = 120,  # 2 minutos para iniciar (aumentado)
                 max_concurrent_models: int = 2):  # Máximo 2 modelos simultáneos
        
        self.idle_timeout = idle_timeout
        self.startup_timeout = startup_timeout
        self.max_concurrent_models = max_concurrent_models
        
        # Estado interno
        self._active_models: Dict[str, Dict] = {}  # modelo_id -> metadata
        self._model_locks: Dict[str, threading.Lock] = {}
        self._cleanup_thread: Optional[threading.Thread] = None
        self._cleanup_running = False
        
        # Configuración
        self._docker_command = "docker"  # Puede ser 'podman' u otro
        
        logger.info(f"🤖 LocalModelManager inicializado - Timeout: {idle_timeout}s, Max concurrent: {max_concurrent_models}")
    
    def start_cleanup_thread(self):
        """Inicia el hilo de limpieza automática"""
        if self._cleanup_thread is None or not self._cleanup_thread.is_alive():
            self._cleanup_running = True
            self._cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
            self._cleanup_thread.start()
            logger.info("🧹 Hilo de limpieza automática iniciado")
    
    def stop_cleanup_thread(self):
        """Detiene el hilo de limpieza automática"""
        self._cleanup_running = False
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)
            logger.info("🛑 Hilo de limpieza automática detenido")
    
    def _cleanup_worker(self):
        """Worker que ejecuta limpieza periódica de modelos inactivos"""
        while self._cleanup_running:
            try:
                self._cleanup_idle_models()
                time.sleep(30)  # Revisar cada 30 segundos
            except Exception as e:
                logger.error(f"Error en cleanup worker: {e}")
                time.sleep(10)
    
    def _cleanup_idle_models(self):
        """Detiene modelos que han estado inactivos por mucho tiempo"""
        current_time = datetime.now()
        models_to_stop = []
        
        for model_id, metadata in self._active_models.items():
            last_used = metadata.get('last_used', current_time)
            idle_time = (current_time - last_used).total_seconds()
            
            if idle_time > self.idle_timeout:
                models_to_stop.append(model_id)
        
        for model_id in models_to_stop:
            logger.info(f"🧹 Deteniendo modelo inactivo: {model_id}")
            self._stop_model(model_id, reason="timeout por inactividad")
    
    def is_model_running(self, model_id: str) -> bool:
        """Verifica si un modelo está ejecutándose actualmente"""
        try:
            result = subprocess.run([
                self._docker_command, "model", "ps"
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                output_lines = result.stdout.strip().split('\n')
                # La primera línea es el header, verificamos las siguientes
                for line in output_lines[1:]:  # Saltar header
                    if line.strip():
                        # El formato es: MODEL NAME  BACKEND  MODE  LAST USED
                        columns = line.split()
                        if len(columns) >= 1 and columns[0] == model_id:
                            logger.info(f"✅ Modelo {model_id} detectado como activo")
                            return True
            
            return False
            
        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout verificando estado de {model_id}")
            return False
        except Exception as e:
            logger.error(f"Error verificando modelo {model_id}: {e}")
            return False
    
    def get_running_models(self) -> List[str]:
        """Obtiene lista de todos los modelos actualmente ejecutándose"""
        try:
            result = subprocess.run([
                self._docker_command, "model", "ps"
            ], capture_output=True, text=True, timeout=10)
            
            running_models = []
            if result.returncode == 0:
                output_lines = result.stdout.strip().split('\n')
                # La primera línea es el header, procesamos las siguientes
                for line in output_lines[1:]:  # Saltar header
                    if line.strip():
                        # El formato es: MODEL NAME  BACKEND  MODE  LAST USED
                        columns = line.split()
                        if len(columns) >= 1:
                            running_models.append(columns[0])  # Primer columna es el nombre
            
            return running_models
            
        except Exception as e:
            logger.error(f"Error obteniendo modelos ejecutándose: {e}")
            return []
    
    def _start_model(self, model_id: str) -> bool:
        """Inicia un modelo local usando Docker"""
        try:
            logger.info(f"🚀 Iniciando modelo local: {model_id}")
            
            # Verificar si ya está ejecutándose
            if self.is_model_running(model_id):
                logger.info(f"✅ Modelo {model_id} ya está ejecutándose")
                self._update_model_metadata(model_id, 'already_running')
                return True
            
            # Verificar límite de modelos concurrentes
            running_count = len(self.get_running_models())
            if running_count >= self.max_concurrent_models:
                logger.warning(f"⚠️ Límite de modelos concurrentes alcanzado ({running_count}/{self.max_concurrent_models})")
                # Intentar detener el modelo menos usado
                self._stop_least_used_model()
            
            # Docker Model Run es interactivo, por lo que lo ejecutamos en segundo plano
            # y verificamos que se inicie correctamente
            start_time = time.time()
            
            try:
                # Docker model run necesita un prompt para iniciarse, luego podemos usarlo como servicio
                # Usamos un prompt inicial simple para "despertar" el modelo
                process = subprocess.Popen([
                    self._docker_command, "model", "run", model_id, "Hello"
                ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                   stdin=subprocess.PIPE, text=True)
                
                # Dar tiempo para que el modelo procese el prompt inicial
                time.sleep(10)  # Más tiempo para que el modelo se cargue y responda
                
                # Verificar si el proceso aún se está ejecutando (procesando o listo)
                poll_result = process.poll()
                if poll_result is not None:
                    # El proceso terminó - esto podría ser normal si completó el prompt
                    try:
                        stdout, stderr = process.communicate(timeout=2)
                        if poll_result == 0:
                            # Salida exitosa - el modelo probablemente respondió al prompt
                            logger.info(f"✅ Modelo {model_id} procesó prompt inicial exitosamente")
                            if stdout:
                                logger.info(f"   Respuesta: {stdout.strip()[:100]}...")
                        else:
                            # Error en el proceso
                            error_msg = stderr.strip() if stderr else "Error desconocido"
                            logger.error(f"❌ Error iniciando {model_id}: {error_msg}")
                            logger.error(f"   Código de salida: {poll_result}")
                            return False
                    except Exception as comm_e:
                        logger.error(f"❌ Error comunicando con proceso {model_id}: {comm_e}")
                        return False
                
                # Verificar que el modelo esté realmente ejecutándose
                max_checks = 12  # 60 segundos total (5s * 12)
                for attempt in range(max_checks):
                    if self.is_model_running(model_id):
                        elapsed = time.time() - start_time
                        logger.info(f"✅ Modelo {model_id} iniciado exitosamente en {elapsed:.1f}s")
                        self._update_model_metadata(model_id, 'started')
                        # Guardar el proceso para poder detenerlo después
                        if not hasattr(self, '_model_processes'):
                            self._model_processes = {}
                        self._model_processes[model_id] = process
                        return True
                    
                    time.sleep(5)  # Esperar 5 segundos entre verificaciones
                    logger.info(f"⏳ Esperando que {model_id} esté disponible (intento {attempt + 1}/{max_checks})...")
                
                # Si llegamos aquí, el modelo no se inició en el tiempo esperado
                logger.error(f"❌ Timeout: {model_id} no se inició en {max_checks * 5} segundos")
                process.terminate()  # Terminar el proceso colgado
                return False
                
            except Exception as e:
                logger.error(f"❌ Error crítico iniciando {model_id}: {e}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"❌ Timeout iniciando {model_id} (>{self.startup_timeout}s)")
            return False
        except Exception as e:
            logger.error(f"❌ Error crítico iniciando {model_id}: {e}")
            return False
    
    def _stop_model(self, model_id: str, reason: str = "solicitud manual") -> bool:
        """Detiene un modelo local usando Docker y terminando el proceso"""
        try:
            logger.info(f"🛑 Deteniendo modelo: {model_id} (razón: {reason})")
            
            success = False
            
            # Primero, intentar terminar el proceso directamente si existe
            if hasattr(self, '_model_processes') and model_id in self._model_processes:
                try:
                    process = self._model_processes[model_id]
                    if process.poll() is None:  # Proceso aún ejecutándose
                        process.terminate()
                        process.wait(timeout=5)  # Esperar hasta 5 segundos
                        logger.info(f"✅ Proceso de {model_id} terminado directamente")
                        success = True
                    del self._model_processes[model_id]
                except Exception as proc_e:
                    logger.warning(f"⚠️ No se pudo terminar proceso directamente: {proc_e}")
            
            # Intentar usar docker model unload como alternativa
            try:
                result = subprocess.run([
                    self._docker_command, "model", "unload", model_id
                ], capture_output=True, text=True, timeout=15)
                
                if result.returncode == 0:
                    logger.info(f"✅ Modelo {model_id} descargado exitosamente")
                    success = True
                else:
                    error_msg = result.stderr.strip() or result.stdout.strip()
                    logger.warning(f"⚠️ Problema descargando {model_id}: {error_msg}")
            except Exception as unload_e:
                logger.warning(f"⚠️ Error con docker model unload: {unload_e}")
            
            if success:
                self._remove_model_metadata(model_id)
            
            return success
                
        except Exception as e:
            logger.error(f"❌ Error deteniendo {model_id}: {e}")
            return False
    
    def _stop_least_used_model(self):
        """Detiene el modelo que ha sido usado menos recientemente"""
        if not self._active_models:
            return
        
        # Encontrar modelo menos usado
        least_used_model = min(
            self._active_models.items(), 
            key=lambda x: x[1].get('last_used', datetime.min)
        )[0]
        
        logger.info(f"🔄 Deteniendo modelo menos usado para liberar espacio: {least_used_model}")
        self._stop_model(least_used_model, reason="liberar espacio para nuevo modelo")
    
    def _update_model_metadata(self, model_id: str, action: str):
        """Actualiza metadatos de uso de un modelo"""
        current_time = datetime.now()
        
        if model_id not in self._active_models:
            self._active_models[model_id] = {
                'started_at': current_time,
                'total_requests': 0
            }
        
        self._active_models[model_id].update({
            'last_used': current_time,
            'last_action': action,
            'total_requests': self._active_models[model_id].get('total_requests', 0) + 1
        })
    
    def _remove_model_metadata(self, model_id: str):
        """Elimina metadatos de un modelo detenido"""
        if model_id in self._active_models:
            del self._active_models[model_id]
        if model_id in self._model_locks:
            del self._model_locks[model_id]
        # Limpiar procesos si existen
        if hasattr(self, '_model_processes') and model_id in self._model_processes:
            del self._model_processes[model_id]
    
    def ensure_model_running(self, model_id: str) -> bool:
        """
        Asegura que un modelo esté ejecutándose, iniciándolo si es necesario
        
        Returns:
            bool: True si el modelo está disponible, False si falló
        """
        if not model_id or not model_id.startswith('ai/'):
            logger.warning(f"⚠️ ID de modelo inválido: {model_id}")
            return False
        
        # Obtener lock para este modelo específico
        if model_id not in self._model_locks:
            self._model_locks[model_id] = threading.Lock()
        
        with self._model_locks[model_id]:
            # Verificar si ya está ejecutándose
            if self.is_model_running(model_id):
                self._update_model_metadata(model_id, 'used')
                return True
            
            # Iniciar el modelo si no está ejecutándose
            logger.info(f"🔄 Modelo {model_id} no está activo, iniciando bajo demanda...")
            success = self._start_model(model_id)
            
            if success:
                # Iniciar cleanup thread si no está activo
                self.start_cleanup_thread()
            
            return success
    
    def get_model_stats(self) -> Dict:
        """Obtiene estadísticas de uso de modelos"""
        running_models = self.get_running_models()
        
        return {
            'running_models': running_models,
            'active_count': len(running_models),
            'max_concurrent': self.max_concurrent_models,
            'managed_models': list(self._active_models.keys()),
            'cleanup_active': self._cleanup_running,
            'model_details': self._active_models.copy()
        }
    
    def force_stop_all(self):
        """Detiene todos los modelos gestionados (para shutdown)"""
        logger.info("🛑 Deteniendo todos los modelos gestionados...")
        
        self.stop_cleanup_thread()
        
        models_to_stop = list(self._active_models.keys())
        for model_id in models_to_stop:
            self._stop_model(model_id, reason="shutdown del sistema")
        
        logger.info("🔚 Todos los modelos han sido detenidos")


# Instancia global del gestor
_model_manager = None

def get_model_manager() -> LocalModelManager:
    """Obtiene la instancia global del gestor de modelos"""
    global _model_manager
    if _model_manager is None:
        _model_manager = LocalModelManager()
    return _model_manager

def ensure_model_available(model_id: str) -> bool:
    """Función de conveniencia para asegurar que un modelo esté disponible"""
    if not model_id or not model_id.startswith('ai/'):
        return True  # No es un modelo local, asumir disponible
    
    manager = get_model_manager()
    return manager.ensure_model_running(model_id)