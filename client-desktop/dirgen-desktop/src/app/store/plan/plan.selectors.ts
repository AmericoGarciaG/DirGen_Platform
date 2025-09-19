import { createFeatureSelector, createSelector } from '@ngrx/store';
import { PlanState, TaskStatus } from '../models';

export const selectPlanState = createFeatureSelector<PlanState>('plan');

// Plan Selectors
export const selectCurrentPlan = createSelector(
  selectPlanState,
  (state: PlanState) => state.currentPlan
);

export const selectPlanTasks = createSelector(
  selectCurrentPlan,
  (plan) => plan?.tasks || []
);

export const selectPlanStatus = createSelector(
  selectCurrentPlan,
  (plan) => plan?.status || null
);

export const selectCurrentTaskId = createSelector(
  selectCurrentPlan,
  (plan) => plan?.currentTaskId || null
);

export const selectCurrentTask = createSelector(
  selectPlanTasks,
  selectCurrentTaskId,
  (tasks, currentTaskId) => tasks.find(task => task.id === currentTaskId) || null
);

// Task Status Selectors
export const selectTasksByStatus = createSelector(
  selectPlanTasks,
  (tasks) => {
    const tasksByStatus: { [status in TaskStatus]: any[] } = {
      pending: [],
      in_progress: [],
      completed: [],
      failed: [],
      blocked: []
    };
    
    tasks.forEach(task => {
      tasksByStatus[task.status].push(task);
    });
    
    return tasksByStatus;
  }
);

export const selectPendingTasks = createSelector(
  selectTasksByStatus,
  (tasksByStatus) => tasksByStatus.pending
);

export const selectInProgressTasks = createSelector(
  selectTasksByStatus,
  (tasksByStatus) => tasksByStatus.in_progress
);

export const selectCompletedTasks = createSelector(
  selectTasksByStatus,
  (tasksByStatus) => tasksByStatus.completed
);

export const selectFailedTasks = createSelector(
  selectTasksByStatus,
  (tasksByStatus) => tasksByStatus.failed
);

// Progress Selectors
export const selectPlanProgress = createSelector(
  selectPlanTasks,
  (tasks) => {
    if (tasks.length === 0) return { percentage: 0, completed: 0, total: 0 };
    
    const completed = tasks.filter(task => task.status === 'completed').length;
    const total = tasks.length;
    const percentage = Math.round((completed / total) * 100);
    
    return { percentage, completed, total };
  }
);

export const selectNextTask = createSelector(
  selectPendingTasks,
  (pendingTasks) => pendingTasks.sort((a, b) => a.order - b.order)[0] || null
);

// UI State Selectors
export const selectExpandedTaskIds = createSelector(
  selectPlanState,
  (state: PlanState) => state.expandedTaskIds
);

export const selectPlanLoading = createSelector(
  selectPlanState,
  (state: PlanState) => state.loading
);

export const selectPlanError = createSelector(
  selectPlanState,
  (state: PlanState) => state.error
);

// Task-specific Selectors
export const createSelectTaskById = (taskId: string) => createSelector(
  selectPlanTasks,
  (tasks) => tasks.find(task => task.id === taskId) || null
);

export const createSelectIsTaskExpanded = (taskId: string) => createSelector(
  selectExpandedTaskIds,
  (expandedIds) => expandedIds.includes(taskId)
);

// Plan Summary Selectors
export const selectPlanSummary = createSelector(
  selectCurrentPlan,
  selectPlanProgress,
  selectCurrentTask,
  (plan, progress, currentTask) => ({
    title: plan?.title || 'Sin plan',
    status: plan?.status || null,
    progress: progress,
    currentTask: currentTask?.title || null,
    createdAt: plan?.createdAt || null,
    approvedAt: plan?.approvedAt || null
  })
);

// Artifacts Selectors
export const selectAllArtifacts = createSelector(
  selectPlanTasks,
  (tasks) => {
    const artifacts: string[] = [];
    tasks.forEach(task => {
      artifacts.push(...task.actualArtifacts);
    });
    return [...new Set(artifacts)]; // Remove duplicates
  }
);

export const selectExpectedArtifacts = createSelector(
  selectPlanTasks,
  (tasks) => {
    const artifacts: string[] = [];
    tasks.forEach(task => {
      artifacts.push(...task.expectedArtifacts);
    });
    return [...new Set(artifacts)]; // Remove duplicates
  }
);