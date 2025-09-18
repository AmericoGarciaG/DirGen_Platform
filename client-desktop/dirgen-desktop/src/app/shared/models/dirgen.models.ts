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
  | 'status'
  | 'error'
  | 'completion'
  | 'file_operation'
  | 'log';

// Interface base para todos los mensajes WebSocket
export interface BaseMessage {
  type: DirgenMessageType;
  timestamp: string;
  run_id: string;
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

// Union type de todos los mensajes posibles
export type DirgenMessage = 
  | ThoughtMessage 
  | PlanMessage 
  | StatusMessage 
  | ErrorMessage 
  | CompletionMessage 
  | FileOperationMessage 
  | LogMessage;

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

// Interface para el estado del test de conexión
export interface TestConnectionState {
  isLoading: boolean;
  selectedFile?: File;
  runId?: string;
  webSocketState: WebSocketState;
  error?: string;
}