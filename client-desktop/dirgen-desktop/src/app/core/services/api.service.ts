import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, Subject, BehaviorSubject } from 'rxjs';
import { map, catchError } from 'rxjs/operators';
import { 
  InitiateRunResponse, 
  DirgenMessage, 
  WebSocketConnectionStatus,
  WebSocketState 
} from '../../shared/models/dirgen.models';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private readonly baseUrl = 'http://127.0.0.1:8000';
  private readonly wsBaseUrl = 'ws://127.0.0.1:8000';
  
  // WebSocket related properties
  private webSocket: WebSocket | null = null;
  private messagesSubject = new Subject<DirgenMessage>();
  private connectionStatusSubject = new BehaviorSubject<WebSocketConnectionStatus>('disconnected');
  private webSocketStateSubject = new BehaviorSubject<WebSocketState>({
    status: 'disconnected',
    messages: []
  });

  // Public observables
  public messages$ = this.messagesSubject.asObservable();
  public connectionStatus$ = this.connectionStatusSubject.asObservable();
  public webSocketState$ = this.webSocketStateSubject.asObservable();

  constructor(private http: HttpClient) {}

  /**
   * Inicia una nueva ejecución enviando un archivo SVAD al backend
   * @param file - Archivo SVAD a procesar
   * @returns Observable con la respuesta que contiene el run_id
   */
  initiateRun(file: File): Observable<InitiateRunResponse> {
    console.log('🚀 Iniciando petición HTTP POST...');
    console.log('📄 Archivo:', file.name, 'Tamaño:', file.size, 'bytes');
    console.log('🌐 URL destino:', `${this.baseUrl}/v1/initiate_from_svad`);
    
    const formData = new FormData();
    formData.append('svad_file', file);
    console.log('📦 FormData creado con campo svad_file');

    const headers = new HttpHeaders();
    // Note: No establecemos Content-Type para multipart/form-data
    // El navegador lo establecerá automáticamente con el boundary correcto

    return this.http.post<InitiateRunResponse>(
      `${this.baseUrl}/v1/initiate_from_svad`,
      formData,
      { headers }
    ).pipe(
      map(response => {
        console.log('✅ Run iniciado exitosamente:', response);
        console.log('🆔 Run ID recibido:', response.run_id);
        return response;
      }),
      catchError(error => {
        console.error('❌ Error completo al iniciar run:');
        console.error('Status:', error.status);
        console.error('Status Text:', error.statusText);
        console.error('Error Object:', error);
        console.error('URL:', error.url);
        if (error.error) {
          console.error('Error Details:', error.error);
        }
        throw error;
      })
    );
  }

  /**
   * Establece una conexión WebSocket para recibir mensajes en tiempo real
   * @param runId - ID del run para conectarse
   * @returns Observable que emite cada mensaje recibido
   */
  connectToStream(runId: string): Observable<DirgenMessage> {
    return new Observable(observer => {
      try {
        // Cerrar conexión existente si hay una
        this.disconnectWebSocket();

        // Actualizar estado de conexión
        this.updateConnectionStatus('connecting');
        this.updateWebSocketState(runId, 'connecting');

        // Crear nueva conexión WebSocket
        const wsUrl = `${this.wsBaseUrl}/ws/${runId}`;
        console.log('🔌 Conectando a WebSocket:', wsUrl);
        
        this.webSocket = new WebSocket(wsUrl);

        // Event handlers
        this.webSocket.onopen = (event) => {
          console.log('✅ WebSocket conectado:', event);
          this.updateConnectionStatus('connected');
          this.updateWebSocketState(runId, 'connected');
        };

        this.webSocket.onmessage = (event) => {
          try {
            const rawMessage = event.data;
            console.log('📨 Mensaje WebSocket recibido:', rawMessage);
            
            // Intentar parsear como JSON
            let parsedMessage: DirgenMessage;
            try {
              parsedMessage = JSON.parse(rawMessage);
            } catch (parseError) {
              // Si no es JSON válido, crear un mensaje de log
              parsedMessage = {
                type: 'log',
                timestamp: new Date().toISOString(),
                run_id: runId,
                level: 'info',
                message: rawMessage
              };
            }

            // Asegurar que el mensaje tenga los campos requeridos
            if (!parsedMessage.run_id) {
              parsedMessage.run_id = runId;
            }
            if (!parsedMessage.timestamp) {
              parsedMessage.timestamp = new Date().toISOString();
            }

            // Emitir mensaje a todos los observadores
            this.messagesSubject.next(parsedMessage);
            observer.next(parsedMessage);
            
            // Actualizar estado del WebSocket
            this.addMessageToState(parsedMessage);

          } catch (error) {
            console.error('❌ Error procesando mensaje WebSocket:', error);
            const errorMessage: DirgenMessage = {
              type: 'error',
              timestamp: new Date().toISOString(),
              run_id: runId,
              error: 'Error procesando mensaje del servidor',
              details: error
            };
            this.messagesSubject.next(errorMessage);
            observer.next(errorMessage);
          }
        };

        this.webSocket.onerror = (error) => {
          console.error('❌ Error en WebSocket:', error);
          this.updateConnectionStatus('error');
          this.updateWebSocketState(runId, 'error', 'Error de conexión WebSocket');
          observer.error(error);
        };

        this.webSocket.onclose = (event) => {
          console.log('🔌 WebSocket cerrado:', event);
          this.updateConnectionStatus('disconnected');
          this.updateWebSocketState(runId, 'disconnected');
          
          if (!event.wasClean) {
            observer.error(new Error(`WebSocket cerrado inesperadamente: ${event.code} ${event.reason}`));
          } else {
            observer.complete();
          }
        };

      } catch (error) {
        console.error('❌ Error creando WebSocket:', error);
        this.updateConnectionStatus('error');
        observer.error(error);
      }

      // Cleanup function
      return () => {
        this.disconnectWebSocket();
      };
    });
  }

  /**
   * Desconecta el WebSocket actual
   */
  disconnectWebSocket(): void {
    if (this.webSocket) {
      console.log('🔌 Cerrando WebSocket...');
      this.webSocket.close(1000, 'Client disconnecting');
      this.webSocket = null;
    }
  }

  /**
   * Obtiene el estado actual de la conexión WebSocket
   */
  getCurrentWebSocketState(): WebSocketState {
    return this.webSocketStateSubject.value;
  }

  /**
   * Limpia todos los mensajes del estado actual
   */
  clearMessages(): void {
    const currentState = this.webSocketStateSubject.value;
    this.webSocketStateSubject.next({
      ...currentState,
      messages: []
    });
  }

  // Private helper methods

  private updateConnectionStatus(status: WebSocketConnectionStatus): void {
    this.connectionStatusSubject.next(status);
  }

  private updateWebSocketState(
    runId: string, 
    status: WebSocketConnectionStatus, 
    error?: string
  ): void {
    const currentState = this.webSocketStateSubject.value;
    this.webSocketStateSubject.next({
      ...currentState,
      runId,
      status,
      error
    });
  }

  private addMessageToState(message: DirgenMessage): void {
    const currentState = this.webSocketStateSubject.value;
    const updatedMessages = [...currentState.messages, message];
    
    this.webSocketStateSubject.next({
      ...currentState,
      messages: updatedMessages
    });
  }

  /**
   * Aprueba o rechaza un plan generado por el Orquestador
   * @param runId - ID del run para el cual responder al plan
   * @param approved - Si el plan es aprobado (true) o rechazado (false)
   * @param userResponse - Respuesta del usuario (opcional)
   * @returns Observable con la respuesta
   */
  approvePlan(runId: string, approved: boolean, userResponse?: string): Observable<any> {
    console.log(`📋 Enviando ${approved ? 'aprobación' : 'rechazo'} del plan para run:`, runId);
    console.log('💬 Respuesta del usuario:', userResponse);
    
    const body = {
      approved: approved,
      user_response: userResponse || (approved ? 'Aprobado' : 'Rechazado')
    };
    
    return this.http.post(
      `${this.baseUrl}/v1/run/${runId}/approve_plan`,
      body,
      {
        headers: new HttpHeaders({
          'Content-Type': 'application/json'
        })
      }
    ).pipe(
      map(response => {
        console.log(`✅ Plan ${approved ? 'aprobado' : 'rechazado'} exitosamente:`, response);
        return response;
      }),
      catchError(error => {
        console.error(`❌ Error ${approved ? 'aprobando' : 'rechazando'} plan:`);
        console.error('Status:', error.status);
        console.error('Error Object:', error);
        throw error;
      })
    );
  }
}
