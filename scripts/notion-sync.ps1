# ===================================================================
# NOTION SYNC — Sincronización de archivos movidos con BD Notion
# ===================================================================
# Actualiza estado de propuestas, interacciones y clientes en Notion
# Usa NOTION_API_KEY de .secrets (guardado en env)
# ===================================================================

param(
    [string]$NotionToken = $null,
    [string]$LogFile = "$PSScriptRoot\..\logs\notion-sync.log",
    [string]$VerboseLogging = $true
)

# ===================================================================
# 1. OBTENER NOTION API KEY
# ===================================================================

if ([string]::IsNullOrEmpty($NotionToken)) {
    # Intentar leer desde .secrets
    $secretsPath = "$env:USERPROFILE\.claude\.secrets"
    if (Test-Path $secretsPath) {
        $secretsContent = Get-Content $secretsPath -Raw
        if ($secretsContent -match 'NOTION_API_KEY=([^\r\n]+)') {
            $NotionToken = $matches[1]
        }
    }
}

if ([string]::IsNullOrEmpty($NotionToken)) {
    Write-Host "ERROR: NOTION_API_KEY no encontrada en parámetros ni en .secrets" -ForegroundColor Red
    exit 1
}

# ===================================================================
# 2. CONFIGURACIÓN
# ===================================================================

$NotionConfig = @{
    ApiKey = $NotionToken
    BaseUrl = "https://api.notion.com/v1"
    Version = "2022-06-28"
    DbInteracciones = "896da7d5-0b9c-4f4e-ad4b-750cef851389"
    DbProspectos = "f0e2667c-9471-4b07-b4a4-a41d6567e595"
    DbClientes = "80d8624f-2461-4208-ad92-897df3e60379"
}

# ===================================================================
# 3. FUNCIONES
# ===================================================================

function Write-SyncLog {
    param([string]$Message, [string]$Level = "INFO")
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "[$Timestamp] [$Level] $Message"
    Add-Content -Path $LogFile -Value $LogMessage
    if ($VerboseLogging -eq $true -or $VerboseLogging -eq "true") {
        Write-Host $LogMessage
    }
}

function Invoke-NotionAPI {
    param(
        [string]$Endpoint,
        [string]$Method = "GET",
        [object]$Body = $null
    )

    $Headers = @{
        "Authorization" = "Bearer $($NotionConfig.ApiKey)"
        "Notion-Version" = $NotionConfig.Version
        "Content-Type" = "application/json"
    }

    $Uri = "$($NotionConfig.BaseUrl)$Endpoint"

    try {
        $params = @{
            Uri = $Uri
            Method = $Method
            Headers = $Headers
            ErrorAction = "Stop"
        }

        if ($Body) {
            $params.Body = $Body | ConvertTo-Json -Depth 10
        }

        $response = Invoke-RestMethod @params
        return @{ Success = $true; Data = $response }
    }
    catch {
        Write-SyncLog "API Error: $_" "ERROR"
        return @{ Success = $false; Error = $_ }
    }
}

function Update-PropuestaInteraction {
    param(
        [string]$ClientCode,
        [string]$PropuestaName,
        [string]$Status = "Enviada"
    )

    $body = @{
        parent = @{ database_id = $NotionConfig.DbInteracciones }
        properties = @{
            "Tipo" = @{ select = @{ name = "Propuesta" } }
            "Cliente" = @{ rich_text = @( @{ text = @{ content = $ClientCode } } ) }
            "Resultado" = @{ rich_text = @( @{ text = @{ content = $Status } } ) }
            "Proximo paso" = @{ rich_text = @( @{ text = @{ content = "Seguimiento en 7 días" } } ) }
        }
    }

    $response = Invoke-NotionAPI -Endpoint "/pages" -Method "POST" -Body $body
    if ($response.Success) {
        Write-SyncLog "Interacción creada: $PropuestaName | Cliente: $ClientCode" "INFO"
        return $true
    }
    else {
        Write-SyncLog "Fallo crear interacción: $($response.Error)" "ERROR"
        return $false
    }
}

function Query-NotionDatabase {
    param(
        [string]$DatabaseId,
        [object]$Filter = $null
    )

    $body = @{
        filter = $Filter
    }

    $response = Invoke-NotionAPI -Endpoint "/databases/$DatabaseId/query" -Method "POST" -Body $body
    return $response
}

# ===================================================================
# 4. SINCRONIZACIÓN PRINCIPAL
# ===================================================================

Write-SyncLog "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" "INFO"
Write-SyncLog "NOTION SYNC — Iniciando" "INFO"
Write-SyncLog "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" "INFO"

# Verificar conectividad
Write-SyncLog "Verificando conexión a Notion API..." "INFO"
$testResponse = Invoke-NotionAPI -Endpoint "/databases/$($NotionConfig.DbInteracciones)" -Method "GET"

if ($testResponse.Success) {
    Write-SyncLog "Conexión OK a Notion" "INFO"
}
else {
    Write-SyncLog "No se pudo conectar a Notion API" "ERROR"
    exit 1
}

# ===================================================================
# 5. WRAPPER PARA file-manager.ps1
# ===================================================================

# Este script puede ser llamado directamente desde file-manager.ps1
# Ejemplo: Sync-WithNotion -File $result -Client $client
# Aquí creamos la función para reutilizar

function Sync-MovedFile {
    param([object]$MovedFile, [object]$Client)

    if ($MovedFile.Rule.notify_notion) {
        $status = switch ($MovedFile.Rule.id) {
            "propuestas" { "Propuesta Enviada" }
            "contratos" { "Contrato Recibido" }
            default { "Archivo Movido" }
        }

        Update-PropuestaInteraction -ClientCode $Client.code -PropuestaName $MovedFile.NewName -Status $status
    }
}

Write-SyncLog "Sincronización completada" "INFO"
