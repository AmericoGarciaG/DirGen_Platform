import { createAction, props } from '@ngrx/store';
import { ContextFile, DeliverableFile } from '../models';

// Acciones para Context Files
export const addContextFile = createAction(
  '[Workspace] Add Context File',
  props<{ file: ContextFile }>()
);

export const removeContextFile = createAction(
  '[Workspace] Remove Context File',
  props<{ fileId: string }>()
);

export const clearContextFiles = createAction(
  '[Workspace] Clear Context Files'
);

// Acciones para Deliverables
export const addDeliverable = createAction(
  '[Workspace] Add Deliverable',
  props<{ deliverable: DeliverableFile }>()
);

export const updateDeliverable = createAction(
  '[Workspace] Update Deliverable',
  props<{ deliverableId: string; updates: Partial<DeliverableFile> }>()
);

export const removeDeliverable = createAction(
  '[Workspace] Remove Deliverable',
  props<{ deliverableId: string }>()
);

export const clearDeliverables = createAction(
  '[Workspace] Clear Deliverables'
);

// Acciones para UI state
export const setSelectedTab = createAction(
  '[Workspace] Set Selected Tab',
  props<{ tabIndex: number }>()
);

export const setWorkspaceLoading = createAction(
  '[Workspace] Set Loading',
  props<{ loading: boolean }>()
);

export const setWorkspaceError = createAction(
  '[Workspace] Set Error',
  props<{ error: string | null }>()
);

// Acciones derivadas de eventos WebSocket
export const fileUploadedFromCommand = createAction(
  '[Workspace] File Uploaded From Command',
  props<{ fileName: string; fileSize: number; fileType: 'svad' | 'pcce' | 'other' }>()
);

export const deliverableCreatedFromAgent = createAction(
  '[Workspace] Deliverable Created From Agent',
  props<{ filePath: string; agentName: string; description?: string }>()
);