"""
DirGen Platform - Configuración Centralizada de Logging
======================================================

Sistema de logging unificado con:
1. Rotación automática de archivos por tamaño y tiempo
2. Formatos específicos para seguimiento del Logic Book  
3. Niveles configurables por ambiente (dev/prod)
4. Logs estructurados para trazabilidad de estados y fases
5. Compatibilidad con todos los componentes de la plataforma

Referencia: Logic Book Capítulo 3 - Observabilidad y Monitoreo
"""

import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import json

# --- Configuración Global ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOGS_ROOT = PROJECT_ROOT / "logs"

# Asegurar que el directorio de logs existe
LOGS_ROOT.mkdir(exist_ok=True)
for subdir in ["orchestrator", "agents/requirements", "agents/planner", "agents/validator", "client", "core"]:
    (LOGS_ROOT / subdir).mkdir(parents=True, exist_ok=True)

# --- Niveles de Logging ---
class LogLevel:
    DEBUG = logging.DEBUG
    INFO = logging.INFO  
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL

# --- Formateadores Especializados ---
class LogicBookFormatter(logging.Formatter):
    """
    Formateador especializado para seguimiento del Logic Book.
    Incluye contexto específico para fases, estados y transiciones.
    """
    
    def __init__(self, component_name: str):
        self.component_name = component_name
        super().__init__()
    
    def format(self, record):
        # Formato base con timestamp y componente
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        # Extraer contexto del Logic Book si existe
        logic_book_context = getattr(record, 'logic_book_context', {})
        
        # Construir mensaje base
        base_msg = f"[{timestamp}] [{self.component_name}] [{record.levelname}]"
        
        # Añadir contexto del Logic Book si existe
        if logic_book_context:
            if 'phase' in logic_book_context:
                base_msg += f" [FASE:{logic_book_context['phase']}]"
            if 'state' in logic_book_context:
                base_msg += f" [ESTADO:{logic_book_context['state']}]"
            if 'run_id' in logic_book_context:
                base_msg += f" [RUN:{logic_book_context['run_id'][:8]}...]"
            if 'chapter' in logic_book_context:
                base_msg += f" [LB-CAP:{logic_book_context['chapter']}]"
        
        # Mensaje principal
        base_msg += f" {record.getMessage()}"
        
        # Añadir contexto adicional como JSON si existe
        if logic_book_context and len(logic_book_context) > 0:
            context_str = json.dumps(logic_book_context, separators=(',', ':'))
            base_msg += f" | CONTEXT: {context_str}"
        
        return base_msg

class StandardFormatter(logging.Formatter):
    """Formateador estándar para logs generales"""
    
    def __init__(self, component_name: str):
        format_str = f'[%(asctime)s] [{component_name}] [%(levelname)s] %(message)s'
        super().__init__(format_str, datefmt='%Y-%m-%d %H:%M:%S')

# --- Configurador de Loggers ---
class DirGenLogger:
    """
    Configurador principal de loggers para la plataforma DirGen.
    Proporciona loggers específicos por componente con rotación automática.
    """
    
    _loggers: Dict[str, logging.Logger] = {}
    
    @classmethod
    def get_logger(
        cls,
        component_name: str,
        log_level: int = LogLevel.INFO,
        use_logic_book_format: bool = True,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        console_output: bool = True
    ) -> logging.Logger:
        """
        Obtiene o crea un logger configurado para un componente específico.
        
        Args:
            component_name: Nombre del componente (ej: "orchestrator", "requirements_agent")
            log_level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            use_logic_book_format: Si usar el formateador especializado del Logic Book
            max_file_size: Tamaño máximo del archivo antes de rotar (bytes)
            backup_count: Número de archivos de backup a mantener
            console_output: Si mostrar logs en consola también
        
        Returns:
            Logger configurado y listo para usar
        """
        
        if component_name in cls._loggers:
            return cls._loggers[component_name]
        
        # Crear logger
        logger = logging.getLogger(f"dirgen.{component_name}")
        logger.setLevel(log_level)
        
        # Evitar duplicación de handlers
        if logger.handlers:
            logger.handlers.clear()
        
        # Determinar ruta del archivo de log
        log_subdir = cls._get_log_subdir(component_name)
        log_file = LOGS_ROOT / log_subdir / f"{component_name}.log"
        
        # Handler de archivo con rotación
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        
        # Handler de consola (si se requiere)
        if console_output:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(log_level)
            
            # Usar formato estándar para consola
            console_formatter = StandardFormatter(component_name)
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
        
        # Seleccionar formateador
        if use_logic_book_format:
            file_formatter = LogicBookFormatter(component_name)
        else:
            file_formatter = StandardFormatter(component_name)
        
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        # Evitar propagación a root logger
        logger.propagate = False
        
        cls._loggers[component_name] = logger
        return logger
    
    @classmethod
    def _get_log_subdir(cls, component_name: str) -> str:
        """Determina el subdirectorio apropiado para un componente"""
        if "orchestrator" in component_name.lower() or "mcp" in component_name.lower():
            return "orchestrator"
        elif "requirements" in component_name.lower():
            return "agents/requirements"
        elif "planner" in component_name.lower():
            return "agents/planner"
        elif "validator" in component_name.lower():
            return "agents/validator"
        elif "tui" in component_name.lower() or "client" in component_name.lower():
            return "client"
        else:
            return "core"

# --- Utilidades para Logging del Logic Book ---
class LogicBookLogger:
    """
    Utilidades especializadas para logging de eventos relacionados con el Logic Book.
    Proporciona métodos convenientes para loggear fases, estados, transiciones, etc.
    """
    
    @staticmethod
    def log_phase_transition(logger: logging.Logger, run_id: str, from_phase: str, to_phase: str, chapter: str = None):
        """Log de transición entre fases según Logic Book"""
        context = {
            'run_id': run_id,
            'phase_from': from_phase,
            'phase_to': to_phase,
            'transition_type': 'PHASE_TRANSITION'
        }
        if chapter:
            context['chapter'] = chapter
            
        logger.info(
            f"TRANSICIÓN DE FASE: {from_phase} → {to_phase}",
            extra={'logic_book_context': context}
        )
    
    @staticmethod
    def log_state_change(logger: logging.Logger, run_id: str, state: str, phase: str = None, metadata: Dict[str, Any] = None):
        """Log de cambio de estado según Logic Book"""
        context = {
            'run_id': run_id,
            'state': state,
            'event_type': 'STATE_CHANGE'
        }
        if phase:
            context['phase'] = phase
        if metadata:
            context.update(metadata)
            
        logger.info(
            f"CAMBIO DE ESTADO: {state}",
            extra={'logic_book_context': context}
        )
    
    @staticmethod
    def log_quality_gate(logger: logging.Logger, run_id: str, gate_name: str, result: str, details: str = None):
        """Log de Quality Gate según Logic Book"""
        context = {
            'run_id': run_id,
            'quality_gate': gate_name,
            'result': result,
            'event_type': 'QUALITY_GATE'
        }
        
        level = logging.INFO if result == 'PASSED' else logging.WARNING
        message = f"QUALITY GATE [{gate_name}]: {result}"
        if details:
            message += f" - {details}"
            
        logger.log(
            level,
            message,
            extra={'logic_book_context': context}
        )
    
    @staticmethod
    def log_agent_action(logger: logging.Logger, run_id: str, agent_name: str, action: str, details: Dict[str, Any] = None):
        """Log de acción de agente según Logic Book"""
        context = {
            'run_id': run_id,
            'agent': agent_name,
            'action': action,
            'event_type': 'AGENT_ACTION'
        }
        if details:
            context['details'] = details
            
        logger.info(
            f"ACCIÓN AGENTE [{agent_name}]: {action}",
            extra={'logic_book_context': context}
        )
    
    @staticmethod
    def log_artifact_generation(logger: logging.Logger, run_id: str, artifact_type: str, artifact_path: str, success: bool = True):
        """Log de generación de artefactos según Logic Book"""
        context = {
            'run_id': run_id,
            'artifact_type': artifact_type,
            'artifact_path': artifact_path,
            'success': success,
            'event_type': 'ARTIFACT_GENERATION'
        }
        
        status = "EXITOSA" if success else "FALLIDA"
        logger.info(
            f"GENERACIÓN DE ARTEFACTO [{artifact_type}]: {status} - {artifact_path}",
            extra={'logic_book_context': context}
        )

# --- Configuraciones Predefinidas ---
def get_orchestrator_logger(log_level: int = LogLevel.INFO) -> logging.Logger:
    """Logger configurado para el Orchestrator/MCP Host"""
    return DirGenLogger.get_logger(
        "orchestrator",
        log_level=log_level,
        use_logic_book_format=True,
        console_output=True
    )

def get_agent_logger(agent_name: str, log_level: int = LogLevel.INFO) -> logging.Logger:
    """Logger configurado para agentes"""
    return DirGenLogger.get_logger(
        f"{agent_name}_agent",
        log_level=log_level,
        use_logic_book_format=True,
        console_output=True
    )

def get_client_logger(log_level: int = LogLevel.INFO) -> logging.Logger:
    """Logger configurado para clientes (TUI, Desktop)"""
    return DirGenLogger.get_logger(
        "client",
        log_level=log_level,
        use_logic_book_format=False,  # Cliente usa formato estándar
        console_output=False  # Cliente maneja su propia salida
    )

def get_core_logger(component_name: str, log_level: int = LogLevel.INFO) -> logging.Logger:
    """Logger configurado para componentes core"""
    return DirGenLogger.get_logger(
        f"core_{component_name}",
        log_level=log_level,
        use_logic_book_format=False,
        console_output=True
    )

# --- Configuración de Ambiente ---
def configure_logging_for_environment(environment: str = "development"):
    """
    Configura logging según el ambiente.
    
    Args:
        environment: "development", "production", "testing"
    """
    if environment == "development":
        default_level = LogLevel.DEBUG
    elif environment == "production":
        default_level = LogLevel.INFO
    elif environment == "testing":
        default_level = LogLevel.WARNING
    else:
        default_level = LogLevel.INFO
    
    # Configurar nivel por defecto para todos los nuevos loggers
    DirGenLogger._default_level = default_level
    
    # Configurar root logger para capturar logs no manejados
    root_logger = logging.getLogger()
    root_logger.setLevel(default_level)

# --- Inicialización ---
def initialize_logging(environment: str = None):
    """
    Inicializa el sistema de logging centralizado.
    Debe ser llamado al inicio de cada componente.
    """
    env = environment or os.getenv("DIRGEN_ENVIRONMENT", "development")
    configure_logging_for_environment(env)
    
    # Log de inicialización
    init_logger = get_core_logger("logging_init")
    init_logger.info(f"Sistema de logging DirGen inicializado - Ambiente: {env}")
    init_logger.info(f"Directorio de logs: {LOGS_ROOT}")

# Inicializar automáticamente al importar
initialize_logging()