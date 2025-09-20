import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subscription } from 'rxjs';

// Angular Material imports
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';

// Feature components - TODOS los componentes avanzados para web
import { StatusBarAdvancedComponent } from './components/status-bar-advanced/status-bar-advanced.component';
import { StatusFooterComponent } from './components/status-footer/status-footer.component';
import { ProjectControlComponent } from './components/project-control/project-control.component';
import { PlanWidgetComponent } from './components/plan-widget/plan-widget.component';
import { EventLogComponent } from '../event-log/event-log.component';
import { CommandCenterComponent } from '../command-center/command-center.component';

// Services
import { ApiService } from '../../core/services/api.service';
import { EnvironmentDetectorService } from '../../core/services/environment-detector.service';
import { DirgenMessage, WebSocketState } from '../../shared/models/dirgen.models';

@Component({
  selector: 'app-monitoring-web-advanced',
  standalone: true,
  imports: [
    CommonModule,
    MatToolbarModule,
    MatSidenavModule,
    MatCardModule,
    MatIconModule,
    MatSnackBarModule,
    StatusBarAdvancedComponent,
    StatusFooterComponent,
    ProjectControlComponent,
    PlanWidgetComponent,
    EventLogComponent,
    CommandCenterComponent
  ],
  templateUrl: './monitoring-web-advanced.component.html',
  styleUrls: ['./monitoring-web-advanced.component.scss']
})
export class MonitoringWebAdvancedComponent implements OnInit, OnDestroy {
  
  // Estado actual
  webSocketState: WebSocketState = {
    status: 'disconnected',
    messages: []
  };

  // Estados de la UI
  isFooterExpanded: boolean = false;
  showWelcomeMessage: boolean = true;

  // Subscripciones para cleanup
  private subscriptions: Subscription[] = [];

  constructor(
    private apiService: ApiService,
    private environmentDetector: EnvironmentDetectorService,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    console.log('🌐 MonitoringWebAdvanced iniciado para entorno WEB');
    console.log('🔍 Entorno detectado:', this.environmentDetector.getCurrentEnvironment());
    
    // Verificar que estamos en entorno web
    if (!this.environmentDetector.isWeb()) {
      console.warn('⚠️ MonitoringWebAdvanced cargado en entorno no-web');
    }

    this.initializeWebSocketConnection();
    this.showWelcomeMessage = true;
    
    // Ocultar mensaje de bienvenida después de 5 segundos
    setTimeout(() => {
      this.showWelcomeMessage = false;
    }, 5000);

    // Mostrar notificación de bienvenida
    this.showNotification('🌐 Interfaz Web Avanzada cargada correctamente', 'success');
  }

  ngOnDestroy(): void {
    console.log('🌐 MonitoringWebAdvanced destruido');
    // Limpiar subscripciones
    this.subscriptions.forEach(sub => sub.unsubscribe());
    
    // Desconectar WebSocket si está activo
    this.apiService.disconnectWebSocket();
  }

  private initializeWebSocketConnection(): void {
    // Escuchar el estado del WebSocket
    const wsStateSubscription = this.apiService.webSocketState$.subscribe(state => {
      console.log('📡 WebSocket state updated:', state);
      this.webSocketState = state;
      
      // Manejar cambios de estado para notificaciones
      this.handleWebSocketStateChanges(state);
    });

    this.subscriptions.push(wsStateSubscription);
  }

  private handleWebSocketStateChanges(state: WebSocketState): void {
    // Lógica adicional para manejar cambios de estado del WebSocket
    // Por ejemplo, mostrar notificaciones específicas
    
    if (state.status === 'connected' && this.webSocketState.status !== 'connected') {
      this.showNotification('🔗 Conexión establecida con el backend', 'success');
    } else if (state.status === 'error') {
      this.showNotification('❌ Error de conexión con el backend', 'error');
    } else if (state.status === 'disconnected' && this.webSocketState.status === 'connected') {
      this.showNotification('🔌 Conexión cerrada', 'info');
    }
  }

  /**
   * Maneja el evento cuando se inicia una nueva ejecución desde ProjectControl
   */
  onExecutionStarted(event: any): void {
    console.log('🎯 Ejecución iniciada desde ProjectControl:', event);
    this.showNotification('🚀 Nuevo análisis iniciado', 'success');
    
    // Lógica adicional para manejar inicio de ejecución
    // Por ejemplo, scroll automático al log, etc.
  }

  /**
   * Maneja las acciones del footer (pausar, detener, exportar, etc.)
   */
  onFooterAction(actionId: string): void {
    console.log(`🎯 Acción del footer ejecutada: ${actionId}`);
    
    switch (actionId) {
      case 'pause':
        this.handlePause();
        break;
      case 'stop':
        this.handleStop();
        break;
      case 'export':
        this.handleExport();
        break;
      case 'settings':
        this.handleSettings();
        break;
      case 'openFullLog':
        this.handleOpenFullLog();
        break;
      case 'clearMessages':
        this.handleClearMessages();
        break;
      case 'restart':
        this.handleRestart();
        break;
      case 'diagnostic':
        this.handleDiagnostic();
        break;
      case 'about':
        this.handleAbout();
        break;
      case 'shortcuts':
        this.handleShortcuts();
        break;
      case 'reset-layout':
        this.handleResetLayout();
        break;
      default:
        console.log(`⚠️ Acción no manejada: ${actionId}`);
        this.showNotification(`Acción "${actionId}" ejecutada`, 'info');
    }
  }

  // Manejadores de acciones específicas
  private handlePause(): void {
    if (this.webSocketState.status === 'connected') {
      // Lógica para pausar análisis
      this.showNotification('⏸️ Análisis pausado', 'info');
    } else {
      this.showNotification('▶️ Análisis reanudado', 'success');
    }
  }

  private handleStop(): void {
    // Lógica para detener análisis
    this.apiService.disconnectWebSocket();
    this.showNotification('⏹️ Análisis detenido', 'info');
  }

  private handleExport(): void {
    if (this.webSocketState.messages.length === 0) {
      this.showNotification('⚠️ No hay datos para exportar', 'error');
      return;
    }
    
    // Lógica para exportar datos
    const dataStr = JSON.stringify(this.webSocketState.messages, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    
    const link = document.createElement('a');
    link.href = url;
    link.download = `dirgen-log-${new Date().getTime()}.json`;
    link.click();
    
    URL.revokeObjectURL(url);
    this.showNotification('📥 Log exportado correctamente', 'success');
  }

  private handleSettings(): void {
    // Abrir configuración (en una implementación real sería un modal o ruta)
    this.showNotification('⚙️ Configuración no implementada aún', 'info');
  }

  private handleOpenFullLog(): void {
    // Abrir log completo (en una implementación real sería una nueva ventana/modal)
    console.log('📋 Abriendo log completo:', this.webSocketState.messages);
    this.showNotification('📋 Log completo mostrado en consola', 'info');
  }

  private handleClearMessages(): void {
    // Limpiar mensajes (esto sería una acción del backend en una implementación real)
    this.showNotification('🗑️ Mensajes limpiados', 'info');
  }

  private handleRestart(): void {
    // Reiniciar servicio
    this.apiService.disconnectWebSocket();
    setTimeout(() => {
      // Reconectar después de un breve delay
      this.showNotification('🔄 Servicio reiniciado', 'success');
    }, 1000);
  }

  private handleDiagnostic(): void {
    // Ejecutar diagnóstico del sistema
    const diagnosticInfo = {
      environment: this.environmentDetector.getCurrentEnvironment(),
      webSocketState: this.webSocketState,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      performance: {
        memory: (performance as any).memory ? {
          usedJSHeapSize: (performance as any).memory.usedJSHeapSize,
          totalJSHeapSize: (performance as any).memory.totalJSHeapSize,
          jsHeapSizeLimit: (performance as any).memory.jsHeapSizeLimit
        } : 'No disponible'
      }
    };
    
    console.log('🔧 Diagnóstico del sistema:', diagnosticInfo);
    this.showNotification('🔧 Diagnóstico ejecutado (ver consola)', 'info');
  }

  private handleAbout(): void {
    const aboutInfo = `
DirGen Platform - Interfaz Web Avanzada
Versión: 1.0.0
Entorno: ${this.environmentDetector.getCurrentEnvironment().type}
Desarrollado con Angular 17 + Tauri
    `;
    console.log(aboutInfo);
    this.showNotification('ℹ️ Información mostrada en consola', 'info');
  }

  private handleShortcuts(): void {
    const shortcuts = `
Atajos de teclado disponibles:
- Ctrl+R: Recargar página
- Ctrl+Shift+I: Abrir DevTools
- F5: Actualizar
- Esc: Cerrar modales
    `;
    console.log(shortcuts);
    this.showNotification('⌨️ Atajos mostrados en consola', 'info');
  }

  private handleResetLayout(): void {
    // Resetear layout a valores por defecto
    this.isFooterExpanded = false;
    this.showNotification('🎨 Layout restablecido', 'info');
  }

  private showNotification(message: string, type: 'success' | 'error' | 'info' = 'info'): void {
    const config = {
      duration: 4000,
      panelClass: [`snackbar-${type}`],
      horizontalPosition: 'end' as const,
      verticalPosition: 'top' as const
    };

    this.snackBar.open(message, 'Cerrar', config);
  }

  // Getters para el template
  get canPause(): boolean {
    return this.webSocketState.status === 'connected';
  }

  get canStop(): boolean {
    return this.webSocketState.status === 'connected';
  }

  get canExport(): boolean {
    return this.webSocketState.messages.length > 0;
  }

  get hasRecentActivity(): boolean {
    return this.webSocketState.messages.length > 0;
  }

  get isAnalysisRunning(): boolean {
    return this.webSocketState.status === 'connected';
  }
}