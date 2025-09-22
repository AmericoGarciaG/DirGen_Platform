"""
DirGen Platform - Utilitarios Específicos para Logic Book
=======================================================

Funciones helper adicionales para logging especializado en seguimiento
del Logic Book y validación de cumplimiento de procesos.

Referencia: Logic Book - Todos los Capítulos
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

try:
    from .logging_config import LogicBookLogger
except ImportError:
    LogicBookLogger = None

class LogicBookTracker:
    """
    Tracker especializado para seguimiento de cumplimiento del Logic Book.
    Mantiene estado de fases, transiciones y validaciones.
    """
    
    def __init__(self):
        self.run_states = {}  # run_id -> state_info
    
    def track_run_start(self, logger: logging.Logger, run_id: str, starting_phase: str, svad_info: Dict[str, Any] = None):
        """Registra el inicio de un run según Logic Book"""
        self.run_states[run_id] = {
            'current_phase': starting_phase,
            'start_time': datetime.now(),
            'phase_history': [starting_phase],
            'svad_info': svad_info or {},
            'artifacts_generated': [],
            'quality_gates_passed': [],
            'quality_gates_failed': []
        }
        
        if LogicBookLogger:
            logger.info(
                f"RUN INICIADO: {run_id} - Fase Inicial: {starting_phase}",
                extra={'logic_book_context': {
                    'run_id': run_id,
                    'phase': starting_phase,
                    'event_type': 'RUN_START',
                    'chapter': 'CAP-1',
                    'svad_info': svad_info
                }}
            )
    
    def track_phase_completion(self, logger: logging.Logger, run_id: str, completed_phase: str, next_phase: str = None):
        """Registra la completación de una fase según Logic Book"""
        if run_id in self.run_states:
            state = self.run_states[run_id]
            state['current_phase'] = next_phase or 'COMPLETED'
            state['phase_history'].append(next_phase or 'COMPLETED')
            
            if LogicBookLogger:
                logger.info(
                    f"FASE COMPLETADA: {completed_phase} → {next_phase or 'COMPLETED'}",
                    extra={'logic_book_context': {
                        'run_id': run_id,
                        'phase_completed': completed_phase,
                        'next_phase': next_phase,
                        'event_type': 'PHASE_COMPLETION',
                        'chapter': 'CAP-1',
                        'total_phases': len(state['phase_history'])
                    }}
                )
    
    def track_artifact_generated(self, logger: logging.Logger, run_id: str, artifact_type: str, artifact_path: str):
        """Registra la generación de artefactos según Logic Book"""
        if run_id in self.run_states:
            self.run_states[run_id]['artifacts_generated'].append({
                'type': artifact_type,
                'path': artifact_path,
                'timestamp': datetime.now()
            })
            
            if LogicBookLogger:
                logger.info(
                    f"ARTEFACTO GENERADO: {artifact_type} - {artifact_path}",
                    extra={'logic_book_context': {
                        'run_id': run_id,
                        'artifact_type': artifact_type,
                        'artifact_path': artifact_path,
                        'event_type': 'ARTIFACT_GENERATED',
                        'chapter': 'CAP-3',
                        'total_artifacts': len(self.run_states[run_id]['artifacts_generated'])
                    }}
                )
    
    def track_quality_gate(self, logger: logging.Logger, run_id: str, gate_name: str, result: str, details: str = None):
        """Registra un Quality Gate según Logic Book"""
        if run_id in self.run_states:
            gate_info = {
                'name': gate_name,
                'result': result,
                'details': details,
                'timestamp': datetime.now()
            }
            
            if result == 'PASSED':
                self.run_states[run_id]['quality_gates_passed'].append(gate_info)
            else:
                self.run_states[run_id]['quality_gates_failed'].append(gate_info)
            
            if LogicBookLogger:
                level = logging.INFO if result == 'PASSED' else logging.WARNING
                logger.log(
                    level,
                    f"QUALITY GATE [{gate_name}]: {result}" + (f" - {details}" if details else ""),
                    extra={'logic_book_context': {
                        'run_id': run_id,
                        'quality_gate': gate_name,
                        'result': result,
                        'event_type': 'QUALITY_GATE',
                        'chapter': 'CAP-4',
                        'total_gates_passed': len(self.run_states[run_id]['quality_gates_passed']),
                        'total_gates_failed': len(self.run_states[run_id]['quality_gates_failed'])
                    }}
                )
    
    def get_run_summary(self, run_id: str) -> Dict[str, Any]:
        """Obtiene resumen completo de un run"""
        if run_id not in self.run_states:
            return {}
        
        state = self.run_states[run_id]
        duration = datetime.now() - state['start_time']
        
        return {
            'run_id': run_id,
            'duration_minutes': duration.total_seconds() / 60,
            'current_phase': state['current_phase'],
            'phase_history': state['phase_history'],
            'artifacts_generated': len(state['artifacts_generated']),
            'quality_gates_passed': len(state['quality_gates_passed']),
            'quality_gates_failed': len(state['quality_gates_failed']),
            'completion_rate': self._calculate_completion_rate(state)
        }
    
    def _calculate_completion_rate(self, state: Dict[str, Any]) -> float:
        """Calcula tasa de completación basada en fases típicas del Logic Book"""
        typical_phases = ['INITIAL', 'REQUIREMENTS', 'DESIGN', 'VALIDATION', 'COMPLETED']
        completed_phases = len([p for p in state['phase_history'] if p in typical_phases])
        return min(completed_phases / len(typical_phases), 1.0) * 100

# Instancia global del tracker
logic_book_tracker = LogicBookTracker()

# --- Funciones Helper de Conveniencia ---

def log_svad_validation(logger: logging.Logger, run_id: str, validation_result: Dict[str, Any]):
    """Log específico para validación SVAD"""
    result = "PASSED" if validation_result.get('valid', False) else "FAILED"
    quality_score = validation_result.get('quality_score', 0)
    missing_sections = len(validation_result.get('missing_sections', []))
    
    if LogicBookLogger:
        logger.info(
            f"VALIDACIÓN SVAD: {result} - Calidad: {quality_score}%, Secciones faltantes: {missing_sections}",
            extra={'logic_book_context': {
                'run_id': run_id,
                'validation_type': 'SVAD_STRUCTURE',
                'result': result,
                'quality_score': quality_score,
                'missing_sections': missing_sections,
                'event_type': 'SVAD_VALIDATION',
                'chapter': 'CAP-2'
            }}
        )

def log_pcce_generation(logger: logging.Logger, run_id: str, pcce_size: int, model_used: str):
    """Log específico para generación PCCE"""
    if LogicBookLogger:
        logger.info(
            f"PCCE GENERADO: {pcce_size} caracteres usando {model_used}",
            extra={'logic_book_context': {
                'run_id': run_id,
                'pcce_size': pcce_size,
                'model_used': model_used,
                'event_type': 'PCCE_GENERATION',
                'chapter': 'CAP-2'
            }}
        )

def log_strategic_plan(logger: logging.Logger, run_id: str, plan_tasks: List[str], model_used: str):
    """Log específico para plan estratégico"""
    if LogicBookLogger:
        logger.info(
            f"PLAN ESTRATÉGICO: {len(plan_tasks)} tareas generadas con {model_used}",
            extra={'logic_book_context': {
                'run_id': run_id,
                'plan_tasks_count': len(plan_tasks),
                'model_used': model_used,
                'plan_tasks': plan_tasks[:3],  # Solo primeras 3 tareas para logs
                'event_type': 'STRATEGIC_PLAN',
                'chapter': 'CAP-3'
            }}
        )

def log_retry_attempt(logger: logging.Logger, run_id: str, attempt: int, max_attempts: int, reason: str):
    """Log específico para intentos de retry"""
    if LogicBookLogger:
        logger.warning(
            f"REINTENTO {attempt}/{max_attempts}: {reason}",
            extra={'logic_book_context': {
                'run_id': run_id,
                'retry_attempt': attempt,
                'max_attempts': max_attempts,
                'retry_reason': reason,
                'event_type': 'RETRY_ATTEMPT',
                'chapter': 'CAP-1'
            }}
        )

def log_agent_communication(logger: logging.Logger, run_id: str, from_agent: str, to_component: str, message_type: str, data_size: int = None):
    """Log específico para comunicación entre agentes"""
    if LogicBookLogger:
        message = f"COMUNICACIÓN: {from_agent} → {to_component} ({message_type})"
        if data_size:
            message += f" - {data_size} bytes"
            
        logger.debug(
            message,
            extra={'logic_book_context': {
                'run_id': run_id,
                'from_agent': from_agent,
                'to_component': to_component,
                'message_type': message_type,
                'data_size': data_size,
                'event_type': 'AGENT_COMMUNICATION',
                'chapter': 'CAP-2'
            }}
        )

def log_orchestrator_decision(logger: logging.Logger, run_id: str, decision_type: str, decision_reason: str, next_action: str):
    """Log específico para decisiones del orchestrator"""
    if LogicBookLogger:
        logger.info(
            f"DECISIÓN ORCHESTRATOR: {decision_type} - {decision_reason} → {next_action}",
            extra={'logic_book_context': {
                'run_id': run_id,
                'decision_type': decision_type,
                'decision_reason': decision_reason,
                'next_action': next_action,
                'event_type': 'ORCHESTRATOR_DECISION',
                'chapter': 'CAP-1'
            }}
        )

def generate_logic_book_compliance_report(run_id: str) -> str:
    """Genera reporte de cumplimiento del Logic Book para un run"""
    summary = logic_book_tracker.get_run_summary(run_id)
    
    if not summary:
        return f"No se encontró información para el run {run_id}"
    
    report = f"""
=== REPORTE DE CUMPLIMIENTO LOGIC BOOK ===
Run ID: {run_id}
Duración: {summary['duration_minutes']:.1f} minutos
Fase Actual: {summary['current_phase']}

🔄 HISTORIAL DE FASES:
{' → '.join(summary['phase_history'])}

📋 ARTEFACTOS GENERADOS: {summary['artifacts_generated']}

✅ QUALITY GATES PASADOS: {summary['quality_gates_passed']}
❌ QUALITY GATES FALLIDOS: {summary['quality_gates_failed']}

📊 TASA DE COMPLETACIÓN: {summary['completion_rate']:.1f}%

=== CUMPLIMIENTO LOGIC BOOK ===
Fases según LB: {'✓' if summary['completion_rate'] > 80 else '⚠️'}
Quality Gates: {'✓' if summary['quality_gates_failed'] == 0 else '⚠️'}
Artefactos: {'✓' if summary['artifacts_generated'] > 0 else '⚠️'}

EVALUACIÓN GENERAL: {'CUMPLIMIENTO COMPLETO' if summary['completion_rate'] == 100 and summary['quality_gates_failed'] == 0 else 'CUMPLIMIENTO PARCIAL'}
"""
    return report