import { Component, Input, OnChanges, ViewChild, ElementRef, AfterViewChecked } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatExpansionModule } from '@angular/material/expansion';
import { WebSocketState, DirgenMessage } from '../../../../shared/models/dirgen.models';

@Component({
  selector: 'app-live-event-log',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule, MatChipsModule, MatExpansionModule],
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
        
      // Nuevos tipos de mensaje para el flujo de aprobación
      case 'plan_generated':
        const planMessage = (message as any).data?.message || (message as any).message;
        const defaultQuestion = '¿El plan ha sido generado. ¿Deseas proceder con la ejecución?';
        return {
          icon: '🤖',
          color: '#ff6b35',
          text: `Sistema: ${planMessage || defaultQuestion}`,
          source: 'Orquestador'
        };
        
      case 'plan_approved':
        return {
          icon: '✅',
          color: '#4caf50',
          text: `Plan aprobado: ${(message as any).data?.message || 'El usuario ha aprobado el plan'}`,
          source
        };
        
      case 'plan_rejected':
        return {
          icon: '❌',
          color: '#f44336',
          text: `Plan rechazado: ${(message as any).data?.message || 'El usuario ha rechazado el plan'}`,
          source
        };
        
      case 'executive_summary':
        return {
          icon: '📊',
          color: '#2196f3',
          text: `Resumen Ejecutivo (${(message as any).data?.agent_role || 'Agente'}): ${(message as any).data?.summary || 'Resumen disponible'}`,
          source
        };
        
      case 'retry_attempt':
        const retryData = (message as any).data;
        return {
          icon: '🔄',
          color: '#ff5722',
          text: `Reintento ${retryData?.attempt || '?'}/${retryData?.max_attempts || '?'}: ${retryData?.feedback || 'Reintentando...'}`,
          source
        };
        
      case 'quality_gate_start':
        return {
          icon: '🛡️',
          color: '#9c27b0',
          text: `Iniciando Quality Gate: ${(message as any).data?.name || 'Validación'}`,
          source
        };
        
      case 'quality_gate_result':
        const qgResult = (message as any).data;
        return {
          icon: qgResult?.success ? '🛡️✅' : '🛡️❌',
          color: qgResult?.success ? '#4caf50' : '#f44336',
          text: `Quality Gate: ${qgResult?.success ? 'Aprobado' : 'Fallido'} - ${qgResult?.message || 'Sin detalles'}`,
          source
        };
        
      case 'info':
        return {
          icon: 'ℹ️',
          color: '#2196f3',
          text: (message as any).data?.message || (message as any).message || 'Información del sistema',
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

  /**
   * Genera un resumen corto para el panel colapsado
   */
  getMessageSummary(message: any): string {
    const parsed = this.parseMessage(message);
    const maxLength = 80;
    
    // Para mensajes cortos, devolver el texto completo
    if (parsed.text.length <= maxLength) {
      return parsed.text;
    }
    
    // Para mensajes largos, crear un resumen más inteligente
    const firstSentence = parsed.text.split(/[.!?]/, 1)[0];
    if (firstSentence.length > 0 && firstSentence.length <= maxLength) {
      return firstSentence + '...';
    }
    
    // Fallback: truncar por caracteres
    return parsed.text.substring(0, maxLength) + '...';
  }

  /**
   * Determina si un mensaje debe ser expandible
   */
  isMessageExpandable(message: any): boolean {
    const parsed = this.parseMessage(message);
    
    // Expandible si el texto es largo
    if (parsed.text.length > 80) return true;
    
    // Expandible si es un mensaje de tipo debug/error que incluye JSON
    if (parsed.icon === '❓' || message.type === 'error') return true;
    
    // Expandible si incluye datos estructurados adicionales
    if (this.hasDataProperty(message) && this.getMessageData(message)) {
      const data = this.getMessageData(message);
      if (data && Object.keys(data).length > 0) return true;
    }
    
    return false;
  }

  /**
   * Formatea valores de datos adicionales para visualización
   */
  formatDataValue(value: any): string {
    if (value === null || value === undefined) {
      return 'N/A';
    }
    
    if (typeof value === 'object') {
      return JSON.stringify(value, null, 2);
    }
    
    if (typeof value === 'boolean') {
      return value ? 'Sí' : 'No';
    }
    
    return String(value);
  }

  /**
   * Helper para usar Object.entries en el template
   */
  readonly Object = Object;

  /**
   * Type guard para verificar si un mensaje tiene la propiedad data
   */
  hasDataProperty(message: any): message is DirgenMessage & { data?: any } {
    return message && typeof message === 'object' && 'data' in message;
  }

  /**
   * Obtiene de forma segura la propiedad data de un mensaje
   */
  getMessageData(message: any): any | null {
    if (!this.hasDataProperty(message)) return null;
    return (message as any).data || null;
  }

  /**
   * Obtiene las entradas de data de forma segura para el template
   */
  getDataEntries(message: any): [string, any][] {
    const data = this.getMessageData(message);
    if (!data || typeof data !== 'object') return [];
    return Object.entries(data);
  }
}
