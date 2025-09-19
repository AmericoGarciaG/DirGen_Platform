import { Component, Input, OnChanges, ViewChild, ElementRef, AfterViewChecked } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { WebSocketState, DirgenMessage } from '../../../../shared/models/dirgen.models';

@Component({
  selector: 'app-live-event-log',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule, MatChipsModule],
  templateUrl: './live-event-log.component.html',
  styleUrls: ['./live-event-log.component.scss']
})
export class LiveEventLogComponent implements OnChanges, AfterViewChecked {
  @Input() webSocketState!: WebSocketState;
  @ViewChild('logContainer', { static: false }) private logContainer!: ElementRef;
  
  private shouldScrollToBottom = false;

  ngOnChanges(): void {
    // Marcar para auto-scroll cuando lleguen nuevos mensajes
    this.shouldScrollToBottom = true;
  }

  ngAfterViewChecked(): void {
    // Auto-scroll al final después de renderizar
    if (this.shouldScrollToBottom) {
      this.scrollToBottom();
      this.shouldScrollToBottom = false;
    }
  }

  private scrollToBottom(): void {
    try {
      if (this.logContainer) {
        this.logContainer.nativeElement.scrollTop = this.logContainer.nativeElement.scrollHeight;
      }
    } catch (err) {
      console.warn('Error al hacer scroll:', err);
    }
  }

  /**
   * Parsea y formatea un mensaje según su tipo
   */
  parseMessage(message: any): { icon: string; color: string; text: string; source: string } {
    // Determinar si es un mensaje estructurado o texto crudo
    if (typeof message === 'string') {
      return {
        icon: '💬',
        color: '#95a5a6',
        text: message,
        source: 'Backend'
      };
    }

    // Mensajes con estructura conocida
    if (message.type) {
      return this.parseStructuredMessage(message);
    }

    // Mensajes crudos que vienen como JSON
    if (message.message) {
      return {
        icon: '📨',
        color: '#3498db',
        text: message.message,
        source: message.source || 'Sistema'
      };
    }

    // Fallback para cualquier otro formato
    return {
      icon: '❓',
      color: '#95a5a6',
      text: JSON.stringify(message, null, 2),
      source: 'Desconocido'
    };
  }

  private parseStructuredMessage(message: DirgenMessage): { icon: string; color: string; text: string; source: string } {
    const source = message.source || 'Sistema';
    
    switch (message.type) {
      case 'phase_start':
        return {
          icon: '🚀',
          color: '#f39c12',
          text: `Iniciando fase: ${(message as any).phase || 'Desconocida'}`,
          source
        };
        
      case 'phase_end':
        const phaseEndMsg = message as any;
        const status = phaseEndMsg.data?.status || 'DESCONOCIDO';
        const name = phaseEndMsg.data?.name || 'Fase';
        const statusColor = status === 'APROBADO' ? '#27ae60' : status === 'RECHAZADO' ? '#e74c3c' : '#f39c12';
        
        return {
          icon: status === 'APROBADO' ? '✅' : status === 'RECHAZADO' ? '❌' : '⏳',
          color: statusColor,
          text: `${name}: ${status}`,
          source
        };
        
      case 'thought':
        return {
          icon: '💭',
          color: '#9b59b6',
          text: (message as any).content || 'Pensamiento del sistema',
          source
        };
        
      case 'action':
        return {
          icon: '⚡',
          color: '#e67e22',
          text: `Acción: ${(message as any).action || 'Ejecutando...'}`,
          source
        };
        
      case 'error':
        return {
          icon: '🚨',
          color: '#e74c3c',
          text: (message as any).error || 'Error del sistema',
          source
        };
        
      case 'log':
        const logMsg = message as any;
        const level = logMsg.level || 'info';
        const icons: any = { error: '🚨', warn: '⚠️', info: 'ℹ️', debug: '🔧' };
        const colors: any = { error: '#e74c3c', warn: '#f39c12', info: '#3498db', debug: '#95a5a6' };
        
        return {
          icon: icons[level] || 'ℹ️',
          color: colors[level] || '#3498db',
          text: logMsg.message || 'Log del sistema',
          source
        };
        
      default:
        return {
          icon: '📄',
          color: '#34495e',
          text: (message as any).message || `Mensaje tipo: ${message.type}`,
          source
        };
    }
  }

  /**
   * Formatea timestamp para display
   */
  formatTimestamp(timestamp: string): string {
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString('es-ES', { 
        hour: '2-digit', 
        minute: '2-digit', 
        second: '2-digit' 
      });
    } catch {
      return timestamp;
    }
  }

  /**
   * Trunca texto largo para mejor visualización
   */
  truncateText(text: string, maxLength: number = 200): string {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  }
}