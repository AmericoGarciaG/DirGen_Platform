import { Component, Input, OnInit, OnDestroy, OnChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subscription } from 'rxjs';

// Angular Material
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';

// Models
import { WebSocketState, ExecutionState, PhaseEndMessage } from '../../../../shared/models/dirgen.models';

@Component({
  selector: 'app-status-bar',
  standalone: true,
  imports: [
    CommonModule,
    MatToolbarModule,
    MatChipsModule,
    MatIconModule,
    MatTooltipModule
  ],
  templateUrl: './status-bar.component.html',
  styleUrls: ['./status-bar.component.scss']
})
export class StatusBarComponent implements OnInit, OnDestroy, OnChanges {
  
  @Input() webSocketState!: WebSocketState;
  
  // Estado de ejecución derivado
  executionState: ExecutionState = {
    isRunning: false,
    overallStatus: 'idle'
  };
  
  currentPhase: string = 'Sin actividad';
  runTime: string = '00:00:00';
  
  private subscriptions: Subscription[] = [];
  private startTime?: Date;
  private timerInterval?: any;

  constructor() {}

  ngOnInit(): void {
    this.updateExecutionState();
    this.startTimer();
  }

  ngOnDestroy(): void {
    this.subscriptions.forEach(sub => sub.unsubscribe());
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
    }
  }

  ngOnChanges(): void {
    this.updateExecutionState();
  }

  private updateExecutionState(): void {
    if (!this.webSocketState) return;

    // Determinar estado general basado en WebSocket y mensajes
    if (this.webSocketState.status === 'connected' && this.webSocketState.runId) {
      this.executionState.isRunning = true;
      this.executionState.runId = this.webSocketState.runId;
      this.executionState.overallStatus = 'running';
      
      if (!this.startTime) {
        this.startTime = new Date();
      }
    } else if (this.webSocketState.status === 'disconnected' && this.executionState.isRunning) {
      this.executionState.isRunning = false;
      this.executionState.overallStatus = 'completed';
    } else if (this.webSocketState.status === 'error') {
      this.executionState.overallStatus = 'failed';
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
        this.currentPhase = lastPhaseMessage.data.name;
      }
    } else if (this.webSocketState.messages.length > 0) {
      // Si hay mensajes pero no de fase, mostrar que está procesando
      this.currentPhase = 'Procesando...';
    }
  }

  private startTimer(): void {
    this.timerInterval = setInterval(() => {
      if (this.startTime && this.executionState.isRunning) {
        const elapsed = Date.now() - this.startTime.getTime();
        this.runTime = this.formatTime(elapsed);
      }
    }, 1000);
  }

  private formatTime(milliseconds: number): string {
    const totalSeconds = Math.floor(milliseconds / 1000);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;

    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
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

  formatRunId(runId?: string): string {
    if (!runId) return 'N/A';
    return runId.substring(0, 8) + '...';
  }
}