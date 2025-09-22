# Corrección del Problema: "Ruta inválida o insegura"

**Fecha:** 22 de septiembre, 2024  
**Problema:** Error "Ruta inválida o insegura" durante ejecución del RequirementsAgent  
**Causa Raíz:** Conflicto entre refactorización de sandboxing y rutas temporales absolutas  

---

## 🔍 **Análisis del Problema**

### Error Observado:
```
2025-09-21 20:45:36,951 - AGENT(Requirements) - Error guardando PCCE: Ruta inválida o insegura
```

### Causa Raíz Identificada:
1. **RequirementsAgent** intentaba usar ruta temporal absoluta de Windows: `C:\Users\eagg2\AppData\Local\Temp\run-xxx_pcce.yml`
2. **Nueva validación de sandboxing** rechaza correctamente rutas absolutas por seguridad
3. **Conflicto:** Lógica antigua vs. validación nueva generaba fallo

---

## 🔧 **Correcciones Realizadas**

### 1. **RequirementsAgent (`agents/requirements/requirements_agent.py`)**

**ANTES (Problemático):**
```python
# Guardar PCCE en archivo temporal
temp_dir = tempfile.gettempdir()  # C:\Users\eagg2\AppData\Local\Temp\
pcce_path = os.path.join(temp_dir, f"{run_id}_pcce.yml")

tool_result = use_tool("writeFile", {
    "path": pcce_path,  # ❌ Ruta absoluta rechazada por sandboxing
    "content": cleaned_yaml
})
```

**DESPUÉS (Corregido):**
```python
# Guardar PCCE en archivo temporal (CORREGIDO: usar ruta relativa del proyecto)
pcce_relative_path = f"temp/{run_id}_pcce.yml"

tool_result = use_tool("writeFile", {
    "path": pcce_relative_path,  # ✅ Ruta relativa dentro del proyecto
    "content": cleaned_yaml
})
```

### 2. **Orquestador - Función `approve_plan` (`mcp_host/main.py`)**

**ANTES:**
```python
# Leer el PCCE
temp_dir = tempfile.gettempdir()
temp_pcce_path = os.path.join(temp_dir, f"{run_id}_pcce.yml")

if not os.path.exists(temp_pcce_path):
    # Error: archivo no encontrado
```

**DESPUÉS:**
```python
# Leer el PCCE (CORREGIDO: usar ruta relativa del proyecto)
pcce_relative_path = f"temp/{run_id}_pcce.yml"
pcce_full_path = PROJECT_ROOT / pcce_relative_path

if not pcce_full_path.exists():
    # Busca en la ubicación correcta
```

### 3. **Función `run_phase_1_design`**

**ANTES:**
```python
temp_dir = tempfile.gettempdir()
temp_pcce_path = os.path.join(temp_dir, f"{run_id}_pcce.yml")
with open(temp_pcce_path, "wb") as f: f.write(pcce_content)

agent_command = [..., "--pcce-path", temp_pcce_path]
```

**DESPUÉS:**
```python
# CORREGIDO: usar ubicación relativa del proyecto para el PCCE
pcce_relative_path = f"temp/{run_id}_pcce.yml"
pcce_full_path = PROJECT_ROOT / pcce_relative_path

# El archivo PCCE ya debería existir desde RequirementsAgent
if not pcce_full_path.exists():
    pcce_full_path.parent.mkdir(parents=True, exist_ok=True)
    with open(pcce_full_path, "wb") as f: f.write(pcce_content)

agent_command = [..., "--pcce-path", str(pcce_full_path)]
```

### 4. **Función `run_quality_gate_1`** - Corrección idéntica
### 5. **Función `handle_validation_failure`** - Corrección idéntica

---

## 🏗️ **Arquitectura de Archivos Corregida**

### Antes (Problemática):
```
Sistema de Archivos:
├── K:\00 SW Projects\05 DirGen Platform\DirGen\     (Proyecto)
└── C:\Users\eagg2\AppData\Local\Temp\               (Temporal del sistema)
    └── run-xxx_pcce.yml                             ❌ Fuera del sandbox
```

### Después (Segura):
```
Proyecto:
K:\00 SW Projects\05 DirGen Platform\DirGen\
├── mcp_host/
├── agents/
├── client-desktop/
└── temp/                                            ✅ Dentro del sandbox
    └── run-xxx_pcce.yml                             ✅ Ruta relativa válida
```

---

## 🛡️ **Validación de Seguridad Mantenida**

### Sandboxing Reforzado:
```python
# Validación de seguridad según Capítulo 2.1: Principio de Sandboxing
if not path_str or ".." in path_str or os.path.isabs(path_str):
    return {"success": False, "error": "Ruta inválida o insegura"}

# Verificar que la ruta final esté dentro del PROJECT_ROOT
if not str(full_path.resolve()).startswith(str(PROJECT_ROOT.resolve())):
    return {"success": False, "error": "Ruta fuera del sandbox del proyecto"}
```

### Rutas Ahora Válidas:
- ✅ `temp/run-xxx_pcce.yml` (relativa)
- ✅ `design/architecture.puml` (relativa)
- ✅ `design/api/component.yml` (relativa)

### Rutas Rechazadas (Seguridad):
- ❌ `C:\Users\...` (absoluta)
- ❌ `../../../etc/passwd` (path traversal)
- ❌ `\\server\share\file` (UNC)

---

## ✅ **Resultado Final**

### Problema Resuelto:
- **RequirementsAgent** ahora genera PCCE en `temp/{run_id}_pcce.yml`
- **Orquestador** busca PCCE en la ubicación correcta
- **Todas las fases** usan la misma ubicación consistente
- **Sandboxing** mantiene la seguridad sin romper funcionalidad

### Flujo de Archivos Corregido:
1. **RequirementsAgent** → Crear `temp/run-xxx_pcce.yml` ✅
2. **Orquestador** → Leer `temp/run-xxx_pcce.yml` ✅
3. **PlannerAgent** → Recibir ruta a `temp/run-xxx_pcce.yml` ✅
4. **ValidatorAgent** → Acceder a `temp/run-xxx_pcce.yml` ✅

### Conformidad Logic Book:
- ✅ **Capítulo 2.1:** Principio de Sandboxing implementado correctamente
- ✅ **Capítulo 2.2:** Toolbelt con validación de seguridad robusta
- ✅ **Capítulo 3.2:** Protocolo de comunicación mantenido intacto

---

## 🎯 **Beneficios de la Corrección**

1. **Seguridad Mantenida:** La validación de sandboxing sigue protegiendo contra ataques
2. **Funcionalidad Restaurada:** El flujo completo RequirementsAgent → PlannerAgent funciona
3. **Consistencia:** Todas las fases usan la misma ubicación para archivos temporales
4. **Trazabilidad:** Archivos temporales organizados en directorio dedicado
5. **Mantenibilidad:** Ubicación centralizada facilita debugging y limpieza

---
*Corrección realizada por Warp AI - Ingeniería de Backend Senior*