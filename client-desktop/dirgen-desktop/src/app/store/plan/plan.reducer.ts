import { createReducer, on } from '@ngrx/store';
import { PlanState, initialPlanState, createExecutionPlan, createPlanTask } from '../models';
import * as PlanActions from './plan.actions';

export const planReducer = createReducer(
  initialPlanState,
  
  // Plan Management
  on(PlanActions.loadPlan, (state) => ({
    ...state,
    loading: true,
    error: null
  })),
  
  on(PlanActions.loadPlanSuccess, (state, { plan }) => ({
    ...state,
    currentPlan: plan,
    loading: false,
    error: null
  })),
  
  on(PlanActions.loadPlanFailure, (state, { error }) => ({
    ...state,
    loading: false,
    error
  })),
  
  on(PlanActions.createPlan, (state, { plan }) => ({
    ...state,
    currentPlan: plan,
    loading: false,
    error: null
  })),
  
  on(PlanActions.updatePlanStatus, (state, { planId, status }) => ({
    ...state,
    currentPlan: state.currentPlan && state.currentPlan.id === planId
      ? { ...state.currentPlan, status }
      : state.currentPlan
  })),
  
  on(PlanActions.approvePlan, (state, { planId }) => ({
    ...state,
    currentPlan: state.currentPlan && state.currentPlan.id === planId
      ? { ...state.currentPlan, status: 'approved' as const, approvedAt: new Date() }
      : state.currentPlan
  })),
  
  on(PlanActions.clearCurrentPlan, (state) => ({
    ...state,
    currentPlan: null,
    expandedTaskIds: [],
    error: null
  })),
  
  // Task Management
  on(PlanActions.updateTaskStatus, (state, { taskId, status, startedAt, completedAt }) => ({
    ...state,
    currentPlan: state.currentPlan ? {
      ...state.currentPlan,
      tasks: state.currentPlan.tasks.map(task =>
        task.id === taskId
          ? { 
              ...task, 
              status,
              ...(startedAt && { startedAt }),
              ...(completedAt && { completedAt })
            }
          : task
      ),
      ...(status === 'in_progress' && { currentTaskId: taskId })
    } : state.currentPlan
  })),
  
  on(PlanActions.assignTaskToAgent, (state, { taskId, agentName }) => ({
    ...state,
    currentPlan: state.currentPlan ? {
      ...state.currentPlan,
      tasks: state.currentPlan.tasks.map(task =>
        task.id === taskId
          ? { ...task, assignedAgent: agentName }
          : task
      )
    } : state.currentPlan
  })),
  
  on(PlanActions.addArtifactToTask, (state, { taskId, artifactPath }) => ({
    ...state,
    currentPlan: state.currentPlan ? {
      ...state.currentPlan,
      tasks: state.currentPlan.tasks.map(task =>
        task.id === taskId
          ? { 
              ...task, 
              actualArtifacts: [...task.actualArtifacts, artifactPath]
            }
          : task
      )
    } : state.currentPlan
  })),
  
  on(PlanActions.updateTaskProgress, (state, { taskId, updates }) => ({
    ...state,
    currentPlan: state.currentPlan ? {
      ...state.currentPlan,
      tasks: state.currentPlan.tasks.map(task =>
        task.id === taskId
          ? { ...task, ...updates }
          : task
      )
    } : state.currentPlan
  })),
  
  // UI State
  on(PlanActions.toggleTaskExpansion, (state, { taskId }) => ({
    ...state,
    expandedTaskIds: state.expandedTaskIds.includes(taskId)
      ? state.expandedTaskIds.filter(id => id !== taskId)
      : [...state.expandedTaskIds, taskId]
  })),
  
  on(PlanActions.expandAllTasks, (state) => ({
    ...state,
    expandedTaskIds: state.currentPlan 
      ? state.currentPlan.tasks.map(task => task.id)
      : []
  })),
  
  on(PlanActions.collapseAllTasks, (state) => ({
    ...state,
    expandedTaskIds: []
  })),
  
  on(PlanActions.setCurrentTaskId, (state, { taskId }) => ({
    ...state,
    currentPlan: state.currentPlan 
      ? { ...state.currentPlan, currentTaskId: taskId || undefined }
      : state.currentPlan
  })),
  
  on(PlanActions.setPlanLoading, (state, { loading }) => ({
    ...state,
    loading
  })),
  
  on(PlanActions.setPlanError, (state, { error }) => ({
    ...state,
    error,
    loading: false
  })),
  
  // WebSocket-derived actions
  on(PlanActions.planGeneratedFromAgent, (state, { runId, tasks, planData }) => {
    // Convertir las tareas del agente al formato interno
    const planTasks = tasks.map((task: any, index: number) => 
      createPlanTask(
        task.title || task.description || `Tarea ${index + 1}`,
        task.description || task.title || '',
        index + 1
      )
    );
    
    const newPlan = createExecutionPlan(
      runId,
      planData?.title || `Plan para ${runId}`,
      planTasks
    );
    
    return {
      ...state,
      currentPlan: newPlan,
      loading: false,
      error: null
    };
  }),
  
  on(PlanActions.taskStartedFromAgent, (state, { taskId, agentName }) => ({
    ...state,
    currentPlan: state.currentPlan ? {
      ...state.currentPlan,
      tasks: state.currentPlan.tasks.map(task =>
        task.id === taskId
          ? { 
              ...task, 
              status: 'in_progress' as const,
              assignedAgent: agentName,
              startedAt: new Date()
            }
          : task
      ),
      currentTaskId: taskId
    } : state.currentPlan
  })),
  
  on(PlanActions.taskCompletedFromAgent, (state, { taskId, artifacts }) => ({
    ...state,
    currentPlan: state.currentPlan ? {
      ...state.currentPlan,
      tasks: state.currentPlan.tasks.map(task =>
        task.id === taskId
          ? { 
              ...task, 
              status: 'completed' as const,
              completedAt: new Date(),
              actualArtifacts: artifacts || task.actualArtifacts
            }
          : task
      ),
      currentTaskId: state.currentPlan.currentTaskId === taskId ? undefined : state.currentPlan.currentTaskId
    } : state.currentPlan
  })),
  
  on(PlanActions.planApprovedFromUser, (state, { runId, userResponse }) => ({
    ...state,
    currentPlan: state.currentPlan && state.currentPlan.runId === runId ? {
      ...state.currentPlan,
      status: 'approved' as const,
      approvedAt: new Date()
    } : state.currentPlan
  }))
);