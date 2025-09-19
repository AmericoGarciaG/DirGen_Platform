// Interfaces para la comunicación con el backend DirGen

// Respuesta del endpoint de inicio de run
export interface InitiateRunResponse {
  message: string;
  run_id: string;
}

// Tipos de mensajes WebSocket que pueden llegar del backend
export type DirgenMessageType = 
  | 'thought'
  | 'plan'
  | 'plan_generated'
  | 'plan_updated'
  | 'status'
  | 'error'
  | 'completion'
  | 'file_operation'
  | 'log'
  | 'phase_start'
  | 'phase_end'
  | 'action'
  | 'quality_gate_result'
  | 'executive_summary'
  | 'raw_message';

// Tipos adicionales basados en mensajes reales del backend
export type MessageSource = 
  | 'Orchestrator'
  | 'AnalysisAgent'
  | 'PlanningAgent'
  | 'ValidationAgent'
  | 'System'
  | 'Unknown';

// Interface base para todos los mensajes WebSocket
export interface BaseMessage {
  type?: DirgenMessageType;
  timestamp: string;
  run_id: string;
  source?: MessageSource;
  message?: string; // Mensaje crudo del backend
}

// Mensaje de pensamiento/reasoning del AI
export interface ThoughtMessage extends BaseMessage {
  type: 'thought';
  content: string;
  step?: number;
}

// Mensaje de plan/estrategia
export interface PlanMessage extends BaseMessage {
  type: 'plan';
  content: string;
  steps?: PlanStep[];
}

export interface PlanStep {
  id: string;
  description: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
}

// Mensaje de estado general
export interface StatusMessage extends BaseMessage {
  type: 'status';
  status: 'started' | 'processing' | 'completed' | 'failed';
  message: string;
  progress?: number; // 0-100
}

// Mensaje de error
export interface ErrorMessage extends BaseMessage {
  type: 'error';
  error: string;
  details?: any;
}

// Mensaje de finalización
export interface CompletionMessage extends BaseMessage {
  type: 'completion';
  success: boolean;
  result?: any;
  summary?: string;
}

// Mensaje de operación de archivo
export interface FileOperationMessage extends BaseMessage {
  type: 'file_operation';
  operation: 'create' | 'update' | 'delete' | 'read';
  file_path: string;
  content?: string;
}

// Mensaje de log genérico
export interface LogMessage extends BaseMessage {
  type: 'log';
  level: 'debug' | 'info' | 'warn' | 'error';
  message: string;
  context?: any;
}

// Mensaje de inicio de fase
export interface PhaseStartMessage extends BaseMessage {
  type: 'phase_start';
  phase: string;
  description?: string;
}

// Mensaje de fin de fase
export interface PhaseEndMessage extends BaseMessage {
  type: 'phase_end';
  data?: {
    name: string;
    status: 'APROBADO' | 'RECHAZADO' | 'EN_PROGRESO';
    reason?: string;
    [key: string]: any;
  };
}

// Mensaje de acción
export interface ActionMessage extends BaseMessage {
  type: 'action';
  action: string;
  details?: any;
}

// Mensaje crudo (sin parsear o formato desconocido)
export interface RawMessage extends BaseMessage {
  type: 'raw_message';
  raw_content: string;
}

// Mensaje de plan generado
export interface PlanGeneratedMessage extends BaseMessage {
  type: 'plan_generated';
  plan: PlanStep[];
  description?: string;
}

// Union type de todos los mensajes posibles
export type DirgenMessage = 
  | ThoughtMessage 
  | PlanMessage 
  | PlanGeneratedMessage
  | StatusMessage 
  | ErrorMessage 
  | CompletionMessage 
  | FileOperationMessage 
  | LogMessage
  | PhaseStartMessage
  | PhaseEndMessage
  | ActionMessage
  | RawMessage;

// Estados de conexión WebSocket
export type WebSocketConnectionStatus = 
  | 'disconnected' 
  | 'connecting' 
  | 'connected' 
  | 'error' 
  | 'reconnecting';

// Interface para el estado de la conexión WebSocket
export interface WebSocketState {
  status: WebSocketConnectionStatus;
  runId?: string;
  messages: DirgenMessage[];
  error?: string;
}

// Interface para el estado de ejecución actual
export interface ExecutionState {
  isRunning: boolean;
  runId?: string;
  currentPhase?: string;
  overallStatus: 'idle' | 'starting' | 'running' | 'completed' | 'failed';
  selectedFile?: File;
  startTime?: Date;
  endTime?: Date;
  error?: string;
}

// Interface para el estado del plan
export interface PlanState {
  isLoaded: boolean;
  currentPlan?: PlanStep[];
  planDescription?: string;
  lastUpdated?: Date;
}

// Interface para el estado del test de conexión (legacy)
export interface TestConnectionState {
  isLoading: boolean;
  selectedFile?: File;
  runId?: string;
  webSocketState: WebSocketState;
  error?: string;
}

// Interface para eventos de UI
export interface ExecutionStartedEvent {
  runId: string;
  file: File;
}
