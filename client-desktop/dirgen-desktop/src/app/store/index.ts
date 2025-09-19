import { ActionReducerMap, MetaReducer } from '@ngrx/store';
import { environment } from '../../environments/environment';

// Import reducers
import { workspaceReducer } from './workspace/workspace.reducer';
import { planReducer } from './plan/plan.reducer';

// Import state interfaces
import { AppState } from './models';

// Root reducer map
export const reducers: ActionReducerMap<AppState> = {
  workspace: workspaceReducer,
  plan: planReducer
};

// Meta reducers for development
export const metaReducers: MetaReducer<AppState>[] = !environment.production ? [] : [];

// Re-export everything for convenience
export * from './models';
export * from './workspace/workspace.actions';
export * from './workspace/workspace.selectors';
export * from './plan/plan.actions';
export * from './plan/plan.selectors';