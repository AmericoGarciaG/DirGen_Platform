import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Store } from '@ngrx/store';
import { Observable, Subscription } from 'rxjs';
import { map } from 'rxjs/operators';

// Angular Material
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';

// Services
import { ApiService } from '../../core/services/api.service';

// Store
import { AppState } from '../../store/models';
import * as AppSelectors from '../../store/app.selectors';

export interface EventLogEntry {
  id: string;
  timestamp: string;
  source: string;
  message: string;
  type: string;
  level?: string;
}

@Component({
  selector: 'app-event-log',
  standalone: true,
  imports: [
    CommonModule,
    MatIconModule,
    MatCardModule
  ],
  template: `
    <div class="event-log-container">
      <div class="log-header">
        <mat-icon>article</mat-icon>
        <h3>Log de Eventos</h3>
        <div class="connection-indicator" 
             [class.connected]="webSocketConnected$ | async"
             [class.disconnected]="!(webSocketConnected$ | async)">
          <mat-icon>{{ (webSocketConnected$ | async) ? 'wifi' : 'wifi_off' }}</mat-icon>
        </div>
      </div>
      
      <div class="log-content" #logContainer>
        <ng-container *ngIf="events.length > 0; else noEvents">
          <div *ngFor="let event of events; trackBy: trackByEventId" 
               class="event-entry"
               [class.error]="event.level === 'error'"
               [class.warning]="event.level === 'warning'"
               [class.info]="event.level === 'info'"
               [class.success]="event.type === 'plan_generated' || event.type === 'execution_started'">
            
            <div class="event-time">{{ formatTime(event.timestamp) }}</div>
            <div class="event-source">{{ event.source || 'Sistema' }}</div>
            <div class="event-message">{{ event.message || event.type }}</div>
            <div class="event-type">{{ getEventTypeLabel(event.type) }}</div>
          </div>
        </ng-container>
        
        <ng-template #noEvents>
          <div class="no-events">
            <mat-icon>hourglass_empty</mat-icon>
            <p>Esperando eventos...</p>
          </div>
        </ng-template>
      </div>
    </div>
  `,
  styles: [`
    .event-log-container {
      display: flex;
      flex-direction: column;
      height: 100%;
      background: #1a1a1a;
      border-radius: 8px;
      overflow: hidden;
    }

    .log-header {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 12px 16px;
      background: #2d2d30;
      border-bottom: 1px solid #404040;
      
      mat-icon {
        color: #ff9800;
        font-size: 18px;
        width: 18px;
        height: 18px;
      }
      
      h3 {
        margin: 0;
        font-size: 14px;
        font-weight: 600;
        color: #e0e0e0;
        flex: 1;
      }
      
      .connection-indicator {
        display: flex;
        align-items: center;
        
        mat-icon {
          font-size: 16px;
          width: 16px;
          height: 16px;
        }
        
        &.connected mat-icon {
          color: #4caf50;
        }
        
        &.disconnected mat-icon {
          color: #666;
        }
      }
    }

    .log-content {
      flex: 1;
      overflow-y: auto;
      padding: 8px;
      
      .event-entry {
        display: grid;
        grid-template-columns: 80px 100px 1fr 80px;
        gap: 8px;
        padding: 6px 8px;
        margin: 2px 0;
        border-radius: 4px;
        font-size: 11px;
        border-left: 2px solid transparent;
        transition: all 0.2s ease;
        
        &:hover {
          background: rgba(255, 255, 255, 0.02);
        }
        
        &.error {
          background: rgba(244, 67, 54, 0.1);
          border-left-color: #f44336;
        }
        
        &.warning {
          background: rgba(255, 152, 0, 0.1);
          border-left-color: #ff9800;
        }
        
        &.info {
          background: rgba(33, 150, 243, 0.1);
          border-left-color: #2196f3;
        }
        
        &.success {
          background: rgba(76, 175, 80, 0.1);
          border-left-color: #4caf50;
        }
        
        .event-time {
          color: #888;
          font-family: 'Courier New', monospace;
          font-size: 10px;
        }
        
        .event-source {
          color: #007acc;
          font-weight: 600;
          text-overflow: ellipsis;
          overflow: hidden;
          white-space: nowrap;
        }
        
        .event-message {
          color: #e0e0e0;
          text-overflow: ellipsis;
          overflow: hidden;
          white-space: nowrap;
        }
        
        .event-type {
          color: #888;
          font-size: 9px;
          text-align: right;
          text-transform: uppercase;
        }
      }
      
      .no-events {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 150px;
        color: #666;
        text-align: center;
        
        mat-icon {
          font-size: 32px;
          width: 32px;
          height: 32px;
          margin-bottom: 8px;
          opacity: 0.5;
        }
        
        p {
          margin: 0;
          font-style: italic;
        }
      }
    }

    // Scrollbar styling
    .log-content::-webkit-scrollbar {
      width: 4px;
    }

    .log-content::-webkit-scrollbar-track {
      background: #1a1a1a;
    }

    .log-content::-webkit-scrollbar-thumb {
      background: #404040;
      border-radius: 2px;
      
      &:hover {
        background: #505050;
      }
    }

    // Responsive
    @media (max-width: 768px) {
      .log-content .event-entry {
        grid-template-columns: 60px 80px 1fr 60px;
        font-size: 10px;
        padding: 4px 6px;
      }
    }
  `]
})
export class EventLogComponent implements OnInit, OnDestroy {
  
  events: EventLogEntry[] = [];
  webSocketConnected$: Observable<boolean>;
  
  private subscriptions: Subscription[] = [];
  
  constructor(
    private store: Store<AppState>,
    private apiService: ApiService
  ) {
    this.webSocketConnected$ = this.store.select(AppSelectors.selectWebSocketConnected);
  }
  
  ngOnInit(): void {
    // Subscribe to WebSocket messages
    const messagesSubscription = this.apiService.messages$.subscribe(message => {
      this.addEvent({
        id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
        timestamp: message.timestamp || new Date().toISOString(),
        source: message.source || 'Sistema',
        message: this.getMessageText(message),
        type: message.type || 'info',
        level: (message as any).level || 'info'
      });
    });
    
    this.subscriptions.push(messagesSubscription);
  }
  
  ngOnDestroy(): void {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }
  
  private addEvent(event: EventLogEntry): void {
    this.events.push(event);
    
    // Limit to last 100 events
    if (this.events.length > 100) {
      this.events = this.events.slice(-100);
    }
    
    // Auto-scroll to bottom
    setTimeout(() => {
      const logContainer = document.querySelector('.log-content');
      if (logContainer) {
        logContainer.scrollTop = logContainer.scrollHeight;
      }
    }, 50);
  }
  
  private getMessageText(message: any): string {
    if (message.message) return message.message;
    if (message.data?.message) return message.data.message;
    if (message.type === 'plan_generated') return 'Plan de ejecución generado';
    if (message.type === 'execution_started') return 'Ejecución iniciada';
    if (message.type === 'file_operation') return `Operación de archivo: ${message.data?.operation || 'unknown'}`;
    if (message.type === 'phase_end') return `Fase completada: ${message.data?.name || 'unknown'}`;
    return message.type || 'Evento del sistema';
  }
  
  formatTime(timestamp: string): string {
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString('es-ES', { 
        hour: '2-digit', 
        minute: '2-digit', 
        second: '2-digit' 
      });
    } catch {
      return timestamp.substring(0, 8) || '--:--:--';
    }
  }
  
  getEventTypeLabel(type: string): string {
    const typeLabels: { [key: string]: string } = {
      'plan_generated': 'PLAN',
      'execution_started': 'EXEC',
      'file_operation': 'FILE',
      'phase_end': 'PHASE',
      'action': 'ACTION',
      'log': 'LOG',
      'error': 'ERROR',
      'info': 'INFO'
    };
    
    return typeLabels[type] || type.toUpperCase();
  }
  
  trackByEventId(index: number, event: EventLogEntry): string {
    return event.id;
  }
}