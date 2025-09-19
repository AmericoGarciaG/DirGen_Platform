import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

export type RuntimeEnvironment = 'web' | 'desktop' | 'unknown';

export interface EnvironmentInfo {
  type: RuntimeEnvironment;
  isWeb: boolean;
  isDesktop: boolean;
  isTauri: boolean;
  userAgent: string;
  platform: string;
  capabilities: {
    animations: boolean;
    advancedMaterial: boolean;
    nativeNotifications: boolean;
    fileSystem: boolean;
  };
}

@Injectable({
  providedIn: 'root'
})
export class EnvironmentDetectorService {
  
  private environmentInfoSubject = new BehaviorSubject<EnvironmentInfo>(this.detectEnvironment());
  
  /**
   * Observable que emite información del entorno actual
   */
  public environmentInfo$: Observable<EnvironmentInfo> = this.environmentInfoSubject.asObservable();
  
  constructor() {
    console.log('🔍 EnvironmentDetectorService iniciado');
    console.log('📱 Entorno detectado:', this.getCurrentEnvironment());
  }

  /**
   * Obtiene la información actual del entorno
   */
  getCurrentEnvironment(): EnvironmentInfo {
    return this.environmentInfoSubject.getValue();
  }

  /**
   * Verifica si está ejecutándose en entorno web (navegador)
   */
  isWeb(): boolean {
    return this.getCurrentEnvironment().isWeb;
  }

  /**
   * Verifica si está ejecutándose en entorno desktop (Tauri)
   */
  isDesktop(): boolean {
    return this.getCurrentEnvironment().isDesktop;
  }

  /**
   * Verifica si está ejecutándose en Tauri específicamente
   */
  isTauri(): boolean {
    return this.getCurrentEnvironment().isTauri;
  }

  /**
   * Obtiene las capacidades disponibles en el entorno actual
   */
  getCapabilities() {
    return this.getCurrentEnvironment().capabilities;
  }

  /**
   * Detecta automáticamente el entorno de ejecución
   */
  private detectEnvironment(): EnvironmentInfo {
    const userAgent = navigator.userAgent || '';
    const platform = navigator.platform || '';
    
    // Detectar Tauri
    const isTauri = this.detectTauri();
    
    // Detectar si es web o desktop
    const isDesktop = isTauri || this.detectElectron() || this.detectOtherDesktop();
    const isWeb = !isDesktop;
    
    // Determinar tipo de entorno
    let type: RuntimeEnvironment = 'unknown';
    if (isTauri) {
      type = 'desktop';
    } else if (isWeb) {
      type = 'web';
    }

    // Determinar capacidades según el entorno
    const capabilities = this.determineCapabilities(type, isTauri);

    const environmentInfo: EnvironmentInfo = {
      type,
      isWeb,
      isDesktop,
      isTauri,
      userAgent,
      platform,
      capabilities
    };

    console.log('🔍 Entorno detectado:', environmentInfo);
    return environmentInfo;
  }

  /**
   * Detecta si está ejecutándose en Tauri
   */
  private detectTauri(): boolean {
    try {
      // Verificar si existe el objeto Tauri en window
      return !!(window as any).__TAURI__ || 
             !!(window as any).__TAURI_METADATA__ ||
             !!(window as any).Tauri ||
             // Verificar user agent específico de Tauri
             navigator.userAgent.includes('Tauri') ||
             // Verificar por presencia de APIs específicas de Tauri
             typeof (window as any).__TAURI_INVOKE__ === 'function';
    } catch (error) {
      return false;
    }
  }

  /**
   * Detecta si está ejecutándose en Electron
   */
  private detectElectron(): boolean {
    try {
      return !!(window as any).require && 
             !!(window as any).require('electron') ||
             navigator.userAgent.includes('Electron');
    } catch (error) {
      return false;
    }
  }

  /**
   * Detecta otros entornos desktop
   */
  private detectOtherDesktop(): boolean {
    // Verificar si no tiene características típicas de navegador
    const hasWindow = typeof window !== 'undefined';
    const hasDocument = typeof document !== 'undefined';
    const hasNavigator = typeof navigator !== 'undefined';
    
    if (!hasWindow || !hasDocument || !hasNavigator) {
      return true; // Probablemente Node.js o similar
    }

    // Verificar características del navegador
    const hasWebAPIs = 'serviceWorker' in navigator && 'fetch' in window;
    const hasDeviceAPIs = 'geolocation' in navigator;
    
    // Si no tiene APIs típicas del navegador, probablemente es desktop
    return !hasWebAPIs && !hasDeviceAPIs;
  }

  /**
   * Determina las capacidades disponibles según el entorno
   */
  private determineCapabilities(type: RuntimeEnvironment, isTauri: boolean) {
    if (type === 'web') {
      return {
        animations: true,              // Web soporta todas las animaciones
        advancedMaterial: true,        // Angular Material completo
        nativeNotifications: 'Notification' in window, // API de notificaciones del navegador
        fileSystem: 'showOpenFilePicker' in window     // File System Access API
      };
    } else if (type === 'desktop' && isTauri) {
      return {
        animations: false,             // Tauri tiene problemas con animaciones complejas
        advancedMaterial: false,       // Material simplificado
        nativeNotifications: true,     // Notificaciones nativas del OS
        fileSystem: true               // Acceso completo al sistema de archivos
      };
    } else {
      return {
        animations: false,
        advancedMaterial: false,
        nativeNotifications: false,
        fileSystem: false
      };
    }
  }

  /**
   * Fuerza una re-detección del entorno (útil para testing)
   */
  forceRedetection(): void {
    const newEnvironmentInfo = this.detectEnvironment();
    this.environmentInfoSubject.next(newEnvironmentInfo);
    console.log('🔄 Entorno re-detectado:', newEnvironmentInfo);
  }

  /**
   * Simula un entorno específico (útil para desarrollo y testing)
   */
  simulateEnvironment(type: RuntimeEnvironment): void {
    console.warn('⚠️ Simulando entorno:', type);
    
    const simulatedInfo: EnvironmentInfo = {
      type,
      isWeb: type === 'web',
      isDesktop: type === 'desktop',
      isTauri: type === 'desktop',
      userAgent: type === 'desktop' ? 'Tauri/Simulated' : navigator.userAgent,
      platform: navigator.platform,
      capabilities: this.determineCapabilities(type, type === 'desktop')
    };

    this.environmentInfoSubject.next(simulatedInfo);
  }
}