import { Component, OnInit, OnDestroy, ViewChild, ElementRef, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';

// Angular Material
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatProgressBarModule } from '@angular/material/progress-bar';

// Services
import { ApiService } from '../../core/services/api.service';
import { WebSocketState } from '../../shared/models/dirgen.models';

export interface AttachedFile {
  file: File;
  id: string;
  name: string;
  size: number;
  type: string;
}

export interface ConversationMessage {
  id: string;
  sender: 'user' | 'orchestrator' | 'agent';
  content: string;
  timestamp: Date;
  type: 'message' | 'file_attached' | 'approval_request' | 'system';
  files?: AttachedFile[];
  runId?: string;
}

@Component({
  selector: 'app-command-prompt',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatTooltipModule,
    MatProgressBarModule
  ],
  templateUrl: './command-prompt.component.html',
  styleUrls: ['./command-prompt.component.scss']
})
export class CommandPromptComponent implements OnInit, OnDestroy {
  
  @ViewChild('promptInput', { static: true }) promptInput!: ElementRef<HTMLInputElement>;
  @ViewChild('fileInput', { static: true }) fileInput!: ElementRef<HTMLInputElement>;
  
  // Input properties
  @Input() webSocketState: WebSocketState | null = null;
  
  // Component state
  promptText = '';
  attachedFiles: AttachedFile[] = [];
  conversationHistory: ConversationMessage[] = [];
  isProcessing = false;
  waitingForApproval = false;
  currentRunId: string | null = null;
  
  // Drag and drop state
  isDragOver = false;
  
  private subscriptions: Subscription[] = [];
  
  constructor(private apiService: ApiService) {}
  
  ngOnInit(): void {
    // Escuchar mensajes del WebSocket para detectar solicitudes de aprobación
    const messagesSubscription = this.apiService.messages$.subscribe(message => {
      this.handleIncomingMessage(message);
    });
    
    // Escuchar estado del WebSocket
    const stateSubscription = this.apiService.webSocketState$.subscribe(state => {
      this.webSocketState = state;
    });
    
    this.subscriptions.push(messagesSubscription, stateSubscription);
    
    // Mensaje de bienvenida
    this.addConversationMessage({
      sender: 'orchestrator',
      content: 'Bienvenido al Centro de Mando de DirGen. Arrastra un archivo SVAD aquí o usa el selector de archivos para comenzar.',
      type: 'system'
    });
  }
  
  ngOnDestroy(): void {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }
  
  /**
   * Maneja mensajes entrantes del WebSocket
   */
  private handleIncomingMessage(message: any): void {
    // Detectar solicitudes de aprobación del plan
    if (message.type === 'plan_generated') {
      this.waitingForApproval = true;
      this.currentRunId = message.run_id;
      
      const taskCount = message.data?.tasks?.length || 'varias';
      this.addConversationMessage({
        sender: 'orchestrator',
        content: `Se ha construido el plan de ejecución con ${taskCount} tareas. ¿Procedemos con la ejecución?`,
        type: 'approval_request'
      });
      
      // Enfocar el input para que el usuario pueda responder
      setTimeout(() => {
        this.promptInput.nativeElement.focus();
      }, 100);
    }
    
    // Otros tipos de mensajes conversacionales
    if (message.source === 'Orchestrator' && message.type === 'info') {
      this.addConversationMessage({
        sender: 'orchestrator',
        content: message.data?.message || message.message || 'Mensaje del orquestador',
        type: 'system'
      });
    }
    
    // Cuando la ejecución comienza, limpiar el estado de aprobación
    if (message.type === 'execution_started') {
      this.waitingForApproval = false;
      this.currentRunId = null;
    }
  }
  
  /**
   * Añade un mensaje al historial de conversación
   */
  private addConversationMessage(message: Partial<ConversationMessage>): void {
    const newMessage: ConversationMessage = {
      id: Date.now().toString(),
      sender: message.sender || 'user',
      content: message.content || '',
      timestamp: new Date(),
      type: message.type || 'message',
      files: message.files,
      runId: message.runId
    };
    
    this.conversationHistory.push(newMessage);
    
    // Limitar el historial a los últimos 50 mensajes
    if (this.conversationHistory.length > 50) {
      this.conversationHistory = this.conversationHistory.slice(-50);
    }
  }
  
  /**
   * Envía el comando actual
   */
  async onSendCommand(): Promise<void> {
    if (!this.promptText.trim() && this.attachedFiles.length === 0) {
      return;
    }
    
    try {
      this.isProcessing = true;
      
      // Si hay archivos adjuntos, procesar como iniciación de run
      if (this.attachedFiles.length > 0) {
        await this.processFileInitiation();
      }
      // Si estamos esperando aprobación, procesar como aprobación
      else if (this.waitingForApproval && this.currentRunId) {
        await this.processApprovalResponse();
      }
      // Comando de texto general
      else {
        await this.processTextCommand();
      }
      
    } catch (error: any) {
      console.error('Error procesando comando:', error);
      this.addConversationMessage({
        sender: 'orchestrator',
        content: `Error: ${error.message || error}`,
        type: 'system'
      });
    } finally {
      this.isProcessing = false;
      this.clearPrompt();
    }
  }
  
  /**
   * Procesa la iniciación con archivos SVAD
   */
  private async processFileInitiation(): Promise<void> {
    const svadFile = this.attachedFiles[0]; // Por ahora solo procesamos el primer archivo
    
    // Añadir mensaje del usuario
    this.addConversationMessage({
      sender: 'user',
      content: this.promptText || `Archivo adjuntado: ${svadFile.name}`,
      type: 'file_attached',
      files: [...this.attachedFiles]
    });
    
    // Iniciar el run
    const response = await this.apiService.initiateRun(svadFile.file).toPromise();
    
    if (response && response.run_id) {
      this.currentRunId = response.run_id;
      
      this.addConversationMessage({
        sender: 'orchestrator',
        content: `Análisis iniciado con ID: ${response.run_id}. Conectando al stream de eventos...`,
        type: 'system'
      });
      
      // Conectar al WebSocket
      const streamSubscription = this.apiService.connectToStream(response.run_id).subscribe({
        next: (message) => {
          // Los mensajes ya se manejan en handleIncomingMessage
          console.log('Stream message:', message);
        },
        error: (error) => {
          this.addConversationMessage({
            sender: 'orchestrator',
            content: `Error en conexión: ${error.message || error}`,
            type: 'system'
          });
        }
      });
      
      this.subscriptions.push(streamSubscription);
    }
  }
  
  /**
   * Procesa la respuesta de aprobación del plan
   */
  private async processApprovalResponse(): Promise<void> {
    // Añadir mensaje del usuario
    this.addConversationMessage({
      sender: 'user',
      content: this.promptText,
      type: 'message'
    });
    
    // Determinar si es aprobación o rechazo
    const text = this.promptText.toLowerCase();
    const isApproval = text.includes('sí') || text.includes('si') || 
                      text.includes('adelante') || text.includes('procede') ||
                      text.includes('ok') || text.includes('aprobar');
    
    if (isApproval && this.currentRunId) {
      // Enviar aprobación al backend
      await this.apiService.approvePlan(this.currentRunId, this.promptText).toPromise();
      
      this.addConversationMessage({
        sender: 'orchestrator',
        content: 'Plan aprobado. Iniciando ejecución...',
        type: 'system'
      });
      
      this.waitingForApproval = false;
    } else {
      this.addConversationMessage({
        sender: 'orchestrator',
        content: 'Plan no aprobado. Puedes adjuntar un nuevo archivo SVAD para empezar de nuevo.',
        type: 'system'
      });
      
      this.waitingForApproval = false;
      this.currentRunId = null;
    }
  }
  
  /**
   * Procesa comandos de texto generales
   */
  private async processTextCommand(): Promise<void> {
    this.addConversationMessage({
      sender: 'user',
      content: this.promptText,
      type: 'message'
    });
    
    // Por ahora, solo respuesta informativa
    this.addConversationMessage({
      sender: 'orchestrator',
      content: 'Comando recibido. Para iniciar un análisis, adjunta un archivo SVAD.',
      type: 'system'
    });
  }
  
  /**
   * Limpia el prompt
   */
  private clearPrompt(): void {
    this.promptText = '';
    this.attachedFiles = [];
    this.promptInput.nativeElement.focus();
  }
  
  /**
   * Maneja la selección de archivos desde el input
   */
  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.addFiles(Array.from(input.files));
      input.value = ''; // Limpiar el input
    }
  }
  
  /**
   * Abre el selector de archivos
   */
  openFileSelector(): void {
    this.fileInput.nativeElement.click();
  }
  
  /**
   * Maneja drag over
   */
  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver = true;
  }
  
  /**
   * Maneja drag leave
   */
  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver = false;
  }
  
  /**
   * Maneja drop de archivos
   */
  onDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver = false;
    
    if (event.dataTransfer?.files) {
      this.addFiles(Array.from(event.dataTransfer.files));
    }
  }
  
  /**
   * Añade archivos a la lista de adjuntos
   */
  private addFiles(files: File[]): void {
    files.forEach(file => {
      // Validar tipo de archivo
      if (this.isValidFile(file)) {
        const attachedFile: AttachedFile = {
          file,
          id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
          name: file.name,
          size: file.size,
          type: file.type
        };
        
        this.attachedFiles.push(attachedFile);
        
        // Actualizar el prompt text si está vacío
        if (!this.promptText.trim()) {
          this.promptText = `Iniciar análisis con ${file.name}`;
        }
      }
    });
  }
  
  /**
   * Valida si el archivo es aceptable
   */
  private isValidFile(file: File): boolean {
    const validExtensions = ['.md', '.txt'];
    const extension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));
    return validExtensions.includes(extension);
  }
  
  /**
   * Remueve un archivo adjunto
   */
  removeAttachedFile(fileId: string): void {
    this.attachedFiles = this.attachedFiles.filter(f => f.id !== fileId);
  }
  
  /**
   * Formatea el tamaño del archivo
   */
  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }
  
  /**
   * Maneja el Enter en el input
   */
  onKeyDown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.onSendCommand();
    }
  }
}