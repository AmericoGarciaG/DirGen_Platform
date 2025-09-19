import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Store } from '@ngrx/store';
import { Observable, Subscription } from 'rxjs';

// Angular Material
import { MatTabsModule } from '@angular/material/tabs';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatBadgeModule } from '@angular/material/badge';
import { MatListModule } from '@angular/material/list';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatButtonModule } from '@angular/material/button';

// Store
import { AppState, ContextFile, DeliverableFile } from '../../store/models';
import * as WorkspaceSelectors from '../../store/workspace/workspace.selectors';
import * as WorkspaceActions from '../../store/workspace/workspace.actions';

@Component({
  selector: 'app-workspace',
  standalone: true,
  imports: [
    CommonModule,
    MatTabsModule,
    MatCardModule,
    MatIconModule,
    MatBadgeModule,
    MatListModule,
    MatChipsModule,
    MatTooltipModule,
    MatProgressBarModule,
    MatButtonModule
  ],
  templateUrl: './workspace.component.html',
  styleUrls: ['./workspace.component.scss']
})
export class WorkspaceComponent implements OnInit, OnDestroy {
  
  // Observables from Store
  contextFiles$: Observable<ContextFile[]>;
  deliverables$: Observable<DeliverableFile[]>;
  selectedTabIndex$: Observable<number>;
  loading$: Observable<boolean>;
  error$: Observable<string | null>;
  workspaceSummary$: Observable<any>;
  
  private subscriptions: Subscription[] = [];
  
  constructor(private store: Store<AppState>) {
    // Initialize observables
    this.contextFiles$ = this.store.select(WorkspaceSelectors.selectContextFiles);
    this.deliverables$ = this.store.select(WorkspaceSelectors.selectDeliverables);
    this.selectedTabIndex$ = this.store.select(WorkspaceSelectors.selectSelectedTabIndex);
    this.loading$ = this.store.select(WorkspaceSelectors.selectWorkspaceLoading);
    this.error$ = this.store.select(WorkspaceSelectors.selectWorkspaceError);
    this.workspaceSummary$ = this.store.select(WorkspaceSelectors.selectWorkspaceSummary);
  }
  
  ngOnInit(): void {
    // Component initialization logic if needed
  }
  
  ngOnDestroy(): void {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }
  
  /**
   * Handles tab change events
   */
  onTabChange(index: number): void {
    this.store.dispatch(WorkspaceActions.setSelectedTab({ tabIndex: index }));
  }
  
  /**
   * Removes a context file
   */
  removeContextFile(fileId: string): void {
    this.store.dispatch(WorkspaceActions.removeContextFile({ fileId }));
  }
  
  /**
   * Removes a deliverable
   */
  removeDeliverable(deliverableId: string): void {
    this.store.dispatch(WorkspaceActions.removeDeliverable({ deliverableId }));
  }
  
  /**
   * Gets the appropriate icon for a file type
   */
  getFileIcon(fileName: string): string {
    const extension = fileName.split('.').pop()?.toLowerCase();
    
    switch (extension) {
      case 'md': return 'article';
      case 'txt': return 'description';
      case 'json': return 'code';
      case 'yml':
      case 'yaml': return 'settings';
      case 'puml': return 'account_tree';
      case 'png':
      case 'jpg':
      case 'jpeg':
      case 'gif': return 'image';
      case 'pdf': return 'picture_as_pdf';
      case 'html': return 'language';
      case 'css': return 'palette';
      case 'js':
      case 'ts': return 'javascript';
      default: return 'insert_drive_file';
    }
  }
  
  /**
   * Gets the color for file type chips
   */
  getFileTypeColor(type: string): string {
    switch (type.toLowerCase()) {
      case 'svad': return 'primary';
      case 'pcce': return 'accent';
      case 'md': return 'primary';
      case 'json': return 'warn';
      case 'yml':
      case 'yaml': return 'accent';
      default: return '';
    }
  }
  
  /**
   * Formats file size for display
   */
  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 B';
    
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }
  
  /**
   * Formats timestamp for display
   */
  formatTimestamp(date: Date): string {
    return new Date(date).toLocaleString('es-ES', {
      day: '2-digit',
      month: '2-digit',
      year: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
  
  /**
   * Gets human-readable agent name
   */
  getAgentDisplayName(agentName: string): string {
    const agentNames: { [key: string]: string } = {
      'planner': 'Planificador',
      'requirements': 'Análisis de Req.',
      'validator': 'Validador',
      'architect': 'Arquitecto',
      'developer': 'Desarrollador',
      'tester': 'Tester'
    };
    
    return agentNames[agentName.toLowerCase()] || agentName;
  }
  
  /**
   * Gets the color for agent chips
   */
  getAgentColor(agentName: string): string {
    const colors: { [key: string]: string } = {
      'planner': 'primary',
      'requirements': 'accent',
      'validator': 'warn',
      'architect': 'primary',
      'developer': 'accent',
      'tester': 'warn'
    };
    
    return colors[agentName.toLowerCase()] || '';
  }
  
  /**
   * Track function for ngFor optimization
   */
  trackByFileId(index: number, file: ContextFile | DeliverableFile): string {
    return file.id;
  }
}