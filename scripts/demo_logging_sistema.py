#!/usr/bin/env python3
"""
Demostración del Sistema de Logging Centralizado DirGen
=====================================================

Script que demuestra el sistema de logging funcionando correctamente
con todos los componentes y seguimiento del Logic Book.
"""

import time
import uuid
from dirgen_core.logging_config import (
    get_orchestrator_logger, get_agent_logger, 
    LogicBookLogger, LogLevel
)
from dirgen_core.logic_book_utils import (
    logic_book_tracker, log_svad_validation, log_pcce_generation,
    log_strategic_plan, log_retry_attempt, log_orchestrator_decision,
    generate_logic_book_compliance_report
)

def demo_complete_run():
    """Demuestra un run completo con logging según Logic Book"""
    
    print("🚀 INICIANDO DEMOSTRACIÓN DEL SISTEMA DE LOGGING")
    print("=" * 55)
    
    # Crear loggers
    orchestrator_logger = get_orchestrator_logger(LogLevel.DEBUG)
    requirements_logger = get_agent_logger("requirements", LogLevel.DEBUG)
    planner_logger = get_agent_logger("planner", LogLevel.DEBUG)
    validator_logger = get_agent_logger("validator", LogLevel.DEBUG)
    
    logic_logger = LogicBookLogger()
    
    # Simular un run completo
    run_id = f"demo-{uuid.uuid4()}"
    print(f"📋 Run ID: {run_id}")
    
    print("\n🔄 FASE 0: INICIO DE RUN")
    print("-" * 30)
    
    # 1. Inicio del run
    logic_book_tracker.track_run_start(
        orchestrator_logger, run_id, "INITIAL", 
        {"svad": "demo_svad.md", "size": "2.5KB"}
    )
    
    time.sleep(0.1)
    
    print("\n🔍 FASE 1: ANÁLISIS DE REQUERIMIENTOS")
    print("-" * 40)
    
    # 2. Invocar Requirements Agent
    logic_logger.log_agent_action(
        orchestrator_logger, run_id, "Requirements", "INVOKED",
        {"pid": 12345, "svad_path": "/temp/demo_svad.md"}
    )
    
    # 3. Validación SVAD
    validation_result = {
        "valid": True,
        "quality_score": 98,
        "missing_sections": []
    }
    
    log_svad_validation(requirements_logger, run_id, validation_result)
    
    # 4. Generación PCCE
    log_pcce_generation(requirements_logger, run_id, 3420, "ai/gemma3-qat")
    
    # 5. Transición de fase
    logic_logger.log_phase_transition(
        orchestrator_logger, run_id, "REQUIREMENTS", "DESIGN", "CAP-2"
    )
    
    time.sleep(0.1)
    
    print("\n🎨 FASE 2: DISEÑO Y PLANIFICACIÓN")  
    print("-" * 35)
    
    # 6. Invocar Planner Agent
    logic_logger.log_agent_action(
        orchestrator_logger, run_id, "Planner", "INVOKED",
        {"pid": 12346, "pcce_path": "/temp/demo_pcce.yml"}
    )
    
    # 7. Generación de plan estratégico
    plan_tasks = [
        "Analizar requerimientos del PCCE",
        "Diseñar arquitectura C4",
        "Generar especificaciones OpenAPI", 
        "Crear diagramas PlantUML",
        "Validar completitud"
    ]
    
    log_strategic_plan(planner_logger, run_id, plan_tasks, "ai/smollm3")
    
    # 8. Generación de artefactos
    artifacts = [
        ("ARCHITECTURE_DIAGRAM", "design/architecture.puml"),
        ("API_SPECIFICATION", "design/api/users.yml"),
        ("API_SPECIFICATION", "design/api/orders.yml")
    ]
    
    for artifact_type, artifact_path in artifacts:
        logic_logger.log_artifact_generation(
            planner_logger, run_id, artifact_type, artifact_path, True
        )
        time.sleep(0.05)
    
    time.sleep(0.1)
    
    print("\n✅ FASE 3: QUALITY GATE - VALIDACIÓN")
    print("-" * 40)
    
    # 9. Invocar Validator Agent
    logic_logger.log_agent_action(
        orchestrator_logger, run_id, "Validator", "INVOKED",
        {"pid": 12347, "artifacts_to_check": 3}
    )
    
    # 10. Quality Gates
    quality_gates = [
        ("ARCHITECTURE_VALIDATION", "PASSED", "Diagrama C4 válido"),
        ("API_SPECIFICATION_VALIDATION", "PASSED", "3/3 especificaciones válidas"),
        ("COMPLETENESS_CHECK", "PASSED", "Todos los artefactos generados")
    ]
    
    for gate_name, result, details in quality_gates:
        logic_logger.log_quality_gate(
            validator_logger, run_id, gate_name, result, details
        )
        time.sleep(0.05)
    
    time.sleep(0.1)
    
    print("\n🎯 FASE 4: COMPLETACIÓN")
    print("-" * 25)
    
    # 11. Decisión del orchestrator
    log_orchestrator_decision(
        orchestrator_logger, run_id, "COMPLETION", 
        "Todos los quality gates pasaron", "Finalizar run exitosamente"
    )
    
    # 12. Completar fase
    logic_book_tracker.track_phase_completion(
        orchestrator_logger, run_id, "VALIDATION", "COMPLETED"
    )
    
    time.sleep(0.1)
    
    print("\n📊 GENERANDO REPORTE DE CUMPLIMIENTO")
    print("-" * 40)
    
    # 13. Generar reporte
    report = generate_logic_book_compliance_report(run_id)
    print(report)
    
    print(f"\n✅ DEMOSTRACIÓN COMPLETADA")
    print("=" * 55)
    print(f"📁 Revisa los logs en: logs/")
    print(f"🔍 Busca el Run ID: {run_id[:8]}...")
    
    return run_id

def show_recent_logs():
    """Muestra las últimas líneas de los logs generados"""
    from pathlib import Path
    
    print("\n📋 ÚLTIMAS ENTRADAS EN LOGS:")
    print("=" * 40)
    
    logs_dir = Path("logs")
    
    # Mostrar logs del orchestrator
    orchestrator_log = logs_dir / "orchestrator" / "orchestrator.log"
    if orchestrator_log.exists():
        print("\n🎯 ORCHESTRATOR LOG (últimas 3 líneas):")
        with open(orchestrator_log, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines[-3:]:
                print(f"  {line.strip()}")
    
    # Mostrar logs de requirements
    req_log = logs_dir / "agents" / "requirements" / "requirements_agent.log" 
    if req_log.exists():
        print("\n🔍 REQUIREMENTS AGENT LOG (últimas 2 líneas):")
        with open(req_log, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines[-2:]:
                print(f"  {line.strip()}")

if __name__ == "__main__":
    try:
        run_id = demo_complete_run()
        show_recent_logs()
        
        print(f"\n💡 Para verificar logs detallados:")
        print(f"   grep '{run_id[:8]}' logs/**/*.log")
        
    except Exception as e:
        print(f"❌ Error en demostración: {e}")
        import traceback
        traceback.print_exc()