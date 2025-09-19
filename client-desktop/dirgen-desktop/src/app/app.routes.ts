import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () => import('./features/monitoring/monitoring-web-advanced.component')
      .then(m => m.MonitoringWebAdvancedComponent)
  },
  {
    path: 'monitoring-web-advanced',
    loadComponent: () => import('./features/monitoring/monitoring-web-advanced.component')
      .then(m => m.MonitoringWebAdvancedComponent)
  },
  
  // Ruta para versión web avanzada (con StatusBar y Footer completos)
  {
    path: 'monitoring-web-advanced',
    loadComponent: () => import('./features/monitoring/monitoring-web-advanced.component')
      .then(m => m.MonitoringWebAdvancedComponent),
    data: { title: 'DirGen Monitor Web - Interfaz Avanzada' }
  },
  
  // Ruta para versión desktop (sin StatusBar problemático)
  {
    path: 'monitoring-desktop', 
    loadComponent: () => import('./features/monitoring/monitoring-no-statusbar.component')
      .then(m => m.MonitoringNoStatusbarComponent),
    data: { title: 'DirGen Monitor Desktop' }
  },
  
  // Ruta para versión web básica (compatible)
  {
    path: 'monitoring',
    loadComponent: () => import('./features/monitoring/monitoring.component')
      .then(m => m.MonitoringComponent),
    data: { title: 'DirGen Monitor - Interfaz Básica' }
  },
  
  // Ruta para versión ultra simple (fallback)
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
    redirectTo: '/monitoring-ultra-simple'
  }
];
