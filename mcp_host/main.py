import asyncio
import json
import logging
import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

import uvicorn
import yaml
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, WebSocket, WebSocketDisconnect
from websockets.exceptions import ConnectionClosed

# --- Configuración y Estado ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ORCHESTRATOR")
app = FastAPI(title="DirGen Orchestrator")
ACTIVE_PROCESSES = {}
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Estados de reintento por run_id
RETRY_STATES = {}
MAX_RETRIES = 3

# --- Gestor de Conexiones WebSocket ---
class ConnectionManager:
    def __init__(self): self.active_connections: dict[str, WebSocket] = {}
    async def connect(self, run_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[run_id] = websocket
    def disconnect(self, run_id: str):
        if run_id in self.active_connections: del self.active_connections[run_id]
    async def broadcast(self, run_id: str, message_data: dict):
        if run_id in self.active_connections:
            try: await self.active_connections[run_id].send_text(json.dumps(message_data))
            except (ConnectionClosed, WebSocketDisconnect): self.disconnect(run_id)

manager = ConnectionManager()

# --- Lógica de Orquestación de Fases ---
async def run_phase_1_design(run_id: str, pcce_content: bytes, feedback: str = None):
    await manager.broadcast(run_id, {"source": "Orchestrator", "type": "phase_start", "data": {"name": "Diseño"}})
    
    temp_dir = tempfile.gettempdir()
    temp_pcce_path = os.path.join(temp_dir, f"{run_id}_pcce.yml")
    with open(temp_pcce_path, "wb") as f: f.write(pcce_content)

    agent_script_path = PROJECT_ROOT / "agents" / "planner" / "planner_agent.py"
    agent_command = [sys.executable, str(agent_script_path), "--run-id", run_id, "--pcce-path", temp_pcce_path]
    
    # Agregar feedback si está presente
    if feedback:
        agent_command.extend(["--feedback", feedback])
        await manager.broadcast(run_id, {"source": "Orchestrator", "type": "info", "data": {"message": f"Reinvocando Agente Planificador con feedback: {feedback[:100]}..."}})
    
    process = subprocess.Popen(agent_command)
    ACTIVE_PROCESSES[f"{run_id}_planner"] = process
    await manager.broadcast(run_id, {"source": "Orchestrator", "type": "info", "data": {"message": f"Agente Planificador invocado (PID: {process.pid})..."}})

async def run_quality_gate_1(run_id: str, pcce_content: bytes):
    await manager.broadcast(run_id, {"source": "Orchestrator", "type": "quality_gate_start", "data": {"name": "Validación de Diseño"}})

    temp_dir = tempfile.gettempdir()
    temp_pcce_path = os.path.join(temp_dir, f"{run_id}_pcce.yml")
    with open(temp_pcce_path, "wb") as f: f.write(pcce_content)

    agent_script_path = PROJECT_ROOT / "agents" / "validator" / "validator_agent.py"
    agent_command = [sys.executable, str(agent_script_path), "--run-id", run_id, "--pcce-path", temp_pcce_path]

    process = subprocess.Popen(agent_command)
    ACTIVE_PROCESSES[f"{run_id}_validator"] = process
    await manager.broadcast(run_id, {"source": "Orchestrator", "type": "info", "data": {"message": f"Agente Validador invocado (PID: {process.pid})..."}})

# --- Endpoints ---
@app.post("/v1/start_run")
async def start_run(pcce_file: UploadFile = File(...)):
    run_id = f"run-{uuid.uuid4()}"
    pcce_content = await pcce_file.read()
    
    # Iniciar Fase 1 asíncronamente para no bloquear la respuesta HTTP
    asyncio.create_task(run_phase_1_design(run_id, pcce_content))
    
    return {"message": "Ejecución DirGen iniciada.", "run_id": run_id}

@app.post("/v1/agent/{run_id}/task_complete")
async def agent_task_complete(run_id: str, request: Request):
    data = await request.json()
    agent_role = data.get("role")
    task_status = data.get("status", "success")
    
    if agent_role == "planner":
        if task_status == "impossible":
            # El agente declaró la tarea como imposible
            reason = data.get("reason", "El agente determinó que la tarea no es posible de completar")
            logger.warning(f"Planner declared task impossible for {run_id}: {reason}")
            
            # Limpiar estado de reintentos
            if run_id in RETRY_STATES:
                del RETRY_STATES[run_id]
            
            await manager.broadcast(run_id, {
                "source": "Orchestrator", 
                "type": "phase_end", 
                "data": {
                    "name": "Diseño", 
                    "status": "RECHAZADO", 
                    "reason": f"Agente declaró tarea imposible: {reason}"
                }
            })
        else:
            # Tarea completada normalmente - proceder con validación
            await manager.broadcast(run_id, {"source": "Orchestrator", "type": "info", "data": {"message": "Agente Planificador ha finalizado. Iniciando Quality Gate 1."}})
            
            # Necesitamos el contenido del PCCE de nuevo para el Validador
            temp_dir = tempfile.gettempdir()
            temp_pcce_path = os.path.join(temp_dir, f"{run_id}_pcce.yml")
            with open(temp_pcce_path, "rb") as f: pcce_content = f.read()

            asyncio.create_task(run_quality_gate_1(run_id, pcce_content))

    return {"status": "acknowledged"}

@app.post("/v1/agent/{run_id}/validation_result")
async def validation_result(run_id: str, request: Request):
    result = await request.json()
    await manager.broadcast(run_id, {"source": "Orchestrator", "type": "quality_gate_result", "data": result})
    
    if result.get("success"):
        # Validación exitosa - limpiar estado de reintentos y aprobar fase
        if run_id in RETRY_STATES:
            del RETRY_STATES[run_id]
        await manager.broadcast(run_id, {"source": "Orchestrator", "type": "phase_end", "data": {"name": "Diseño", "status": "APROBADO"}})
    else:
        # Validación fallida - implementar lógica de reintentos
        await handle_validation_failure(run_id, result.get("message", "Error desconocido"))
    
    return {"status": "processed"}

async def handle_validation_failure(run_id: str, error_message: str):
    """Maneja fallos de validación con lógica de reintentos inteligente"""
    # Inicializar estado de reintentos si no existe
    if run_id not in RETRY_STATES:
        RETRY_STATES[run_id] = {
            "retry_count": 0,
            "feedback_history": []
        }
    
    retry_state = RETRY_STATES[run_id]
    retry_state["retry_count"] += 1
    retry_state["feedback_history"].append(error_message)
    
    logger.info(f"Validation failed for {run_id}. Attempt {retry_state['retry_count']}/{MAX_RETRIES}")
    
    if retry_state["retry_count"] <= MAX_RETRIES:
        # Construir feedback enriquecido
        feedback = f"Intento {retry_state['retry_count']}/{MAX_RETRIES}. Error: {error_message}"
        
        # Agregar contexto de intentos anteriores si existe
        if len(retry_state["feedback_history"]) > 1:
            prev_errors = "; ".join(retry_state["feedback_history"][:-1])
            feedback += f" Errores anteriores: {prev_errors}"
        
        await manager.broadcast(run_id, {
            "source": "Orchestrator", 
            "type": "retry_attempt", 
            "data": {
                "attempt": retry_state["retry_count"],
                "max_attempts": MAX_RETRIES,
                "feedback": feedback
            }
        })
        
        # Re-invocar al planner con feedback
        temp_dir = tempfile.gettempdir()
        temp_pcce_path = os.path.join(temp_dir, f"{run_id}_pcce.yml")
        
        if os.path.exists(temp_pcce_path):
            with open(temp_pcce_path, "rb") as f:
                pcce_content = f.read()
            asyncio.create_task(run_phase_1_design(run_id, pcce_content, feedback))
        else:
            logger.error(f"No se pudo encontrar el archivo PCCE para {run_id}")
            await manager.broadcast(run_id, {
                "source": "Orchestrator", 
                "type": "phase_end", 
                "data": {"name": "Diseño", "status": "RECHAZADO", "reason": "Archivo PCCE no encontrado"}
            })
    else:
        # Se agotaron los reintentos
        logger.warning(f"Maximum retries exceeded for {run_id}")
        del RETRY_STATES[run_id]
        await manager.broadcast(run_id, {
            "source": "Orchestrator", 
            "type": "phase_end", 
            "data": {
                "name": "Diseño", 
                "status": "RECHAZADO", 
                "reason": f"Se agotaron los {MAX_RETRIES} reintentos. Último error: {error_message}"
            }
        })

@app.websocket("/ws/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str):
    await manager.connect(run_id, websocket)
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect: manager.disconnect(run_id)

# --- Toolbelt (solo lo que el planner necesita por ahora) ---
@app.post("/v1/tools/filesystem/writeFile")
async def tool_write_file(request: Request):
    data = await request.json()
    path_str = data.get("path")
    content = data.get("content")
    
    try:
        # Asegurarse de que el directorio exista
        full_path = PROJECT_ROOT / path_str
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/v1/agent/{run_id}/report")
async def report_agent_progress(run_id: str, request: Request):
    progress_data = await request.json()
    await manager.broadcast(run_id, progress_data)
    return {"status": "reported"}