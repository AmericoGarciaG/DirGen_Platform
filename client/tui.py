import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Log, ListItem, ListView, Button, DirectoryTree
from textual.containers import Horizontal, Vertical, Container
from textual.screen import Screen
from textual.reactive import reactive
from textual import on
import websockets
import requests
import os
from typing import Optional

# --- Configuración del Logger ---
# Intentar usar logging centralizado, mantener sistema existente como fallback
try:
    from pathlib import Path
    import sys
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    from dirgen_core.logging_config import get_client_logger, LogLevel
    logger = get_client_logger(LogLevel.DEBUG)
    
    # Mantener compatibilidad con logs antiguos
    OLD_LOG_DIR = Path(__file__).parent / "logs"
    OLD_LOG_DIR.mkdir(exist_ok=True)
    OLD_LOG_FILE = OLD_LOG_DIR / f"tui_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # Handler adicional para mantener formato existente en directorio viejo
    old_file_handler = logging.FileHandler(OLD_LOG_FILE, encoding='utf-8')
    old_file_handler.setLevel(logging.DEBUG)
    old_file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    old_file_handler.setFormatter(old_file_format)
    logger.addHandler(old_file_handler)
    
except ImportError:
    # Fallback al sistema anterior
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

# --- Detección de proyectos ---
def detect_projects(directory: str = ".") -> list[dict]:
    """Detecta archivos .md que pueden ser proyectos SVAD"""
    projects = []
    try:
        for file_path in Path(directory).glob("*.md"):
            if file_path.is_file() and file_path.name != "README.md":
                # Leer primeras líneas para obtener descripción
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read(200)  # Primeros 200 caracteres
                        first_line = content.split('\n')[0].strip()
                        description = first_line if len(first_line) > 10 else "Proyecto DirGen"
                except:
                    description = "Proyecto DirGen"
                
                projects.append({
                    "name": file_path.name,
                    "path": str(file_path.absolute()),
                    "description": description
                })
    except Exception as e:
        logger.error(f"Error detectando proyectos: {e}")
    
    return projects

# --- Pantalla de Selección de Archivos - FileSelectionScreen ---
class FileSelectionScreen(Screen):
    """Pantalla para selección manual de archivos usando DirectoryTree"""
    
    BINDINGS = [
        ("enter", "select_file", "Seleccionar"),
        ("escape", "cancel", "Cancelar"),
        ("q", "cancel", "Volver")
    ]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_file_path: Optional[str] = None
    
    def compose(self) -> ComposeResult:
        """Composición de la pantalla de selección de archivos"""
        yield Header()
        
        yield Static(
            "*** SELECCION MANUAL DE ARCHIVOS ***\n\n"
            "Navega por los directorios y selecciona un archivo .md para ejecutar.",
            id="file-selection-title",
            classes="welcome-text"
        )
        
        # Árbol de directorios
        yield DirectoryTree(
            "./",  # Directorio actual
            id="directory-tree",
            classes="directory-tree"
        )
        
        # Barra de estado
        yield Static(">> Usa las flechas para navegar, ENTER para seleccionar, ESC para cancelar", id="file-selection-status", classes="home-status")
        
        yield Footer()
    
    @on(DirectoryTree.FileSelected)
    async def on_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        """Manejar selección de archivo del DirectoryTree - ejecuta inmediatamente"""
        file_path = str(event.path)
        logger.debug(f"DirectoryTree.FileSelected disparado para: {file_path}")
        
        # Validar que sea un archivo .md
        if file_path.lower().endswith('.md') and Path(file_path).is_file():
            self.selected_file_path = file_path
            filename = Path(file_path).name
            
            self.query_one("#file-selection-status", Static).update(
                f"OK: Ejecutando: {filename}..."
            )
            logger.debug(f"Archivo .md seleccionado y ejecutando: {file_path}")
            
            # Cerrar pantalla y ejecutar archivo inmediatamente
            self.app.pop_screen()
            if callable(getattr(self, 'callback', None)):
                self.callback(file_path)
        else:
            self.query_one("#file-selection-status", Static).update(
                f"WARN: Solo se pueden seleccionar archivos .md - Archivo actual: {Path(file_path).name}"
            )
    
    @on(DirectoryTree.DirectorySelected)
    async def on_directory_selected(self, event: DirectoryTree.DirectorySelected) -> None:
        """Manejar selección de directorio (solo feedback)"""
        dir_path = str(event.path)
        self.query_one("#file-selection-status", Static).update(
            f"[DIR] Directorio: {Path(dir_path).name} - Navega a un archivo .md"
        )
    
    async def on_directory_tree_cursor_changed(self, event) -> None:
        """Manejar cambio de cursor en DirectoryTree para feedback inmediato"""
        try:
            tree = self.query_one("#directory-tree", DirectoryTree)
            if tree.cursor_node and tree.cursor_node.data and hasattr(tree.cursor_node.data, 'path'):
                current_path = str(tree.cursor_node.data.path)
                filename = Path(current_path).name
                
                if Path(current_path).is_file():
                    if current_path.lower().endswith('.md'):
                        self.query_one("#file-selection-status", Static).update(
                            f"OK: {filename} - Presiona ENTER para seleccionar este archivo .md"
                        )
                    else:
                        self.query_one("#file-selection-status", Static).update(
                            f"WARN: {filename} - Este archivo no es .md (solo archivos .md permitidos)"
                        )
                else:
                    self.query_one("#file-selection-status", Static).update(
                        f"[DIR] {filename} - Directorio (navega a archivos .md)"
                    )
        except Exception as e:
            logger.debug(f"Error en cursor_changed: {e}")
    
    async def action_select_file(self) -> None:
        """Confirmar selección del archivo usando el cursor actual"""
        try:
            # Obtener el archivo/directorio destacado actual del DirectoryTree
            tree = self.query_one("#directory-tree", DirectoryTree)
            
            # Intentar obtener el nodo actual de diferentes maneras
            current_path = None
            
            # Método 1: cursor_node
            if hasattr(tree, 'cursor_node') and tree.cursor_node and tree.cursor_node.data:
                if hasattr(tree.cursor_node.data, 'path'):
                    current_path = str(tree.cursor_node.data.path)
                    logger.debug(f"Path desde cursor_node: {current_path}")
            
            # Método 2: selected_node o highlighted_node
            if not current_path and hasattr(tree, 'selected') and tree.selected:
                current_path = str(tree.selected)
                logger.debug(f"Path desde selected: {current_path}")
            
            # Método 3: usar el archivo preseleccionado
            if not current_path and self.selected_file_path:
                current_path = self.selected_file_path
                logger.debug(f"Path desde selected_file_path: {current_path}")
            
            # Validar y ejecutar
            if current_path and current_path.lower().endswith('.md') and Path(current_path).is_file():
                filename = Path(current_path).name
                self.query_one("#file-selection-status", Static).update(
                    f"OK: Ejecutando: {filename}..."
                )
                logger.debug(f"Ejecutando archivo desde ENTER: {current_path}")
                
                # Cerrar pantalla y enviar archivo seleccionado
                self.app.pop_screen()
                if callable(getattr(self, 'callback', None)):
                    self.callback(current_path)
            else:
                self.query_one("#file-selection-status", Static).update(
                    "ERROR: No hay archivo .md seleccionado - Navega a un archivo .md y presiona ENTER"
                )
                logger.debug(f"No se puede ejecutar: {current_path}")
        
        except Exception as e:
            logger.error(f"Error en action_select_file: {e}")
            self.query_one("#file-selection-status", Static).update(
                f"❌ Error detectando archivo: {str(e)}"
            )
    
    async def action_cancel(self) -> None:
        """Cancelar selección y volver"""
        self.app.pop_screen()
        if callable(getattr(self, 'callback', None)):
            self.callback(None)

# --- Pantalla de Inicio - HomeScreen ---
class HomeScreen(Screen):
    """Pantalla de inicio que permite seleccionar proyectos SVAD"""
    
    BINDINGS = [
        ("enter", "select_project", "Ejecutar Proyecto"),
        ("f", "select_file_manually", "Seleccionar Archivo"),
        ("q", "quit_app", "Salir"),
        ("r", "refresh_projects", "Actualizar")
    ]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.projects = []
        self.selected_file_path: Optional[str] = None
    
    def compose(self) -> ComposeResult:
        """Composición de la pantalla de inicio"""
        yield Header()
        
        # Título y descripción
        yield Static(
            "*** DIRGEN PLATFORM ***\n\n"
            "Selecciona un proyecto SVAD para ejecutar o navega manualmente para seleccionar un archivo.\n"
            "Los proyectos detectados se muestran a continuación:\n",
            id="welcome-text",
            classes="welcome-text"
        )
        
        # Lista de proyectos
        yield ListView(id="projects-list", classes="projects-list")
        
        # Botones de acción
        with Horizontal(classes="action-buttons"):
            yield Button("[F] Seleccionar Archivo Manualmente", id="select-file-btn", variant="primary")
            yield Button("[R] Actualizar Proyectos", id="refresh-btn", variant="default")
        
        # Barra de estado
        yield Static("", id="home-status", classes="home-status")
        
        yield Footer()
    
    async def on_mount(self) -> None:
        """Cargar proyectos al montar la pantalla"""
        await self.refresh_projects()
    
    async def refresh_projects(self) -> None:
        """Actualiza la lista de proyectos detectados"""
        try:
            self.projects = detect_projects()
            projects_list = self.query_one("#projects-list", ListView)
            projects_list.clear()
            
            if self.projects:
                for project in self.projects:
                    item = ListItem(
                        Static(f"[*] **{project['name']}**\n{project['description'][:80]}..."),
                        classes="project-item"
                    )
                    projects_list.append(item)
                
                status_text = f"OK: {len(self.projects)} proyecto(s) detectado(s)"
            else:
                # Agregar opción para selección manual si no hay proyectos
                projects_list.append(
                    ListItem(
                        Static("[!] No se detectaron proyectos SVAD\n[i] Usa 'Seleccionar Archivo Manualmente' para navegar"),
                        classes="no-projects-item"
                    )
                )
                status_text = "WARN: No se detectaron proyectos automáticamente"
            
            # Actualizar estado
            self.query_one("#home-status", Static).update(status_text)
            
        except Exception as e:
            logger.error(f"Error actualizando proyectos: {e}")
            self.query_one("#home-status", Static).update(f"ERROR: {str(e)}")
    
    @on(ListView.Highlighted)
    async def on_project_highlighted(self, event: ListView.Highlighted) -> None:
        """Manejar resaltado de proyecto (feedback visual inmediato)"""
        if (self.projects and 
            event.list_view.index is not None and 
            event.list_view.index >= 0 and 
            event.list_view.index < len(self.projects)):
            
            highlighted_project = self.projects[event.list_view.index]
            status_text = f">> {highlighted_project['name']} - Presiona ENTER para ejecutar"
            self.query_one("#home-status", Static).update(status_text)
    
    @on(ListView.Selected)
    async def on_project_selected(self, event: ListView.Selected) -> None:
        """Manejar selección definitiva de proyecto de la lista - ejecuta inmediatamente"""
        if (self.projects and 
            event.list_view.index is not None and 
            event.list_view.index >= 0 and 
            event.list_view.index < len(self.projects)):
            
            selected_project = self.projects[event.list_view.index]
            self.selected_file_path = selected_project["path"]
            
            # Ejecutar inmediatamente cuando se hace clic o se selecciona
            logger.debug(f"Proyecto seleccionado para ejecución: {selected_project['name']} en índice {event.list_view.index}")
            await self._start_execution_with_file(self.selected_file_path)
    
    @on(Button.Pressed, "#select-file-btn")
    async def on_select_file_button(self, event: Button.Pressed) -> None:
        """Abrir diálogo de selección de archivos"""
        await self.action_select_file_manually()
    
    @on(Button.Pressed, "#refresh-btn")
    async def on_refresh_button(self, event: Button.Pressed) -> None:
        """Actualizar lista de proyectos"""
        await self.refresh_projects()
    
    async def action_select_project(self) -> None:
        """Ejecutar el proyecto actualmente destacado"""
        try:
            projects_list = self.query_one("#projects-list", ListView)
            
            if (self.projects and 
                projects_list.index is not None and 
                projects_list.index >= 0 and 
                projects_list.index < len(self.projects)):
                
                selected_project = self.projects[projects_list.index]
                file_path = selected_project["path"]
                
                if Path(file_path).exists():
                    # Iniciar ejecución con el archivo seleccionado
                    await self._start_execution_with_file(file_path)
                else:
                    self.query_one("#home-status", Static).update(
                        f"❌ Archivo no encontrado: {selected_project['name']}"
                    )
            elif self.projects:
                # Si hay proyectos pero no hay índice válido
                self.query_one("#home-status", Static).update(
                    "🔍 Usa las flechas para navegar y ENTER para seleccionar un proyecto"
                )
            else:
                self.query_one("#home-status", Static).update(
                    "❌ No hay proyectos disponibles"
                )
                
        except Exception as e:
            logger.error(f"Error en action_select_project: {e}")
            self.query_one("#home-status", Static).update(
                f"❌ Error de selección: {str(e)}"
            )
    
    async def action_select_file_manually(self) -> None:
        """Abrir selector de archivos usando DirectoryTree"""
        try:
            # Crear una pantalla de selección de archivos personalizada
            file_selector = FileSelectionScreen()
            
            def handle_file_selected(file_path: Optional[str]) -> None:
                """Callback cuando se selecciona un archivo - ejecuta inmediatamente"""
                if file_path and Path(file_path).exists():
                    self.selected_file_path = file_path
                    filename = Path(file_path).name
                    logger.debug(f"Archivo seleccionado manualmente: {file_path}")
                    
                    # Ejecutar inmediatamente el archivo seleccionado
                    asyncio.create_task(self._start_execution_with_file(file_path))
                else:
                    # Usuario canceló o no seleccionó nada
                    self.query_one("#home-status", Static).update(
                        "CANCEL: Selección cancelada - Usa la lista o inténtalo de nuevo"
                    )
            
            # Asignar el callback directamente a la pantalla
            file_selector.callback = handle_file_selected
            
            # Usar push_screen
            self.app.push_screen(file_selector)
            
        except Exception as e:
            logger.error(f"Error abriendo selector de archivos: {e}")
            self.query_one("#home-status", Static).update(
                f"❌ Error abriendo selector: {str(e)}"
            )
    
    async def action_refresh_projects(self) -> None:
        """Actualizar proyectos detectados"""
        await self.refresh_projects()
    
    async def action_quit_app(self) -> None:
        """Salir de la aplicación"""
        self.app.exit()
    
    async def _start_execution_with_file(self, file_path: str) -> None:
        """Inicia la ejecución enviando el archivo al Orquestador"""
        try:
            filename = Path(file_path).name
            self.query_one("#home-status", Static).update(f"📤 Enviando {filename} al Orquestador...")
            
            # Verificar conexión con el Orquestador
            try:
                response = requests.get("http://127.0.0.1:8000/docs", timeout=3)
                if response.status_code != 200:
                    raise requests.RequestException("Orquestador no disponible")
            except requests.RequestException:
                self.query_one("#home-status", Static).update(
                    "❌ Error: No se puede conectar con el Orquestador (http://127.0.0.1:8000)"
                )
                return
            
            # Enviar archivo al Orquestador
            with open(file_path, 'rb') as f:
                files = {'svad_file': (filename, f, 'text/markdown')}
                response = requests.post(
                    "http://127.0.0.1:8000/v1/initiate_from_svad", 
                    files=files, 
                    timeout=15
                )
                response.raise_for_status()
            
            # Obtener run_id de la respuesta
            run_data = response.json()
            run_id = run_data.get("run_id")
            
            if not run_id:
                raise ValueError("No se recibió run_id del Orquestador")
            
            # Navegar a la pantalla de logs
            self.app.push_screen(LogScreen(run_id, filename))
            
        except requests.RequestException as e:
            error_msg = f"❌ Error enviando archivo: {str(e)}"
            logger.error(error_msg)
            self.query_one("#home-status", Static).update(error_msg)
        except Exception as e:
            error_msg = f"❌ Error inesperado: {str(e)}"
            logger.error(error_msg)
            self.query_one("#home-status", Static).update(error_msg)

# --- Componentes de la UI Profesional ---
class PlanWidget(Static):
    """Widget especializado para mostrar y actualizar el plan estratégico del agente"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_plan = []
        self.total_tasks = 0
        self.plan_status = "Sin plan"
        
    def update_plan(self, plan_data: dict):
        """Actualiza el contenido del plan"""
        self.current_plan = plan_data.get("plan", [])
        self.total_tasks = plan_data.get("total_tasks", len(self.current_plan))
        reason = plan_data.get("reason", "")
        
        # Determinar si es actualización o plan inicial
        if reason:
            self.plan_status = f"Plan actualizado ({reason})"
        else:
            self.plan_status = "Plan estratégico inicial"
            
        self._refresh_display()
    
    def _refresh_display(self):
        """Actualiza la visualización del plan"""
        if not self.current_plan:
            content = "📋 **PLAN ESTRATÉGICO**\n\n⚠️  Sin plan generado aún"
        else:
            header = f"📋 **PLAN ESTRATÉGICO** ({len(self.current_plan)} tareas)\n"
            header += f"Estado: {self.plan_status}\n"
            header += "─" * 50 + "\n"
            
            # Formatear cada tarea del plan
            task_lines = []
            for i, task in enumerate(self.current_plan, 1):
                # Estado por defecto: pendiente
                status_icon = "⚪"  # ◯ para círculo vacío, ⚪ para círculo medio
                task_lines.append(f"{status_icon} **{i}.** {task}")
            
            content = header + "\n".join(task_lines)
            
            # Añadir footer
            content += "\n" + "─" * 50
            content += f"\n📊 Total: {len(self.current_plan)} tareas | 🔄 Adaptable según obstáculos"
            
        self.update(content)
    
    def mark_task_progress(self, task_index: int, status: str = "in_progress"):
        """Marca el progreso de una tarea específica (funcionalidad futura)"""
        # Esta funcionalidad se puede implementar más adelante cuando el agente
        # reporte progreso granular por tarea
        pass

# --- Pantalla de Logs - LogScreen ---
class LogScreen(Screen):
    """Pantalla de monitoreo que muestra logs y plan de ejecución"""
    
    BINDINGS = [
        ("q", "quit_screen", "Volver"),
        ("c", "clear_log", "Limpiar"),
        ("s", "scroll_to_bottom", "Ir al final"),
        ("r", "reconnect", "Reconectar")
    ]
    
    def __init__(self, run_id: str, project_name: str, **kwargs):
        super().__init__(**kwargs)
        self.run_id = run_id
        self.project_name = project_name
        self.current_phase = "Inicializando"
        self.connection_status = "Conectando"
        self.retry_count = 0
        self.websocket_task = None
    
    def compose(self) -> ComposeResult:
        """Layout de la pantalla de logs: Status + Plan + Log horizontal"""
        yield Header()
        yield Static(self._get_status_text(), id="log-status-bar", classes="status-bar")
        
        # Layout horizontal: Plan a la izquierda, Log a la derecha
        with Horizontal():
            yield PlanWidget(id="plan-widget", classes="plan-widget")
            yield Log(id="main-log", auto_scroll=True, highlight=True, classes="main-log")
        
        yield Footer()
    
    def _get_status_text(self) -> str:
        """Genera el texto de la barra de estado"""
        project_display = f"Proyecto: {self.project_name}"
        run_id_display = f"Run: {self.run_id}"
        phase_display = f"Fase: {self.current_phase}"
        status_display = f"Estado: {self.connection_status}"
        return f"🤖 {project_display} | {run_id_display} | {phase_display} | {status_display}"
    
    def update_status(self, phase: str = None, status: str = None):
        """Actualiza la barra de estado dinámicamente"""
        if phase:
            self.current_phase = phase
        if status:
            self.connection_status = status
        
        try:
            status_bar = self.query_one("#log-status-bar", Static)
            status_bar.update(self._get_status_text())
        except:
            pass  # Si no se puede actualizar, continuar
    
    async def on_mount(self) -> None:
        """Inicializar la conexión WebSocket al montar la pantalla"""
        # Inicializar log
        try:
            log = self.query_one("#main-log", Log)
            log.can_focus = False
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Error inicializando log: {str(e)}")
        
        self.log_message(f"🚀 Iniciando monitoreo para {self.project_name}...", "info")
        self.log_message(f"🎯 Run ID: {self.run_id}", "info")
        
        # Iniciar escucha WebSocket
        self.websocket_task = asyncio.create_task(self.listen_to_websocket())
    
    async def on_unmount(self) -> None:
        """Limpiar recursos al desmontar la pantalla"""
        if self.websocket_task:
            self.websocket_task.cancel()
            try:
                await self.websocket_task
            except asyncio.CancelledError:
                pass
    
    def log_message(self, message: str, level: str = "info"):
        """Registra un mensaje tanto en archivo como en la TUI"""
        try:
            # Logging a archivo
            log_funcs = {
                "debug": logger.debug,
                "info": logger.info,
                "warning": logger.warning,
                "error": logger.error,
                "critical": logger.critical
            }
            
            clean_message = message.replace("\n", " ").strip()
            log_func = log_funcs.get(level.lower(), logger.info)
            log_func(clean_message)
            
            # Mostrar en TUI
            self._write_to_tui(message)
                
        except Exception as e:
            logger.error(f"Error en log_message: {str(e)}")
    
    def _write_to_tui(self, message: str):
        """Escribe mensaje a la TUI con autoscroll"""
        try:
            log = self.query_one("#main-log", Log)
            if log:
                if len(message) > 1000:
                    message = message[:997] + "..."
                
                log.write_line(message)
                log.write_line("")  # Línea vacía para separar mensajes
                log.scroll_end(animate=False)
            else:
                logger.error("Log widget not found")
        except Exception as e:
            logger.error(f"Error writing to TUI: {e}")
    
    async def listen_to_websocket(self):
        """Escucha mensajes del WebSocket con reconexión automática"""
        uri = f"ws://127.0.0.1:8000/ws/{self.run_id}"
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
            msg_type = message_data.get("type")
            data = message_data.get("data", {})
            source = message_data.get("source", "System")
            
            # Manejo de mensajes de planificación
            if msg_type == "plan_generated":
                await self._update_plan_widget(data)
                self.update_status(status="Plan generado")
                self.log_message(f"📋 Plan estratégico generado con {data.get('total_tasks', '?')} tareas", "info")
                return
                
            elif msg_type == "plan_updated":
                await self._update_plan_widget(data)
                reason = data.get("reason", "Motivo no especificado")
                self.update_status(status="Plan actualizado")
                self.log_message(f"🔄 Plan actualizado: {reason}", "warning")
                return
            
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
            
            # Generar mensaje formateado
            formatted_message = self._format_websocket_message(message_data)
            self._write_to_tui(formatted_message)
            
        except Exception as e:
            error_msg = f"Error procesando mensaje WebSocket: {e}"
            logger.error(error_msg)
            logger.error(f"Mensaje original: {message_data}")
            self._write_to_tui(f"⚠️  {error_msg}")
    
    async def _update_plan_widget(self, plan_data: dict):
        """Actualiza el PlanWidget con nuevos datos del plan"""
        try:
            plan_widget = self.query_one("#plan-widget", PlanWidget)
            plan_widget.update_plan(plan_data)
            logger.info(f"PlanWidget actualizado con {len(plan_data.get('plan', []))} tareas")
        except Exception as e:
            logger.error(f"Error actualizando PlanWidget: {e}")
            # Fallback: mostrar en log principal
            plan_tasks = plan_data.get("plan", [])
            if plan_tasks:
                plan_text = "\n".join([f"- {task}" for task in plan_tasks])
                self.log_message(f"📋 PLAN ESTRATÉGICO:\n{plan_text}", "info")
    
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
            elif msg_type == "executive_summary":
                summary = data.get('summary', 'Resumen no disponible')
                agent_role = data.get('agent_role', 'Agent')
                return f"📈 RESUMEN EJECUTIVO ({agent_role.upper()})\n\n{summary}\n\n{'*' * 60}"
            elif msg_type == "phase_end":
                status = data.get("status", "DESCONOCIDO")
                reason = data.get("reason", "")
                text = f"🏁 FASE FINALIZADA: {data.get('name', '')} - {status}"
                if reason:
                    text += f"\n{format_content(reason, 100)}"
                text += f"\n{'#' * 60}"
                return text
            else:  # info
                message = format_content(data.get('message', ''), 100)
                return f"ℹ️  {message}"
                
        elif "Agent" in source:
            if msg_type == "thought":
                content = format_content(data.get('content', ''), 110)
                return f"🤔 PENSAMIENTO ({source})\n{content}\n{'-' * 50}"
            elif msg_type == "action":
                tool = data.get('tool', 'unknown')
                args = data.get('args', {})
                if isinstance(args, dict) and 'path' in args:
                    args_str = args.get('path', 'unknown')
                    if 'content_length' in args:
                        args_str += f" ({args.get('content_length', 0)} chars)"
                else:
                    args_str = str(args)[:50] + ("..." if len(str(args)) > 50 else "")
                return f"⚡ ACCIÓN ({source}): {tool}\n{args_str}\n{'=' * 50}"
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
    
    # Acciones de teclado
    async def action_quit_screen(self) -> None:
        """Volver a la pantalla de inicio"""
        self.app.pop_screen()
    
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
        """Reconectar WebSocket"""
        if self.websocket_task:
            self.websocket_task.cancel()
            try:
                await self.websocket_task
            except asyncio.CancelledError:
                pass
        
        self.log_message("🔄 Reconectando manualmente...", "info")
        self.websocket_task = asyncio.create_task(self.listen_to_websocket())

# --- Aplicación Principal TUI ---
class DirGenTUI(App):
    """Aplicación principal que maneja la navegación entre pantallas"""
    CSS_PATH = "tui.css"
    TITLE = "DirGen Platform"
    SUB_TITLE = "Generador de Proyectos con IA"

    def on_mount(self) -> None:
        """Mostrar la pantalla de inicio al montar la aplicación"""
        self.push_screen(HomeScreen())

if __name__ == "__main__":
    DirGenTUI().run()