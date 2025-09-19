import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';

@Component({
  selector: 'app-monitoring-ultra-simple',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule, MatButtonModule],
  template: `
    <div class="main-container">
      <!-- Status Bar Simulado -->
      <div class="status-bar">
        <mat-icon>dashboard</mat-icon>
        <h1>DirGen Monitor Desktop</h1>
        <span class="status">✅ Funcionando</span>
      </div>

      <!-- Layout principal -->
      <div class="main-layout">
        <!-- Panel izquierdo -->
        <div class="left-panel">
          <mat-card>
            <mat-card-header>
              <mat-card-title>🎮 Control</mat-card-title>
            </mat-card-header>
            <mat-card-content>
              <button mat-raised-button color="primary">
                <mat-icon>play_arrow</mat-icon>
                Iniciar Análisis
              </button>
            </mat-card-content>
          </mat-card>
        </div>

        <!-- Panel derecho -->
        <div class="right-panel">
          <mat-card>
            <mat-card-header>
              <mat-card-title>📋 Log de Eventos</mat-card-title>
            </mat-card-header>
            <mat-card-content>
              <div class="log-entry">✅ Aplicación desktop iniciada</div>
              <div class="log-entry">🔧 Componentes cargados</div>
              <div class="log-entry">🚀 Sistema listo</div>
            </mat-card-content>
          </mat-card>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .main-container {
      height: 100vh;
      width: 100vw;
      background: #1a1a1a;
      color: #e0e0e0;
      display: flex;
      flex-direction: column;
    }

    .status-bar {
      height: 60px;
      background: linear-gradient(90deg, #2c3e50, #34495e);
      display: flex;
      align-items: center;
      padding: 0 20px;
      gap: 15px;
      border-bottom: 2px solid #3498db;

      mat-icon {
        color: #3498db;
        font-size: 28px;
      }

      h1 {
        margin: 0;
        color: #ecf0f1;
        font-size: 18px;
        flex: 1;
      }

      .status {
        color: #27ae60;
        font-weight: 500;
      }
    }

    .main-layout {
      flex: 1;
      display: flex;
      padding: 16px;
      gap: 16px;
    }

    .left-panel {
      width: 35%;
    }

    .right-panel {
      width: 65%;
    }

    mat-card {
      background: #333 !important;
      color: #e0e0e0 !important;
      height: 100%;
    }

    .log-entry {
      padding: 8px 0;
      border-bottom: 1px solid #444;
      font-family: 'Courier New', monospace;
      font-size: 14px;
    }

    button {
      width: 100%;
      height: 48px;
      font-size: 16px;
    }
  `]
})
export class MonitoringUltraSimpleComponent {
  
}