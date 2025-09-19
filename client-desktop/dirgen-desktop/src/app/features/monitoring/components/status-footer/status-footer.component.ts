import { Component, Input, OnInit, OnDestroy, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subscription, interval } from 'rxjs';

// Angular Material
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatMenuModule } from '@angular/material/menu';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatBadgeModule } from '@angular/material/badge';
import { MatDividerModule } from '@angular/material/divider';

// Models
import { WebSocketState, DirgenMessage } from '../../../../shared/models/dirgen.models';

// Services
import { EnvironmentDetectorService } from '../../../../core/services/environment-detector.service';

interface SystemMetrics {
  cpuUsage: number;
  memoryUsage: number;
  networkSpeed: number;
  diskUsage: number;
}

interface QuickAction {
  id: string;
  label: string;
  icon: string;
  action: () => void;
  disabled?: boolean;
  tooltip: string;
}

@Component({
  selector: 'app-status-footer',
  standalone: true,
  imports: [
    CommonModule,
    MatToolbarModule,
    MatIconModule,
    MatButtonModule,
    MatChipsModule,
    MatTooltipModule,
    MatMenuModule,
    MatProgressBarModule,
    MatBadgeModule,
    MatDividerModule
  ],
  templateUrl: './status-footer.component.html',
  styleUrls: ['./status-footer.component.scss']
})
export class StatusFooterComponent implements OnInit, OnDestroy {
  
  @Input() webSocketState!: WebSocketState;
  @Output() actionTriggered = new EventEmitter<string>();
  
  // Métricas del sistema simuladas
  systemMetrics: SystemMetrics = {
    cpuUsage: 0,
    memoryUsage: 0,
    networkSpeed: 0,
    diskUsage: 0
  };
  
  // Log resumido - últimos mensajes importantes
  recentMessages: DirgenMessage[] = [];
  
  // Estados
  isExpanded: boolean = false;
  showMetrics: boolean = true;
  
  // Acciones rápidas
  quickActions: QuickAction[] = [
    {
      id: 'pause',
      label: 'Pausar',
      icon: 'pause',
      tooltip: 'Pausar análisis actual',
      action: () => this.triggerAction('pause')
    },
    {
      id: 'stop',
      label: 'Detener',
      icon: 'stop',
      tooltip: 'Detener análisis completamente',
      action: () => this.triggerAction('stop')
    },
    {
      id: 'export',
      label: 'Exportar',
      icon: 'download',
      tooltip: 'Exportar resultados a archivo',
      action: () => this.triggerAction('export')
    },
    {
      id: 'settings',
      label: 'Configurar',
      icon: 'settings',
      tooltip: 'Abrir configuración avanzada',
      action: () => this.triggerAction('settings')
    }
  ];
  
  private subscriptions: Subscription[] = [];
  private metricsInterval?: any;

  constructor(public environmentDetector: EnvironmentDetectorService) {}

  ngOnInit(): void {
    console.log('🦶 StatusFooter iniciado para entorno WEB');
    
    // No iniciar intervalos durante compilación/SSR
    if (typeof window !== 'undefined' && typeof document !== 'undefined') {
      this.startMetricsTracking();
    }
    
    this.updateRecentMessages();
  }

  ngOnDestroy(): void {
    console.log('🦶 StatusFooter destruido');
    this.subscriptions.forEach(sub => sub.unsubscribe());
    if (this.metricsInterval) {
      clearInterval(this.metricsInterval);
    }
  }

  ngOnChanges(): void {
    this.updateRecentMessages();
    this.updateActionStates();
  }

  private startMetricsTracking(): void {
    // Simular métricas del sistema (en producción vendría de APIs reales)
    this.updateSystemMetrics();
    this.metricsInterval = setInterval(() => {
      this.updateSystemMetrics();
    }, 3000); // Actualizar cada 3 segundos
  }

  private updateSystemMetrics(): void {
    const isProcessing = this.webSocketState?.status === 'connected';
    
    // Simular métricas basadas en el estado
    if (isProcessing) {
      this.systemMetrics.cpuUsage = Math.min(85, 45 + Math.random() * 40);
      this.systemMetrics.memoryUsage = Math.min(90, 60 + Math.random() * 30);
      this.systemMetrics.networkSpeed = 1.2 + Math.random() * 2.8; // MB/s
      this.systemMetrics.diskUsage = 15 + Math.random() * 10;
    } else {
      this.systemMetrics.cpuUsage = Math.max(5, 25 - Math.random() * 20);
      this.systemMetrics.memoryUsage = Math.max(30, 50 - Math.random() * 20);
      this.systemMetrics.networkSpeed = 0.1 + Math.random() * 0.3;
      this.systemMetrics.diskUsage = 2 + Math.random() * 3;
    }
  }

  private updateRecentMessages(): void {
    if (!this.webSocketState?.messages) return;
    
    // Filtrar y obtener últimos 3 mensajes importantes
    const importantTypes = ['error', 'phase_end', 'log', 'status'];
    this.recentMessages = this.webSocketState.messages
      .filter(msg => importantTypes.includes(msg.type))
      .slice(-3)
      .reverse();
  }

  private updateActionStates(): void {
    const isRunning = this.webSocketState?.status === 'connected';
    
    this.quickActions.forEach(action => {
      switch (action.id) {
        case 'pause':
          action.disabled = !isRunning;
          action.icon = isRunning ? 'pause' : 'play_arrow';
          action.label = isRunning ? 'Pausar' : 'Reanudar';
          action.tooltip = isRunning ? 'Pausar análisis actual' : 'Reanudar análisis';
          break;
        case 'stop':
          action.disabled = !isRunning;
          break;
        case 'export':
          action.disabled = !this.webSocketState?.messages?.length;
          break;
      }
    });
  }

  public triggerAction(actionId: string): void {
    console.log(`🎯 Acción ejecutada: ${actionId}`);
    this.actionTriggered.emit(actionId);
  }

  // Métodos para el template
  toggleExpanded(): void {
    this.isExpanded = !this.isExpanded;
  }

  toggleMetrics(): void {
    this.showMetrics = !this.showMetrics;
  }

  getMetricColor(value: number, type: 'cpu' | 'memory' | 'disk'): string {
    switch (type) {
      case 'cpu':
        if (value > 80) return 'warn';
        if (value > 60) return 'accent';
        return 'primary';
      case 'memory':
        if (value > 85) return 'warn';
        if (value > 70) return 'accent';
        return 'primary';
      case 'disk':
        if (value > 50) return 'warn';
        if (value > 20) return 'accent';
        return 'primary';
      default:
        return 'primary';
    }
  }

  getMessageIcon(message: DirgenMessage): string {
    switch (message.type) {
      case 'error': return 'error';
      case 'phase_end': return 'check_circle';
      case 'log': return 'message';
      case 'status': return 'info';
      default: return 'message';
    }
  }

  getMessageColor(message: DirgenMessage): string {
    switch (message.type) {
      case 'error': return '#e74c3c';
      case 'phase_end': return '#27ae60';
      case 'log': return '#95a5a6';
      case 'status': return '#3498db';
      default: return '#95a5a6';
    }
  }

  formatTimestamp(timestamp: string): string {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('es-ES', { 
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  }

  formatNetworkSpeed(speed: number): string {
    if (speed < 1) {
      return `${Math.round(speed * 1000)} KB/s`;
    }
    return `${speed.toFixed(1)} MB/s`;
  }

  formatMemoryUsage(percentage: number): string {
    const totalGB = 16; // Simular 16GB RAM
    const usedGB = (percentage / 100) * totalGB;
    return `${usedGB.toFixed(1)}GB / ${totalGB}GB`;
  }

  openFullLog(): void {
    this.triggerAction('openFullLog');
  }

  openDocumentation(): void {
    window.open('https://docs.dirgen-platform.com', '_blank');
  }

  openConfiguration(): void {
    this.triggerAction('openConfiguration');
  }

  clearMessages(): void {
    this.triggerAction('clearMessages');
  }

  getWebSocketStatusColor(): string {
    switch (this.webSocketState?.status) {
      case 'connected': return '#27ae60';
      case 'connecting': return '#f39c12';
      case 'error': return '#e74c3c';
      case 'disconnected': return '#6c757d';
      default: return '#6c757d';
    }
  }

  // Enlaces rápidos
  quickLinks = [
    {
      label: 'Documentación',
      icon: 'help',
      action: () => this.openDocumentation(),
      tooltip: 'Abrir documentación'
    },
    {
      label: 'Configuración',
      icon: 'tune',
      action: () => this.openConfiguration(),
      tooltip: 'Configuración del sistema'
    },
    {
      label: 'Log Completo',
      icon: 'list_alt',
      action: () => this.openFullLog(),
      tooltip: 'Ver log completo'
    }
  ];
}
