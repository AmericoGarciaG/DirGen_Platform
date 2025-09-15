import typer
from pathlib import Path
import requests
import logging

# Configuración del logger para el cliente
logging.basicConfig(level=logging.INFO, format='CLIENT - %(message)s')
logger = logging.getLogger("DIRGEN_CLI")

app = typer.Typer()

@app.command()
def execute(
    pcce_path: Path = typer.Argument(..., help="Ruta al archivo PCCE."),
    host: str = typer.Option("http://127.0.0.1:8000", help="URL del MCP Host.")
):
    """
    Envía un PCCE al MCP Host para iniciar una nueva ejecución de DirGen.
    """
    if not pcce_path.is_file():
        logger.error(f"Error: El archivo '{pcce_path}' no fue encontrado.")
        raise typer.Exit(code=1)

    url = f"{host}/v1/run"
    logger.info(f"Enviando '{pcce_path.name}' a {url}...")

    try:
        with open(pcce_path, 'rb') as f:
            files = {'pcce_file': (pcce_path.name, f, 'application/x-yaml')}
            # --- MODIFICADO: Aumentamos timeout ya que el servidor ahora espera al modelo ---
            response = requests.post(url, files=files, timeout=120) 
        
        response.raise_for_status()
        response_data = response.json()
        
        logger.info("✅ Petición de inicio exitosa!")
        logger.info(f"   Run ID: {response_data.get('run_id')}")
        logger.info(f"   Mensaje: {response_data.get('message')}")
        logger.info(f"\nUsa 'python client/cli.py stop {response_data.get('run_id')}' para detener la ejecución.")

    except requests.exceptions.Timeout:
        logger.error("❌ Error: La petición excedió el tiempo de espera. El MCP Host tardó demasiado en responder.")
        logger.error("   Esto puede ocurrir si el modelo Docker tarda mucho en iniciar. Inténtalo de nuevo.")
        raise typer.Exit(code=1)
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Error de conexión al MCP Host: {e}")
        logger.error(f"   Detalle: {e.response.text if e.response else 'Sin respuesta del servidor.'}")
        raise typer.Exit(code=1)

@app.command()
def stop(
    run_id: str = typer.Argument(..., help="El ID de la ejecución a detener."),
    host: str = typer.Option("http://12-7.0.0.1:8000", help="URL del MCP Host.")
):
    """
    Envía una petición para detener todos los procesos asociados a una ejecución.
    """
    url = f"{host}/v1/run/{run_id}/stop"
    logger.info(f"Enviando petición de detención para '{run_id}' a {url}...")

    try:
        response = requests.post(url, timeout=10)
        response.raise_for_status()
        response_data = response.json()
        
        logger.info("✅ Petición de detención exitosa!")
        logger.info(f"   Mensaje: {response_data.get('message')}")

    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Error de conexión al MCP Host: {e}")
        logger.error(f"   Detalle: {e.response.text if e.response else 'Sin respuesta'}")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()