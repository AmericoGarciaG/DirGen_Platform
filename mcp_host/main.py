import asyncio
import json
import logging
import os
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime
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
    summary = data.get("summary")  # Nuevo campo para el resumen ejecutivo
    
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
        elif task_status == "failed":
            # Auto-verificación falló
            reason = data.get("reason", "Auto-verificación falló")
            logger.warning(f"Planner verification failed for {run_id}: {reason}")
            
            await manager.broadcast(run_id, {
                "source": "Orchestrator", 
                "type": "phase_end", 
                "data": {
                    "name": "Diseño", 
                    "status": "RECHAZADO", 
                    "reason": f"Verificación falló: {reason}"
                }
            })
        elif task_status == "incomplete":
            # Tarea incompleta - mantener lógica existente de reintentos
            reason = data.get("reason", "Tarea incompleta")
            logger.warning(f"Planner task incomplete for {run_id}: {reason}")
            
            # Tratar como fallo de validación para activar reintentos
            await handle_validation_failure(run_id, reason)
        else:
            # Tarea completada exitosamente 
            if summary:
                # Mostrar resumen ejecutivo de forma destacada
                await manager.broadcast(run_id, {
                    "source": "Orchestrator", 
                    "type": "executive_summary", 
                    "data": {
                        "summary": summary,
                        "agent_role": "planner"
                    }
                })
                logger.info(f"Executive summary sent to TUI for {run_id}")
            
            # Proceder con validación como siempre
            await manager.broadcast(run_id, {"source": "Orchestrator", "type": "info", "data": {"message": "Agente Planificador ha finalizado exitosamente. Iniciando Quality Gate 1."}})
            
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

# --- Endpoints de Gestión de Modelos Locales ---
@app.get("/v1/models/status")
async def get_models_status():
    """Obtiene el estado de todos los modelos locales"""
    try:
        # Importar el gestor de modelos
        sys.path.append(str(PROJECT_ROOT / "agents" / "planner"))
        from local_model_manager import get_model_manager
        
        manager = get_model_manager()
        stats = manager.get_model_stats()
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo estado de modelos: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/v1/models/{model_id}/ensure")
async def ensure_model_running(model_id: str):
    """Asegura que un modelo específico esté ejecutándose"""
    try:
        sys.path.append(str(PROJECT_ROOT / "agents" / "planner"))
        from local_model_manager import ensure_model_available
        
        success = ensure_model_available(model_id)
        
        return {
            "success": success,
            "model_id": model_id,
            "message": f"Modelo {'disponible' if success else 'falló al iniciar'}",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error asegurando modelo {model_id}: {e}")
        return {
            "success": False,
            "model_id": model_id,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/v1/models/cleanup")
async def cleanup_idle_models():
    """Fuerza limpieza de modelos inactivos"""
    try:
        sys.path.append(str(PROJECT_ROOT / "agents" / "planner"))
        from local_model_manager import get_model_manager
        
        manager = get_model_manager()
        # Forzar limpieza inmediata
        manager._cleanup_idle_models()
        
        return {
            "success": True,
            "message": "Limpieza de modelos ejecutada",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error en limpieza de modelos: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/v1/agent/{run_id}/report")
async def report_agent_progress(run_id: str, request: Request):
    progress_data = await request.json()
    
    # Retransmitir todos los mensajes, incluidos los de planificación
    message_type = progress_data.get("type")
    
    if message_type in ["plan_generated", "plan_updated"]:
        # Mensajes de planificación: retransmitir directamente al TUI
        logger.info(f"Retransmitiendo mensaje de planificación: {message_type}")
        await manager.broadcast(run_id, progress_data)
    else:
        # Otros mensajes: retransmisión normal
        await manager.broadcast(run_id, progress_data)
    
    return {"status": "reported"}
