#!/usr/bin/env python3
"""
Script para Extraer Logs Específicos - Comparación UI vs Backend
===============================================================

Este script extrae exactamente los logs que necesitas para:
1. Comparar UI con proceso real
2. Seguimiento completo del Logic Book

Usage:
    python extraer_logs_comparacion.py [run-id]
    python extraer_logs_comparacion.py run-0242c2f7  # ejemplo
"""

import sys
import re
import json
from pathlib import Path
from datetime import datetime

def find_recent_runs():
    """Encuentra los runs más recientes en los logs"""
    orchestrator_log = Path("logs/orchestrator/orchestrator.log")
    
    if not orchestrator_log.exists():
        print("❌ No se encontró el log del orchestrator")
        return []
    
    runs = set()
    with open(orchestrator_log, 'r', encoding='utf-8') as f:
        for line in f:
            match = re.search(r'run-([a-f0-9\-]+)', line)
            if match:
                runs.add("run-" + match.group(1))
    
    return sorted(list(runs))[-5:]  # Últimos 5 runs

def extract_ui_events(run_id):
    """Extrae eventos que llegan a la UI (via WebSocket)"""
    print(f"\n📱 EVENTOS QUE VE EL USUARIO EN LA UI (run: {run_id[:12]}...)")
    print("=" * 60)
    
    # Los eventos de UI llegan via WebSocket y se logean en diferentes lugares
    orchestrator_log = Path("logs/orchestrator/orchestrator.log")
    
    ui_events = []
    
    if orchestrator_log.exists():
        with open(orchestrator_log, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if run_id in line and "Retransmitiendo mensaje" in line:
                    # Estos son mensajes que se envían a la UI via WebSocket
                    ui_events.append({
                        'line': line_num,
                        'timestamp': extract_timestamp(line),
                        'content': line.strip()
                    })
    
    if ui_events:
        for event in ui_events[-10:]:  # Últimos 10 eventos
            timestamp = event['timestamp']
            content = event['content']
            # Extraer el tipo de mensaje y fuente
            match = re.search(r'\[([^:]+):([^\]]+)\]', content)
            if match:
                source, msg_type = match.groups()
                print(f"[{timestamp}] {source} → UI: {msg_type}")
            else:
                print(f"[{timestamp}] WebSocket: {content[50:150]}...")
    else:
        print("🔍 Buscando en logs de cliente...")
        client_log = Path("logs/client/client.log")
        if client_log.exists():
            with open(client_log, 'r', encoding='utf-8') as f:
                for line in f:
                    if run_id in line:
                        print(f"  📱 {line.strip()}")
        else:
            print("⚠️ No se encontraron eventos específicos de UI para este run")

def extract_backend_process(run_id):
    """Extrae el proceso real del backend"""
    print(f"\n⚙️ PROCESO REAL EN EL BACKEND (run: {run_id[:12]}...)")
    print("=" * 60)
    
    orchestrator_log = Path("logs/orchestrator/orchestrator.log")
    
    if not orchestrator_log.exists():
        print("❌ No se encontró el log del orchestrator")
        return
    
    backend_events = []
    
    with open(orchestrator_log, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if run_id in line:
                backend_events.append({
                    'line': line_num,
                    'timestamp': extract_timestamp(line),
                    'content': line.strip()
                })
    
    # Mostrar eventos clave del backend
    for event in backend_events:
        content = event['content']
        timestamp = event['timestamp']
        
        # Identificar tipos de eventos importantes
        if "CAMBIO DE ESTADO:" in content:
            estado = re.search(r'CAMBIO DE ESTADO: (\w+)', content)
            if estado:
                print(f"[{timestamp}] 📊 Estado: {estado.group(1)}")
        
        elif "TRANSICIÓN DE FASE:" in content:
            transicion = re.search(r'TRANSICIÓN DE FASE: (\w+) → (\w+)', content)
            if transicion:
                print(f"[{timestamp}] 🔄 Fase: {transicion.group(1)} → {transicion.group(2)}")
        
        elif "ACCIÓN AGENTE" in content:
            agente = re.search(r'ACCIÓN AGENTE \[([^\]]+)\]: (\w+)', content)
            if agente:
                print(f"[{timestamp}] 🤖 Agente: {agente.group(1)} - {agente.group(2)}")
        
        elif "INICIO DE RUN:" in content:
            print(f"[{timestamp}] 🚀 Run iniciado")
        
        elif "Iniciando Fase" in content:
            fase = re.search(r'Iniciando Fase \d+ \(([^)]+)\)', content)
            if fase:
                print(f"[{timestamp}] 🔄 Nueva Fase: {fase.group(1)}")

def extract_logic_book_tracking(run_id):
    """Extrae seguimiento específico del Logic Book"""
    print(f"\n📋 SEGUIMIENTO COMPLETO DEL LOGIC BOOK (run: {run_id[:12]}...)")
    print("=" * 70)
    
    log_files = [
        ("orchestrator", "logs/orchestrator/orchestrator.log"),
        ("requirements", "logs/agents/requirements/requirements_agent.log"),
        ("planner", "logs/agents/planner/planner_agent.log"),
        ("validator", "logs/agents/validator/validator_agent.log")
    ]
    
    logic_book_events = []
    
    for component, log_file in log_files:
        log_path = Path(log_file)
        if log_path.exists():
            with open(log_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if run_id in line and ("LB-CAP:" in line or "CONTEXT:" in line):
                        logic_book_events.append({
                            'component': component,
                            'timestamp': extract_timestamp(line),
                            'content': line.strip()
                        })
    
    # Ordenar por timestamp
    logic_book_events.sort(key=lambda x: x['timestamp'] or "")
    
    print("\n🔍 REFERENCIAS AL LOGIC BOOK:")
    for event in logic_book_events:
        timestamp = event['timestamp']
        component = event['component']
        content = event['content']
        
        # Extraer capítulo del Logic Book
        cap_match = re.search(r'\[LB-CAP:([^\]]+)\]', content)
        chapter = cap_match.group(1) if cap_match else "?"
        
        # Extraer tipo de evento
        if "TRANSICIÓN DE FASE" in content:
            print(f"[{timestamp}] [{component}] 📖 {chapter} - Transición de Fase")
        elif "CAMBIO DE ESTADO" in content:
            print(f"[{timestamp}] [{component}] 📖 {chapter} - Cambio de Estado")
        elif "QUALITY GATE" in content:
            print(f"[{timestamp}] [{component}] 📖 {chapter} - Quality Gate")
        elif "ACCIÓN AGENTE" in content:
            print(f"[{timestamp}] [{component}] 📖 {chapter} - Acción de Agente")
        elif "VALIDACIÓN SVAD" in content:
            print(f"[{timestamp}] [{component}] 📖 {chapter} - Validación SVAD")
        elif "PCCE GENERADO" in content:
            print(f"[{timestamp}] [{component}] 📖 {chapter} - Generación PCCE")
        else:
            # Mostrar el contexto JSON si está disponible
            context_match = re.search(r'CONTEXT: (\{.*\})', content)
            if context_match:
                try:
                    context = json.loads(context_match.group(1))
                    event_type = context.get('event_type', 'UNKNOWN')
                    print(f"[{timestamp}] [{component}] 📖 {chapter} - {event_type}")
                except:
                    print(f"[{timestamp}] [{component}] 📖 {chapter} - Evento Logic Book")

def extract_timestamp(line):
    """Extrae timestamp de una línea de log"""
    match = re.search(r'\[([0-9\-: .]+)\]', line)
    return match.group(1) if match else ""

def show_summary(run_id):
    """Muestra resumen del análisis"""
    print(f"\n📊 RESUMEN PARA RUN: {run_id[:12]}...")
    print("=" * 50)
    
    try:
        from dirgen_core.logic_book_utils import generate_logic_book_compliance_report
        report = generate_logic_book_compliance_report(run_id)
        print(report)
    except Exception as e:
        print(f"⚠️ No se pudo generar reporte de cumplimiento: {e}")

def main():
    print("🔍 EXTRACTOR DE LOGS - COMPARACIÓN UI vs BACKEND")
    print("=" * 55)
    
    # Determinar run ID
    if len(sys.argv) > 1:
        run_id = sys.argv[1]
        if not run_id.startswith("run-"):
            run_id = f"run-{run_id}"
    else:
        print("🔎 Buscando runs recientes...")
        recent_runs = find_recent_runs()
        if recent_runs:
            run_id = recent_runs[-1]  # Más reciente
            print(f"📋 Usando run más reciente: {run_id[:12]}...")
        else:
            print("❌ No se encontraron runs en los logs")
            return
    
    # Extraer información
    extract_ui_events(run_id)
    extract_backend_process(run_id)
    extract_logic_book_tracking(run_id)
    show_summary(run_id)
    
    print(f"\n💡 COMANDOS ÚTILES PARA ESTE RUN:")
    print(f"   grep '{run_id[:12]}' logs/**/*.log")
    print(f"   grep 'LB-CAP:' logs/**/*.log | grep '{run_id[:12]}'")

if __name__ == "__main__":
    main()