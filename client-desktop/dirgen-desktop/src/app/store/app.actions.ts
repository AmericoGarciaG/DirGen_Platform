import { createAction, props } from '@ngrx/store';

// ============================================================================
// COMMAND CENTER ACTIONS
// ============================================================================

/**
 * Se despacha cuando el usuario inicia una nueva ejecución desde el Command Center
 */
export const runInitiated = createAction(
  '[Command Center] Run Initiated',
  props<{ file: File; prompt: string }>()
);

/**
 * Se despacha cuando la API responde exitosamente al iniciar un run
 */
export const runInitiationSuccess = createAction(
  '[API] Run Initiation Success',
  props<{ run_id: string; file: File; prompt: string }>()
);

/**
 * Se despacha cuando la API falla al iniciar un run
 */
export const runInitiationFailure = createAction(
  '[API] Run Initiation Failure',
  props<{ error: any }>()
);

// ============================================================================
// WEBSOCKET CONNECTION ACTIONS
// ============================================================================

/**
 * Se despacha para iniciar la conexión WebSocket después de un run exitoso
 */
export const connectWebSocket = createAction(
  '[WebSocket] Connect',
  props<{ run_id: string }>()
);

/**
 * Se despacha cuando la conexión WebSocket se establece exitosamente
 */
export const webSocketConnected = createAction(
  '[WebSocket] Connected',
  props<{ run_id: string }>()
);

/**
 * Se despacha cuando la conexión WebSocket falla
 */
export const webSocketConnectionFailed = createAction(
  '[WebSocket] Connection Failed',
  props<{ error: any }>()
);

/**
 * Se despacha cuando se recibe un mensaje del WebSocket
 */
export const webSocketMessageReceived = createAction(
  '[WebSocket] Message Received',
  props<{ message: any }>()
);

/**
 * Se despacha para desconectar el WebSocket
 */
export const disconnectWebSocket = createAction(
  '[WebSocket] Disconnect'
);

// ============================================================================
// PLAN APPROVAL ACTIONS
// ============================================================================

/**
 * Se despacha cuando el usuario aprueba o rechaza un plan
 */
export const planApprovalSubmitted = createAction(
  '[Command Center] Plan Approval Submitted',
  props<{ run_id: string; approved: boolean; userResponse: string }>()
);

/**
 * Se despacha cuando la respuesta de aprobación es exitosa
 */
export const planApprovalSuccess = createAction(
  '[API] Plan Approval Success',
  props<{ run_id: string }>()
);

/**
 * Se despacha cuando la respuesta de aprobación falla
 */
export const planApprovalFailure = createAction(
  '[API] Plan Approval Failure',
  props<{ error: any }>()
);

// ============================================================================
// APPLICATION STATE ACTIONS
// ============================================================================

/**
 * Se despacha para actualizar el estado global de la aplicación
 */
export const setApplicationStatus = createAction(
  '[App] Set Application Status',
  props<{ status: 'idle' | 'initializing' | 'running' | 'waiting_approval' | 'completed' | 'error' }>()
);

/**
 * Se despacha para limpiar el estado de ejecución actual
 */
export const clearCurrentRun = createAction(
  '[App] Clear Current Run'
);