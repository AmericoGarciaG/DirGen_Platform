import { Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { Store } from '@ngrx/store';
import { map, filter, withLatestFrom } from 'rxjs/operators';

// Services
import { ApiService } from '../core/services/api.service';

// Store
import { AppState } from './models';
import * as WorkspaceActions from './workspace/workspace.actions';
import * as PlanActions from './plan/plan.actions';

@Injectable()
export class AppEffects {
  
  constructor(
    private actions$: Actions,
    private store: Store<AppState>,
    private apiService: ApiService
  ) {}
  
  // Listen to WebSocket messages and dispatch appropriate actions
  webSocketMessages$ = createEffect(() =>
    this.apiService.messages$.pipe(
      map(message => {
        console.log('📨 Processing WebSocket message in Effects:', message);
        
        // Handle different message types
        switch (message.type) {
          // Plan-related messages
          case 'plan_generated':
            return PlanActions.planGeneratedFromAgent({
              runId: message.run_id || '',
              tasks: (message as any).data?.tasks || [],
              planData: (message as any).data
            });
          
          case 'plan_approved':
            return PlanActions.planApprovedFromUser({
              runId: message.run_id || '',
              userResponse: (message as any).data?.user_response || ''
            });
          
          case 'executive_summary':
            // Could trigger a notification or update plan details
            return PlanActions.updateTaskProgress({
              taskId: 'summary_task',
              updates: {
                justification: (message as any).data?.summary
              }
            });
          
          // File operation messages (deliverables)
          case 'file_operation':
            if ((message as any).operation === 'create') {
              return WorkspaceActions.deliverableCreatedFromAgent({
                filePath: (message as any).file_path || '',
                agentName: message.source || 'Unknown',
                description: `Archivo creado: ${(message as any).file_path}`
              });
            }
            break;
          
          // Task progress messages
          case 'action':
            // If action is related to file creation, add as deliverable
            if ((message as any).action?.includes('writeFile') || 
                (message as any).action?.includes('createFile')) {
              const filePath = this.extractFilePathFromAction((message as any).action);
              if (filePath) {
                return WorkspaceActions.deliverableCreatedFromAgent({
                  filePath,
                  agentName: message.source || 'Agent',
                  description: `Archivo generado por ${message.source}`
                });
              }
            }
            break;
          
          // Phase messages that might indicate task completion
          case 'phase_end':
            const phaseData = (message as any).data;
            if (phaseData?.status === 'APROBADO') {
              // Could mark related tasks as completed
              console.log('Phase completed:', phaseData.name);
            }
            break;
            
          default:
            // For other message types, we might not need specific actions
            console.log('Unhandled message type in effects:', message.type);
            break;
        }
        
        // Return a no-op action for unhandled messages
        return { type: '[WebSocket] Unhandled Message', payload: message };
      }),
      filter(action => action.type !== '[WebSocket] Unhandled Message')
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
  
  // Helper method to extract file path from action strings
  private extractFilePathFromAction(actionString: string): string | null {
    // Try to extract file path from action descriptions
    // This is a simple regex that looks for file paths
    const pathMatch = actionString.match(/(?:write|create|save).*?([a-zA-Z0-9_\-\/\\\.]+\.[a-zA-Z0-9]+)/i);
    return pathMatch ? pathMatch[1] : null;
  }
}