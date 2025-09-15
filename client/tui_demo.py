#!/usr/bin/env python3
"""
Versión de demostración del TUI mejorado
Muestra cómo se ven las mejoras sin conectar al orquestador
"""

import asyncio
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Header, Footer, Static, Log
from tui import StatusBlock, format_message_content

class DirGenTUIDemo(App):
    CSS_PATH = "tui.css"
    BINDINGS = [
        ("q", "quit", "Salir"),
        ("d", "show_demo", "Demo"),
        ("c", "clear_log", "Limpiar")
    ]
    TITLE = "DirGen Platform - Demo UI Mejorado"
    SUB_TITLE = "Demostrando las mejoras visuales"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="main_container"):
            with Vertical():
                yield Static(
                    "🤖 [bold cyan]DirGen Platform[/] - [italic]Demo de Interfaz Mejorada[/]\n"
                    "⚙️  [yellow]Estado:[/] Demostrando mejoras visuales\n"
                    "✨ [green]Nuevo diseño[/] con saltos de línea automáticos", 
                    id="status_header", 
                    classes="status-panel"
                )
                yield Log(id="log_view", auto_scroll=True, highlight=True)
        yield Footer()

    def on_mount(self) -> None:
        """Al cargar la aplicación, mostrar mensaje de bienvenida"""
        log = self.query_one(Log)
        log.can_focus = False
        
        # Mensaje de bienvenida
        welcome_msg = (
            "🎉 [bold green]¡Bienvenido al TUI Mejorado de DirGen![/]\n\n"
            "Mejoras implementadas:\n"
            "✅ Saltos de línea automáticos\n"
            "✅ Colores y tema moderno\n" 
            "✅ Mejor organización visual\n"
            "✅ Emojis descriptivos\n"
            "✅ Separadores para mejor legibilidad\n\n"
            "Presiona [bold yellow]D[/] para ver ejemplos de mensajes\n"
            "Presiona [bold yellow]C[/] para limpiar el log\n"
            "Presiona [bold yellow]Q[/] para salir"
        )
        log.write_line(welcome_msg)

    async def action_quit(self) -> None:
        """Salir de la aplicación"""
        self.exit()
    
    async def action_clear_log(self) -> None:
        """Limpiar el log"""
        log = self.query_one(Log)
        log.clear()
        log.write_line("🗑️ [yellow]Log limpiado[/]")
    
    async def action_show_demo(self) -> None:
        """Mostrar ejemplos de los diferentes tipos de mensajes"""
        log = self.query_one(Log)
        
        # Separador
        log.write_line("\n" + "─" * 80)
        log.write_line("🎯 [bold magenta]DEMOSTRACIÓN DE MENSAJES[/]")
        log.write_line("─" * 80 + "\n")
        
        # 1. Mensaje de inicio de fase
        phase_start = {
            "source": "Orchestrator",
            "type": "phase_start",
            "data": {"name": "Diseño"}
        }
        block = StatusBlock(phase_start)
        log.write_line(str(block))
        
        await asyncio.sleep(0.5)
        
        # 2. Pensamiento largo
        thought_data = {
            "source": "Planner Agent",
            "type": "thought", 
            "data": {
                "content": "Comenzaré creando el diagrama de arquitectura general utilizando PlantUML. Este diagrama proporcionará una vista de alto nivel de los componentes del sistema, su interacción y el flujo de datos. Utilizaré el estándar C4 para estructurar el diagrama y asegurar claridad en la comunicación de la arquitectura. Los componentes principales incluirán los microservicios, el broker de mensajes RabbitMQ, y la base de datos TimescaleDB."
            }
        }
        block = StatusBlock(thought_data)
        log.write_line(str(block))
        
        await asyncio.sleep(0.5)
        
        # 3. Acción
        action_data = {
            "source": "Planner Agent",
            "type": "action",
            "data": {
                "tool": "writeFile",
                "args": {
                    "path": "design/architecture.puml",
                    "content_length": 1440
                }
            }
        }
        block = StatusBlock(action_data)
        log.write_line(str(block))
        
        await asyncio.sleep(0.5)
        
        # 4. Quality Gate exitoso
        qg_success = {
            "source": "Orchestrator",
            "type": "quality_gate_result",
            "data": {
                "success": True,
                "message": "Todos los artefactos de diseño fueron generados exitosamente. Se han validado los siguientes archivos: design/architecture.puml, design/api/collector.yml, design/api/quality.yml, design/api/storage.yml, design/api/api.yml, design/api/backfill.yml. El sistema está listo para continuar a la siguiente fase."
            }
        }
        block = StatusBlock(qg_success)
        log.write_line(str(block))
        
        await asyncio.sleep(0.5)
        
        # 5. Error ejemplo
        error_data = {
            "source": "Planner Agent",
            "type": "error",
            "data": {
                "message": "La Acción no era un JSON válido: Expecting value: line 1 column 1 (char 0). Esto puede ocurrir cuando el LLM no genera una respuesta correctamente formateada o cuando hay problemas de conectividad temporal."
            }
        }
        block = StatusBlock(error_data)
        log.write_line(str(block))
        
        await asyncio.sleep(0.5)
        
        # 6. Fin de fase
        phase_end = {
            "source": "Orchestrator",
            "type": "phase_end",
            "data": {"name": "Diseño", "status": "APROBADO"}
        }
        block = StatusBlock(phase_end)
        log.write_line(str(block))
        
        log.write_line("\n✨ [bold green]Demo completada[/] - Observa cómo los mensajes largos se ajustan automáticamente")
        log.write_line("🎯 [cyan]Ya no necesitas desplazarte horizontalmente[/]")

if __name__ == "__main__":
    DirGenTUIDemo().run()