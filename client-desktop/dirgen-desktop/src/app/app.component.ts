import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet } from '@angular/router';
import { Subscription, Observable } from 'rxjs';
import { Store } from '@ngrx/store';

// Services
import { ApiService } from './core/services/api.service';
import { WebSocketState } from './shared/models/dirgen.models';

// Components
import { WorkspaceComponent } from './features/workspace/workspace.component';
import { PlanWidgetComponent } from './features/monitoring/components/plan-widget/plan-widget.component';
import { CommandCenterComponent } from './features/command-center/command-center.component';
import { EventLogComponent } from './features/event-log/event-log.component';

// Store
import { AppState } from './store/models';
import { selectCurrentSdlcStatus, selectCurrentSdlcPhase } from './store/app.selectors';

// Interface para las etapas del SDLC
interface SdlcStage {
  name: string;
  icon: string;
  statusKeys: string[]; // Estados del backend que corresponden a esta etapa
  status: 'completed' | 'active' | 'pending';
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule, 
    RouterOutlet,
    WorkspaceComponent,
    PlanWidgetComponent,
    CommandCenterComponent,
    EventLogComponent
  ],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss'
})

export class AppComponent implements OnInit, OnDestroy {
  title = 'dirgen-desktop';
  
  // Estado global de la aplicación
  webSocketState: WebSocketState = {
    status: 'disconnected',
    messages: []
  };
  
  // Etapas del SDLC
  sdlcStages: SdlcStage[] = [
    {
      name: 'Análisis de Req.',
      icon: '📋',
      statusKeys: ['initial', 'requirements_processing', 'requirements_waiting_approval', 'requirements_approved', 'requirements_rejected'],
      status: 'pending'
    },
    {
      name: 'Diseño',
      icon: '🎯',
      statusKeys: ['design_processing', 'design_waiting_approval', 'design_approved', 'design_rejected'],
      status: 'pending'
    },
    {
      name: 'Validación',
      icon: '🔍',
      statusKeys: ['validation_processing', 'validation_passed', 'validation_failed'],
      status: 'pending'
    },
    {
      name: 'Ejecución',
      icon: '💻',
      statusKeys: ['execution_processing', 'execution_completed', 'execution_failed'],
      status: 'pending'
    },
    {
      name: 'Completado',
      icon: '🎆',
      statusKeys: ['execution_completed'],
      status: 'pending'
    }
  ];
  
  // Observables del store
  currentSdlcStatus$: Observable<string | null>;
  currentSdlcPhase$: Observable<string | null>;
  
  private subscriptions: Subscription[] = [];
  
  constructor(
    private apiService: ApiService,
    private store: Store<AppState>
  ) {
    // Inicializar observables del store
    this.currentSdlcStatus$ = this.store.select(selectCurrentSdlcStatus);
    this.currentSdlcPhase$ = this.store.select(selectCurrentSdlcPhase);
  }
  
  ngOnInit(): void {
    // Escuchar el estado del WebSocket para toda la aplicación
    const wsStateSubscription = this.apiService.webSocketState$.subscribe(state => {
      this.webSocketState = state;
    });
    
    // Escuchar cambios en el estado SDLC para actualizar las etapas
    const sdlcStatusSubscription = this.currentSdlcStatus$.subscribe(status => {
      this.updateSdlcStages(status);
    });
    
    this.subscriptions.push(wsStateSubscription, sdlcStatusSubscription);
  }
  
  ngOnDestroy(): void {
    this.subscriptions.forEach(sub => sub.unsubscribe());
    this.apiService.disconnectWebSocket();
  }
  
  /**
   * Track function para ngFor
   */
  trackMessage(index: number, item: any): string {
    return item.timestamp + index;
  }
  
  /**
   * Track function para etapas SDLC
   */
  trackStage(index: number, stage: SdlcStage): string {
    return stage.name;
  }
  
  /**
   * Actualiza el estado visual de las etapas SDLC basado en el estado actual
   */
  private updateSdlcStages(currentStatus: string | null): void {
    if (!currentStatus) {
      // Resetear todas las etapas a pending si no hay estado
      this.sdlcStages.forEach(stage => stage.status = 'pending');
      return;
    }

    let activeStageFound = false;

    for (let i = 0; i < this.sdlcStages.length; i++) {
      const stage = this.sdlcStages[i];
      
      if (stage.statusKeys.includes(currentStatus)) {
        // Esta es la etapa activa
        stage.status = 'active';
        activeStageFound = true;
        
        // Marcar etapas anteriores como completadas
        for (let j = 0; j < i; j++) {
          this.sdlcStages[j].status = 'completed';
        }
        
        // Marcar etapas posteriores como pendientes
        for (let k = i + 1; k < this.sdlcStages.length; k++) {
          this.sdlcStages[k].status = 'pending';
        }
        
        break;
      }
    }

    // Si no encontramos una etapa activa, mantener el estado anterior
    if (!activeStageFound) {
      console.warn(`Estado SDLC desconocido: ${currentStatus}`);
    }
  }

  /**
   * Formatea timestamp para display
   */
  formatTime(timestamp: string | undefined): string {
    if (!timestamp) return '--:--:--';
    
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString('es-ES', { 
        hour: '2-digit', 
        minute: '2-digit', 
        second: '2-digit' 
      });
    } catch {
      return timestamp.substring(0, 8);
    }
  }
}
