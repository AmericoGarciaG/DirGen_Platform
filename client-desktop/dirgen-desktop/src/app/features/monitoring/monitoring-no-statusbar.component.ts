import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subscription } from 'rxjs';

// Angular Material imports
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';

// Feature components (TODOS menos StatusBar)
import { ProjectControlComponent } from './components/project-control/project-control.component';
import { PlanWidgetComponent } from './components/plan-widget/plan-widget.component';
import { LiveEventLogComponent } from './components/live-event-log/live-event-log.component';

// Services
import { ApiService } from '../../core/services/api.service';
import { DirgenMessage, WebSocketState } from '../../shared/models/dirgen.models';

@Component({
  selector: 'app-monitoring-no-statusbar',
  standalone: true,
  imports: [
    CommonModule,
    MatToolbarModule,
    MatSidenavModule,
    MatCardModule,
    MatIconModule,
    ProjectControlComponent,
    PlanWidgetComponent,
    LiveEventLogComponent
  ],
  template: `
    <div class="monitoring-dashboard">
      
      <!-- StatusBar SIMULADO simple (sin el componente problemático) -->
      <div class="simple-status-bar">
        <mat-icon>dashboard</mat-icon>
        <span class="app-title">DirGen Monitor Desktop</span>
        <span class="status-indicator" [style.color]="getStatusColor()">
          {{ getStatusText() }}
        </span>
        <span class="message-count" *ngIf="webSocketState.messages.length">
          📧 {{ webSocketState.messages.length }}
        </span>
      </div>
      
      <!-- Main Content - Layout horizontal con paneles -->
      <div class="main-content">
        
        <!-- Left Panel - Panel izquierdo (35% del ancho) -->
        <div class="left-panel">
          
          <!-- Project Control Section -->
          <app-project-control 
            class="project-control-section"
            (executionStarted)="onExecutionStarted($event)">
          </app-project-control>
          
          <!-- Plan Widget Section -->
          <app-plan-widget 
            [webSocketState]="webSocketState"
            class="plan-widget-section">
          </app-plan-widget>
          
        </div>
        
        <!-- Right Panel - Panel derecho (65% del ancho) -->
        <div class="right-panel">
          
          <!-- Live Event Log -->
          <app-live-event-log 
            [webSocketState]="webSocketState"
            class="live-event-log-section">
          </app-live-event-log>
          
        </div>
        
      </div>
      
    </div>
  `,
  styleUrls: ['./monitoring.component.scss']
})
export class MonitoringNoStatusbarComponent implements OnInit, OnDestroy {
  
  // Estado actual
  webSocketState: WebSocketState = {
    status: 'disconnected',
    messages: []
  };

  // Subscripciones para cleanup
  private subscriptions: Subscription[] = [];

  constructor(private apiService: ApiService) {}

  ngOnInit(): void {
    console.log('🚀 MonitoringNoStatusbar iniciado - SIN StatusBar problemático');
    
    // Escuchar el estado del WebSocket
    const wsStateSubscription = this.apiService.webSocketState$.subscribe(state => {
      console.log('📡 WebSocket state updated:', state);
      this.webSocketState = state;
    });

    this.subscriptions.push(wsStateSubscription);
  }

  ngOnDestroy(): void {
    console.log('🚀 MonitoringNoStatusbar destruido');
    // Limpiar subscripciones
    this.subscriptions.forEach(sub => sub.unsubscribe());
    
    // Desconectar WebSocket si está activo
    this.apiService.disconnectWebSocket();
  }

  /**
   * Maneja el evento cuando se inicia una nueva ejecución
   */
  onExecutionStarted(event: any): void {
    console.log('🎯 Ejecución iniciada:', event);
    // Aquí podemos agregar lógica adicional si es necesario
  }

  // Helper methods para el status bar simple
  getStatusColor(): string {
    switch (this.webSocketState.status) {
      case 'connected': return '#27ae60';
      case 'connecting': return '#f39c12';
      case 'error': return '#e74c3c';
      default: return '#95a5a6';
    }
  }

  getStatusText(): string {
    switch (this.webSocketState.status) {
      case 'connected': return '✅ Conectado';
      case 'connecting': return '🔄 Conectando...';
      case 'error': return '❌ Error';
      default: return '⚪ Desconectado';
    }
  }
}