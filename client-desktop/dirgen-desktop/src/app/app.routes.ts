import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    redirectTo: '/monitoring-web-advanced',
    pathMatch: 'full'
  },
  
  // Legacy routes for backward compatibility
  {
    path: 'monitoring-web-advanced',
    loadComponent: () => import('./features/monitoring/monitoring-web-advanced.component')
      .then(m => m.MonitoringWebAdvancedComponent),
    data: { title: 'DirGen Monitor Web - Interfaz Avanzada' }
  },
  
  {
    path: 'monitoring-desktop', 
    loadComponent: () => import('./features/monitoring/monitoring-no-statusbar.component')
      .then(m => m.MonitoringNoStatusbarComponent),
    data: { title: 'DirGen Monitor Desktop' }
  },
  
  {
    path: 'monitoring',
    loadComponent: () => import('./features/monitoring/monitoring.component')
      .then(m => m.MonitoringComponent),
    data: { title: 'DirGen Monitor - Interfaz Básica' }
  },
  
  {
    path: 'monitoring-ultra-simple',
    loadComponent: () => import('./features/monitoring/monitoring-ultra-simple.component')
      .then(m => m.MonitoringUltraSimpleComponent),
    data: { title: 'DirGen Monitor - Modo Simple' }
  },
  
  // Rutas de acceso directo (para testing y desarrollo)
  {
    path: 'force-web',
    redirectTo: '/monitoring-web-advanced'
  },
  {
    path: 'force-desktop', 
    redirectTo: '/monitoring-desktop'
  },
  {
    path: 'force-simple',
    redirectTo: '/monitoring-ultra-simple'
  },
  
  // Ruta de fallback
  {
    path: '**',
    redirectTo: ''
  }
];
