import { Component, OnInit, OnDestroy, ViewChild, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Store } from '@ngrx/store';
import { Observable, Subscription } from 'rxjs';

// Angular Material
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatProgressBarModule } from '@angular/material/progress-bar';

// Store
import { AppState } from '../../store/models';
import * as AppActions from '../../store/app.actions';
import * as AppSelectors from '../../store/app.selectors';

export interface AttachedFile {
  file: File;
  id: string;
  name: string;
  size: number;
  type: string;
}

@Component({
  selector: 'app-command-center',
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
  template: `
    <!-- Command Center - Centro de Mando NgRx Version -->
    <div class="command-center" 
         [class.drag-over]="isDragOver"
         (dragover)="onDragOver($event)"
         (dragleave)="onDragLeave($event)"
         (drop)="onDrop($event)">

      <!-- Status Display -->
      <div class="status-display" *ngIf="applicationStatus$ | async as status; else hideStatus">
        <div class="status-info" 
             [class.error-status]="status === 'error'" 
             [class.completed-status]="status === 'completed'"
             *ngIf="status !== 'idle'">
          <mat-icon [color]="getStatusColor()">{{ getStatusIcon() }}</mat-icon>
          <span class="status-text">{{ getStatusText() }}</span>
          <div *ngIf="status === 'error'" class="error-details">
            <small class="error-message" *ngIf="appError$ | async as error">{{ error }}</small>
          </div>
        </div>
      </div>
      <ng-template #hideStatus></ng-template>

      <!-- File Display Area -->
      <div *ngIf="attachedFiles.length > 0" class="attached-files">
        <h4>📁 Archivo Seleccionado:</h4>
        <mat-chip-set>
          <mat-chip *ngFor="let file of attachedFiles"
                    [removable]="!isProcessing"
                    (removed)="removeAttachedFile(file.id)">
            <mat-icon matChipAvatar>attach_file</mat-icon>
            <span class="filename">{{ file.name || 'Archivo sin nombre' }}</span>
            <small class="file-size">({{ formatFileSize(file.size) }})</small>
            <button matChipRemove [disabled]="isProcessing">
              <mat-icon>cancel</mat-icon>
            </button>
          </mat-chip>
        </mat-chip-set>
      </div>

      <!-- Progress Bar -->
      <mat-progress-bar 
        *ngIf="isProcessing" 
        mode="indeterminate"
        class="progress-bar">
      </mat-progress-bar>

      <!-- Input Field -->
      <div class="input-container">
        <mat-form-field appearance="outline" class="prompt-input">
          <mat-label>
            <span *ngIf="!(waitingForApproval$ | async)">Escribe un comando o arrastra archivos SVAD...</span>
            <span *ngIf="waitingForApproval$ | async">Responde al sistema (sí/no)...</span>
          </mat-label>
          
          <input matInput
                 #promptInput
                 [(ngModel)]="promptText"
                 (keydown)="onKeyDown($event)"
                 [disabled]="isProcessing"
                 [placeholder]="getPlaceholderText()"
                 autocomplete="off"
                 spellcheck="false">
          
          <!-- File Attach Button -->
          <button *ngIf="!(waitingForApproval$ | async)" 
                  matSuffix 
                  mat-icon-button 
                  type="button"
                  (click)="openFileSelector()"
                  [disabled]="isProcessing"
                  matTooltip="Adjuntar archivo SVAD">
            <mat-icon>attach_file</mat-icon>
          </button>

          <!-- Send Button -->
          <button matSuffix 
                  mat-icon-button 
                  type="button"
                  (click)="onSendCommand()"
                  [disabled]="!canSend()"
                  [color]="(waitingForApproval$ | async) ? 'warn' : 'primary'"
                  [matTooltip]="(waitingForApproval$ | async) ? 'Enviar respuesta de aprobación' : 'Enviar comando'">
            <mat-icon *ngIf="!isProcessing">
              {{ (waitingForApproval$ | async) ? 'check_circle' : 'send' }}
            </mat-icon>
            <mat-icon *ngIf="isProcessing" class="spinning">sync</mat-icon>
          </button>
        </mat-form-field>
      </div>

      <!-- Hidden File Input -->
      <input #fileInput
             type="file"
             accept=".md,.txt"
             multiple
             (change)="onFileSelected($event)"
             style="display: none;">

      <!-- Drag & Drop Overlay -->
      <div *ngIf="isDragOver" class="drag-overlay">
        <div class="drag-content">
          <mat-icon class="drag-icon">cloud_upload</mat-icon>
          <h3>Suelta el archivo SVAD aquí</h3>
          <p>Archivos soportados: .md, .txt</p>
        </div>
      </div>

      <!-- Connection Status -->
      <div class="connection-status">
        <div class="status-indicator" 
             [class.connected]="webSocketConnected$ | async"
             [class.error]="webSocketError$ | async">
          
          <mat-icon *ngIf="webSocketConnected$ | async">wifi</mat-icon>
          <mat-icon *ngIf="!(webSocketConnected$ | async)">wifi_off</mat-icon>
          
          <span class="status-text">
            {{ (webSocketConnected$ | async) ? 'Conectado' : 'Desconectado' }}
          </span>
          
          <small *ngIf="currentRunId$ | async as runId" class="run-id">
            Run: {{ runId }}
          </small>
        </div>
      </div>

    </div>
  `,
  styleUrls: ['./command-center.component.scss']
})
export class CommandCenterComponent implements OnInit, OnDestroy {
  
  @ViewChild('promptInput', { static: true }) promptInput!: ElementRef<HTMLInputElement>;
  @ViewChild('fileInput', { static: true }) fileInput!: ElementRef<HTMLInputElement>;
  
  // Component state
  promptText = '';
  attachedFiles: AttachedFile[] = [];
  isDragOver = false;
  
  // Observables from Store
  applicationStatus$: Observable<string>;
  isProcessing$: Observable<boolean>;
  currentRunId$: Observable<string | null>;
  waitingForApproval$: Observable<boolean>;
  webSocketConnected$: Observable<boolean>;
  webSocketError$: Observable<string | null>;
  appError$: Observable<string | null>;
  
  // Derived states
  isProcessing = false;
  
  private subscriptions: Subscription[] = [];
  
  constructor(private store: Store<AppState>) {
    // Initialize observables
    this.applicationStatus$ = this.store.select(AppSelectors.selectApplicationStatus);
    this.isProcessing$ = this.store.select(AppSelectors.selectIsLoading);
    this.currentRunId$ = this.store.select(AppSelectors.selectCurrentRunId);
    this.waitingForApproval$ = this.store.select(AppSelectors.selectWaitingForApproval);
    this.webSocketConnected$ = this.store.select(AppSelectors.selectWebSocketConnected);
    this.webSocketError$ = this.store.select(AppSelectors.selectWebSocketError);
    this.appError$ = this.store.select(AppSelectors.selectAppError);
  }
  
  ngOnInit(): void {
    // Subscribe to loading state
    const loadingSubscription = this.isProcessing$.subscribe(isLoading => {
      this.isProcessing = isLoading;
    });
    
    this.subscriptions.push(loadingSubscription);
  }
  
  ngOnDestroy(): void {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }
  
  /**
   * Envía el comando actual usando NgRx
   */
  onSendCommand(): void {
    if (!this.promptText.trim() && this.attachedFiles.length === 0) {
      return;
    }
    
    // Si hay archivos adjuntos, procesar como iniciación de run
    if (this.attachedFiles.length > 0) {
      this.processFileInitiation();
    }
    // Si estamos esperando aprobación, procesar como aprobación
    else if (this.promptText.trim()) {
      this.processApprovalOrCommand();
    }
  }
  
  /**
   * Procesa la iniciación con archivos SVAD usando NgRx
   */
  private processFileInitiation(): void {
    const svadFile = this.attachedFiles[0]; // Por ahora solo procesamos el primer archivo
    
    // Despachar acción para iniciar run
    this.store.dispatch(AppActions.runInitiated({
      file: svadFile.file,
      prompt: this.promptText || `Iniciar análisis con ${svadFile.name}`
    }));
    
    this.clearPrompt();
  }
  
  /**
   * Procesa la respuesta de aprobación o comando general
   */
  private processApprovalOrCommand(): void {
    const text = this.promptText.toLowerCase();
    const isApproval = text.includes('sí') || text.includes('si') || 
                      text.includes('adelante') || text.includes('procede') ||
                      text.includes('ok') || text.includes('aprobar') ||
                      text.includes('yes') || text.includes('y');
    
    const isRejection = text.includes('no') || text.includes('rechazar') ||
                       text.includes('cancelar') || text.includes('parar') ||
                       text.includes('detener');
    
    // Si estamos esperando aprobación, manejar la respuesta
    this.store.select(AppSelectors.selectWaitingForApproval).subscribe(waitingForApproval => {
      if (waitingForApproval) {
        this.store.select(AppSelectors.selectCurrentRunId).subscribe(runId => {
          if (runId) {
            // Determinar si es aprobación o rechazo
            let approved = false;
            if (isApproval) {
              approved = true;
            } else if (isRejection) {
              approved = false;
            } else {
              // Si no es claro, tratar como aprobación si el texto es positivo
              approved = !text.includes('no');
            }
            
            console.log(`🔄 Procesando respuesta de aprobación: ${approved ? 'APROBADO' : 'RECHAZADO'}`);
            
            this.store.dispatch(AppActions.planApprovalSubmitted({
              run_id: runId,
              approved: approved,
              userResponse: this.promptText
            }));
          }
        }).unsubscribe();
      }
    }).unsubscribe();
    
    this.clearPrompt();
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
      console.log('📁 Archivo cargado:', file.name, 'Tamaño:', file.size, 'Tipo:', file.type);
      
      // Validar tipo de archivo
      if (this.isValidFile(file)) {
        const attachedFile: AttachedFile = {
          file,
          id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
          name: file.name,
          size: file.size,
          type: file.type
        };
        
        console.log('✅ AttachedFile creado:', attachedFile);
        this.attachedFiles.push(attachedFile);
        console.log('📋 Lista actual de archivos:', this.attachedFiles);
        
        // Actualizar el prompt text si está vacío
        if (!this.promptText.trim()) {
          this.promptText = `Iniciar análisis con ${file.name}`;
        }
      } else {
        console.log('❌ Archivo no válido:', file.name);
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
  
  /**
   * Determina si se puede enviar el comando
   */
  canSend(): boolean {
    return !this.isProcessing && (this.promptText.trim().length > 0 || this.attachedFiles.length > 0);
  }
  
  /**
   * Obtiene el texto del placeholder dinámicamente
   */
  getPlaceholderText(): string {
    if (this.isProcessing) return 'Procesando...';
    
    let placeholderText = 'Iniciar análisis, adjuntar archivos, dar instrucciones...';
    this.applicationStatus$.subscribe(status => {
      switch (status) {
        case 'error':
          placeholderText = 'Error en el proceso. Puedes intentar de nuevo...';
          break;
        case 'completed':
          placeholderText = 'Proceso completado. ¿Quieres iniciar uno nuevo?';
          break;
        case 'waiting_approval':
          placeholderText = 'Responde \'sí\' o \'no\' para aprobar el plan...';
          break;
        case 'running':
          placeholderText = 'Proceso en ejecución...';
          break;
        case 'initializing':
          placeholderText = 'Iniciando...';
          break;
        case 'idle':
        default:
          placeholderText = 'Iniciar análisis, adjuntar archivos, dar instrucciones...';
          break;
      }
    }).unsubscribe();
    
    return placeholderText;
  }
  
  /**
   * Obtiene el color del status según el estado de la aplicación
   */
  getStatusColor(): string {
    let statusColor = 'primary';
    this.applicationStatus$.subscribe(status => {
      switch (status) {
        case 'error':
          statusColor = 'warn';
          break;
        case 'completed':
          statusColor = 'accent';
          break;
        case 'waiting_approval':
          statusColor = 'warn';
          break;
        case 'running':
        case 'initializing':
        default:
          statusColor = 'primary';
          break;
      }
    }).unsubscribe();
    return statusColor;
  }
  
  /**
   * Obtiene el icono del status según el estado de la aplicación
   */
  getStatusIcon(): string {
    let statusIcon = 'info';
    this.applicationStatus$.subscribe(status => {
      switch (status) {
        case 'error':
          statusIcon = 'error';
          break;
        case 'completed':
          statusIcon = 'check_circle';
          break;
        case 'waiting_approval':
          statusIcon = 'schedule';
          break;
        case 'running':
          statusIcon = 'sync';
          break;
        case 'initializing':
          statusIcon = 'hourglass_empty';
          break;
        default:
          statusIcon = 'info';
          break;
      }
    }).unsubscribe();
    return statusIcon;
  }
  
  /**
   * Obtiene el texto del status según el estado de la aplicación
   */
  getStatusText(): string {
    let statusText = 'Procesando...';
    this.applicationStatus$.subscribe(status => {
      switch (status) {
        case 'error':
          statusText = 'Proceso terminado con error';
          break;
        case 'completed':
          statusText = 'Proceso completado exitosamente';
          break;
        case 'waiting_approval':
          statusText = 'Esperando tu aprobación...';
          break;
        case 'running':
          statusText = 'Procesando...';
          break;
        case 'initializing':
          statusText = 'Iniciando proceso...';
          break;
        case 'idle':
        default:
          statusText = 'Listo para iniciar';
          break;
      }
    }).unsubscribe();
    return statusText;
  }
}