import { Component, Output, EventEmitter, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subscription } from 'rxjs';

// Angular Material
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDividerModule } from '@angular/material/divider';
import { MatTooltipModule } from '@angular/material/tooltip';

// Services
import { ApiService } from '../../../../core/services/api.service';
import { ExecutionStartedEvent } from '../../../../shared/models/dirgen.models';

@Component({
  selector: 'app-project-control',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatDividerModule,
    MatTooltipModule
  ],
  templateUrl: './project-control.component.html',
  styleUrls: ['./project-control.component.scss']
})
export class ProjectControlComponent implements OnInit, OnDestroy {
  
  @Output() executionStarted = new EventEmitter<ExecutionStartedEvent>();
  
  // Estado del componente
  selectedFile: File | null = null;
  isLoading = false;
  error: string | null = null;
  
  private subscriptions: Subscription[] = [];

  constructor(private apiService: ApiService) {}

  ngOnInit(): void {
    // Aquí podemos suscribirnos a estados adicionales si es necesario
  }

  ngOnDestroy(): void {
    this.subscriptions.forEach(sub => sub.unsubscribe());
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
      if (!this.isValidFile(this.selectedFile)) {
        this.error = 'Por favor selecciona un archivo de texto válido (.md, .txt)';
        this.selectedFile = null;
        return;
      }
      
      console.log('📁 Archivo seleccionado:', this.selectedFile.name, this.selectedFile.size, 'bytes');
    }
  }

  /**
   * Inicia la ejecución del análisis
   */
  async startExecution(): Promise<void> {
    if (!this.selectedFile) {
      this.error = 'Por favor selecciona un archivo primero';
      return;
    }

    try {
      this.isLoading = true;
      this.error = null;
      
      console.log('🚀 Iniciando análisis de documento...');
      
      // Limpiar mensajes anteriores
      this.apiService.clearMessages();

      // Paso 1: Iniciar run
      console.log('📤 Enviando archivo al backend...');
      const response = await this.apiService.initiateRun(this.selectedFile).toPromise();
      
      if (!response || !response.run_id) {
        throw new Error('No se recibió un run_id válido del backend');
      }
      
      console.log('✅ Run iniciado con ID:', response.run_id);
      
      // Emitir evento de inicio
      this.executionStarted.emit({
        runId: response.run_id,
        file: this.selectedFile
      });
      
      // Paso 2: Conectar al WebSocket
      console.log('🔌 Conectando al stream de WebSocket...');
      const streamSubscription = this.apiService.connectToStream(response.run_id).subscribe({
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
      console.error('❌ Error en ejecución:', error);
      this.error = `Error: ${error.message || error}`;
      this.isLoading = false;
    }
  }

  /**
   * Detiene la ejecución actual
   */
  stopExecution(): void {
    console.log('🛑 Deteniendo ejecución...');
    this.apiService.disconnectWebSocket();
    this.isLoading = false;
    this.error = null;
  }

  /**
   * Limpia el archivo seleccionado
   */
  clearSelection(): void {
    this.selectedFile = null;
    this.error = null;
    
    // También limpiar el input file
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    if (fileInput) {
      fileInput.value = '';
    }
  }

  /**
   * Valida si el archivo es de un tipo aceptable
   */
  private isValidFile(file: File): boolean {
    const validExtensions = ['.md', '.txt'];
    const validTypes = ['text/plain', 'text/markdown'];
    
    const extension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));
    const isValidExtension = validExtensions.includes(extension);
    const isValidType = validTypes.includes(file.type) || file.type.startsWith('text/');
    
    return isValidExtension || isValidType;
  }

  /**
   * Formatea el tamaño del archivo para display
   */
  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  /**
   * Obtiene el icono apropiado para el tipo de archivo
   */
  getFileIcon(filename: string): string {
    const extension = filename.toLowerCase().substring(filename.lastIndexOf('.'));
    
    switch (extension) {
      case '.md':
        return 'article';
      case '.txt':
        return 'description';
      default:
        return 'insert_drive_file';
    }
  }
}