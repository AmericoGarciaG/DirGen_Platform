import { createFeatureSelector, createSelector } from '@ngrx/store';
import { WorkspaceState } from '../models';

export const selectWorkspaceState = createFeatureSelector<WorkspaceState>('workspace');

// Context Files Selectors
export const selectContextFiles = createSelector(
  selectWorkspaceState,
  (state: WorkspaceState) => state.contextFiles
);

export const selectContextFilesCount = createSelector(
  selectContextFiles,
  (files) => files.length
);

export const selectSvadFiles = createSelector(
  selectContextFiles,
  (files) => files.filter(file => file.type === 'svad')
);

export const selectPcceFiles = createSelector(
  selectContextFiles,
  (files) => files.filter(file => file.type === 'pcce')
);

// Deliverables Selectors
export const selectDeliverables = createSelector(
  selectWorkspaceState,
  (state: WorkspaceState) => state.deliverables
);

export const selectDeliverablesCount = createSelector(
  selectDeliverables,
  (deliverables) => deliverables.length
);

export const selectDeliverablesByAgent = createSelector(
  selectDeliverables,
  (deliverables) => {
    const byAgent: { [agentName: string]: any[] } = {};
    deliverables.forEach(deliverable => {
      if (!byAgent[deliverable.createdBy]) {
        byAgent[deliverable.createdBy] = [];
      }
      byAgent[deliverable.createdBy].push(deliverable);
    });
    return byAgent;
  }
);

export const selectRecentDeliverables = createSelector(
  selectDeliverables,
  (deliverables) => {
    return deliverables
      .slice() // Create a copy to avoid mutating the original array
      .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
      .slice(0, 10); // Get the 10 most recent
  }
);

// UI State Selectors
export const selectSelectedTabIndex = createSelector(
  selectWorkspaceState,
  (state: WorkspaceState) => state.selectedTabIndex
);

export const selectWorkspaceLoading = createSelector(
  selectWorkspaceState,
  (state: WorkspaceState) => state.loading
);

export const selectWorkspaceError = createSelector(
  selectWorkspaceState,
  (state: WorkspaceState) => state.error
);

// Composite Selectors
export const selectWorkspaceSummary = createSelector(
  selectContextFilesCount,
  selectDeliverablesCount,
  selectWorkspaceLoading,
  (contextCount, deliverablesCount, loading) => ({
    contextFilesCount: contextCount,
    deliverablesCount: deliverablesCount,
    loading
  })
);