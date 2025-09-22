// Models para el Estado de la Aplicación DirGen

export interface ContextFile {
  id: string;
  name: string;
  type: 'svad' | 'pcce' | 'other';
  size: number;
  uploadedAt: Date;
  content?: string; // Contenido del archivo si se necesita
}

export interface DeliverableFile {
  id: string;
  path: string;
  name: string;
  type: string;
  createdAt: Date;
  createdBy: string; // Qué agente lo creó
  size?: number;
  description?: string;
}

export type TaskStatus = 'pending' | 'in_progress' | 'completed' | 'failed' | 'blocked';

export interface PlanTask {
  id: string;
  title: string;
  description: string;
  status: TaskStatus;
  order: number;
  justification?: string; // Por qué esta tarea es necesaria
  expectedArtifacts: string[]; // Lista de archivos que se espera genere
  actualArtifacts: string[]; // Archivos que realmente generó
  assignedAgent?: string; // Qué agente está trabajando en esta tarea
  startedAt?: Date;
  completedAt?: Date;
  estimatedDuration?: number; // en minutos
  actualDuration?: number; // en minutos
}

export interface ExecutionPlan {
  id: string;
  runId: string;
  title: string;
  description: string;
  status: 'draft' | 'approved' | 'executing' | 'completed' | 'failed';
  tasks: PlanTask[];
  createdAt: Date;
  approvedAt?: Date;
  completedAt?: Date;
  currentTaskId?: string; // ID de la tarea que se está ejecutando actualmente
}

// Estados de los features
export interface WorkspaceState {
  contextFiles: ContextFile[];
  deliverables: DeliverableFile[];
  selectedTabIndex: number; // 0 = Contexto, 1 = Entregables
  loading: boolean;
  error: string | null;
}

export interface PlanState {
  currentPlan: ExecutionPlan | null;
  expandedTaskIds: string[]; // IDs de las tareas que están expandidas en la UI
  loading: boolean;
  error: string | null;
}

export interface ApplicationState {
  // Estado general de la aplicación
  status: 'idle' | 'initializing' | 'running' | 'waiting_approval' | 'completed' | 'error';
  
  // Información del run actual
  currentRunId: string | null;
  currentFile: {
    file: File | null;
    name: string | null;
    size: number | null;
    prompt: string | null;
  };
  
  // Estado de carga
  isLoading: boolean;
  error: string | null;
  
  // WebSocket
  webSocketConnected: boolean;
  webSocketError: string | null;
  
  // Plan approval state
  waitingForApproval: boolean;
  planApprovalInProgress: boolean;
  
  // Estado del SDLC
  currentSdlcStatus: string | null;  // Estado técnico del backend
  currentSdlcPhase: string | null;   // Nombre legible para UI
  sdlcMetadata: any;
}

// Estado raíz de la aplicación
export interface AppState {
  app: ApplicationState;
  workspace: WorkspaceState;
  plan: PlanState;
}

// Estado inicial
export const initialWorkspaceState: WorkspaceState = {
  contextFiles: [],
  deliverables: [],
  selectedTabIndex: 0,
  loading: false,
  error: null
};

export const initialPlanState: PlanState = {
  currentPlan: null,
  expandedTaskIds: [],
  loading: false,
  error: null
};

export const initialApplicationState: ApplicationState = {
  status: 'idle',
  currentRunId: null,
  currentFile: {
    file: null,
    name: null,
    size: null,
    prompt: null
  },
  isLoading: false,
  error: null,
  webSocketConnected: false,
  webSocketError: null,
  waitingForApproval: false,
  planApprovalInProgress: false,
  currentSdlcStatus: null,
  currentSdlcPhase: null,
  sdlcMetadata: {}
};

// Helpers para crear objetos
export const createContextFile = (name: string, size: number, type: 'svad' | 'pcce' | 'other' = 'other'): ContextFile => ({
  id: `ctx_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
  name,
  type,
  size,
  uploadedAt: new Date()
});

export const createDeliverableFile = (path: string, createdBy: string, description?: string): DeliverableFile => ({
  id: `del_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
  path,
  name: path.split('/').pop() || path,
  type: path.split('.').pop() || 'unknown',
  createdAt: new Date(),
  createdBy,
  description
});

export const createPlanTask = (title: string, description: string, order: number): PlanTask => ({
  id: `task_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
  title,
  description,
  status: 'pending',
  order,
  expectedArtifacts: [],
  actualArtifacts: []
});

export const createExecutionPlan = (runId: string, title: string, tasks: PlanTask[]): ExecutionPlan => ({
  id: `plan_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
  runId,
  title,
  description: `Plan de ejecución para ${title}`,
  status: 'draft',
  tasks: tasks.map((task, index) => ({ ...task, order: index + 1 })),
  createdAt: new Date()
});