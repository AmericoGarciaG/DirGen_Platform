import { ActionReducerMap, MetaReducer } from '@ngrx/store';
import { environment } from '../../environments/environment';

// Import reducers
import { appReducer } from './app.reducer';
import { workspaceReducer } from './workspace/workspace.reducer';
import { planReducer } from './plan/plan.reducer';

// Import state interfaces
import { AppState } from './models';

// Root reducer map
export const reducers: ActionReducerMap<AppState> = {
  app: appReducer,
  workspace: workspaceReducer,
  plan: planReducer
};

// Meta reducers for development
export const metaReducers: MetaReducer<AppState>[] = !environment.production ? [] : [];

// Re-export everything for convenience
export * from './models';
export * from './app.actions';
export * from './app.selectors';
export * from './workspace/workspace.actions';
export * from './workspace/workspace.selectors';
export * from './plan/plan.actions';
export * from './plan/plan.selectors';
