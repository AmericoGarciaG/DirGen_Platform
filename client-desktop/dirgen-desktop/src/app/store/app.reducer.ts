import { createReducer, on } from '@ngrx/store';
import { ApplicationState, initialApplicationState } from './models';
import * as AppActions from './app.actions';

export const appReducer = createReducer(
  initialApplicationState,

  // ============================================================================
  // RUN INITIATION
  // ============================================================================
  
  on(AppActions.runInitiated, (state, { file, prompt }) => ({
    ...state,
    status: 'initializing' as const,
    isLoading: true,
    error: null,
    currentFile: {
      file,
      name: file.name,
      size: file.size,
      prompt
    }
  })),

  on(AppActions.runInitiationSuccess, (state, { run_id, file, prompt }) => ({
    ...state,
    status: 'running' as const,
    currentRunId: run_id,
    isLoading: false,
    error: null,
    currentFile: {
      file,
      name: file.name,
      size: file.size,
      prompt
    }
  })),

  on(AppActions.runInitiationFailure, (state, { error }) => ({
    ...state,
    status: 'error' as const,
    isLoading: false,
    error: error.message || error.toString(),
    currentFile: {
      file: null,
      name: null,
      size: null,
      prompt: null
    }
  })),

  // ============================================================================
  // WEBSOCKET CONNECTION
  // ============================================================================
  
  on(AppActions.connectWebSocket, (state) => ({
    ...state,
    webSocketConnected: false,
    webSocketError: null
  })),

  on(AppActions.webSocketConnected, (state, { run_id }) => ({
    ...state,
    webSocketConnected: true,
    webSocketError: null,
    currentRunId: run_id
  })),

  on(AppActions.webSocketConnectionFailed, (state, { error }) => ({
    ...state,
    webSocketConnected: false,
    webSocketError: error.message || error.toString()
  })),

  on(AppActions.webSocketMessageReceived, (state, { message }) => {
    // Detectar si el mensaje es una solicitud de aprobación de plan
    if (message.type === 'plan_generated') {
      return {
        ...state,
        status: 'waiting_approval' as const,
        waitingForApproval: true
      };
    }
    
    // Detectar si la ejecución ha comenzado
    if (message.type === 'execution_started') {
      return {
        ...state,
        status: 'running' as const,
        waitingForApproval: false,
        planApprovalInProgress: false
      };
    }
    
    return state;
  }),

  on(AppActions.disconnectWebSocket, (state) => ({
    ...state,
    webSocketConnected: false,
    webSocketError: null
  })),

  // ============================================================================
  // PLAN APPROVAL
  // ============================================================================
  
  on(AppActions.planApprovalSubmitted, (state) => ({
    ...state,
    planApprovalInProgress: true
  })),

  on(AppActions.planApprovalSuccess, (state) => ({
    ...state,
    planApprovalInProgress: false,
    waitingForApproval: false,
    status: 'running' as const
  })),

  on(AppActions.planApprovalFailure, (state, { error }) => ({
    ...state,
    planApprovalInProgress: false,
    error: error.message || error.toString()
  })),

  // ============================================================================
  // APPLICATION STATE
  // ============================================================================
  
  on(AppActions.setApplicationStatus, (state, { status }) => ({
    ...state,
    status
  })),

  on(AppActions.clearCurrentRun, () => initialApplicationState)
);