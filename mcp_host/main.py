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
from fastapi.middleware.cors import CORSMiddleware
from websockets.exceptions import ConnectionClosed

# --- Configuración y Estado ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ORCHESTRATOR")
app = FastAPI(title="DirGen Orchestrator")

# Configurar CORS para permitir peticiones desde Tauri
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar orígenes específicos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ACTIVE_PROCESSES = {}
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Estados de reintento por run_id
RETRY_STATES = {}
MAX_RETRIES = 3

# Estados de aprobación por run_id
APPROVAL_STATES = {}
# Estados posibles: "waiting_approval", "approved", "rejected"

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
    
    # CORREGIDO: usar ubicación relativa del proyecto para el PCCE
    pcce_relative_path = f"temp/{run_id}_pcce.yml"
    pcce_full_path = PROJECT_ROOT / pcce_relative_path
    
    # El archivo PCCE ya debería existir desde RequirementsAgent
    # Si no existe, crearlo a partir del contenido proporcionado
    if not pcce_full_path.exists():
        pcce_full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(pcce_full_path, "wb") as f: f.write(pcce_content)
        logger.info(f"PCCE creado en {pcce_relative_path} para el Planner Agent")

    agent_script_path = PROJECT_ROOT / "agents" / "planner" / "planner_agent.py"
    agent_command = [sys.executable, str(agent_script_path), "--run-id", run_id, "--pcce-path", str(pcce_full_path)]
    
    # Agregar feedback si está presente
    if feedback:
        agent_command.extend(["--feedback", feedback])
        await manager.broadcast(run_id, {"source": "Orchestrator", "type": "info", "data": {"message": f"Reinvocando Agente Planificador con feedback: {feedback[:100]}..."}})
    
    process = subprocess.Popen(agent_command)
    ACTIVE_PROCESSES[f"{run_id}_planner"] = process
    await manager.broadcast(run_id, {"source": "Orchestrator", "type": "info", "data": {"message": f"Agente Planificador invocado (PID: {process.pid})..."}})

async def run_quality_gate_1(run_id: str, pcce_content: bytes):
    await manager.broadcast(run_id, {"source": "Orchestrator", "type": "quality_gate_start", "data": {"name": "Validación de Diseño"}})

    # CORREGIDO: usar ubicación relativa del proyecto para el PCCE
    pcce_relative_path = f"temp/{run_id}_pcce.yml"
    pcce_full_path = PROJECT_ROOT / pcce_relative_path
    
    # El archivo PCCE ya debería existir desde fases anteriores
    # Si no existe, crearlo a partir del contenido proporcionado
    if not pcce_full_path.exists():
        pcce_full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(pcce_full_path, "wb") as f: f.write(pcce_content)
        logger.info(f"PCCE creado en {pcce_relative_path} para el Validator Agent")

    agent_script_path = PROJECT_ROOT / "agents" / "validator" / "validator_agent.py"
    agent_command = [sys.executable, str(agent_script_path), "--run-id", run_id, "--pcce-path", str(pcce_full_path)]

    process = subprocess.Popen(agent_command)
    ACTIVE_PROCESSES[f"{run_id}_validator"] = process
    await manager.broadcast(run_id, {"source": "Orchestrator", "type": "info", "data": {"message": f"Agente Validador invocado (PID: {process.pid})..."}})

# --- Lógica de Fase 0: Análisis de Requerimientos ---
async def run_phase_0_requirements(run_id: str, svad_content: bytes):
    """Ejecuta la Fase 0: Análisis de Requerimientos"""
    await manager.broadcast(run_id, {
        "source": "Orchestrator", 
        "type": "phase_start", 
        "data": {"name": "Análisis de Requerimientos"}
    })
    
    # Guardar el archivo SVAD en un directorio temporal
    temp_dir = tempfile.gettempdir()
    temp_svad_path = os.path.join(temp_dir, f"{run_id}_svad.md")
    with open(temp_svad_path, "wb") as f:
        f.write(svad_content)
    
    # Invocar el RequirementsAgent
    agent_script_path = PROJECT_ROOT / "agents" / "requirements" / "requirements_agent.py"
    agent_command = [sys.executable, str(agent_script_path), "--run-id", run_id, "--svad-path", temp_svad_path]
    
    process = subprocess.Popen(agent_command)
    ACTIVE_PROCESSES[f"{run_id}_requirements"] = process
    await manager.broadcast(run_id, {
        "source": "Orchestrator", 
        "type": "info", 
        "data": {"message": f"RequirementsAgent invocado (PID: {process.pid})..."}
    })

# --- Endpoints ---
@app.get("/health")
async def health_check():
    """Endpoint de salud para verificar que el servidor está funcionando"""
    return {"status": "healthy", "message": "DirGen Orchestrator is running"}

@app.post("/v1/initiate_from_svad")
async def initiate_from_svad(svad_file: UploadFile = File(...)):
    """Inicia la plataforma DirGen desde un documento SVAD - Fase 0"""
    run_id = f"run-{uuid.uuid4()}"
    svad_content = await svad_file.read()
    
    logger.info(f"Iniciando Fase 0 (Análisis de Requerimientos) para {run_id}")
    
    # Iniciar Fase 0 asíncronamente
    asyncio.create_task(run_phase_0_requirements(run_id, svad_content))
    
    return {"message": "Fase 0: Análisis de Requerimientos iniciada.", "run_id": run_id}

@app.post("/v1/start_run")
async def start_run(pcce_file: UploadFile = File(...)):
    """Legacy endpoint: Inicia directamente desde PCCE - Fase 1"""
    run_id = f"run-{uuid.uuid4()}"
    pcce_content = await pcce_file.read()
    
    # Iniciar Fase 1 asíncronamente para no bloquear la respuesta HTTP
    asyncio.create_task(run_phase_1_design(run_id, pcce_content))
    
    return {"message": "Ejecución DirGen iniciada (modo legacy).", "run_id": run_id}

@app.post("/v1/agent/{run_id}/task_complete")
async def agent_task_complete(run_id: str, request: Request):
    data = await request.json()
    agent_role = data.get("role")
    task_status = data.get("status", "success")
    summary = data.get("summary")  # Nuevo campo para el resumen ejecutivo
    
    # --- FASE 0: REQUIREMENTS AGENT ---
    if agent_role == "requirements":
        if task_status == "failed":
            # Validación del SVAD falló
            reason = data.get("reason", "Validación del documento SVAD falló")
            logger.warning(f"RequirementsAgent validation failed for {run_id}: {reason}")
            
            await manager.broadcast(run_id, {
                "source": "Orchestrator", 
                "type": "phase_end", 
                "data": {
                    "name": "Análisis de Requerimientos", 
                    "status": "RECHAZADO", 
                    "reason": f"SVAD inválido: {reason}"
                }
            })
        else:
            # Fase 0 completada exitosamente - ESPERAR APROBACIÓN
            logger.info(f"RequirementsAgent completed successfully for {run_id}. WAITING FOR USER APPROVAL before starting Phase 1.")
            
            if summary:
                await manager.broadcast(run_id, {
                    "source": "Orchestrator", 
                    "type": "executive_summary", 
                    "data": {
                        "summary": summary,
                        "agent_role": "requirements"
                    }
                })
            
            await manager.broadcast(run_id, {
                "source": "Orchestrator", 
                "type": "phase_end", 
                "data": {
                    "name": "Análisis de Requerimientos", 
                    "status": "APROBADO", 
                    "reason": "SVAD validado y PCCE generado exitosamente"
                }
            })
            
            # CRÍTICO: Establecer estado de espera de aprobación para INICIAR FASE 1 (Diseño)
            APPROVAL_STATES[run_id] = "waiting_design_phase_approval"
            
            # Enviar mensaje para solicitar aprobación de INICIAR Fase de Diseño
            await manager.broadcast(run_id, {
                "source": "Orchestrator", 
                "type": "design_phase_approval_request", 
                "run_id": run_id,
                "data": {
                    "message": "PCCE generado exitosamente a partir del SVAD. ¿Deseas iniciar la Fase de Diseño para construir el proyecto?",
                    "phase_completed": "requirements",
                    "phase_requested": "design",
                    "status": "awaiting_approval",
                    "next_action": "start_design_phase"
                }
            })
            
            logger.info(f"Requirements Phase 0 complete. Design phase approval request sent for {run_id}. Waiting for user response to start Phase 1.")
    
    # --- FASE 1: PLANNER AGENT ---
    elif agent_role == "planner":
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
            # Tarea completada exitosamente - NUEVO FLUJO CON APROBACIÓN
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
            
            # Planner Agent completado - ESTE ES EL VERDADERO PLAN DE EJECUCIÓN
            logger.info(f"Planner completed successfully for {run_id}. Execution plan generated. Waiting for user approval.")
            
            # Establecer estado de espera de aprobación para EJECUTAR el plan
            APPROVAL_STATES[run_id] = "waiting_execution_approval"
            
            # Enviar mensaje de plan de ejecución generado para solicitar aprobación
            await manager.broadcast(run_id, {
                "source": "Orchestrator", 
                "type": "plan_generated", 
                "run_id": run_id,
                "data": {
                    "message": "Plan de ejecución detallado generado exitosamente. ¿Deseas proceder con la ejecución del plan?",
                    "phase_completed": "design_planning",
                    "phase_requested": "execution",
                    "tasks": data.get("tasks", []),  # Si el agente envía las tareas
                    "status": "awaiting_approval",
                    "next_action": "execute_plan"
                }
            })
            
            logger.info(f"Execution plan approval request sent for {run_id}. Waiting for user response.")

    return {"status": "acknowledged"}

@app.post("/v1/agent/{run_id}/validation_result")
async def validation_result(run_id: str, request: Request):
    result = await request.json()
    await manager.broadcast(run_id, {"source": "Orchestrator", "type": "quality_gate_result", "data": result})
    
    if result.get("success"):
        # Validación exitosa - limpiar estado de reintentos y aprobar fase
        if run_id in RETRY_STATES:
            del RETRY_STATES[run_id]
        await manager.broadcast(run_id, {
            "source": "Orchestrator", 
            "type": "phase_end", 
            "data": {"name": "Diseño", "status": "APROBADO"}
        })
    else:
        # Validación fallida - implementar lógica de reintentos
        await handle_validation_failure(run_id, result.get("message", "Error desconocido"))
    
    return {"status": "processed"}

@app.post("/v1/run/{run_id}/approve_plan")
async def approve_plan(run_id: str, request: Request):
    """Endpoint para aprobar o rechazar un plan generado por el Planner"""
    try:
        data = await request.json()
        approved = data.get("approved", False)
        user_response = data.get("user_response", "")
        
        logger.info(f"Plan approval request for {run_id}: approved={approved}, response='{user_response}'")
        
        # Verificar que el run esté en estado de espera de aprobación
        current_approval_state = APPROVAL_STATES.get(run_id, 'none')
        if run_id not in APPROVAL_STATES or current_approval_state not in ["waiting_design_phase_approval", "waiting_execution_approval"]:
            logger.warning(f"Run {run_id} is not waiting for approval. Current state: {current_approval_state}")
            raise HTTPException(
                status_code=400, 
                detail=f"Run {run_id} is not waiting for approval. Current state: {current_approval_state}"
            )
        
        if approved:
            # Determinar qué acción tomar según el estado de aprobación actual
            logger.info(f"Approval received for {run_id} in state {current_approval_state}")
            
            # Leer el PCCE (CORREGIDO: usar ruta relativa del proyecto)
            pcce_relative_path = f"temp/{run_id}_pcce.yml"
            pcce_full_path = PROJECT_ROOT / pcce_relative_path
            
            if not pcce_full_path.exists():
                logger.error(f"PCCE file not found for {run_id} at {pcce_relative_path}")
                await manager.broadcast(run_id, {
                    "source": "Orchestrator",
                    "type": "phase_end",
                    "data": {
                        "name": "Aprobación",
                        "status": "RECHAZADO",
                        "reason": f"Archivo PCCE no encontrado en {pcce_relative_path}"
                    }
                })
                return {"status": "error", "message": "PCCE file not found", "run_id": run_id}
                
            with open(pcce_full_path, "rb") as f:
                pcce_content = f.read()
            
            # CASO 1: Aprobación para INICIAR Fase de Diseño
            if current_approval_state == "waiting_design_phase_approval":
                logger.info(f"Starting Phase 1: Design Planning for {run_id} (user approved design phase)")
                
                # Actualizar estado
                APPROVAL_STATES[run_id] = "design_approved"
                
                # Notificar aprobación
                await manager.broadcast(run_id, {
                    "source": "Orchestrator",
                    "type": "plan_approved",
                    "run_id": run_id,
                    "data": {
                        "message": f"Fase de Diseño aprobada por el usuario. Iniciando planificación detallada...",
                        "user_response": user_response,
                        "phase_approved": "design",
                        "timestamp": datetime.now().isoformat()
                    }
                })
                
                # Iniciar Fase 1: Diseño con PlannerAgent
                await manager.broadcast(run_id, {
                    "source": "Orchestrator", 
                    "type": "info", 
                    "data": {"message": "Iniciando Fase 1: Planificación detallada con el PCCE generado..."}
                })
                asyncio.create_task(run_phase_1_design(run_id, pcce_content))
                
                return {
                    "status": "approved",
                    "message": "Design phase approved, starting Phase 1 planning",
                    "run_id": run_id
                }
            
            # CASO 2: Aprobación para EJECUTAR el Plan
            elif current_approval_state == "waiting_execution_approval":
                logger.info(f"Starting execution for {run_id} (user approved execution plan)")
                
                # Actualizar estado
                APPROVAL_STATES[run_id] = "execution_approved"
                
                # Notificar aprobación
                await manager.broadcast(run_id, {
                    "source": "Orchestrator",
                    "type": "plan_approved",
                    "run_id": run_id,
                    "data": {
                        "message": f"Plan de ejecución aprobado por el usuario. Iniciando validación...",
                        "user_response": user_response,
                        "phase_approved": "execution",
                        "timestamp": datetime.now().isoformat()
                    }
                })
                
                # Iniciar Quality Gate 1 (validación)
                await manager.broadcast(run_id, {
                    "source": "Orchestrator", 
                    "type": "info", 
                    "data": {"message": "Plan de ejecución aprobado. Iniciando Quality Gate 1 (Validación)..."}
                })
                asyncio.create_task(run_quality_gate_1(run_id, pcce_content))
                
                return {
                    "status": "approved",
                    "message": "Execution plan approved, starting validation",
                    "run_id": run_id
                }
            
            else:
                logger.error(f"Unknown approval state for {run_id}: {current_approval_state}")
                return {
                    "status": "error",
                    "message": f"Unknown approval state: {current_approval_state}",
                    "run_id": run_id
                }
            
        else:
            # Plan/Fase rechazado
            logger.info(f"Rejection received for {run_id} in state {current_approval_state}. User response: '{user_response}'")
            
            # Actualizar estado
            APPROVAL_STATES[run_id] = "rejected"
            
            # Determinar qué se rechazó según el estado
            if current_approval_state == "waiting_design_phase_approval":
                phase_name = "Fase de Diseño"
                rejection_message = f"Fase de Diseño rechazada por el usuario: {user_response}"
            elif current_approval_state == "waiting_execution_approval":
                phase_name = "Plan de Ejecución"
                rejection_message = f"Plan de ejecución rechazado por el usuario: {user_response}"
            else:
                phase_name = "Proceso"
                rejection_message = f"Proceso rechazado por el usuario: {user_response}"
            
            # Notificar rechazo
            await manager.broadcast(run_id, {
                "source": "Orchestrator",
                "type": "plan_rejected",
                "run_id": run_id,
                "data": {
                    "message": rejection_message,
                    "user_response": user_response,
                    "phase_rejected": current_approval_state.replace("waiting_", "").replace("_approval", ""),
                    "timestamp": datetime.now().isoformat()
                }
            })
            
            # Terminar la fase como rechazada
            await manager.broadcast(run_id, {
                "source": "Orchestrator",
                "type": "phase_end",
                "data": {
                    "name": phase_name,
                    "status": "RECHAZADO",
                    "reason": rejection_message
                }
            })
            
            # Limpiar estados
            if run_id in APPROVAL_STATES:
                del APPROVAL_STATES[run_id]
            
            return {
                "status": "rejected",
                "message": f"{phase_name} rejected by user",
                "run_id": run_id
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing plan approval for {run_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

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
        
        # Re-invocar al planner con feedback (CORREGIDO: usar ubicación relativa del proyecto)
        pcce_relative_path = f"temp/{run_id}_pcce.yml"
        pcce_full_path = PROJECT_ROOT / pcce_relative_path
        
        if pcce_full_path.exists():
            with open(pcce_full_path, "rb") as f:
                pcce_content = f.read()
            asyncio.create_task(run_phase_1_design(run_id, pcce_content, feedback))
        else:
            logger.error(f"No se pudo encontrar el archivo PCCE para {run_id} en {pcce_relative_path}")
            await manager.broadcast(run_id, {
                "source": "Orchestrator", 
                "type": "phase_end", 
                "data": {"name": "Diseño", "status": "RECHAZADO", "reason": f"Archivo PCCE no encontrado en {pcce_relative_path}"}
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

# --- Toolbelt - Herramientas de Sistema de Archivos (Conformidad Logic Book Capítulo 2.2) ---
@app.post("/v1/tools/filesystem/writeFile")
async def tool_write_file(request: Request):
    """Capítulo 2.2.1: Herramienta writeFile - Escribe contenido en un archivo"""
    data = await request.json()
    path_str = data.get("path")
    content = data.get("content")
    
    # Validación de seguridad según Capítulo 2.1: Principio de Sandboxing
    if not path_str or ".." in path_str or os.path.isabs(path_str):
        return {"success": False, "error": "Ruta inválida o insegura"}
    
    try:
        # Asegurar que la operación esté en el directorio del proyecto (sandboxing)
        full_path = PROJECT_ROOT / path_str
        
        # Verificar que la ruta final esté dentro del PROJECT_ROOT
        if not str(full_path.resolve()).startswith(str(PROJECT_ROOT.resolve())):
            return {"success": False, "error": "Ruta fuera del sandbox del proyecto"}
        
        # Crear directorios padre si no existen
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Escribir archivo
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        logger.info(f"Archivo escrito exitosamente: {path_str}")
        return {"success": True}
    except Exception as e:
        logger.error(f"Error escribiendo archivo {path_str}: {str(e)}")
        return {"success": False, "error": str(e)}

@app.post("/v1/tools/filesystem/readFile")
async def tool_read_file(request: Request):
    """Capítulo 2.2.2: Herramienta readFile - Lee contenido de un archivo"""
    data = await request.json()
    path_str = data.get("path")
    
    # Validación de seguridad según Capítulo 2.1: Principio de Sandboxing
    if not path_str or ".." in path_str or os.path.isabs(path_str):
        return {"success": False, "error": "Ruta inválida o insegura"}
    
    try:
        # Asegurar que la operación esté en el directorio del proyecto (sandboxing)
        full_path = PROJECT_ROOT / path_str
        
        # Verificar que la ruta final esté dentro del PROJECT_ROOT
        if not str(full_path.resolve()).startswith(str(PROJECT_ROOT.resolve())):
            return {"success": False, "error": "Ruta fuera del sandbox del proyecto"}
        
        # Verificar que el archivo exista
        if not full_path.exists():
            return {"success": False, "error": "Archivo no encontrado"}
        
        # Leer archivo
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        logger.info(f"Archivo leído exitosamente: {path_str} ({len(content)} caracteres)")
        return {"success": True, "content": content}
    except Exception as e:
        logger.error(f"Error leyendo archivo {path_str}: {str(e)}")
        return {"success": False, "error": str(e)}

@app.post("/v1/tools/filesystem/listFiles")
async def tool_list_files(request: Request):
    """Capítulo 2.2.3: Herramienta listFiles - Lista archivos y directorios"""
    data = await request.json()
    path_str = data.get("path", ".")  # Por defecto, directorio actual
    
    # Validación de seguridad según Capítulo 2.1: Principio de Sandboxing
    if ".." in path_str or os.path.isabs(path_str):
        return {"success": False, "error": "Ruta inválida o insegura"}
    
    try:
        # Asegurar que la operación esté en el directorio del proyecto (sandboxing)
        full_path = PROJECT_ROOT / path_str
        
        # Verificar que la ruta final esté dentro del PROJECT_ROOT
        if not str(full_path.resolve()).startswith(str(PROJECT_ROOT.resolve())):
            return {"success": False, "error": "Ruta fuera del sandbox del proyecto"}
        
        # Verificar que el directorio exista
        if not full_path.exists():
            return {"success": False, "error": "Directorio no encontrado"}
        
        if not full_path.is_dir():
            return {"success": False, "error": "La ruta especificada no es un directorio"}
        
        # Listar contenido del directorio
        files = []
        directories = []
        
        for item in full_path.iterdir():
            relative_path = str(item.relative_to(PROJECT_ROOT))
            if item.is_file():
                files.append(relative_path)
            elif item.is_dir():
                directories.append(relative_path)
        
        logger.info(f"Directorio listado: {path_str} ({len(files)} archivos, {len(directories)} directorios)")
        return {
            "success": True, 
            "files": sorted(files), 
            "directories": sorted(directories)
        }
    except Exception as e:
        logger.error(f"Error listando directorio {path_str}: {str(e)}")
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
    
    # VALIDACIÓN ESTRICTA DEL PROTOCOLO WEBSOCKET
    # Asegurar que el mensaje siga el esquema {"source": "...", "type": "...", "data": {...}}
    if not isinstance(progress_data, dict):
        logger.error(f"Mensaje inválido de agente para {run_id}: no es un diccionario")
        return {"status": "error", "message": "Mensaje debe ser un objeto JSON"}
    
    required_keys = ["source", "type", "data"]
    missing_keys = [key for key in required_keys if key not in progress_data]
    
    if missing_keys:
        logger.error(f"Mensaje inválido de agente para {run_id}: faltan claves {missing_keys}")
        return {"status": "error", "message": f"Mensaje debe incluir: {', '.join(required_keys)}"}
    
    # Validar que 'data' sea un diccionario
    if not isinstance(progress_data.get("data"), dict):
        logger.error(f"Mensaje inválido de agente para {run_id}: 'data' debe ser un objeto")
        return {"status": "error", "message": "Campo 'data' debe ser un objeto JSON"}
    
    # Validar 'source' y 'type' sean strings no vacíos
    if not isinstance(progress_data.get("source"), str) or not progress_data.get("source").strip():
        logger.error(f"Mensaje inválido de agente para {run_id}: 'source' debe ser string no vacío")
        return {"status": "error", "message": "Campo 'source' debe ser un string no vacío"}
    
    if not isinstance(progress_data.get("type"), str) or not progress_data.get("type").strip():
        logger.error(f"Mensaje inválido de agente para {run_id}: 'type' debe ser string no vacío")
        return {"status": "error", "message": "Campo 'type' debe ser un string no vacío"}
    
    # PROTOCOLO VALIDADO - Retransmitir mensaje
    message_type = progress_data.get("type")
    
    # Logging mejorado para debugging
    logger.info(f"Retransmitiendo mensaje válido [{progress_data.get('source')}:{message_type}] para {run_id}")
    
    # Retransmitir el mensaje validado
    await manager.broadcast(run_id, progress_data)
    
    return {"status": "reported"}
