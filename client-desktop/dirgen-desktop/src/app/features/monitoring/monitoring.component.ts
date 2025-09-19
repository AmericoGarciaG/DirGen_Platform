import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subscription } from 'rxjs';

// Angular Material imports
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';

// Feature components
import { StatusBarComponent } from './components/status-bar/status-bar.component';
import { ProjectControlComponent } from './components/project-control/project-control.component';
import { PlanWidgetComponent } from './components/plan-widget/plan-widget.component';
import { LiveEventLogComponent } from './components/live-event-log/live-event-log.component';

// Services
import { ApiService } from '../../core/services/api.service';
import { DirgenMessage, WebSocketState } from '../../shared/models/dirgen.models';

@Component({
  selector: 'app-monitoring',
  standalone: true,
  imports: [
    CommonModule,
    MatToolbarModule,
    MatSidenavModule,
    MatCardModule,
    MatIconModule,
    StatusBarComponent,
    ProjectControlComponent,
    PlanWidgetComponent,
    LiveEventLogComponent
  ],
  templateUrl: './monitoring.component.html',
  styleUrls: ['./monitoring.component.scss']
})
export class MonitoringComponent implements OnInit, OnDestroy {
  
  // Estado actual
  webSocketState: WebSocketState = {
    status: 'disconnected',
    messages: []
  };

  // Subscripciones para cleanup
  private subscriptions: Subscription[] = [];

  constructor(private apiService: ApiService) {}

  ngOnInit(): void {
    // Escuchar el estado del WebSocket
    const wsStateSubscription = this.apiService.webSocketState$.subscribe(state => {
      this.webSocketState = state;
    });

    this.subscriptions.push(wsStateSubscription);
  }

  ngOnDestroy(): void {
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
}
