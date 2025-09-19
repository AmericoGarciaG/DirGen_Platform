import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Store } from '@ngrx/store';
import { Observable, Subscription } from 'rxjs';

// Angular Material
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatBadgeModule } from '@angular/material/badge';

// Store
import { AppState, ExecutionPlan, PlanTask, TaskStatus } from '../../../../store/models';
import * as PlanSelectors from '../../../../store/plan/plan.selectors';
import * as PlanActions from '../../../../store/plan/plan.actions';

@Component({
  selector: 'app-plan-widget',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatExpansionModule,
    MatButtonModule,
    MatProgressBarModule,
    MatChipsModule,
    MatTooltipModule,
    MatBadgeModule
  ],
  templateUrl: './plan-widget.component.html',
  styleUrls: ['./plan-widget.component.scss']
})
export class PlanWidgetComponent implements OnInit, OnDestroy {
  
  // Observables from Store
  currentPlan$: Observable<ExecutionPlan | null>;
  planTasks$: Observable<PlanTask[]>;
  planProgress$: Observable<any>;
  expandedTaskIds$: Observable<string[]>;
  currentTask$: Observable<PlanTask | null>;
  loading$: Observable<boolean>;
  error$: Observable<string | null>;
  
  private subscriptions: Subscription[] = [];
  
  constructor(private store: Store<AppState>) {
    // Initialize observables
    this.currentPlan$ = this.store.select(PlanSelectors.selectCurrentPlan);
    this.planTasks$ = this.store.select(PlanSelectors.selectPlanTasks);
    this.planProgress$ = this.store.select(PlanSelectors.selectPlanProgress);
    this.expandedTaskIds$ = this.store.select(PlanSelectors.selectExpandedTaskIds);
    this.currentTask$ = this.store.select(PlanSelectors.selectCurrentTask);
    this.loading$ = this.store.select(PlanSelectors.selectPlanLoading);
    this.error$ = this.store.select(PlanSelectors.selectPlanError);
  }
  
  ngOnInit(): void {
    // Component initialization logic if needed
  }
  
  ngOnDestroy(): void {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }
  
  /**
   * Toggles expansion state of a task panel
   */
  onTaskToggle(taskId: string): void {
    this.store.dispatch(PlanActions.toggleTaskExpansion({ taskId }));
  }
  
  /**
   * Expands all tasks
   */
  expandAllTasks(): void {
    this.store.dispatch(PlanActions.expandAllTasks());
  }
  
  /**
   * Collapses all tasks
   */
  collapseAllTasks(): void {
    this.store.dispatch(PlanActions.collapseAllTasks());
  }
  
  /**
   * Gets the icon for task status
   */
  getStatusIcon(status: TaskStatus): string {
    switch (status) {
      case 'pending': return 'radio_button_unchecked';
      case 'in_progress': return 'radio_button_partial';
      case 'completed': return 'check_circle';
      case 'failed': return 'error';
      case 'blocked': return 'block';
      default: return 'help';
    }
  }
  
  /**
   * Gets the color for task status
   */
  getStatusColor(status: TaskStatus): string {
    switch (status) {
      case 'pending': return '';
      case 'in_progress': return 'primary';
      case 'completed': return 'accent';
      case 'failed': return 'warn';
      case 'blocked': return 'warn';
      default: return '';
    }
  }
  
  /**
   * Gets the display text for status
   */
  getStatusText(status: TaskStatus): string {
    switch (status) {
      case 'pending': return 'Pendiente';
      case 'in_progress': return 'En Progreso';
      case 'completed': return 'Completada';
      case 'failed': return 'Falló';
      case 'blocked': return 'Bloqueada';
      default: return 'Desconocido';
    }
  }
  
  /**
   * Gets the display name for an agent
   */
  getAgentDisplayName(agentName?: string): string {
    if (!agentName) return 'Sin asignar';
    
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
   * Formats duration in minutes to readable string
   */
  formatDuration(minutes?: number): string {
    if (!minutes) return '--';
    
    if (minutes < 60) {
      return `${minutes}m`;
    } else {
      const hours = Math.floor(minutes / 60);
      const remainingMinutes = minutes % 60;
      return remainingMinutes > 0 ? `${hours}h ${remainingMinutes}m` : `${hours}h`;
    }
  }
  
  /**
   * Formats timestamp for display
   */
  formatTimestamp(date?: Date): string {
    if (!date) return '--';
    
    return new Date(date).toLocaleString('es-ES', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
  
  /**
   * Track function for ngFor optimization
   */
  trackByTaskId(index: number, task: PlanTask): string {
    return task.id;
  }
  
  /**
   * Check if a task is expanded
   */
  isTaskExpanded(taskId: string, expandedIds: string[]): boolean {
    return expandedIds.includes(taskId);
  }
}
