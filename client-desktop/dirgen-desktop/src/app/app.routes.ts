import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () => import('./features/monitoring/monitoring-no-statusbar.component').then(m => m.MonitoringNoStatusbarComponent)
  },
  {
    path: 'monitoring',
    loadComponent: () => import('./features/monitoring/monitoring.component')
      .then(m => m.MonitoringComponent)
  },
  {
    path: 'monitoring-web',
    loadComponent: () => import('./features/monitoring/monitoring.component')
      .then(m => m.MonitoringComponent)
  },
  {
    path: 'monitoring-ultra-simple',
    loadComponent: () => import('./features/monitoring/monitoring-ultra-simple.component')
      .then(m => m.MonitoringUltraSimpleComponent)
  },
  {
    path: '**',
    redirectTo: ''
  }
];
