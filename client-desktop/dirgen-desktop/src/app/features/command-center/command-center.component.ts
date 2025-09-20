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
      <div class="status-display" *ngIf="(applicationStatus$ | async) !== 'idle'">
        <div class="status-info">
          <mat-icon [color]="getStatusColor()">{{ getStatusIcon() }}</mat-icon>
          <span class="status-text">{{ getStatusText() }}</span>
        </div>
      </div>

      <!-- File Display Area -->
      <div *ngIf="attachedFiles.length > 0" class="attached-files">
        <h4>📁 Archivo Seleccionado:</h4>
        <mat-chip-set>
          <mat-chip *ngFor="let file of attachedFiles"
                    [removable]="!isProcessing"
                    (removed)="removeAttachedFile(file.id)">
            <mat-icon matChipAvatar>attach_file</mat-icon>
            {{ file.name }}
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

      <!-- Approval Request -->
      <div *ngIf="waitingForApproval$ | async" class="approval-request">
        <mat-icon color="warn">schedule</mat-icon>
        <span>⏳ El plan ha sido generado. ¿Deseas proceder con la ejecución?</span>
      </div>

      <!-- Input Field -->
      <div class="input-container">
        <mat-form-field appearance="outline" class="prompt-input">
          <mat-label>
            <span *ngIf="!(waitingForApproval$ | async)">Escribe un comando o arrastra archivos SVAD...</span>
            <span *ngIf="waitingForApproval$ | async">Responde: ¿Aprobar el plan? (sí/no)</span>
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
                      text.includes('ok') || text.includes('aprobar');
    
    // Si estamos esperando aprobación, manejar la respuesta
    this.store.select(AppSelectors.selectWaitingForApproval).pipe(
      // Solo tomar el primer valor
    ).subscribe(waitingForApproval => {
      if (waitingForApproval) {
        this.store.select(AppSelectors.selectCurrentRunId).subscribe(runId => {
          if (runId) {
            this.store.dispatch(AppActions.planApprovalSubmitted({
              run_id: runId,
              approved: isApproval,
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
    // Usar async pipe en el template sería mejor, pero para simplificar:
    return 'Iniciar análisis, adjuntar archivos, dar instrucciones...';
  }
  
  /**
   * Obtiene el color del status
   */
  getStatusColor(): string {
    // Esta lógica se puede mejorar subscribiéndose al estado
    return 'primary';
  }
  
  /**
   * Obtiene el icono del status
   */
  getStatusIcon(): string {
    return 'info';
  }
  
  /**
   * Obtiene el texto del status
   */
  getStatusText(): string {
    return 'Procesando...';
  }
}