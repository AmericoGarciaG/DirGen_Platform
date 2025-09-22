import { Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { map, switchMap, catchError, tap, filter } from 'rxjs/operators';
import { of } from 'rxjs';
import { Store } from '@ngrx/store';

// Services
import { ApiService } from '../core/services/api.service';

// Store
import { AppState } from './models';
import * as AppActions from './app.actions';
import * as WorkspaceActions from './workspace/workspace.actions';
import * as PlanActions from './plan/plan.actions';

@Injectable()
export class AppEffects {
  
  constructor(
    private actions$: Actions,
    private store: Store<AppState>,
    private apiService: ApiService
  ) {}
  
  // Listen to WebSocket messages and dispatch webSocketMessageReceived for ALL messages
  webSocketMessages$ = createEffect(() =>
    this.apiService.messages$.pipe(
      map(message => {
        console.log('📨 Processing WebSocket message in Effects:', message);
        // IMPORTANTE: Siempre despachar webSocketMessageReceived para que el reducer lo procese
        return AppActions.webSocketMessageReceived({ message });
      })
    )
  );
  
  // Effect secundario para manejar acciones específicas basadas en mensajes WebSocket
  handleSpecificWebSocketMessages$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AppActions.webSocketMessageReceived),
      switchMap(({ message }) => {
        const actions = [];
        
        // Handle different message types and generate additional actions
        switch (message.type) {
          case 'plan_generated':
            // CRÍTICO: Despachar acción para que el PlanWidget muestre el plan
            actions.push(PlanActions.planGeneratedFromAgent({
              runId: message.run_id || '',
              tasks: (message as any).data?.tasks || [],
              planData: (message as any).data
            }));
            console.log('📋 Plan generated action dispatched for PlanWidget');
            break;
            
          case 'plan_approved':
            actions.push(PlanActions.planApprovedFromUser({
              runId: message.run_id || '',
              userResponse: (message as any).data?.user_response || ''
            }));
            break;
          
          case 'executive_summary':
            actions.push(PlanActions.updateTaskProgress({
              taskId: 'summary_task',
              updates: {
                justification: (message as any).data?.summary
              }
            }));
            break;
          
          case 'file_operation':
            if ((message as any).operation === 'create') {
              actions.push(WorkspaceActions.deliverableCreatedFromAgent({
                filePath: (message as any).file_path || '',
                agentName: message.source || 'Unknown',
                description: `Archivo creado: ${(message as any).file_path}`
              }));
            }
            break;
          
          case 'action':
            if ((message as any).action?.includes('writeFile') || 
                (message as any).action?.includes('createFile')) {
              const filePath = this.extractFilePathFromAction((message as any).action);
              if (filePath) {
                actions.push(WorkspaceActions.deliverableCreatedFromAgent({
                  filePath,
                  agentName: message.source || 'Agent',
                  description: `Archivo generado por ${message.source}`
                }));
              }
            }
            break;
            
          default:
            console.log('No additional actions needed for message type:', message.type);
            break;
        }
        
        // Return all actions, or empty array if none
        return actions;
      })
    )
  );
  
  // Effect to handle file uploads from the command center
  fileUploadEffect$ = createEffect(() =>
    this.actions$.pipe(
      ofType('[CommandCenter] File Uploaded'), // This action would be dispatched by CommandCenter
      map((action: any) => 
        WorkspaceActions.fileUploadedFromCommand({
          fileName: action.fileName,
          fileSize: action.fileSize,
          fileType: action.fileType || 'other'
        })
      )
    )
  );
  
  // ============================================================================
  // RUN INITIATION EFFECTS
  // ============================================================================

  /**
   * Effect que maneja la inicialización de un run
   * Escucha la acción runInitiated y llama al ApiService
   */
  initiateRun$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AppActions.runInitiated),
      switchMap(({ file, prompt }) =>
        this.apiService.initiateRun(file).pipe(
          map(response => {
            console.log('✅ Run iniciado exitosamente en effect:', response);
            return AppActions.runInitiationSuccess({ 
              run_id: response.run_id, 
              file, 
              prompt 
            });
          }),
          catchError(error => {
            console.error('❌ Error en effect runInitiated:', error);
            return of(AppActions.runInitiationFailure({ error }));
          })
        )
      )
    )
  );

  /**
   * Effect que se dispara después de una iniciación exitosa
   * Automáticamente conecta al WebSocket y agrega el archivo al workspace
   */
  runInitiationSuccessEffects$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AppActions.runInitiationSuccess),
      switchMap(({ run_id, file, prompt }) => {
        // Agregar archivo al workspace como contexto
        const addToWorkspaceAction = WorkspaceActions.addContextFile({
          file: {
            id: `ctx_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            name: file.name,
            type: file.name.toLowerCase().endsWith('.md') ? 'svad' : 'other',
            size: file.size,
            uploadedAt: new Date(),
            content: prompt
          }
        });

        // Conectar al WebSocket
        const connectWebSocketAction = AppActions.connectWebSocket({ run_id });

        // Retornar ambas acciones
        return [addToWorkspaceAction, connectWebSocketAction];
      })
    )
  );

  // ============================================================================
  // WEBSOCKET CONNECTION EFFECTS
  // ============================================================================

  /**
   * Effect que maneja la conexión WebSocket
   */
  connectWebSocket$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AppActions.connectWebSocket),
      switchMap(({ run_id }) =>
        this.apiService.connectToStream(run_id).pipe(
          map(message => {
            console.log('📨 Mensaje WebSocket recibido en effect:', message);
            return AppActions.webSocketMessageReceived({ message });
          }),
          tap({
            subscribe: () => {
              console.log('🔌 Conexión WebSocket establecida para run:', run_id);
            }
          }),
          catchError(error => {
            console.error('❌ Error en conexión WebSocket:', error);
            return of(AppActions.webSocketConnectionFailed({ error }));
          })
        )
      )
    )
  );

  /**
   * Effect que escucha cuando se establece la conexión WebSocket
   */
  webSocketConnected$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AppActions.connectWebSocket),
      map(({ run_id }) => {
        console.log('✅ WebSocket conectado para run:', run_id);
        return AppActions.webSocketConnected({ run_id });
      })
    )
  );

  // ============================================================================
  // PLAN APPROVAL EFFECTS
  // ============================================================================

  /**
   * Effect que maneja la aprobación/rechazo de planes
   */
  submitPlanApproval$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AppActions.planApprovalSubmitted),
      switchMap(({ run_id, approved, userResponse }) => {
        return this.apiService.approvePlan(run_id, approved, userResponse).pipe(
            map(() => {
              console.log(`✅ Plan ${approved ? 'aprobado' : 'rechazado'} exitosamente`);
              if (approved) {
                return AppActions.planApprovalSuccess({ run_id });
              } else {
                // Si el plan fue rechazado, limpiar el run actual
                return AppActions.clearCurrentRun();
              }
            }),
            catchError(error => {
              console.error(`❌ Error ${approved ? 'aprobando' : 'rechazando'} plan:`, error);
              return of(AppActions.planApprovalFailure({ error }));
            })
          );
      })
    )
  );

  // ============================================================================
  // DISCONNECTION EFFECTS
  // ============================================================================

  /**
   * Effect que maneja la desconexión del WebSocket
   */
  disconnectWebSocket$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AppActions.disconnectWebSocket),
      tap(() => {
        console.log('🔌 Desconectando WebSocket...');
        this.apiService.disconnectWebSocket();
      })
    ), 
    { dispatch: false } // Este effect no despacha nuevas acciones
  );

  /**
   * Effect que se ejecuta al limpiar el run actual
   */
  clearCurrentRun$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AppActions.clearCurrentRun),
      tap(() => {
        console.log('🧹 Limpiando run actual...');
        this.apiService.disconnectWebSocket();
        this.apiService.clearMessages();
      })
    ), 
    { dispatch: false }
  );

  // Helper method to extract file path from action strings
  private extractFilePathFromAction(actionString: string): string | null {
    // Try to extract file path from action descriptions
    // This is a simple regex that looks for file paths
    const pathMatch = actionString.match(/(?:write|create|save).*?([a-zA-Z0-9_\-\/\\\.]+\.[a-zA-Z0-9]+)/i);
    return pathMatch ? pathMatch[1] : null;
  }
}
