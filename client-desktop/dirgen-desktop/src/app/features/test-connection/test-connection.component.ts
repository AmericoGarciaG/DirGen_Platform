import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { Subscription } from 'rxjs';
import { ApiService } from '../../core/services/api.service';
import { 
  DirgenMessage, 
  WebSocketState,
  WebSocketConnectionStatus 
} from '../../shared/models/dirgen.models';

@Component({
  selector: 'app-test-connection',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatChipsModule,
    MatDividerModule
  ],
  templateUrl: './test-connection.component.html',
  styleUrls: ['./test-connection.component.scss']
})
export class TestConnectionComponent implements OnInit, OnDestroy {
  
  // Estado del componente
  selectedFile: File | null = null;
  isLoading = false;
  error: string | null = null;
  runId: string | null = null;
  
  // Estado del WebSocket
  webSocketState: WebSocketState = {
    status: 'disconnected',
    messages: []
  };
  
  // Mensajes crudos para mostrar en la UI
  rawMessages: any[] = [];
  
  // Subscripciones
  private subscriptions: Subscription[] = [];

  constructor(private apiService: ApiService) {}

  ngOnInit(): void {
    // Suscribirse al estado del WebSocket
    const wsStateSubscription = this.apiService.webSocketState$.subscribe(
      state => {
        console.log('📊 Estado WebSocket actualizado:', state);
        this.webSocketState = state;
        this.rawMessages = state.messages;
      }
    );
    
    this.subscriptions.push(wsStateSubscription);
  }

  ngOnDestroy(): void {
    // Limpiar subscripciones
    this.subscriptions.forEach(sub => sub.unsubscribe());
    
    // Desconectar WebSocket si está activo
    this.apiService.disconnectWebSocket();
  }

  /**
   * Maneja la selección de archivo desde el input
   */
  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    
    if (input.files && input.files.length > 0) {
      this.selectedFile = input.files[0];
      this.error = null;
      
      // Validar que sea un archivo de texto
      if (!this.selectedFile.name.endsWith('.md') && 
          !this.selectedFile.type.includes('text')) {
        this.error = 'Por favor selecciona un archivo de texto (.md recomendado)';
        this.selectedFile = null;
        return;
      }
      
      console.log('📁 Archivo seleccionado:', this.selectedFile.name, this.selectedFile.size, 'bytes');
    }
  }

  /**
   * Inicia la prueba de conexión
   */
  async startConnectionTest(): Promise<void> {
    if (!this.selectedFile) {
      this.error = 'Por favor selecciona un archivo primero';
      return;
    }

    try {
      this.isLoading = true;
      this.error = null;
      this.runId = null;
      this.rawMessages = [];
      
      // Limpiar mensajes anteriores
      this.apiService.clearMessages();

      console.log('🚀 Iniciando prueba de conexión...');
      
      // Paso 1: Iniciar run
      console.log('📤 Enviando archivo al backend...');
      const response = await this.apiService.initiateRun(this.selectedFile).toPromise();
      
      if (!response || !response.run_id) {
        throw new Error('No se recibió un run_id válido del backend');
      }
      
      this.runId = response.run_id;
      console.log('✅ Run iniciado con ID:', this.runId);
      
      // Paso 2: Conectar al WebSocket
      console.log('🔌 Conectando al stream de WebSocket...');
      const streamSubscription = this.apiService.connectToStream(this.runId).subscribe({
        next: (message) => {
          console.log('📨 Nuevo mensaje recibido:', message);
        },
        error: (error) => {
          console.error('❌ Error en stream WebSocket:', error);
          this.error = `Error en WebSocket: ${error.message || error}`;
          this.isLoading = false;
        },
        complete: () => {
          console.log('✅ Stream WebSocket completado');
          this.isLoading = false;
        }
      });
      
      this.subscriptions.push(streamSubscription);
      
    } catch (error: any) {
      console.error('❌ Error en prueba de conexión:', error);
      this.error = `Error: ${error.message || error}`;
      this.isLoading = false;
    }
  }

  /**
   * Detiene la prueba de conexión y desconecta el WebSocket
   */
  stopConnectionTest(): void {
    console.log('🛑 Deteniendo prueba de conexión...');
    this.apiService.disconnectWebSocket();
    this.isLoading = false;
  }

  /**
   * Limpia todos los mensajes de la pantalla
   */
  clearMessages(): void {
    this.apiService.clearMessages();
    this.rawMessages = [];
  }

  /**
   * Obtiene el color del chip según el estado de conexión
   */
  getConnectionStatusColor(status: WebSocketConnectionStatus): string {
    switch (status) {
      case 'connected': return 'primary';
      case 'connecting': return 'accent';
      case 'error': return 'warn';
      case 'disconnected': return '';
      case 'reconnecting': return 'accent';
      default: return '';
    }
  }

  /**
   * Obtiene el icono según el estado de conexión
   */
  getConnectionStatusIcon(status: WebSocketConnectionStatus): string {
    switch (status) {
      case 'connected': return 'wifi';
      case 'connecting': return 'wifi_find';
      case 'error': return 'wifi_off';
      case 'disconnected': return 'wifi_off';
      case 'reconnecting': return 'wifi_find';
      default: return 'help';
    }
  }

  /**
   * Convierte el estado de conexión a texto legible
   */
  getConnectionStatusText(status: WebSocketConnectionStatus): string {
    switch (status) {
      case 'connected': return 'Conectado';
      case 'connecting': return 'Conectando...';
      case 'error': return 'Error';
      case 'disconnected': return 'Desconectado';
      case 'reconnecting': return 'Reconectando...';
      default: return 'Desconocido';
    }
  }

  /**
   * Obtiene el formato de fecha legible
   */
  formatTimestamp(timestamp: string): string {
    return new Date(timestamp).toLocaleString();
  }

  /**
   * Obtiene el color según el tipo de mensaje
   */
  getMessageTypeColor(messageType: string): string {
    switch (messageType) {
      case 'error': return '#f44336';
      case 'thought': return '#2196f3';
      case 'plan': return '#ff9800';
      case 'status': return '#4caf50';
      case 'completion': return '#9c27b0';
      default: return '#757575';
    }
  }
}