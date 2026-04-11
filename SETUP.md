# SETUP — Instalación y Configuración

Guía completa para instalar Nuvaus File Manager + Task Scheduler.

## Paso 1: Clonar Repositorio

```bash
cd C:\Users\ariel\Desktop\Nuvaus
git clone https://github.com/ariel-meneses/nuvaus-automation.git .automation
cd .automation
```

O si ya está clonado, actualizar:
```bash
cd C:\Users\ariel\Desktop\Nuvaus\.automation
git pull origin main
```

## Paso 2: Crear Carpetas Faltantes

El script crea algunas automáticamente, pero es mejor pre-crearlas:

```powershell
# Abre PowerShell como Administrador y ejecuta:

$BasePath = "C:\Users\ariel\Desktop\Nuvaus"

@(
    "$BasePath\descargas-ordenadas",
    "$BasePath\descargas-ordenadas\diseños",
    "$BasePath\descargas-ordenadas\artículos",
    "$BasePath\propuestas-archivo",
    "$BasePath\documentos",
    "$BasePath\documentos\invoices",
    "$BasePath\documentos\contratos",
    "$BasePath\temp",
    "$BasePath\temp\reportes",
    "$BasePath\.automation\logs"
) | ForEach-Object {
    if (!(Test-Path $_)) {
        New-Item -ItemType Directory -Path $_ -Force | Out-Null
        Write-Host "✓ Creada: $_"
    }
}
```

## Paso 3: Verificar NOTION_API_KEY

El script lee automáticamente de `~/.claude/.secrets`. Verificar que existe:

```powershell
$secretsPath = "$env:USERPROFILE\.claude\.secrets"
$content = Get-Content $secretsPath -Raw
if ($content -match 'NOTION_API_KEY=([^\r\n]+)') {
    Write-Host "✓ NOTION_API_KEY encontrada"
} else {
    Write-Host "✗ NOTION_API_KEY NO encontrada"
    Write-Host "  Abre: $secretsPath"
    Write-Host "  Agrega línea: NOTION_API_KEY=ntn_..."
}
```

## Paso 4: Test en DRY RUN

Antes de automatizar, probar sin ejecutar cambios reales:

```powershell
# Abre PowerShell (NO necesita admin para este test)
cd "C:\Users\ariel\Desktop\Nuvaus\.automation"

# Ejecutar en modo DRY RUN
& .\scripts\file-manager.ps1 -DryRun $true -VerboseLogging $true
```

**Qué debería pasar:**
- Ver análisis de archivos en Downloads
- Ver qué haría sin mover nada
- Ver logs en `logs/file-manager.log`

**Ejemplo de output:**
```
[2026-04-10 14:32:15] [INFO] NUVAUS FILE MANAGER — Iniciando procesamiento
[2026-04-10 14:32:15] [INFO] Modo: DRY RUN
[2026-04-10 14:32:15] [INFO] Procesando 3 archivo(s)
[2026-04-10 14:32:15] [INFO] Analizando: propuesta-cliente.pdf
[2026-04-10 14:32:15] [INFO] Regla coincide: Propuestas Nuvaus (PDF)
[2026-04-10 14:32:15] [INFO] [DRY RUN] Movería: C:\Users\ariel\Downloads\propuesta-cliente.pdf → C:\Users\ariel\Desktop\Nuvaus\propuestas\NV-PROP-CLIENT-10-04-2026.pdf
```

Si dice "Sin archivos nuevos en Downloads" — normal, el test funciona igual.

## Paso 5: Ejecutar por Primera Vez (PRODUCCIÓN)

Una vez validado en DRY RUN, ejecutar de verdad:

```powershell
cd "C:\Users\ariel\Desktop\Nuvaus\.automation"

# Ejecutar producción
& .\scripts\file-manager.ps1
```

Ver logs:
```powershell
Get-Content "logs/file-manager.log" -Tail 20
```

## Paso 6: Programar Task Scheduler

Ejecutar automáticamente cada 15 minutos.

### Opción A: PowerShell Script (RECOMENDADO)

```powershell
# Abre PowerShell COMO ADMINISTRADOR y copia todo esto:

$TaskName = "Nuvaus File Manager"
$TaskPath = "\Nuvaus\"
$ScriptPath = "C:\Users\ariel\Desktop\Nuvaus\.automation\scripts\file-manager.ps1"
$WorkingDir = "C:\Users\ariel\Desktop\Nuvaus\.automation"

# Eliminar tarea antigua si existe
Unregister-ScheduledTask -TaskName $TaskName -TaskPath $TaskPath -Confirm:$false -ErrorAction SilentlyContinue

# Crear disparador cada 15 minutos
$Trigger = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 15) -At (Get-Date) -RepeatIndefinitely

# Crear acción
$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$ScriptPath`"" `
    -WorkingDirectory $WorkingDir

# Crear configuración
$Settings = New-ScheduledTaskSettingsSet `
    -MultipleInstancePolicy IgnoreNew `
    -RunOnlyIfNetworkAvailable `
    -StartWhenAvailable

# Registrar tarea
Register-ScheduledTask `
    -TaskName $TaskName `
    -TaskPath $TaskPath `
    -Trigger $Trigger `
    -Action $Action `
    -Settings $Settings `
    -User $env:USERNAME `
    -RunLevel Highest `
    -Force

Write-Host "✓ Tarea programada: $TaskName"
Write-Host "  Frecuencia: Cada 15 minutos"
Write-Host "  Usuario: $env:USERNAME"
Write-Host "  Próxima ejecución: En 15 minutos"
```

### Opción B: Manualmente en Task Scheduler UI

1. Abrir **Task Scheduler** (buscar en Windows)
2. Crear carpeta → Nueva carpeta: `Nuvaus`
3. Click derecho en carpeta → **Crear tarea**
4. **General**:
   - Nombre: `Nuvaus File Manager`
   - Usuario: Tu usuario Windows
   - ☑ Ejecutar con privilegios máximos
5. **Disparadores**:
   - Click **Nuevo**
   - Tipo: `Diariamente`
   - Tiempo: Ahora
   - Repetición: `15 minutos` durante `1 día`
6. **Acciones**:
   - Programa: `powershell.exe`
   - Argumentos: `-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "C:\Users\ariel\Desktop\Nuvaus\.automation\scripts\file-manager.ps1"`
   - Directorio inicio: `C:\Users\ariel\Desktop\Nuvaus\.automation`
7. **Condiciones**:
   - ☑ Iniciar solo si hay conexión de red disponible
8. **Configuración**:
   - ☑ Permitir que la tarea se ejecute bajo demanda
   - Si ya se está ejecutando: `No iniciar nueva instancia`
9. Click **Aceptar**

## Paso 7: Validar Setup

```powershell
# Verificar que tarea existe
Get-ScheduledTask -TaskName "Nuvaus File Manager" -TaskPath "\Nuvaus\*"

# Ver historial de ejecutiones
Get-ScheduledTaskInfo -TaskName "Nuvaus File Manager" -TaskPath "\Nuvaus\"
```

Output debería ser:
```
TaskName                      TaskPath              State
--------                      --------              -----
Nuvaus File Manager           \Nuvaus\              Ready
```

## Paso 8: Agregar Descarga de Prueba

Descarga un PDF a tu carpeta Downloads con un nombre que coincida con una regla:

```bash
# Crea un archivo de prueba
"test content" > "$env:USERPROFILE\Downloads\NV-PROP-TEST-2026.pdf"
```

Luego ejecuta manualmente:
```powershell
cd "C:\Users\ariel\Desktop\Nuvaus\.automation"
& .\scripts\file-manager.ps1
```

Ver que se movió a `propuestas/`:
```powershell
Get-ChildItem "C:\Users\ariel\Desktop\Nuvaus\propuestas"
```

## Troubleshooting

### Error: "ExecutionPolicy is set to Restricted"
```powershell
# Ejecutar como Admin:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Error: "NOTION_API_KEY no encontrada"
1. Abrir: `C:\Users\ariel\.claude\.secrets`
2. Agregar línea: `NOTION_API_KEY=ntn_...`
3. Guardar
4. Reintentar

### Task Scheduler no ejecuta el script
1. Abrir Task Scheduler
2. Buscar tarea: `\Nuvaus\Nuvaus File Manager`
3. Click derecho → **Ejecutar**
4. Revisar "Último resultado" → debería ser "0" (éxito)
5. Si error, revisar "Historial" → ver log del error

### Verificar que Task Scheduler corre cada 15 min
```powershell
# Ver logs de la tarea
Get-WinEvent -FilterHashtable @{
    LogName = "Microsoft-Windows-TaskScheduler/Operational"
    Level = 0,1,2
    ProviderName = "Microsoft-Windows-TaskScheduler"
} | Where-Object { $_.Message -match "Nuvaus" } | Select-Object -First 10 | Format-Table TimeCreated, Message
```

## Desinstalación

Si necesitas remover el setup:

```powershell
# Como Administrador:

# Eliminar tarea programada
Unregister-ScheduledTask -TaskName "Nuvaus File Manager" -TaskPath "\Nuvaus\" -Confirm:$false

# Eliminar carpeta (opcional)
Remove-Item "C:\Users\ariel\Desktop\Nuvaus\.automation" -Recurse -Force
```

## Siguiente Paso

Una vez funcione, ver `RULES.md` para:
- Agregar nuevas reglas de clasificación
- Personalizar patrones de renombrado
- Cambiar destinos de carpetas

---

**¿Problemas?** Ver README.md en sección "Troubleshooting" o contactar ariel@nuvaus.com
