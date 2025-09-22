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
    // NUEVO: Manejar mensajes de cambio de estado del SDLC
    if (message.type === 'run_status_change') {
      const statusMessage = message as any;
      return {
        ...state,
        currentSdlcStatus: statusMessage.data.status,
        currentSdlcPhase: statusMessage.data.phase,
        sdlcMetadata: statusMessage.data.metadata || {}
      };
    }
    
    // Detectar si el mensaje es una solicitud de aprobación de fase de diseño (NUEVO)
    if (message.type === 'design_phase_approval_request') {
      return {
        ...state,
        status: 'waiting_approval' as const,
        waitingForApproval: true,
        isLoading: false, // CRÍTICO: resetear loading al esperar aprobación
        error: null
      };
    }
    
    // Detectar si el mensaje es una solicitud de aprobación de plan de ejecución
    if (message.type === 'plan_generated') {
      return {
        ...state,
        status: 'waiting_approval' as const,
        waitingForApproval: true,
        isLoading: false, // CRÍTICO: resetear loading al esperar aprobación
        error: null
      };
    }
    
    // Detectar si el plan fue aprobado por el backend (confirmación)
    if (message.type === 'plan_approved') {
      return {
        ...state,
        status: 'running' as const,
        waitingForApproval: false,
        planApprovalInProgress: false,
        isLoading: false,
        error: null
      };
    }
    
    // Detectar si el plan fue rechazado por el backend
    if (message.type === 'plan_rejected') {
      return {
        ...state,
        status: 'idle' as const,
        waitingForApproval: false,
        planApprovalInProgress: false,
        isLoading: false,
        currentRunId: null,
        error: null
      };
    }
    
    // Detectar si la ejecución ha comenzado
    if (message.type === 'execution_started') {
      return {
        ...state,
        status: 'running' as const,
        waitingForApproval: false,
        planApprovalInProgress: false,
        isLoading: false,
        error: null
      };
    }
    
    // CRÍTICO: Detectar errores de fase que deben resetear el estado
    if (message.type === 'phase_end') {
      const phaseData = (message as any).data;
      if (phaseData?.status === 'RECHAZADO' || phaseData?.status === 'ERROR') {
        return {
          ...state,
          status: 'error' as const,
          isLoading: false, // CRITICO: resetear loading al tener error
          waitingForApproval: false,
          planApprovalInProgress: false,
          error: `Fase ${phaseData.name || 'desconocida'} falló: ${phaseData.status}`
        };
      } else if (phaseData?.status === 'APROBADO') {
        // Continuar ejecución normal
        return {
          ...state,
          status: 'running' as const,
          isLoading: false,
          error: null
        };
      }
    }
    
    // Detectar finalización exitosa del run
    if (message.type === 'run_completed' || message.type === 'execution_completed') {
      return {
        ...state,
        status: 'completed' as const,
        isLoading: false,
        waitingForApproval: false,
        planApprovalInProgress: false,
        error: null
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

  on(AppActions.clearCurrentRun, () => ({
    ...initialApplicationState,
    // Limpiar explícitamente el estado SDLC
    currentSdlcStatus: null,
    currentSdlcPhase: null,
    sdlcMetadata: {}
  }))
);