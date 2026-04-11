# ===================================================================
# NUVAUS FILE MANAGER — Automatización de archivos + Notion Sync
# ===================================================================
# Monitorea Descargas, clasifica, renombra y sincroniza con Notion
# Versión: 1.0 | Autor: Ariel Meneses | GitHub: nuvaus-automation
# ===================================================================

param(
    [string]$ConfigPath = "$PSScriptRoot\..\config",
    [string]$DryRun = $false,
    [string]$VerboseLogging = $true
)

# ===================================================================
# 1. CARGA CONFIGURACIÓN
# ===================================================================

$PathsJson = Get-Content "$ConfigPath\paths.json" | ConvertFrom-Json
$RulesJson = Get-Content "$ConfigPath\rules.json" | ConvertFrom-Json

$Config = @{
    NuvausBase = $PathsJson.nuvaus_base
    DownloadsDir = $PathsJson.monitored_downloads
    LogFile = "$($PathsJson.logs)\file-manager.log"
    DryRun = [bool]$DryRun
    Verbose = [bool]$VerboseLogging
    Rules = $RulesJson.rules
    Clients = $RulesJson.clients
    GlobalSettings = $RulesJson.global_settings
}

# Crear carpeta logs si no existe
if (!(Test-Path $PathsJson.logs)) {
    New-Item -ItemType Directory -Path $PathsJson.logs -Force | Out-Null
}

# ===================================================================
# 2. FUNCIONES CORE
# ===================================================================

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "[$Timestamp] [$Level] $Message"

    Add-Content -Path $Config.LogFile -Value $LogMessage

    if ($Config.Verbose) {
        Write-Host $LogMessage
    }
}

function Resolve-ClientFromFilename {
    param([string]$Filename)

    foreach ($client in $Config.Clients) {
        if ($Filename -match $client.code -or $Filename -match $client.name) {
            return $client
        }
    }
    return $null
}

function Test-RuleMatch {
    param([string]$Filename, [object]$Rule)

    $ext = [System.IO.Path]::GetExtension($Filename).ToLower()
    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($Filename)

    # Verificar extensión
    if ($Rule.extensions -notcontains $ext) {
        return $false
    }

    # Verificar patrones
    foreach ($pattern in $Rule.patterns) {
        $regexPattern = $pattern -replace '\*', '.*'
        if ($baseName -match $regexPattern) {
            return $true
        }
    }

    return $false
}

function Get-RenamedFilename {
    param([string]$Filename, [string]$Pattern, [object]$Client)

    $ext = [System.IO.Path]::GetExtension($Filename)
    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($Filename)

    $newName = $Pattern
    $newName = $newName -replace '{CLIENT}', if ($Client) { $Client.code } else { 'UNKNOWN' }
    $newName = $newName -replace '{FILENAME}', $baseName
    $newName = $newName -replace '{DD-MM-YYYY}', (Get-Date -Format "dd-MM-yyyy")
    $newName = $newName -replace '{YYYY-MM-DD}', (Get-Date -Format "yyyy-MM-dd")
    $newName = $newName -replace '{YYYY}', (Get-Date -Format "yyyy")

    return $newName + $ext
}

function Move-FileWithLogging {
    param([string]$SourcePath, [string]$DestDir, [string]$NewName, [object]$Rule)

    # Crear carpeta destino si no existe
    if (!(Test-Path $DestDir)) {
        New-Item -ItemType Directory -Path $DestDir -Force | Out-Null
        Write-Log "Carpeta creada: $DestDir" "INFO"
    }

    $DestPath = Join-Path $DestDir $NewName

    # Evitar sobrescritura
    if (Test-Path $DestPath) {
        $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $baseName = [System.IO.Path]::GetFileNameWithoutExtension($NewName)
        $ext = [System.IO.Path]::GetExtension($NewName)
        $NewName = "$baseName-$timestamp$ext"
        $DestPath = Join-Path $DestDir $NewName
        Write-Log "Archivo existe. Renombrado con timestamp: $NewName" "WARN"
    }

    if (!$Config.DryRun) {
        try {
            Move-Item -Path $SourcePath -Destination $DestPath -Force
            Write-Log "Movido: $SourcePath → $DestDir\$NewName" "INFO"
            return @{ Success = $true; DestPath = $DestPath; NewName = $NewName; Rule = $Rule }
        }
        catch {
            Write-Log "Error moviendo $SourcePath: $_" "ERROR"
            return @{ Success = $false; Error = $_ }
        }
    }
    else {
        Write-Log "[DRY RUN] Movería: $SourcePath → $DestDir\$NewName" "INFO"
        return @{ Success = $true; DestPath = $DestPath; NewName = $NewName; Rule = $Rule; DryRun = $true }
    }
}

# ===================================================================
# 3. PROCESAMIENTO DE ARCHIVOS
# ===================================================================

function Process-Downloads {
    if (!(Test-Path $Config.DownloadsDir)) {
        Write-Log "Carpeta Downloads no existe: $($Config.DownloadsDir)" "ERROR"
        return
    }

    $files = Get-ChildItem -Path $Config.DownloadsDir -File -ErrorAction SilentlyContinue

    if ($files.Count -eq 0) {
        Write-Log "Sin archivos nuevos en Downloads" "INFO"
        return
    }

    Write-Log "Procesando $($files.Count) archivo(s)" "INFO"

    $moved = @()

    foreach ($file in $files) {
        Write-Log "Analizando: $($file.Name)" "DEBUG"

        # Saltar carpetas (por si acaso)
        if ($file.PSIsContainer) {
            continue
        }

        $matched = $false

        # Buscar regla que coincida
        foreach ($rule in $Config.Rules) {
            if (Test-RuleMatch -Filename $file.Name -Rule $rule) {
                Write-Log "Regla coincide: $($rule.name)" "INFO"

                $client = Resolve-ClientFromFilename -Filename $file.Name
                $newName = Get-RenamedFilename -Filename $file.Name -Pattern $rule.rename_pattern -Client $client

                # Resolver ruta destino
                $destDir = Join-Path $Config.NuvausBase $rule.destination

                $result = Move-FileWithLogging -SourcePath $file.FullName -DestDir $destDir -NewName $newName -Rule $rule

                if ($result.Success) {
                    $moved += $result

                    # Sincronizar con Notion si está configurado
                    if ($rule.notify_notion -and !$Config.DryRun) {
                        Sync-WithNotion -File $result -Client $client
                    }
                }

                $matched = $true
                break
            }
        }

        if (!$matched) {
            Write-Log "Sin regla coincidente para: $($file.Name)" "WARN"
        }
    }

    Write-Log "Procesamiento completado. $($moved.Count) archivo(s) movido(s)." "INFO"
    return $moved
}

# ===================================================================
# 4. SINCRONIZACIÓN CON NOTION
# ===================================================================

function Sync-WithNotion {
    param([object]$File, [object]$Client)

    # Este script se llama desde notion-sync.ps1 que maneja la integración
    # Por ahora, solo se registra en log
    Write-Log "Notion sync queued: $($File.NewName) | Client: $($Client.code)" "INFO"
}

# ===================================================================
# 5. LIMPIEZA Y ARCHIVADO
# ===================================================================

function Archive-OldProposals {
    $propActivas = Join-Path $Config.NuvausBase "propuestas"
    $propArchivo = Join-Path $Config.NuvausBase "propuestas-archivo"

    if (!(Test-Path $propActivas)) {
        return
    }

    $archiveDays = $Config.GlobalSettings.archive_propuestas_after_days
    $cutoffDate = (Get-Date).AddDays(-$archiveDays)

    $oldFiles = Get-ChildItem -Path $propActivas -File | Where-Object { $_.LastWriteTime -lt $cutoffDate }

    foreach ($file in $oldFiles) {
        $year = $file.LastWriteTime.Year
        $destDir = Join-Path $propArchivo $year

        if (!(Test-Path $destDir)) {
            New-Item -ItemType Directory -Path $destDir -Force | Out-Null
        }

        if (!$Config.DryRun) {
            Move-Item -Path $file.FullName -Destination $destDir -Force
            Write-Log "Archivado: $($file.Name) → propuestas-archivo/$year" "INFO"
        }
        else {
            Write-Log "[DRY RUN] Archivaría: $($file.Name)" "INFO"
        }
    }
}

# ===================================================================
# 6. EJECUCIÓN PRINCIPAL
# ===================================================================

Write-Log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" "INFO"
Write-Log "NUVAUS FILE MANAGER — Iniciando procesamiento" "INFO"
Write-Log "Modo: $(if ($Config.DryRun) { 'DRY RUN' } else { 'PRODUCCIÓN' })" "INFO"
Write-Log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" "INFO"

try {
    Process-Downloads
    Archive-OldProposals
}
catch {
    Write-Log "Error fatal: $_" "ERROR"
}

Write-Log "Procesamiento finalizado." "INFO"
