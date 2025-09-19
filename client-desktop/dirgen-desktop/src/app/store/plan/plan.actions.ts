import { createAction, props } from '@ngrx/store';
import { ExecutionPlan, PlanTask, TaskStatus } from '../models';

// Acciones para Plan Management
export const loadPlan = createAction(
  '[Plan] Load Plan',
  props<{ runId: string }>()
);

export const loadPlanSuccess = createAction(
  '[Plan] Load Plan Success',
  props<{ plan: ExecutionPlan }>()
);

export const loadPlanFailure = createAction(
  '[Plan] Load Plan Failure',
  props<{ error: string }>()
);

export const createPlan = createAction(
  '[Plan] Create Plan',
  props<{ plan: ExecutionPlan }>()
);

export const updatePlanStatus = createAction(
  '[Plan] Update Plan Status',
  props<{ planId: string; status: ExecutionPlan['status'] }>()
);

export const approvePlan = createAction(
  '[Plan] Approve Plan',
  props<{ planId: string }>()
);

export const clearCurrentPlan = createAction(
  '[Plan] Clear Current Plan'
);

// Acciones para Task Management
export const updateTaskStatus = createAction(
  '[Plan] Update Task Status',
  props<{ taskId: string; status: TaskStatus; startedAt?: Date; completedAt?: Date }>()
);

export const assignTaskToAgent = createAction(
  '[Plan] Assign Task To Agent',
  props<{ taskId: string; agentName: string }>()
);

export const addArtifactToTask = createAction(
  '[Plan] Add Artifact To Task',
  props<{ taskId: string; artifactPath: string }>()
);

export const updateTaskProgress = createAction(
  '[Plan] Update Task Progress',
  props<{ taskId: string; updates: Partial<PlanTask> }>()
);

// Acciones para UI state
export const toggleTaskExpansion = createAction(
  '[Plan] Toggle Task Expansion',
  props<{ taskId: string }>()
);

export const expandAllTasks = createAction(
  '[Plan] Expand All Tasks'
);

export const collapseAllTasks = createAction(
  '[Plan] Collapse All Tasks'
);

export const setCurrentTaskId = createAction(
  '[Plan] Set Current Task ID',
  props<{ taskId: string | null }>()
);

export const setPlanLoading = createAction(
  '[Plan] Set Loading',
  props<{ loading: boolean }>()
);

export const setPlanError = createAction(
  '[Plan] Set Error',
  props<{ error: string | null }>()
);

// Acciones derivadas de eventos WebSocket
export const planGeneratedFromAgent = createAction(
  '[Plan] Plan Generated From Agent',
  props<{ runId: string; tasks: any[]; planData?: any }>()
);

export const taskStartedFromAgent = createAction(
  '[Plan] Task Started From Agent',
  props<{ taskId: string; agentName: string }>()
);

export const taskCompletedFromAgent = createAction(
  '[Plan] Task Completed From Agent',
  props<{ taskId: string; artifacts?: string[] }>()
);

export const planApprovedFromUser = createAction(
  '[Plan] Plan Approved From User',
  props<{ runId: string; userResponse: string }>()
);