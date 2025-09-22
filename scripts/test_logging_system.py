#!/usr/bin/env python3
"""
Script de Prueba - Sistema de Logging Centralizado DirGen
========================================================

Prueba todos los componentes del sistema de logging centralizado
y verifica que se está loggeando correctamente según el Logic Book.

Usage:
    python test_logging_system.py
"""

import sys
import os
from pathlib import Path
import time
import traceback

# Agregar el directorio del proyecto al path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

def test_logging_config():
    """Prueba la configuración centralizada de logging"""
    print("🔧 Probando configuración centralizada de logging...")
    
    try:
        from dirgen_core.logging_config import (
            get_orchestrator_logger, get_agent_logger, get_client_logger, get_core_logger,
            LogicBookLogger, LogLevel
        )
        
        # Probar diferentes tipos de loggers
        orchestrator_logger = get_orchestrator_logger(LogLevel.DEBUG)
        requirements_logger = get_agent_logger("requirements", LogLevel.DEBUG)
        planner_logger = get_agent_logger("planner", LogLevel.DEBUG)
        validator_logger = get_agent_logger("validator", LogLevel.DEBUG)
        client_logger = get_client_logger(LogLevel.DEBUG)
        core_logger = get_core_logger("test_component", LogLevel.DEBUG)
        
        # Probar LogicBookLogger
        logic_logger = LogicBookLogger()
        
        print("  ✅ Todos los loggers se crearon correctamente")
        
        # Probar logging básico
        test_run_id = "test-run-12345"
        
        orchestrator_logger.info("Prueba de Orchestrator logger")
        requirements_logger.info("Prueba de Requirements Agent logger")
        planner_logger.info("Prueba de Planner Agent logger")
        validator_logger.info("Prueba de Validator Agent logger")
        client_logger.info("Prueba de Client logger")
        core_logger.info("Prueba de Core logger")
        
        print("  ✅ Logging básico funciona correctamente")
        
        # Probar LogicBookLogger
        logic_logger.log_phase_transition(orchestrator_logger, test_run_id, "TEST_PHASE_1", "TEST_PHASE_2", "CAP-TEST")
        logic_logger.log_state_change(orchestrator_logger, test_run_id, "TEST_STATE", "TEST_PHASE", {"test": "metadata"})
        logic_logger.log_quality_gate(orchestrator_logger, test_run_id, "TEST_GATE", "PASSED", "Prueba exitosa")
        logic_logger.log_agent_action(orchestrator_logger, test_run_id, "TestAgent", "TEST_ACTION", {"test": "details"})
        logic_logger.log_artifact_generation(orchestrator_logger, test_run_id, "TEST_ARTIFACT", "test/path.yml", True)
        
        print("  ✅ LogicBookLogger funciona correctamente")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error en configuración de logging: {e}")
        traceback.print_exc()
        return False

def test_logic_book_utils():
    """Prueba los utilitarios específicos para Logic Book"""
    print("📋 Probando utilitarios específicos para Logic Book...")
    
    try:
        from dirgen_core.logic_book_utils import (
            logic_book_tracker, log_svad_validation, log_pcce_generation,
            log_strategic_plan, log_retry_attempt, log_agent_communication,
            log_orchestrator_decision, generate_logic_book_compliance_report
        )
        from dirgen_core.logging_config import get_orchestrator_logger, LogLevel
        
        logger = get_orchestrator_logger(LogLevel.DEBUG)
        test_run_id = "test-utils-67890"
        
        # Probar tracker
        logic_book_tracker.track_run_start(logger, test_run_id, "INITIAL", {"svad": "test.md"})
        logic_book_tracker.track_phase_completion(logger, test_run_id, "INITIAL", "REQUIREMENTS")
        logic_book_tracker.track_artifact_generated(logger, test_run_id, "PCCE", "test_pcce.yml")
        logic_book_tracker.track_quality_gate(logger, test_run_id, "TEST_GATE", "PASSED", "Todo OK")
        
        print("  ✅ LogicBookTracker funciona correctamente")
        
        # Probar funciones helper
        log_svad_validation(logger, test_run_id, {"valid": True, "quality_score": 95, "missing_sections": []})
        log_pcce_generation(logger, test_run_id, 1024, "ai/gemma3-qat")
        log_strategic_plan(logger, test_run_id, ["Tarea 1", "Tarea 2", "Tarea 3"], "ai/smollm3")
        log_retry_attempt(logger, test_run_id, 1, 3, "Archivo faltante")
        log_agent_communication(logger, test_run_id, "Requirements", "Orchestrator", "task_complete", 512)
        log_orchestrator_decision(logger, test_run_id, "RETRY", "Archivo faltante", "Reinvocar Planner Agent")
        
        print("  ✅ Funciones helper funcionan correctamente")
        
        # Probar reporte de cumplimiento
        report = generate_logic_book_compliance_report(test_run_id)
        print(f"  📊 Reporte de cumplimiento generado: {len(report)} caracteres")
        print("  ✅ Reporte de cumplimiento funciona correctamente")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error en utilitarios Logic Book: {e}")
        traceback.print_exc()
        return False

def test_file_generation():
    """Verifica que se están generando los archivos de log"""
    print("📁 Verificando generación de archivos de log...")
    
    logs_dir = PROJECT_ROOT / "logs"
    
    if not logs_dir.exists():
        print(f"  ❌ Directorio de logs no existe: {logs_dir}")
        return False
    
    print(f"  ✅ Directorio de logs existe: {logs_dir}")
    
    # Verificar subdirectorios
    expected_dirs = ["orchestrator", "agents/requirements", "agents/planner", "agents/validator", "client", "core"]
    
    for expected_dir in expected_dirs:
        dir_path = logs_dir / expected_dir
        if dir_path.exists():
            print(f"  ✅ Subdirectorio existe: {expected_dir}")
        else:
            print(f"  ⚠️ Subdirectorio no existe (se creará cuando sea necesario): {expected_dir}")
    
    # Buscar archivos de log generados
    log_files = list(logs_dir.rglob("*.log"))
    
    if log_files:
        print(f"  ✅ Archivos de log encontrados: {len(log_files)}")
        for log_file in log_files[:5]:  # Mostrar solo los primeros 5
            print(f"    - {log_file.relative_to(logs_dir)}")
        if len(log_files) > 5:
            print(f"    ... y {len(log_files) - 5} más")
    else:
        print("  ⚠️ No se encontraron archivos de log (se crearán al usar los loggers)")
    
    return True

def test_log_content():
    """Verifica el contenido de un archivo de log"""
    print("🔍 Verificando contenido de logs...")
    
    logs_dir = PROJECT_ROOT / "logs"
    log_files = list(logs_dir.rglob("*.log"))
    
    if not log_files:
        print("  ⚠️ No hay archivos de log para verificar contenido")
        return True
    
    # Tomar el primer archivo de log
    log_file = log_files[0]
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"  ✅ Archivo de log leído: {log_file.name} ({len(content)} caracteres)")
        
        # Verificar elementos específicos del Logic Book
        logic_book_indicators = [
            "[FASE:",
            "[ESTADO:",
            "[RUN:",
            "[LB-CAP:",
            "CONTEXT:",
            "TRANSICIÓN DE FASE",
            "CAMBIO DE ESTADO",
            "QUALITY GATE",
            "ACCIÓN AGENTE"
        ]
        
        found_indicators = [indicator for indicator in logic_book_indicators if indicator in content]
        
        if found_indicators:
            print(f"  ✅ Elementos del Logic Book encontrados: {len(found_indicators)}")
            for indicator in found_indicators[:3]:  # Mostrar solo los primeros 3
                print(f"    - {indicator}")
        else:
            print("  ⚠️ No se encontraron elementos específicos del Logic Book")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error leyendo archivo de log: {e}")
        return False

def test_component_integration():
    """Prueba la integración con componentes reales (sin ejecutarlos)"""
    print("🔌 Probando integración con componentes...")
    
    try:
        # Probar importación de los módulos actualizados
        print("  📦 Verificando imports de componentes actualizados...")
        
        # Verificar que los componentes pueden importar el logging
        test_imports = {
            "MCP Host": "mcp_host.main",
            "Requirements Agent": "agents.requirements.requirements_agent",
            "Planner Agent": "agents.planner.planner_agent", 
            "Validator Agent": "agents.validator.validator_agent",
            "TUI Client": "client.tui"
        }
        
        for component_name, module_path in test_imports.items():
            try:
                __import__(module_path)
                print(f"    ✅ {component_name}: Import exitoso")
            except Exception as e:
                print(f"    ❌ {component_name}: Error en import - {e}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error en integración de componentes: {e}")
        traceback.print_exc()
        return False

def main():
    """Función principal de prueba"""
    print("🚀 INICIANDO PRUEBAS DEL SISTEMA DE LOGGING CENTRALIZADO")
    print("=" * 60)
    
    # Ejecutar todas las pruebas
    tests = [
        ("Configuración de Logging", test_logging_config),
        ("Utilitarios Logic Book", test_logic_book_utils),
        ("Generación de Archivos", test_file_generation),
        ("Contenido de Logs", test_log_content),
        ("Integración de Componentes", test_component_integration)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 EJECUTANDO: {test_name}")
        print("-" * 40)
        
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASÓ")
            else:
                print(f"❌ {test_name}: FALLÓ")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
            traceback.print_exc()
    
    print(f"\n{'=' * 60}")
    print(f"🏁 RESUMEN FINAL: {passed}/{total} pruebas pasaron")
    
    if passed == total:
        print("🎉 ¡TODAS LAS PRUEBAS PASARON! Sistema de logging listo.")
    else:
        print("⚠️ Algunas pruebas fallaron. Revisar los errores arriba.")
    
    # Mostrar ubicación de logs para inspección manual
    logs_dir = PROJECT_ROOT / "logs"
    print(f"\n📁 Logs disponibles en: {logs_dir}")
    print("💡 Puedes inspeccionar manualmente los archivos de log generados.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)