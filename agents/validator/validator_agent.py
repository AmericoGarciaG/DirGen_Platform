import argparse
import json
import logging
import os
from pathlib import Path

import requests
import yaml

logging.basicConfig(level=logging.INFO, format='%(asctime)s - AGENT(Validator) - %(message)s')
logger = logging.getLogger("VALIDATOR_AGENT")
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
    else:
        resultado = {"success": False, "message": f"Faltan los siguientes artefactos: {', '.join(archivos_faltantes)}"}

    requests.post(f"{HOST}/v1/agent/{args.run_id}/validation_result", json=resultado)
    logger.info(f"Resultado de la validación enviado al Orquestador: {'Éxito' if resultado['success'] else 'Fallo'}")

if __name__ == "__main__":
    main()