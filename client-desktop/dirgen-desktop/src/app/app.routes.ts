import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    redirectTo: '/test-connection',
    pathMatch: 'full'
  },
  {
    path: 'test-connection',
    loadComponent: () => import('./features/test-connection/test-connection.component')
      .then(m => m.TestConnectionComponent)
  },
  {
    path: '**',
    redirectTo: '/test-connection'
  }
];
