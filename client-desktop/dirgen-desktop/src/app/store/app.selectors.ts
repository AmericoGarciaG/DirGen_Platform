import { createFeatureSelector, createSelector } from '@ngrx/store';
import { ApplicationState } from './models';

// Feature selector para el estado de la aplicación
export const selectAppState = createFeatureSelector<ApplicationState>('app');

// ============================================================================
// BASIC APP STATE SELECTORS
// ============================================================================

export const selectApplicationStatus = createSelector(
  selectAppState,
  (state) => state.status
);

export const selectIsLoading = createSelector(
  selectAppState,
  (state) => state.isLoading
);

export const selectAppError = createSelector(
  selectAppState,
  (state) => state.error
);

// ============================================================================
// RUN INFORMATION SELECTORS
// ============================================================================

export const selectCurrentRunId = createSelector(
  selectAppState,
  (state) => state.currentRunId
);

export const selectCurrentFile = createSelector(
  selectAppState,
  (state) => state.currentFile
);

export const selectCurrentFileName = createSelector(
  selectCurrentFile,
  (file) => file.name
);

export const selectCurrentFileSize = createSelector(
  selectCurrentFile,
  (file) => file.size
);

export const selectCurrentFilePrompt = createSelector(
  selectCurrentFile,
  (file) => file.prompt
);

// ============================================================================
// WEBSOCKET SELECTORS
// ============================================================================

export const selectWebSocketConnected = createSelector(
  selectAppState,
  (state) => state.webSocketConnected
);

export const selectWebSocketError = createSelector(
  selectAppState,
  (state) => state.webSocketError
);

// ============================================================================
// PLAN APPROVAL SELECTORS
// ============================================================================

export const selectWaitingForApproval = createSelector(
  selectAppState,
  (state) => state.waitingForApproval
);

export const selectPlanApprovalInProgress = createSelector(
  selectAppState,
  (state) => state.planApprovalInProgress
);

// ============================================================================
// SDLC STATE SELECTORS  
// ============================================================================

export const selectCurrentSdlcStatus = createSelector(
  selectAppState,
  (state) => state.currentSdlcStatus
);

export const selectCurrentSdlcPhase = createSelector(
  selectAppState,
  (state) => state.currentSdlcPhase
);

export const selectSdlcMetadata = createSelector(
  selectAppState,
  (state) => state.sdlcMetadata
);

// ============================================================================
// COMBINED SELECTORS
// ============================================================================

export const selectIsInitializing = createSelector(
  selectApplicationStatus,
  (status) => status === 'initializing'
);

export const selectIsRunning = createSelector(
  selectApplicationStatus,
  (status) => status === 'running'
);

export const selectIsIdle = createSelector(
  selectApplicationStatus,
  (status) => status === 'idle'
);

export const selectHasError = createSelector(
  selectApplicationStatus,
  (status) => status === 'error'
);

export const selectCanStartNewRun = createSelector(
  selectApplicationStatus,
  selectIsLoading,
  (status, isLoading) => status === 'idle' && !isLoading
);

export const selectRunInProgress = createSelector(
  selectCurrentRunId,
  selectApplicationStatus,
  (runId, status) => runId !== null && (status === 'running' || status === 'waiting_approval')
);

export const selectConnectionStatus = createSelector(
  selectWebSocketConnected,
  selectWebSocketError,
  selectCurrentRunId,
  (connected, error, runId) => ({
    connected,
    error,
    hasActiveRun: runId !== null
  })
);