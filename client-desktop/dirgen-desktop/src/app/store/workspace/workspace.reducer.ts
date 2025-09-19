import { createReducer, on } from '@ngrx/store';
import { WorkspaceState, initialWorkspaceState, createContextFile, createDeliverableFile } from '../models';
import * as WorkspaceActions from './workspace.actions';

export const workspaceReducer = createReducer(
  initialWorkspaceState,
  
  // Context Files
  on(WorkspaceActions.addContextFile, (state, { file }) => ({
    ...state,
    contextFiles: [...state.contextFiles, file],
    error: null
  })),
  
  on(WorkspaceActions.removeContextFile, (state, { fileId }) => ({
    ...state,
    contextFiles: state.contextFiles.filter(file => file.id !== fileId)
  })),
  
  on(WorkspaceActions.clearContextFiles, (state) => ({
    ...state,
    contextFiles: []
  })),
  
  // Deliverables
  on(WorkspaceActions.addDeliverable, (state, { deliverable }) => ({
    ...state,
    deliverables: [...state.deliverables, deliverable],
    error: null
  })),
  
  on(WorkspaceActions.updateDeliverable, (state, { deliverableId, updates }) => ({
    ...state,
    deliverables: state.deliverables.map(deliverable =>
      deliverable.id === deliverableId 
        ? { ...deliverable, ...updates }
        : deliverable
    )
  })),
  
  on(WorkspaceActions.removeDeliverable, (state, { deliverableId }) => ({
    ...state,
    deliverables: state.deliverables.filter(deliverable => deliverable.id !== deliverableId)
  })),
  
  on(WorkspaceActions.clearDeliverables, (state) => ({
    ...state,
    deliverables: []
  })),
  
  // UI State
  on(WorkspaceActions.setSelectedTab, (state, { tabIndex }) => ({
    ...state,
    selectedTabIndex: tabIndex
  })),
  
  on(WorkspaceActions.setWorkspaceLoading, (state, { loading }) => ({
    ...state,
    loading
  })),
  
  on(WorkspaceActions.setWorkspaceError, (state, { error }) => ({
    ...state,
    error,
    loading: false
  })),
  
  // WebSocket-derived actions
  on(WorkspaceActions.fileUploadedFromCommand, (state, { fileName, fileSize, fileType }) => {
    const file = createContextFile(fileName, fileSize, fileType);
    return {
      ...state,
      contextFiles: [...state.contextFiles, file],
      selectedTabIndex: 0 // Switch to context tab when file is uploaded
    };
  }),
  
  on(WorkspaceActions.deliverableCreatedFromAgent, (state, { filePath, agentName, description }) => {
    const deliverable = createDeliverableFile(filePath, agentName, description);
    return {
      ...state,
      deliverables: [...state.deliverables, deliverable],
      selectedTabIndex: 1 // Switch to deliverables tab when new file is created
    };
  })
);