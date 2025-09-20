import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet } from '@angular/router';
import { Subscription } from 'rxjs';
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
  
  private subscriptions: Subscription[] = [];
  
  constructor(
    private apiService: ApiService,
    private store: Store<AppState>
  ) {}
  
  ngOnInit(): void {
    // Escuchar el estado del WebSocket para toda la aplicación
    const wsStateSubscription = this.apiService.webSocketState$.subscribe(state => {
      this.webSocketState = state;
    });
    
    this.subscriptions.push(wsStateSubscription);
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
