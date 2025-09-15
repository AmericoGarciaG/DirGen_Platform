import asyncio
import json
import logging
import os
import textwrap
from datetime import datetime
from pathlib import Path
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Log, Label
import websockets
import requests

# --- Configuración del Logger ---
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"tui_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Configurar el logger
logger = logging.getLogger("DirGenTUI")
logger.setLevel(logging.DEBUG)

# Handler para archivo
file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_format)
logger.addHandler(file_handler)

# Handler para consola
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_format = logging.Formatter('%(levelname)s: %(message)s')
console_handler.setFormatter(console_format)
logger.addHandler(console_handler)

# --- Utilidades de formateo ---
def wrap_text(text: str, width: int = 80) -> str:
    """Envuelve texto largo en múltiples líneas preservando markup de Rich"""
    if len(text) <= width:
        return text
    
    # Para texto con markup de Rich, envolvemos más conservadoramente
    if '[' in text and ']' in text:
        return textwrap.fill(text, width=width, break_long_words=False, break_on_hyphens=False)
    
    return textwrap.fill(text, width=width)

def format_message_content(content: str, max_width: int = 100) -> str:
    """Formatea el contenido de un mensaje para mejor legibilidad"""
    if not content:
        return ""
    
    # Si es muy largo, lo dividimos en párrafos
    if len(content) > max_width:
        wrapped = wrap_text(content, max_width)
        # Agregamos un pequeño margen a las líneas adicionales
        lines = wrapped.split('\n')
        if len(lines) > 1:
            formatted_lines = [lines[0]]  # Primera línea sin margen
            for line in lines[1:]:
                formatted_lines.append(f"     {line.strip()}")  # Líneas adicionales con margen
            return '\n'.join(formatted_lines)
    
    return content

# --- Componentes de la UI Mejorados ---
class StatusBlock(Static):
    def __init__(self, message_data, **kwargs):
        super().__init__(**kwargs)
        self.message_data = message_data

    def __str__(self) -> str:
        """Convierte el bloque de estado en una cadena formateada"""
        source = self.message_data.get("source", "System")
        msg_type = self.message_data.get("type")
        data = self.message_data.get("data", {})
        
        # Agregar separador visual para mejor organización
        separator = "\n" + "─" * 80 + "\n"
        
        if source == "Orchestrator":
            if msg_type == "phase_start":
                return f"{separator}🏭 [bold magenta]INICIO DE FASE:[/] {data.get('name')}{separator}"
            elif msg_type == "quality_gate_start":
                return f"\n🔍 [bold yellow]QUALITY GATE:[/] Iniciando {data.get('name')}\n"
            elif msg_type == "quality_gate_result":
                message = format_message_content(data.get('message', ''), 90)
                if data.get("success"):
                    return f"\n✅ [bold green]QUALITY GATE APROBADO:[/]\n   {message}\n"
                else:
                    return f"\n❌ [bold red]QUALITY GATE RECHAZADO:[/]\n   {message}\n"
            elif msg_type == "phase_end":
                status = data.get("status")
                color = "green" if status == "APROBADO" else "red"
                return f"\n🏁 [bold {color}]FASE FINALIZADA:[/] {data.get('name')} - {status}{separator}"
            else:  # info
                message = format_message_content(data.get('message', ''), 85)
                return f"\nℹ️  [bold blue][Orquestador][/] {message}\n"
                
        elif "Agent" in source:
            if msg_type == "thought":
                content = format_message_content(data.get('content', ''), 90)
                return f"\n🤔 [cyan][{source}][/]\n   💭 {content}\n"
            elif msg_type == "action":
                tool = data.get('tool', 'unknown')
                args = data.get('args', {})
                # Formatear argumentos de manera más legible
                if isinstance(args, dict):
                    if 'path' in args:
                        args_str = f"path: {args.get('path', 'unknown')}"
                        if 'content_length' in args:
                            args_str += f", content_length: {args.get('content_length', 0)}"
                    else:
                        args_str = str(args)
                else:
                    args_str = str(args)
                    
                return f"\n⚡ [yellow][{source}][/]\n   🔧 Acción: {tool}({args_str})\n"
            elif msg_type == "error":
                message = format_message_content(data.get('message', ''), 85)
                return f"\n❌ [bold red][{source}][/]\n   💥 ERROR: {message}\n"
            else:  # info y otros tipos de mensajes
                message = format_message_content(data.get('message', ''), 85)
                return f"\nℹ️  [bold blue][{source}][/] {message}\n"
                
        return f"\n📋 [dim]{str(self.message_data)}[/]\n"  # Fallback para mensajes desconocidos

    def compose(self) -> ComposeResult:
        # Simplemente usamos el método __str__ que ya formatea todo correctamente
        yield Static(str(self), classes="message-text")

# --- Aplicación Principal TUI ---
class DirGenTUI(App):
    CSS_PATH = "tui.css"
    BINDINGS = [
        ("q", "quit", "Salir"),
        ("c", "clear_log", "Limpiar"),
        ("s", "scroll_to_bottom", "Ir al final")
    ]
    TITLE = "DirGen Platform - Generador de Proyectos con IA"
    SUB_TITLE = "Ejecutando flujo de trabajo automático"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="main_container"):
            with Vertical():
                yield Static(
                    "🤖 [bold cyan]DirGen Platform[/] | ⚙️ [yellow]Estado:[/] Monitoreando agentes | 🔄 [green]Conectado[/]", 
                    id="status_header", 
                    classes="status-panel"
                )
                yield Log(id="log_view", auto_scroll=True, highlight=True)
        yield Footer()

    def log_message(self, message: str, level: str = "info"):
        """Registra un mensaje tanto en el logger como en la TUI"""
        try:
            log_funcs = {
                "debug": logger.debug,
                "info": logger.info,
                "warning": logger.warning,
                "error": logger.error,
                "critical": logger.critical
            }
            
            # Registrar en el archivo de log (sin formato rich)
            clean_message = (message.replace("[/]", "")
                                .replace("[dim]", "")
                                .replace("[yellow]", "")
                                .replace("[green]", "")
                                .replace("[bold red]", "")
                                .replace("[bold blue]", "")
                                .replace("[cyan]", "")
                                .replace("[magenta]", "")
                                .replace("[orange]", ""))
            log_func = log_funcs.get(level.lower(), logger.info)
            log_func(clean_message)
            
            # Mostrar en la TUI - Solo si el widget Log está disponible
            try:
                log = self.query_one(Log)
                if log:
                    # Truncar mensajes muy largos para evitar desbordamiento
                    display_message = message
                    if len(message) > 500:  # Limitar longitud máxima
                        display_message = message[:497] + "..."
                    
                    # Si estamos en un hilo diferente, usamos call_from_thread
                    if hasattr(self, '_loop') and asyncio.get_event_loop() != self._loop:
                        self.call_from_thread(log.write_line, display_message)
                    else:
                        log.write_line(display_message)
            except Exception:
                # Si no se puede obtener el log, simplemente continuar
                pass
                
        except Exception as e:
            # Si algo falla al mostrar en la TUI, al menos lo registramos en el log
            logger.error(f"Error mostrando mensaje en TUI: {str(e)}")
            logger.info(f"Mensaje original: {message}")

    async def on_mount(self) -> None:
        # Asegurar que el log esté correctamente inicializado
        try:
            log = self.query_one(Log)
            log.can_focus = False
            # Esperar un momento para que el layout se estabilice
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Error inicializando log: {str(e)}")
        
        self.log_message("\n🚀 [bold green]Iniciando DirGenTUI...[/]\n", "info")

        self.log_message("[yellow]Verificando conexión con el Orquestador...[/]", "info")
        try:
            # Primero verificamos si el servidor está disponible
            max_retries = 3
            retry_delay = 2
            
            for attempt in range(max_retries):
                try:
                    self.log_message(f"[yellow]Intento {attempt + 1} de {max_retries} para conectar con el Orquestador...[/]", "info")
                    response = requests.get("http://127.0.0.1:8000/docs", timeout=2)
                    if response.status_code == 200:
                        break
                except requests.RequestException as e:
                    logger.debug(f"Error de conexión (intento {attempt + 1}): {str(e)}")
                    if attempt < max_retries - 1:
                        self.log_message(f"[yellow]Reintentando en {retry_delay} segundos...[/]", "warning")
                        await asyncio.sleep(retry_delay)
                    else:
                        self.log_message("[bold red]Error:[/] No se puede conectar con el Orquestador", "error")
                        self.log_message("[dim]Asegúrate de que el servidor (mcp_host/main.py) esté en ejecución[/]", "info")
                        return

            self.log_message("[green]✓[/] Orquestador detectado", "info")
            self.log_message("Enviando PCCE al Orquestador para iniciar la ejecución...", "info")
            
            try:
                with open("pcce_finbase.yml", 'rb') as f:
                    files = {'pcce_file': ("pcce_finbase.yml", f, 'application/x-yaml')}
                    response = requests.post("http://127.0.0.1:8000/v1/start_run", files=files, timeout=5)
                    response.raise_for_status()
                    run_id = response.json().get("run_id")
                    self.log_message(f"[green]Ejecución iniciada con Run ID:[/] {run_id}", "info")
                    asyncio.create_task(self.listen_to_websocket(run_id))
            except FileNotFoundError:
                self.log_message("[bold red]Error:[/] No se encuentra el archivo pcce_finbase.yml", "error")
                self.log_message("[dim]El archivo debe estar en el mismo directorio desde donde ejecutas la aplicación[/]", "info")
            except requests.RequestException as e:
                self.log_message(f"[bold red]Error:[/] No se pudo iniciar la ejecución: {str(e)}", "error")
                self.log_message("[dim]Verifica que el Orquestador esté funcionando correctamente[/]", "info")
        except Exception as e:
            self.log_message(f"[bold red]Error inesperado:[/] {str(e)}", "critical")

    async def listen_to_websocket(self, run_id: str):
        uri = f"ws://127.0.0.1:8000/ws/{run_id}"
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                self.log_message(f"[yellow]Intento {attempt + 1} de {max_retries} para establecer WebSocket...[/]", "info")
                async with websockets.connect(uri, ping_interval=20, ping_timeout=10) as websocket:
                    self.log_message("[green]Conectado al stream de progreso del Orquestador.[/]", "info")
                    self.log_message("[dim]Esperando mensajes...[/]", "info")
                    
                    while True:
                        try:
                            message_str = await websocket.recv()
                            logger.debug(f"Mensaje WebSocket recibido: {message_str}")
                            message_json = json.loads(message_str)
                            status_block = StatusBlock(message_json)
                            self.log_message(str(status_block), "info")
                        except json.JSONDecodeError as je:
                            self.log_message(f"[yellow]Error decodificando mensaje:[/] {str(je)}", "warning")
                            logger.warning(f"Error decodificando JSON: {je}")
                        except Exception as e:
                            self.log_message(f"[orange]Error procesando mensaje:[/] {str(e)}", "error")
                            logger.error(f"Error procesando mensaje: {e}")
                            
            except websockets.exceptions.ConnectionClosed:
                logger.warning(f"Conexión WebSocket cerrada (intento {attempt + 1})")
                if attempt < max_retries - 1:
                    # Como estamos en una corutina, podemos usar self.log_message directamente
                    self.log_message(f"[yellow]Conexión perdida. Reintentando en {retry_delay} segundos...[/]", "warning")
                    await asyncio.sleep(retry_delay)
                else:
                    self.log_message("[red]No se pudo mantener la conexión WebSocket.[/]", "error")
                    break
            except Exception as e:
                logger.exception("Error crítico en la conexión WebSocket:")
                self.log_message(f"[bold red]Error de WebSocket:[/] {str(e)}", "critical")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                else:
                    break

    # --- Métodos de acción para atajos de teclado ---
    async def action_quit(self) -> None:
        """Salir de la aplicación"""
        self.exit()
    
    async def action_clear_log(self) -> None:
        """Limpiar el log"""
        log = self.query_one(Log)
        log.clear()
        self.log_message("🗑️ [yellow]Log limpiado[/]", "info")
    
    async def action_scroll_to_bottom(self) -> None:
        """Ir al final del log"""
        log = self.query_one(Log)
        log.scroll_end()

if __name__ == "__main__":
    DirGenTUI().run()