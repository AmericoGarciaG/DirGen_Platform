import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Log
import websockets
import requests

# --- Configuración del Logger ---
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"tui_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Configurar el logger
logger = logging.getLogger("DirGenTUI")
logger.setLevel(logging.DEBUG)

# Handler para archivo - SOLO archivo, no consola para evitar doble salida en TUI
file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_format)
logger.addHandler(file_handler)

# NO agregar console handler - el TUI maneja la salida visual

# --- Utilidades de formateo ---
def format_content(content: str, max_width: int = 120) -> str:
    """Formatea el contenido de un mensaje para mejor legibilidad"""
    if not content or len(content) <= max_width:
        return content or ""
    
    # Dividir en líneas sin romper palabras
    lines = []
    current_line = ""
    
    for word in content.split():
        if len(current_line) + len(word) + 1 <= max_width:
            current_line += (" " if current_line else "") + word
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    
    if current_line:
        lines.append(current_line)
    
    # Indentar líneas adicionales para mejor legibilidad
    if len(lines) > 1:
        formatted_lines = [lines[0]]
        for line in lines[1:]:
            formatted_lines.append(f"  {line}")
        return "\n".join(formatted_lines)
    
    return content

# --- Componentes de la UI Profesional ---
def create_message_widget(message_data: dict) -> Static:
    """Crea un widget de mensaje con estilo profesional"""
    source = message_data.get("source", "System")
    msg_type = message_data.get("type")
    data = message_data.get("data", {})
    
    # Mapear tipos de mensaje a clases CSS y formato
    if source == "Orchestrator":
        if msg_type == "phase_start":
            text = f"🏭 INICIO DE FASE: {data.get('name', 'Desconocida')}"
            css_class = "phase-start"
        elif msg_type == "quality_gate_start":
            text = f"🔍 QUALITY GATE: {data.get('name', 'Validación')}"
            css_class = "quality-gate-start"
        elif msg_type == "quality_gate_result":
            message = format_content(data.get('message', ''), 100)
            if data.get("success"):
                text = f"✅ QUALITY GATE APROBADO\n{message}"
                css_class = "quality-gate-success"
            else:
                text = f"❌ QUALITY GATE RECHAZADO\n{message}"
                css_class = "quality-gate-error"
        elif msg_type == "retry_attempt":
            attempt = data.get('attempt', '?')
            max_attempts = data.get('max_attempts', '?')
            feedback = format_content(data.get('feedback', ''), 100)
            text = f"🔄 REINTENTO ({attempt}/{max_attempts})\n{feedback}"
            css_class = "retry-attempt"
        elif msg_type == "phase_end":
            status = data.get("status", "DESCONOCIDO")
            reason = data.get("reason", "")
            text = f"🏁 FASE FINALIZADA: {data.get('name', '')} - {status}"
            if reason:
                text += f"\n{format_content(reason, 100)}"
            css_class = "phase-end"
        else:  # info
            message = format_content(data.get('message', ''), 100)
            text = f"ℹ️  {message}"
            css_class = "orchestrator-info"
            
    elif "Agent" in source:
        if msg_type == "thought":
            content = format_content(data.get('content', ''), 110)
            text = f"🤔 PENSAMIENTO ({source})\n{content}"
            css_class = "agent-thought"
        elif msg_type == "action":
            tool = data.get('tool', 'unknown')
            args = data.get('args', {})
            if isinstance(args, dict) and 'path' in args:
                args_str = args.get('path', 'unknown')
                if 'content_length' in args:
                    args_str += f" ({args.get('content_length', 0)} chars)"
            else:
                args_str = str(args)[:50] + ("..." if len(str(args)) > 50 else "")
            text = f"⚡ ACCIÓN ({source}): {tool}\n{args_str}"
            css_class = "agent-action"
        elif msg_type == "error":
            message = format_content(data.get('message', ''), 100)
            text = f"❌ ERROR ({source})\n{message}"
            css_class = "agent-error"
        else:  # info y otros tipos
            message = format_content(data.get('message', ''), 100)
            text = f"ℹ️  {source}: {message}"
            css_class = "agent-info"
    else:
        # Mensajes del sistema
        text = f"📋 {str(message_data)}"
        css_class = "system-info"
    
    return Static(text, classes=css_class)

# --- Aplicación Principal TUI ---
class DirGenTUI(App):
    CSS_PATH = "tui.css"
    BINDINGS = [
        ("q", "quit", "Salir"),
        ("c", "clear_log", "Limpiar"),
        ("s", "scroll_to_bottom", "Ir al final"),
        ("r", "reconnect", "Reconectar")
    ]
    TITLE = "DirGen Platform"
    SUB_TITLE = "Generador de Proyectos con IA"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.run_id = None
        self.current_phase = "Inicializando"
        self.connection_status = "Desconectado"
        self.retry_count = 0
    
    def compose(self) -> ComposeResult:
        """Layout limpio y funcional: Header dinámico + Log principal + Footer"""
        yield Header()
        yield Static(self._get_status_text(), id="status-bar", classes="status-bar")
        yield Log(id="main-log", auto_scroll=True, highlight=True)
        yield Footer()
    
    def _get_status_text(self) -> str:
        """Genera el texto de la barra de estado"""
        run_id_display = f"Run: {self.run_id or 'N/A'}"
        phase_display = f"Fase: {self.current_phase}"
        status_display = f"Estado: {self.connection_status}"
        return f"🤖 DirGen | {run_id_display} | {phase_display} | {status_display}"
    
    def update_status(self, run_id: str = None, phase: str = None, status: str = None):
        """Actualiza la barra de estado dinámicamente"""
        if run_id:
            self.run_id = run_id
        if phase:
            self.current_phase = phase
        if status:
            self.connection_status = status
        
        try:
            status_bar = self.query_one("#status-bar", Static)
            status_bar.update(self._get_status_text())
        except:
            pass  # Si no se puede actualizar, continuar

    def log_message(self, message: str, level: str = "info"):
        """Registra un mensaje limpio tanto en el archivo como en la TUI"""
        try:
            # Logging a archivo (texto plano)
            log_funcs = {
                "debug": logger.debug,
                "info": logger.info,
                "warning": logger.warning,
                "error": logger.error,
                "critical": logger.critical
            }
            
            # Limpiar mensaje para el archivo log
            clean_message = message.replace("\n", " ").strip()
            log_func = log_funcs.get(level.lower(), logger.info)
            log_func(clean_message)
            
            # Mostrar en TUI
            self._write_to_tui(message)
                
        except Exception as e:
            logger.error(f"Error en log_message: {str(e)}")
    
    def _write_to_tui(self, message: str):
        """Escribe mensaje a la TUI con autoscroll garantizado"""
        try:
            log = self.query_one("#main-log", Log)
            if log:
                # Truncar si es muy largo
                if len(message) > 1000:
                    message = message[:997] + "..."
                
                logger.debug(f"Writing to TUI: {message[:100]}...")
                log.write_line(message)
                # Forzar scroll al final
                log.scroll_end(animate=False)
                logger.debug("Message written to TUI successfully")
            else:
                logger.error("Log widget not found")
        except Exception as e:
            logger.error(f"Error writing to TUI: {e}")

    async def on_mount(self) -> None:
        """Inicialización robusta de la TUI"""
        # Inicializar log
        try:
            log = self.query_one("#main-log", Log)
            log.can_focus = False
            await asyncio.sleep(0.1)  # Permitir que se estabilice
        except Exception as e:
            logger.error(f"Error inicializando log: {str(e)}")
        
        self.log_message("🚀 Iniciando DirGen TUI...", "info")
        self.update_status(status="Inicializando")
        
        # Verificar conexión con el Orquestador
        await self._check_orchestrator_connection()
    
    async def _check_orchestrator_connection(self):
        """Verifica y establece conexión con el Orquestador"""
        self.log_message("🔍 Verificando conexión con el Orquestador...", "info")
        self.update_status(status="Conectando")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.get("http://127.0.0.1:8000/docs", timeout=3)
                if response.status_code == 200:
                    self.log_message("✅ Orquestador detectado", "info")
                    await self._start_execution()
                    return
            except requests.RequestException as e:
                if attempt < max_retries - 1:
                    self.log_message(f"⚠️  Intento {attempt + 1} falló, reintentando...", "warning")
                    await asyncio.sleep(2)
                else:
                    self.log_message("❌ No se puede conectar con el Orquestador", "error")
                    self.log_message("Asegúrate de que el servidor esté ejecutándose", "error")
                    self.update_status(status="Error de conexión")
    
    async def _start_execution(self):
        """Inicia una nueva ejecución enviando el PCCE"""
        try:
            self.log_message("📤 Enviando PCCE para iniciar ejecución...", "info")
            
            with open("pcce_finbase.yml", 'rb') as f:
                files = {'pcce_file': ("pcce_finbase.yml", f, 'application/x-yaml')}
                response = requests.post("http://127.0.0.1:8000/v1/start_run", files=files, timeout=10)
                response.raise_for_status()
                
            run_data = response.json()
            self.run_id = run_data.get("run_id")
            
            self.log_message(f"✅ Ejecución iniciada: {self.run_id}", "info")
            self.update_status(run_id=self.run_id, status="Conectado")
            
            # Iniciar escucha WebSocket
            asyncio.create_task(self.listen_to_websocket(self.run_id))
            
        except FileNotFoundError:
            self.log_message("❌ Archivo pcce_finbase.yml no encontrado", "error")
            self.update_status(status="Error: PCCE faltante")
        except requests.RequestException as e:
            self.log_message(f"❌ Error iniciando ejecución: {str(e)}", "error")
            self.update_status(status="Error de inicio")

    async def listen_to_websocket(self, run_id: str):
        """Escucha mensajes del WebSocket con reconexión automática"""
        uri = f"ws://127.0.0.1:8000/ws/{run_id}"
        max_retries = 5
        
        for attempt in range(max_retries):
            try:
                self.log_message(f"🔌 Estableciendo WebSocket (intento {attempt + 1})...", "info")
                
                async with websockets.connect(uri, ping_interval=20, ping_timeout=10) as websocket:
                    self.log_message("✅ Conectado al stream de progreso", "info")
                    self.update_status(status="Monitoreando")
                    
                    while True:
                        try:
                            message_str = await websocket.recv()
                            logger.debug(f"WebSocket raw: {message_str}")
                            
                            message_data = json.loads(message_str)
                            logger.debug(f"WebSocket parsed: {message_data}")
                            
                            # Procesar mensaje
                            await self._process_websocket_message(message_data)
                            
                        except json.JSONDecodeError as e:
                            error_msg = f"⚠️  Error JSON: {str(e)}"
                            logger.error(error_msg)
                            self._write_to_tui(error_msg)
                        except Exception as e:
                            error_msg = f"⚠️  Error procesando: {str(e)}"
                            logger.error(error_msg)
                            self._write_to_tui(error_msg)
                            
            except websockets.exceptions.ConnectionClosed:
                if attempt < max_retries - 1:
                    self.log_message(f"🔄 Conexión perdida, reintentando...", "warning")
                    self.update_status(status="Reconectando")
                    await asyncio.sleep(3)
                else:
                    self.log_message("❌ No se pudo mantener la conexión WebSocket", "error")
                    self.update_status(status="Desconectado")
                    break
            except Exception as e:
                logger.exception("Error WebSocket crítico:")
                if attempt < max_retries - 1:
                    self.update_status(status="Error - reintentando")
                    await asyncio.sleep(3)
                else:
                    self.log_message(f"❌ Error WebSocket crítico: {str(e)}", "error")
                    break
    
    async def _process_websocket_message(self, message_data: dict):
        """Procesa mensajes WebSocket y actualiza el estado"""
        try:
            # Actualizar estado basado en el mensaje
            msg_type = message_data.get("type")
            data = message_data.get("data", {})
            source = message_data.get("source", "System")
            
            # Actualizar barra de estado dinámica
            if msg_type == "phase_start":
                phase_name = data.get("name", "Desconocida")
                self.update_status(phase=phase_name)
            elif msg_type == "retry_attempt":
                attempt = data.get("attempt", "?")
                self.retry_count = int(attempt) if str(attempt).isdigit() else 0
                self.update_status(status=f"Reintento {attempt}")
            elif msg_type == "phase_end":
                status = data.get("status", "DESCONOCIDO")
                if status == "APROBADO":
                    self.update_status(phase="Completado", status="Éxito")
                else:
                    self.update_status(phase="Terminado", status="Falló")
            elif msg_type == "quality_gate_start":
                self.update_status(status="Validando")
            elif msg_type == "quality_gate_result":
                if data.get("success"):
                    self.update_status(status="Validación OK")
                else:
                    self.update_status(status="Validación Falló")
            
            # Generar mensaje formateado directamente
            formatted_message = self._format_websocket_message(message_data)
            
            # Escribir a la TUI
            self._write_to_tui(formatted_message)
            
        except Exception as e:
            error_msg = f"Error procesando mensaje WebSocket: {e}"
            logger.error(error_msg)
            logger.error(f"Mensaje original: {message_data}")
            self._write_to_tui(f"⚠️  {error_msg}")
    
    def _format_websocket_message(self, message_data: dict) -> str:
        """Formatea un mensaje WebSocket para mostrar en la TUI"""
        source = message_data.get("source", "System")
        msg_type = message_data.get("type")
        data = message_data.get("data", {})
        
        # Mapear tipos de mensaje a formato
        if source == "Orchestrator":
            if msg_type == "phase_start":
                return f"🏭 INICIO DE FASE: {data.get('name', 'Desconocida')}"
            elif msg_type == "quality_gate_start":
                return f"🔍 QUALITY GATE: {data.get('name', 'Validación')}"
            elif msg_type == "quality_gate_result":
                message = format_content(data.get('message', ''), 100)
                if data.get("success"):
                    return f"✅ QUALITY GATE APROBADO\n{message}"
                else:
                    return f"❌ QUALITY GATE RECHAZADO\n{message}"
            elif msg_type == "retry_attempt":
                attempt = data.get('attempt', '?')
                max_attempts = data.get('max_attempts', '?')
                feedback = format_content(data.get('feedback', ''), 100)
                return f"🔄 REINTENTO ({attempt}/{max_attempts})\n{feedback}"
            elif msg_type == "phase_end":
                status = data.get("status", "DESCONOCIDO")
                reason = data.get("reason", "")
                text = f"🏁 FASE FINALIZADA: {data.get('name', '')} - {status}"
                if reason:
                    text += f"\n{format_content(reason, 100)}"
                return text
            else:  # info
                message = format_content(data.get('message', ''), 100)
                return f"ℹ️  {message}"
                
        elif "Agent" in source:
            if msg_type == "thought":
                content = format_content(data.get('content', ''), 110)
                return f"🤔 PENSAMIENTO ({source})\n{content}"
            elif msg_type == "action":
                tool = data.get('tool', 'unknown')
                args = data.get('args', {})
                if isinstance(args, dict) and 'path' in args:
                    args_str = args.get('path', 'unknown')
                    if 'content_length' in args:
                        args_str += f" ({args.get('content_length', 0)} chars)"
                else:
                    args_str = str(args)[:50] + ("..." if len(str(args)) > 50 else "")
                return f"⚡ ACCIÓN ({source}): {tool}\n{args_str}"
            elif msg_type == "error":
                message = format_content(data.get('message', ''), 100)
                return f"❌ ERROR ({source})\n{message}"
            else:  # info y otros tipos
                message = format_content(data.get('message', ''), 100)
                return f"ℹ️  {source}: {message}"
        else:
            # Mensajes del sistema
            return f"📋 {str(message_data)}"
        
        # Fallback
        return f"📋 {source}: {msg_type} - {str(data)[:100]}"

    # --- Acciones de teclado ---
    async def action_quit(self) -> None:
        """Salir de la aplicación"""
        self.exit()
    
    async def action_clear_log(self) -> None:
        """Limpiar el log"""
        try:
            log = self.query_one("#main-log", Log)
            log.clear()
            self.log_message("🗑️  Log limpiado", "info")
        except Exception:
            pass
    
    async def action_scroll_to_bottom(self) -> None:
        """Ir al final del log"""
        try:
            log = self.query_one("#main-log", Log)
            log.scroll_end(animate=False)
        except Exception:
            pass
    
    async def action_reconnect(self) -> None:
        """Reconectar al Orquestador"""
        self.log_message("🔄 Reconectando manualmente...", "info")
        await self._check_orchestrator_connection()

if __name__ == "__main__":
    DirGenTUI().run()