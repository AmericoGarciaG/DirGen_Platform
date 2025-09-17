# Documento de Visión y Requerimientos de Software (SVAD)
## FinBase Data Pipeline v1.0

**Versión:** 1.0  
**Fecha:** 17 de Septiembre, 2025  
**Documento:** SVAD-FINBASE-2025-001  
**Estado:** DRAFT - Para Revisión  

---

## 1. Resumen Ejecutivo

### 1.1 Visión del Producto

**FinBase** es una plataforma de **ingesta y procesamiento de datos de mercado financiero en tiempo real** diseñada para centralizar, validar y hacer disponible información crítica de mercado para análisis financiero y toma de decisiones estratégicas.

El sistema implementa una arquitectura de microservicios basada en eventos (Event-Driven Architecture) que garantiza alta disponibilidad, escalabilidad y resiliencia en el procesamiento de datos financieros desde fuentes externas como Yahoo Finance.

### 1.2 Objetivos de Negocio

**Objetivo Principal:**
Crear una infraestructura sólida y escalable que permita el acceso confiable y en tiempo real a datos de mercado financiero para soportar decisiones de negocio basadas en datos.

**Objetivos Específicos:**
- **Centralización de Datos:** Consolidar datos de mercado de múltiples fuentes en un repositorio único y confiable
- **Calidad de Datos:** Implementar mecanismos automáticos de validación y limpieza de datos para asegurar la integridad
- **Acceso en Tiempo Real:** Proporcionar APIs de alta performance para consulta de datos históricos y en tiempo real
- **Escalabilidad Futura:** Establecer las bases arquitectónicas para soportar algoritmos de trading y análisis avanzados
- **Gobernanza como Código:** Implementar políticas de calidad y seguridad automatizadas desde el desarrollo

### 1.3 Alcance del Proyecto (Versión 1.0)

**DENTRO DEL ALCANCE:**
- ✅ Ingesta automatizada de datos OHLCV (Open, High, Low, Close, Volume) desde Yahoo Finance
- ✅ Validación automática de calidad de datos con enrutamiento por flujos limpios/errores
- ✅ Persistencia optimizada en base de datos de series de tiempo (TimescaleDB)
- ✅ API REST para consulta de datos históricos
- ✅ Funcionalidad de backfilling de datos históricos
- ✅ Observabilidad completa con logs estructurados
- ✅ Despliegue local con Docker Compose

**FUERA DEL ALCANCE (Futuras Versiones):**
- ❌ Algoritmos de trading automático
- ❌ Análisis avanzado de patrones (ML/AI)
- ❌ Interfaz gráfica de usuario (Dashboard web)
- ❌ Integración con brokers de trading
- ❌ Despliegue en nube (cloud-native)
- ❌ Alertas y notificaciones en tiempo real

---

## 2. Actores y Casos de Uso

### 2.1 Actores Principales

**A1. Analista Financiero**
- **Descripción:** Profesional que requiere acceso a datos históricos y en tiempo real para realizar análisis de mercado, identificar tendencias y generar reportes de inversión.
- **Responsabilidades:** Consultar datos, solicitar backfilling de información histórica faltante, validar la calidad de los datos para sus análisis.

**A2. Administrador del Sistema**
- **Descripción:** Rol técnico responsable de la operación, monitoreo y mantenimiento de la plataforma FinBase.
- **Responsabilidades:** Monitorear la salud del sistema, gestionar backfills, resolver problemas de calidad de datos, mantener la infraestructura operativa.

**A3. Sistema Externo (Yahoo Finance)**
- **Descripción:** Proveedor externo de datos de mercado financiero que actúa como fuente primaria de información.
- **Responsabilidades:** Proveer datos OHLCV actualizados y históricos para los tickers solicitados.

**A4. Aplicación Cliente**
- **Descripción:** Sistemas downstream que consumen los datos de FinBase para análisis, reportes o algoritmos.
- **Responsabilidades:** Realizar consultas eficientes, manejar errores de API, respetar los límites de rate limiting.

### 2.2 Casos de Uso Principales

**CU-01: Consultar Datos Históricos de un Ticker**
> Un Analista Financiero necesita obtener los datos históricos de precios de Apple (AAPL) de los últimos 3 meses para realizar un análisis de volatilidad. Accede al endpoint `/api/v1/tickers/AAPL/historical` especificando el rango de fechas. El sistema retorna los datos OHLCV en formato JSON con timestamps normalizados.

**CU-02: Monitorear Calidad de Datos en Tiempo Real**
> El Administrador del Sistema recibe una alerta sobre datos anómalos. Consulta los logs estructurados para identificar que el precio de cierre de un ticker específico ha sido marcado como inválido (valor negativo). Los datos fueron automáticamente enrutados al flujo de errores para revisión manual.

**CU-03: Solicitar Backfilling de Datos Faltantes**
> Un Analista Financiero identifica que faltan datos históricos para un nuevo ticker que debe incluirse en su análisis. Utiliza el endpoint protegido `/api/v1/backfill/start` con su API key para solicitar la descarga de datos históricos de los últimos 2 años. El sistema procesa la solicitud de forma asíncrona.

**CU-04: Integrar Nueva Fuente de Datos**
> Una Aplicación Cliente necesita consumir datos de FinBase para alimentar un dashboard de trading. Implementa las llamadas a la API REST siguiendo la especificación OpenAPI, maneja los códigos de error apropiadamente y implementa retry logic para resiliencia.

---

## 3. Requerimientos Funcionales (FRs)

**FR-01: Recolección de Datos de Mercado**
> El sistema debe ser capaz de recolectar datos de mercado en formato OHLCV (Open, High, Low, Close, Volume) desde Yahoo Finance para una lista predefinida de tickers financieros. La recolección debe ejecutarse de forma automática y continua.

*Criterios de Aceptación:*
- Los datos deben incluir: precio de apertura, máximo, mínimo, cierre y volumen
- El sistema debe soportar al menos 50 tickers simultáneos en la versión inicial
- La recolección debe ejecutarse cada 5 minutos durante horas de mercado
- Los errores de conectividad deben ser manejados con reintentos automáticos

**FR-02: Validación de Integridad de Datos**
> El sistema debe validar automáticamente que todos los campos numéricos (precios y volumen) sean valores positivos y que los timestamps sean válidos antes de procesar los datos.

*Criterios de Aceptación:*
- Un mensaje con precio negativo debe ser marcado como inválido
- Timestamps fuera del rango esperado (futuro > 1 día, pasado > 10 años) deben ser rechazados
- Volumen igual a cero debe generar una advertencia pero no rechazar el registro
- Los datos inválidos deben incluir metadatos explicando la causa del rechazo

**FR-03: Enrutamiento por Calidad de Datos**
> El sistema debe enrutar automáticamente los datos validados hacia un flujo de procesamiento 'limpio' y los datos inválidos hacia un flujo de 'errores' para revisión posterior.

*Criterios de Aceptación:*
- Los datos válidos deben continuar al proceso de persistencia sin intervención manual
- Los datos inválidos deben ser almacenados en una cola separada con retención de 30 días
- Debe existir un endpoint para consultar estadísticas de calidad (% datos válidos/inválidos)
- Los errores recurrentes del mismo ticker deben generar alertas automáticas

**FR-04: Persistencia Optimizada para Series de Tiempo**
> El sistema debe persistir los datos limpios en una base de datos optimizada para consultas de series de tiempo (PostgreSQL con extensión TimescaleDB).

*Criterios de Aceptación:*
- Los datos deben organizarse en hipertablas particionadas por fecha
- Las consultas por rango de fechas deben ejecutarse en menos de 100ms para rangos de 1 año
- El sistema debe soportar retención automática de datos (mantener 5 años de histórico)
- Debe implementar compresión automática para datos antiguos (> 1 año)

**FR-05: API REST para Consulta de Datos**
> El sistema debe exponer una API REST que permita consultar datos históricos por ticker, con filtros por rango de fechas y agregaciones temporales.

*Criterios de Aceptación:*
- Endpoint GET `/api/v1/tickers/{symbol}/historical?from={date}&to={date}`
- Soporte para agregaciones: daily, weekly, monthly
- Respuestas en formato JSON con paginación para resultados grandes (> 1000 registros)
- Documentación OpenAPI 3.0 autogenerada y actualizada

**FR-06: Funcionalidad de Backfilling Segura**
> El sistema debe exponer una API protegida con autenticación que permita iniciar tareas de backfilling para obtener datos históricos de tickers específicos.

*Criterios de Aceptación:*
- Endpoint POST `/api/v1/backfill/start` protegido con API Key
- Soporte para especificar ticker, fecha inicio y fecha fin
- Procesamiento asíncrono con endpoint de consulta de estado
- Límite de 1 backfill concurrente por ticker para evitar sobrecargas

---

## 4. Requerimientos No Funcionales (NFRs)

### 4.1 Rendimiento

**NFR-01: Latencia de API y Capacidad de Ingesta**
> El sistema debe mantener una latencia P99 por debajo de 200ms en el endpoint de consulta bajo una carga simulada de 100 usuarios concurrentes. La capacidad de ingesta debe soportar al menos 100 mensajes por segundo.

*Métricas Específicas:*
- P50 ≤ 50ms, P95 ≤ 150ms, P99 ≤ 200ms para consultas de datos históricos
- Throughput de ingesta: ≥ 100 mensajes/segundo sostenidos
- CPU utilization ≤ 70% bajo carga normal
- Memory usage ≤ 2GB por microservicio en condiciones normales

### 4.2 Escalabilidad

**NFR-02: Escalabilidad Horizontal**
> Todos los componentes del sistema deben ser diseñados para escalabilidad horizontal, permitiendo agregar instancias adicionales para manejar incrementos en la carga.

*Especificaciones Técnicas:*
- Microservicios stateless que puedan replicarse independientemente
- Base de datos con soporte para read replicas
- Broker de mensajes con capacidad de clustering
- Load balancing automático entre instancias

### 4.3 Resiliencia

**NFR-03: Tolerancia a Fallos y Recuperación**
> El sistema debe implementar desacoplamiento mediante broker de mensajes y mecanismos de reintentos con exponential backoff para garantizar la entrega eventual de datos.

*Características de Resiliencia:*
- Circuit breakers en llamadas a servicios externos (Yahoo Finance)
- Dead letter queues para mensajes que fallen después de 5 reintentos
- Reintentos con exponential backoff: 1s, 2s, 4s, 8s, 16s
- Health checks automáticos cada 30 segundos

### 4.4 Seguridad

**NFR-04: Seguridad de APIs y Gestión de Secretos**
> La API de backfilling debe estar protegida con autenticación por API Key. Todas las credenciales y secretos deben ser gestionados mediante variables de entorno, sin hardcoding en el código fuente.

*Implementación de Seguridad:*
- API Keys con rotación automática cada 90 días
- Rate limiting: 100 requests/minute por API key
- Logs de auditoría para todas las operaciones privilegiadas
- Secretos gestionados exclusivamente via variables de entorno

### 4.5 Calidad de Código

**NFR-05: Estándares de Calidad y Testing**
> El código fuente debe mantener una cobertura de pruebas superior al 80% y debe ser formateado automáticamente usando Black e isort para Python.

*Métricas de Calidad:*
- Unit test coverage ≥ 80%
- Integration test coverage ≥ 60%
- Code complexity (Cyclomatic) ≤ 10 por función
- Formateo automático: Black + isort + flake8

### 4.6 Observabilidad

**NFR-06: Monitoreo y Logging Estructurado**
> El sistema debe implementar logging estructurado en formato JSON para facilitar el análisis y troubleshooting. Debe incluir métricas de negocio y técnicas.

*Especificaciones de Observabilidad:*
- Logs estructurados en JSON con fields estándar: timestamp, level, service, message, trace_id
- Métricas de negocio: tickers procesados/minuto, % datos válidos/inválidos
- Métricas técnicas: latencia, throughput, error rate, resource utilization
- Dashboard de Grafana pre-configurado con alertas automáticas

---

## 5. Políticas de Gobernanza y Cumplimiento

### 5.1 Calidad de Código (qual-test-coverage-80)

**Política:** Todo código fuente debe mantener una cobertura de pruebas mínima del 80%.

**Justificación:** En sistemas financieros, la calidad y confiabilidad del software es crítica. Una alta cobertura de pruebas reduce significativamente el riesgo de bugs en producción que puedan impactar decisiones financieras basadas en datos incorrectos.

**Implementación:**
- Gate automático en CI/CD que bloquea deploys con coverage < 80%
- Reportes de cobertura generados automáticamente en cada build
- Revisión obligatoria de código para funciones sin pruebas

### 5.2 Estándares de Formato (std-python-black-isort)

**Política:** Todo código Python debe ser formateado automáticamente usando Black e isort.

**Justificación:** La consistencia en el formato de código mejora la legibilidad, reduce el tiempo de code review y minimiza conflictos de merge en equipos distribuidos. Los estándares automatizados eliminan debates subjetivos sobre estilo.

**Implementación:**
- Pre-commit hooks que ejecutan Black + isort + flake8
- CI/CD gates que validan formato antes del merge
- Configuración centralizada en pyproject.toml

### 5.3 Seguridad de Credenciales (sec-no-hardcoded-secrets)

**Política:** Prohibición absoluta de hardcodear secretos, API keys o credenciales en el código fuente.

**Justificación:** Los secretos hardcodeados representan un riesgo crítico de seguridad, especialmente en repositorios que pueden ser accedidos por múltiples desarrolladores o sistemas automatizados. La exposición accidental en control de versiones puede comprometer toda la infraestructura.

**Implementación:**
- Scanners automáticos (truffleHog, git-secrets) en CI/CD
- Gestión de secretos exclusivamente via variables de entorno o secret managers
- Auditorías regulares del código base

### 5.4 Vulnerabilidades Críticas (sec-no-known-critical-cves)

**Política:** El sistema no debe incluir dependencias con vulnerabilidades críticas conocidas (CVE Score ≥ 7.0).

**Justificación:** Las vulnerabilidades de alta severidad pueden ser explotadas por atacantes para comprometer la integridad de los datos financieros o la disponibilidad del sistema. La remediación proactiva es menos costosa que la respuesta reactiva a incidentes.

**Implementación:**
- Scanners automáticos de dependencias (Safety, Snyk) en CI/CD
- Actualizaciones automáticas de dependencias con vulnerabilidades críticas
- Proceso de excepción documentado para casos donde la actualización no es inmediatamente posible

---

## 6. Visión de la Arquitectura de la Solución

### 6.1 Patrón Arquitectónico

**FinBase** implementa una **Arquitectura de Microservicios basada en Eventos (Event-Driven Architecture - EDA)** que proporciona:

- **Desacoplamiento:** Los servicios se comunican de forma asíncrona a través de eventos, reduciendo dependencias directas
- **Escalabilidad:** Cada microservicio puede escalarse independientemente según su carga específica  
- **Resiliencia:** Los fallos en un servicio no propagan automáticamente a otros componentes
- **Extensibilidad:** Nuevos servicios pueden subscribirse a eventos existentes sin modificar productores

### 6.2 Componentes del Sistema

**collector-yfinance**
> **Responsabilidad:** Recolección periódica de datos OHLCV desde Yahoo Finance
> **Funcionalidades:** Polling de APIs externas, manejo de rate limits, publicación de eventos de datos crudos
> **Tecnologías:** FastAPI, Pika (RabbitMQ), yfinance library

**quality-service**
> **Responsabilidad:** Validación y limpieza de datos financieros
> **Funcionalidades:** Validación de rangos numéricos, detección de anomalías, enrutamiento por calidad
> **Tecnologías:** FastAPI, Pydantic para validación, Pika para messaging

**storage-service**
> **Responsabilidad:** Persistencia optimizada de datos limpios
> **Funcionalidades:** Escritura a TimescaleDB, compresión automática, particionamiento temporal
> **Tecnologías:** SQLModel, PostgreSQL con TimescaleDB, conexión pooling

**api-service**
> **Responsabilidad:** Exposición de APIs REST para consulta de datos
> **Funcionalidades:** Consultas históricas, agregaciones temporales, paginación, autenticación
> **Tecnologías:** FastAPI, SQLModel para ORM, OpenAPI documentation

**backfill-worker-service**
> **Responsabilidad:** Procesamiento asíncrono de tareas de backfilling
> **Funcionalidades:** Descarga masiva de datos históricos, procesamiento por lotes, gestión de estado
> **Tecnologias:** Celery para task queue, SQLModel para persistencia

### 6.3 Flujo de Datos del Sistema

```
[Yahoo Finance] 
       ↓ (REST API calls)
[collector-yfinance] 
       ↓ (publishes: raw_data_event)
[RabbitMQ: raw_data_queue]
       ↓ (subscribes)
[quality-service]
       ├─→ (publishes: clean_data_event) → [RabbitMQ: clean_data_queue]
       └─→ (publishes: error_data_event) → [RabbitMQ: error_data_queue]
                ↓ (subscribes to clean_data_queue)
       [storage-service] 
                ↓ (writes to)
       [PostgreSQL + TimescaleDB]
                ↑ (reads from)
       [api-service] ← (REST API calls) ← [Client Applications]
       
[Backfill Requests] → [api-service] → [RabbitMQ: backfill_queue] → [backfill-worker-service]
```

**Descripción del Flujo:**

1. **Ingesta:** collector-yfinance obtiene datos de Yahoo Finance y los publica como eventos crudos
2. **Validación:** quality-service procesa los datos, aplicando reglas de negocio y segregando por calidad
3. **Persistencia:** storage-service consume únicamente datos limpios y los persiste optimizadamente
4. **Consulta:** api-service proporciona acceso de lectura con APIs REST optimizadas
5. **Backfilling:** Flujo paralelo para descarga masiva de datos históricos bajo demanda

---

## 7. Stack Tecnológico Propuesto

### 7.1 Lenguaje y Runtime

**Python 3.11+**
> Elegido por su rico ecosistema para análisis financiero, excelente soporte para APIs REST (FastAPI), y bibliotecas maduras para procesamiento de datos. Python 3.11 ofrece mejoras significativas de performance sobre versiones anteriores.

### 7.2 Frameworks y Librerías

**FastAPI**
> Framework moderno para APIs REST con soporte nativo para OpenAPI, validación automática de tipos con Pydantic, y performance superior a frameworks tradicionales como Flask. Ideal para microservicios con alta carga.

**Pydantic**
> Validación de datos basada en type hints de Python. Garantiza integridad de datos entre servicios y proporciona serialización/deserialización automática con excelente performance.

**SQLModel**
> Desarrollado por el creador de FastAPI, combina SQLAlchemy con Pydantic para proporcionar un ORM type-safe que se integra perfectamente con APIs FastAPI.

**Pika**
> Cliente Python oficial para RabbitMQ. Proporciona una API simple y robusta para messaging asíncrono con soporte completo para features avanzadas como confirmaciones de entrega.

### 7.3 Infraestructura de Datos

**PostgreSQL con TimescaleDB**
> PostgreSQL ofrece robustez enterprise-grade, mientras que TimescaleDB proporciona optimizaciones específicas para series de tiempo: particionamiento automático, compresión, y consultas de agregación ultra-rápidas. Ideal para datos de mercado financiero.

**RabbitMQ**
> Message broker maduro con soporte robusto para patrones de messaging complejos, garantías de entrega, y clustering para alta disponibilidad. Excelente integración con Python ecosystem.

### 7.4 Contenedorización y Orquestación

**Docker + Docker Compose**
> Docker proporciona consistency entre entornos de desarrollo y producción. Docker Compose permite orquestación sencilla de la stack completa para desarrollo local, con networking automático entre servicios.

### 7.5 Justificación de la Selección

La selección tecnológica prioriza:
- **Performance:** FastAPI + Pydantic para APIs de alta velocidad
- **Confiabilidad:** PostgreSQL + TimescaleDB para garantizar integridad de datos financieros
- **Mantenibilidad:** Type safety con SQLModel y Pydantic reduce bugs en runtime
- **Escalabilidad:** Arquitectura desacoplada con RabbitMQ permite escalar componentes independientemente

---

## 8. Glosario de Términos

**API Key**
> Credencial de autenticación única que identifica y autoriza a una aplicación para acceder a APIs protegidas.

**Backfilling**
> Proceso de descarga y procesamiento retrospectivo de datos históricos faltantes en el sistema.

**Circuit Breaker**
> Patrón de diseño que previene llamadas a servicios externos que están fallando, mejorando la resiliencia del sistema.

**Dead Letter Queue (DLQ)**
> Cola especial donde se almacenan mensajes que han fallado múltiples veces durante su procesamiento.

**Event-Driven Architecture (EDA)**
> Patrón arquitectónico donde los componentes se comunican produciendo y consumiendo eventos de forma asíncrona.

**Exponential Backoff**
> Estrategia de reintentos donde el tiempo de espera entre intentos se incrementa exponencialmente.

**Hipertabla**
> Abstracción de TimescaleDB que presenta múltiples chunks (particiones) como una sola tabla SQL.

**OHLCV**
> Open, High, Low, Close, Volume - Los cinco puntos de datos estándar para información de precios de mercado financiero.

**P99 (Percentil 99)**
> Métrica que indica que el 99% de las requests tienen una latencia menor o igual al valor especificado.

**Rate Limiting**
> Técnica para controlar el número de requests que una aplicación puede hacer a una API en un período determinado.

**Ticker**
> Símbolo único que identifica un instrumento financiero en los mercados (ej: AAPL para Apple Inc.).

**TimescaleDB**
> Extensión de PostgreSQL optimizada para workloads de series de tiempo con particionamiento automático y compresión.

**Type Safety**
> Característica de lenguajes/frameworks que detectan errores de tipos de datos en tiempo de compilación o desarrollo.

---

## 9. Control de Cambios

| Versión | Fecha | Autor | Cambios |
|---------|--------|--------|---------|
| 1.0 | 2025-09-17 | Sistema DirGen | Creación inicial del documento SVAD basado en ingeniería inversa del PCCE |

---

## 10. Aprobaciones Requeridas

- [ ] **Product Owner** - Validación de objetivos de negocio y casos de uso
- [ ] **Arquitecto de Soluciones** - Aprobación de decisiones arquitectónicas
- [ ] **Tech Lead** - Validación de stack tecnológico y NFRs
- [ ] **Security Officer** - Revisión de políticas de seguridad
- [ ] **Comité de Dirección** - Aprobación final del alcance y presupuesto

---

*Este documento representa la visión completa y los requerimientos detallados para el desarrollo de FinBase v1.0. Debe servir como referencia única para todas las decisiones de diseño e implementación durante el proyecto.*