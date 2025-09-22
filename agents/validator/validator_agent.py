import argparse
import json
import logging
import os
from pathlib import Path

import requests
import yaml

# Intentar usar logging centralizado, fallback a configuración básica
try:
    import sys
    project_root = Path(__file__).parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    from dirgen_core.logging_config import get_agent_logger, LogicBookLogger, LogLevel
    logger = get_agent_logger("validator", LogLevel.DEBUG)
    logic_logger = LogicBookLogger()
except ImportError:
    # Fallback a configuración básica
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - AGENT(Validator) - %(message)s')
    logger = logging.getLogger("VALIDATOR_AGENT")
    logic_logger = None
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HOST = "http://127.0.0.1:8000"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--pcce-path", required=True)
    args = parser.parse_args()

    with open(args.pcce_path, 'r') as f:
        pcce_data = yaml.safe_load(f)

    salidas_esperadas = pcce_data.get('fases', {}).get('diseno', {}).get('salidas_esperadas', [])
    archivos_faltantes = []
    
    logger.info("Iniciando validación de artefactos de diseño...")
    
    # Log inicio de quality gate según Logic Book
    if logic_logger:
        logic_logger.log_quality_gate(
            logger, args.run_id, "DESIGN_ARTIFACTS_VALIDATION", "STARTED",
            f"Validando {len(salidas_esperadas)} artefactos de diseño"
        )
    for archivo in salidas_esperadas:
        ruta_completa = PROJECT_ROOT / archivo
        if not ruta_completa.exists():
            archivos_faltantes.append(archivo)
            logger.error(f"Artefacto FALTANTE: {archivo}")
        else:
            logger.info(f"Artefacto ENCONTRADO: {archivo}")

    # Reportar resultado al Orquestador
    if not archivos_faltantes:
        resultado = {"success": True, "message": "Todos los artefactos de diseño fueron generados."}
        # Log quality gate exitoso según Logic Book
        if logic_logger:
            logic_logger.log_quality_gate(
                logger, args.run_id, "DESIGN_ARTIFACTS_VALIDATION", "PASSED",
                f"Todos los {len(salidas_esperadas)} artefactos validados exitosamente"
            )
    else:
        resultado = {"success": False, "message": f"Faltan los siguientes artefactos: {', '.join(archivos_faltantes)}"}
        # Log quality gate fallido según Logic Book
        if logic_logger:
            logic_logger.log_quality_gate(
                logger, args.run_id, "DESIGN_ARTIFACTS_VALIDATION", "FAILED",
                f"Faltan {len(archivos_faltantes)} artefactos: {', '.join(archivos_faltantes)}"
            )

    requests.post(f"{HOST}/v1/agent/{args.run_id}/validation_result", json=resultado)
    logger.info(f"Resultado de la validación enviado al Orquestador: {'Éxito' if resultado['success'] else 'Fallo'}")
    
    # Log completación del agente según Logic Book
    if logic_logger:
        status = "COMPLETED" if resultado['success'] else "FAILED"
        logic_logger.log_agent_action(
            logger, args.run_id, "Validator", f"VALIDATION_{status}",
            {'artifacts_checked': len(salidas_esperadas), 'artifacts_missing': len(archivos_faltantes), 'chapter': 'CAP-4'}
        )

if __name__ == "__main__":
    main()