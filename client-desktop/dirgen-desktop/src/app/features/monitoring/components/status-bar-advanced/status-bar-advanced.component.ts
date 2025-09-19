import { Component, Input, OnInit, OnDestroy, OnChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subscription, interval } from 'rxjs';

// Angular Material
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatButtonModule } from '@angular/material/button';
import { MatBadgeModule } from '@angular/material/badge';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';

// Models
import { WebSocketState, ExecutionState, PhaseEndMessage } from '../../../../shared/models/dirgen.models';

// Services
import { EnvironmentDetectorService } from '../../../../core/services/environment-detector.service';

@Component({
  selector: 'app-status-bar-advanced',
  standalone: true,
  imports: [
    CommonModule,
    MatToolbarModule,
    MatChipsModule,
    MatIconModule,
    MatTooltipModule,
    MatProgressBarModule,
    MatButtonModule,
    MatBadgeModule,
    MatSnackBarModule
  ],
  templateUrl: './status-bar-advanced.component.html',
  styleUrls: ['./status-bar-advanced.component.scss']
})
export class StatusBarAdvancedComponent implements OnInit, OnDestroy, OnChanges {
  
  @Input() webSocketState!: WebSocketState;
  
  // Estado de ejecución derivado
  executionState: ExecutionState = {
    isRunning: false,
    overallStatus: 'idle'
  };
  
  // Métricas en tiempo real
  currentTime: string = '00:00:00';
  currentPhase: string = 'Sin actividad';
  runTime: string = '00:00:00';
  progressPercentage: number = 0;
  
  // Estadísticas avanzadas
  processedFiles: number = 0;
  totalFiles: number = 0;
  processingSpeed: number = 0;
  completionPercentage: number = 0;
  estimatedTimeRemaining: string = '';
  
  // Estados de animación
  isProcessing: boolean = false;
  showSuccessAnimation: boolean = false;
  
  private subscriptions: Subscription[] = [];
  private startTime?: Date;
  private timerInterval?: any;
  private clockInterval?: any;
  private statsInterval?: any;
  
  // Historial para calcular velocidad
  private processingHistory: { timestamp: number; count: number }[] = [];

  constructor(
    private environmentDetector: EnvironmentDetectorService,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    console.log('🚀 StatusBarAdvanced iniciado para entorno WEB');
    
    // No iniciar intervalos durante compilación/SSR
    if (typeof window !== 'undefined' && typeof document !== 'undefined') {
      this.startClock();
      this.startTimer();
      this.startStatsTracking();
    }
    
    this.updateExecutionState();
  }

  ngOnDestroy(): void {
    console.log('🚀 StatusBarAdvanced destruido');
    this.subscriptions.forEach(sub => sub.unsubscribe());
    this.clearIntervals();
  }

  ngOnChanges(): void {
    this.updateExecutionState();
    this.calculateStatistics();
  }

  private clearIntervals(): void {
    if (this.timerInterval) clearInterval(this.timerInterval);
    if (this.clockInterval) clearInterval(this.clockInterval);
    if (this.statsInterval) clearInterval(this.statsInterval);
  }

  private startClock(): void {
    this.updateClock();
    this.clockInterval = setInterval(() => {
      this.updateClock();
    }, 1000);
  }

  private updateClock(): void {
    const now = new Date();
    this.currentTime = now.toLocaleTimeString('es-ES', { 
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  }

  private startTimer(): void {
    this.timerInterval = setInterval(() => {
      if (this.startTime && this.executionState.isRunning) {
        const elapsed = Date.now() - this.startTime.getTime();
        this.runTime = this.formatTime(elapsed);
        this.calculateETA();
      }
    }, 1000);
  }

  private startStatsTracking(): void {
    this.statsInterval = setInterval(() => {
      this.updateProcessingSpeed();
    }, 2000); // Actualizar cada 2 segundos
  }

  private updateExecutionState(): void {
    if (!this.webSocketState) return;

    const wasRunning = this.executionState.isRunning;

    // Determinar estado general basado en WebSocket y mensajes
    if (this.webSocketState.status === 'connected' && this.webSocketState.runId) {
      this.executionState.isRunning = true;
      this.executionState.runId = this.webSocketState.runId;
      this.executionState.overallStatus = 'running';
      this.isProcessing = true;
      
      if (!this.startTime) {
        this.startTime = new Date();
        this.showNotification('🚀 Análisis iniciado', 'success');
      }
    } else if (this.webSocketState.status === 'disconnected' && this.executionState.isRunning) {
      this.executionState.isRunning = false;
      this.executionState.overallStatus = 'completed';
      this.isProcessing = false;
      this.showSuccessAnimation = true;
      this.showNotification('✅ Análisis completado', 'success');
      
      setTimeout(() => {
        this.showSuccessAnimation = false;
      }, 3000);
    } else if (this.webSocketState.status === 'error') {
      this.executionState.overallStatus = 'failed';
      this.isProcessing = false;
      this.showNotification('❌ Error en el análisis', 'error');
    }

    // Extraer fase actual de los mensajes
    this.extractCurrentPhase();
  }

  private extractCurrentPhase(): void {
    if (!this.webSocketState.messages?.length) return;

    // Buscar el último mensaje de phase_end para determinar la fase actual
    const phaseMessages = this.webSocketState.messages
      .filter(msg => msg.type === 'phase_end')
      .reverse();

    if (phaseMessages.length > 0) {
      const lastPhaseMessage = phaseMessages[0] as PhaseEndMessage;
      if (lastPhaseMessage.data?.name) {
        const oldPhase = this.currentPhase;
        this.currentPhase = lastPhaseMessage.data.name;
        
        if (oldPhase !== this.currentPhase) {
          this.showNotification(`🔄 ${this.currentPhase}`, 'info');
        }
      }
    } else if (this.webSocketState.messages.length > 0) {
      this.currentPhase = 'Procesando...';
    }
  }

  getConnectionStatusText(): string {
    switch (this.webSocketState?.status) {
      case 'connected': return 'Conectado';
      case 'connecting': return 'Conectando...';
      case 'disconnected': return 'Desconectado';
      case 'error': return 'Error de conexión';
      default: return 'Sin estado';
    }
  }
  
  private calculateStatistics(): void {
    if (!this.webSocketState.messages?.length) return;

    // Simular estadísticas basadas en mensajes (en una implementación real vendría del backend)
    const messageCount = this.webSocketState.messages.length;
    
    // Estimar archivos procesados basado en mensajes
    this.processedFiles = Math.floor(messageCount * 0.7); // Aproximación
    this.totalFiles = this.processedFiles > 0 ? Math.ceil(this.processedFiles * 1.3) : 100;
    
    // Calcular porcentaje de completitud
    if (this.totalFiles > 0) {
      this.completionPercentage = Math.round((this.processedFiles / this.totalFiles) * 100);
      this.progressPercentage = Math.min(this.completionPercentage, 100);
    }

    // Guardar para calcular velocidad
    this.processingHistory.push({
      timestamp: Date.now(),
      count: this.processedFiles
    });

    // Mantener solo los últimos 10 puntos de datos
    if (this.processingHistory.length > 10) {
      this.processingHistory.shift();
    }
  }

  private updateProcessingSpeed(): void {
    if (this.processingHistory.length < 2) return;

    const recent = this.processingHistory[this.processingHistory.length - 1];
    const previous = this.processingHistory[this.processingHistory.length - 2];

    if (recent && previous) {
      const timeDiff = (recent.timestamp - previous.timestamp) / 1000; // segundos
      const filesDiff = recent.count - previous.count;
      
      if (timeDiff > 0) {
        this.processingSpeed = Math.round((filesDiff / timeDiff) * 10) / 10; // 1 decimal
      }
    }
  }

  private calculateETA(): void {
    if (this.processingSpeed > 0 && this.totalFiles > this.processedFiles) {
      const remainingFiles = this.totalFiles - this.processedFiles;
      const etaSeconds = remainingFiles / this.processingSpeed;
      this.estimatedTimeRemaining = this.formatTime(etaSeconds * 1000);
    } else {
      this.estimatedTimeRemaining = '';
    }
  }

  private formatTime(milliseconds: number): string {
    const totalSeconds = Math.floor(milliseconds / 1000);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;

    if (hours > 0) {
      return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    } else {
      return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }
  }

  private showNotification(message: string, type: 'success' | 'error' | 'info' = 'info'): void {
    const config = {
      duration: 3000,
      panelClass: [`snackbar-${type}`],
      horizontalPosition: 'end' as const,
      verticalPosition: 'top' as const
    };

    this.snackBar.open(message, 'Cerrar', config);
  }

  // Helpers para el template
  getStatusColor(): string {
    switch (this.executionState.overallStatus) {
      case 'idle': return '#6c757d';
      case 'starting': return '#fd7e14';
      case 'running': return '#28a745';
      case 'completed': return '#007bff';
      case 'failed': return '#dc3545';
      default: return '#6c757d';
    }
  }

  getStatusIcon(): string {
    switch (this.executionState.overallStatus) {
      case 'idle': return 'pause_circle';
      case 'starting': return 'hourglass_empty';
      case 'running': return 'play_circle';
      case 'completed': return 'check_circle';
      case 'failed': return 'error';
      default: return 'help';
    }
  }

  getStatusText(): string {
    switch (this.executionState.overallStatus) {
      case 'idle': return 'Sin actividad';
      case 'starting': return 'Iniciando...';
      case 'running': return 'En ejecución';
      case 'completed': return 'Completado';
      case 'failed': return 'Error';
      default: return 'Desconocido';
    }
  }

  getProgressColor(): string {
    if (this.completionPercentage < 30) return 'warn';
    if (this.completionPercentage < 70) return 'accent';
    return 'primary';
  }

  getPhaseDescription(): string {
    const phaseDescriptions: { [key: string]: string } = {
      'Procesando...': 'Analizando estructura del proyecto',
      'Scanning': 'Explorando archivos y directorios',
      'Analyzing': 'Analizando contenido y dependencias',
      'Generating': 'Generando documentación',
      'Finalizing': 'Finalizando proceso'
    };
    
    return phaseDescriptions[this.currentPhase] || 'Procesando información';
  }

  copyRunId(): void {
    if (this.executionState.runId) {
      navigator.clipboard.writeText(this.executionState.runId).then(() => {
        this.showNotification('📋 Run ID copiado al portapapeles', 'success');
      }).catch(() => {
        this.showNotification('❌ Error al copiar Run ID', 'error');
      });
    }
  }

  formatRunId(runId?: string): string {
    if (!runId) return 'N/A';
    return runId.substring(0, 8) + '...';
  }

  formatDetailedTime(): string {
    if (!this.runTime) return '00:00';
    
    // Si es menos de una hora, mostrar MM:SS
    if (this.runTime.length <= 5) {
      return this.runTime;
    }
    
    // Si es más de una hora, mostrar HH:MM:SS
    return this.runTime;
  }

  getWebSocketStatusColor(): string {
    switch (this.webSocketState?.status) {
      case 'connected': return '#28a745';
      case 'connecting': return '#fd7e14';
      case 'error': return '#dc3545';
      case 'disconnected': return '#6c757d';
      default: return '#6c757d';
    }
  }

  getWebSocketStatusIcon(): string {
    switch (this.webSocketState?.status) {
      case 'connected': return 'wifi';
      case 'connecting': return 'wifi_find';
      case 'error': return 'wifi_off';
      case 'disconnected': return 'wifi_off';
      default: return 'help';
    }
  }

  getWebSocketStatusText(): string {
    switch (this.webSocketState?.status) {
      case 'connected': return 'Conectado';
      case 'connecting': return 'Conectando...';
      case 'error': return 'Error';
      case 'disconnected': return 'Desconectado';
      default: return 'Desconocido';
    }
  }
}
