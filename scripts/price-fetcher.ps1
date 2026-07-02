# ===================================================================
# NUVAUS PRICE FETCHER — Monitor de precios multi-tienda (anti-scraping)
# ===================================================================
# Consulta precios de productos en tiendas chilenas con una cadena
# resiliente de fuentes, evitando el bloqueo anti-bot:
#   1. API oficial de MercadoLibre  (sin scraping)
#   2. API pública de SoloTodo       (sin scraping)
#   3. Fetch directo con cabeceras de navegador
#   4. Fallback a scraping-API (ScraperAPI / ZenRows) con geo-Chile
# Guarda historial, cachea resultados y alerta bajo precio objetivo.
# Versión: 1.0 | Autor: Ariel Meneses | GitHub: nuvaus-automation
# ===================================================================

param(
    [string]$ConfigPath = "$PSScriptRoot\..\config",
    [string]$LogDir     = "$PSScriptRoot\..\logs",
    [string]$DryRun     = $false,
    [string]$VerboseLogging = $true,
    [string]$OnlyId     = ""      # Procesar un solo producto por su "id"
)

# ===================================================================
# 1. CARGA CONFIGURACIÓN
# ===================================================================

$PriceJson = Get-Content "$ConfigPath\price-watch.json" -Raw | ConvertFrom-Json

$Config = @{
    Settings   = $PriceJson.settings
    Watchlist  = $PriceJson.watchlist
    LogFile    = "$LogDir\price-fetcher.log"
    HistoryFile = "$LogDir\price-history.json"
    CacheFile  = "$LogDir\price-cache.json"
    DryRun     = ($DryRun -eq $true -or $DryRun -eq "true")
    Verbose    = ($VerboseLogging -eq $true -or $VerboseLogging -eq "true")
}

if (!(Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

# ===================================================================
# 2. FUNCIONES CORE (logging / secrets / precios)
# ===================================================================

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "[$Timestamp] [$Level] $Message"
    Add-Content -Path $Config.LogFile -Value $LogMessage
    if ($Config.Verbose) { Write-Host $LogMessage }
}

# Lee una clave desde ~/.claude/.secrets (mismo patrón que notion-sync.ps1)
function Get-Secret {
    param([string]$Key)
    $secretsPath = "$env:USERPROFILE\.claude\.secrets"
    if (Test-Path $secretsPath) {
        $content = Get-Content $secretsPath -Raw
        if ($content -match "$Key=([^\r\n]+)") {
            return $matches[1].Trim()
        }
    }
    return $null
}

# Convierte "$399.990" / "399.990 CLP" / "$1.199.990" → 399990 (entero)
function ConvertTo-Clp {
    param([string]$Raw)
    if ([string]::IsNullOrWhiteSpace($Raw)) { return $null }
    # Quitar todo excepto dígitos, puntos y comas
    $clean = ($Raw -replace '[^\d\.,]', '')
    if ([string]::IsNullOrWhiteSpace($clean)) { return $null }
    # En CLP el separador de miles es "." y no hay decimales → quitar todo lo no dígito
    $digits = ($clean -replace '[\.,]', '')
    if ($digits -match '^\d+$') { return [int64]$digits }
    return $null
}

# Extrae precios de un blob HTML/JSON (JSON-LD "price" o patrón $ chileno)
function Get-PricesFromHtml {
    param([string]$Html, [string]$SourceUrl)
    $found = @()
    if ([string]::IsNullOrWhiteSpace($Html)) { return $found }

    # a) JSON-LD / atributos: "price": "399990" | "price":399990
    $jsonMatches = [regex]::Matches($Html, '"price"\s*:\s*"?([0-9]{4,9})(?:\.[0-9]+)?"?')
    foreach ($m in $jsonMatches) {
        $val = [int64]$m.Groups[1].Value
        if ($val -ge 1000) { $found += $val }
    }

    # b) Precio visible formato chileno: $399.990
    $clpMatches = [regex]::Matches($Html, '\$\s?([0-9]{1,3}(?:\.[0-9]{3})+)')
    foreach ($m in $clpMatches) {
        $val = ConvertTo-Clp $m.Groups[1].Value
        if ($val -and $val -ge 1000) { $found += $val }
    }

    if ($found.Count -eq 0) {
        Write-Log "Sin precios detectables en HTML de: $SourceUrl" "DEBUG"
        return @()
    }
    # Devolver únicos ordenados
    return ($found | Sort-Object -Unique)
}

# ===================================================================
# 3. FUENTES DE PRECIO (cada una devuelve lista de ofertas)
#    Oferta = @{ store; price; url; title }
# ===================================================================

# --- 3.1 MercadoLibre (API oficial, sin scraping) ---
function Get-FromMercadoLibre {
    param([object]$Item)
    $offers = @()
    $site = $Config.Settings.mercadolibre_site
    $q = [uri]::EscapeDataString($Item.query)
    $uri = "https://api.mercadolibre.com/sites/$site/search?q=$q&limit=15"

    $headers = @{ "User-Agent" = $Config.Settings.user_agent }
    $token = Get-Secret "ML_ACCESS_TOKEN"
    if ($token) { $headers["Authorization"] = "Bearer $token" }

    try {
        $resp = Invoke-RestMethod -Uri $uri -Headers $headers -TimeoutSec $Config.Settings.request_timeout_sec -ErrorAction Stop
        foreach ($r in $resp.results) {
            # Filtrar por modelo cuando esté definido (evita accesorios/otros)
            if ($Item.model -and ($r.title -notmatch [regex]::Escape($Item.model))) { continue }
            if ($r.price -and [int64]$r.price -ge 1000) {
                $offers += @{
                    store = "MercadoLibre"
                    price = [int64]$r.price
                    url   = $r.permalink
                    title = $r.title
                }
            }
        }
        Write-Log "MercadoLibre: $($offers.Count) oferta(s) para '$($Item.query)'" "INFO"
    }
    catch {
        Write-Log "MercadoLibre falló para '$($Item.query)': $_" "WARN"
    }
    return $offers
}

# --- 3.2 SoloTodo (API pública, sin scraping) ---
function Get-FromSoloTodo {
    param([object]$Item)
    $offers = @()
    $base = $Config.Settings.solotodo_api_base
    $q = [uri]::EscapeDataString($Item.query)
    $uri = "$base/products/?search=$q&page_size=5"
    $headers = @{ "User-Agent" = $Config.Settings.user_agent }

    try {
        $resp = Invoke-RestMethod -Uri $uri -Headers $headers -TimeoutSec $Config.Settings.request_timeout_sec -ErrorAction Stop
        $results = if ($resp.results) { $resp.results } else { $resp }
        foreach ($p in $results) {
            # Cada producto expone su entidad más barata en distintas formas según versión de API.
            $price = $null
            if ($p.min_price) { $price = ConvertTo-Clp ([string]$p.min_price) }
            elseif ($p.price)  { $price = ConvertTo-Clp ([string]$p.price) }
            if ($price -and $price -ge 1000) {
                $offers += @{
                    store = "SoloTodo (min)"
                    price = $price
                    url   = if ($p.url) { $p.url } else { "https://www.solotodo.cl" }
                    title = $p.name
                }
            }
        }
        Write-Log "SoloTodo: $($offers.Count) oferta(s) para '$($Item.query)'" "INFO"
    }
    catch {
        Write-Log "SoloTodo falló para '$($Item.query)' (endpoint puede requerir ajuste): $_" "WARN"
    }
    return $offers
}

# --- 3.3 Fetch directo con cabeceras de navegador ---
function Get-FromDirectUrl {
    param([string]$Url)
    $offers = @()
    $headers = @{
        "User-Agent"      = $Config.Settings.user_agent
        "Accept"          = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        "Accept-Language" = "es-CL,es;q=0.9"
    }
    try {
        $resp = Invoke-WebRequest -Uri $Url -Headers $headers -TimeoutSec $Config.Settings.request_timeout_sec -UseBasicParsing -ErrorAction Stop
        $prices = Get-PricesFromHtml -Html $resp.Content -SourceUrl $Url
        foreach ($pr in $prices) {
            $offers += @{ store = "Directo ($([uri]::new($Url).Host))"; price = $pr; url = $Url; title = "" }
        }
        Write-Log "Directo OK ($Url): $($prices.Count) precio(s)" "INFO"
    }
    catch {
        Write-Log "Directo bloqueado/falló ($Url): $($_.Exception.Message)" "DEBUG"
    }
    return $offers
}

# --- 3.4 Fallback scraping-API (ScraperAPI / ZenRows) con geo-Chile ---
function Get-FromScraperApi {
    param([string]$Url)
    $offers = @()

    $provider = $Config.Settings.scraper_provider
    $scraperKey = Get-Secret "SCRAPER_API_KEY"
    $zenKey     = Get-Secret "ZENROWS_API_KEY"

    # Resolver proveedor efectivo
    $useProvider = $null
    if ($provider -eq "scraperapi" -and $scraperKey) { $useProvider = "scraperapi" }
    elseif ($provider -eq "zenrows" -and $zenKey)     { $useProvider = "zenrows" }
    elseif ($provider -eq "auto") {
        if ($scraperKey) { $useProvider = "scraperapi" }
        elseif ($zenKey) { $useProvider = "zenrows" }
    }

    if (!$useProvider) {
        Write-Log "Sin API key de scraping en .secrets (SCRAPER_API_KEY / ZENROWS_API_KEY). Se omite fallback para $Url" "WARN"
        return $offers
    }

    $encoded = [uri]::EscapeDataString($Url)
    if ($useProvider -eq "scraperapi") {
        $api = "https://api.scraperapi.com/?api_key=$scraperKey&country_code=cl&render=true&url=$encoded"
    }
    else {
        $api = "https://api.zenrows.com/v1/?apikey=$zenKey&js_render=true&proxy_country=cl&url=$encoded"
    }

    try {
        $resp = Invoke-WebRequest -Uri $api -TimeoutSec ([int]$Config.Settings.request_timeout_sec * 3) -UseBasicParsing -ErrorAction Stop
        $prices = Get-PricesFromHtml -Html $resp.Content -SourceUrl $Url
        foreach ($pr in $prices) {
            $offers += @{ store = "$([uri]::new($Url).Host) (via $useProvider)"; price = $pr; url = $Url; title = "" }
        }
        Write-Log "Scraper-API ($useProvider) OK ($Url): $($prices.Count) precio(s)" "INFO"
    }
    catch {
        Write-Log "Scraper-API ($useProvider) falló ($Url): $($_.Exception.Message)" "ERROR"
    }
    return $offers
}

# ===================================================================
# 4. CACHÉ
# ===================================================================

function Get-Cache {
    if (Test-Path $Config.CacheFile) {
        try { return (Get-Content $Config.CacheFile -Raw | ConvertFrom-Json) } catch { return $null }
    }
    return $null
}

function Test-CacheFresh {
    param([object]$Cache, [string]$Id)
    if (!$Cache -or !$Cache.$Id) { return $false }
    $ts = [datetime]$Cache.$Id.timestamp
    $ageMin = ((Get-Date) - $ts).TotalMinutes
    return ($ageMin -lt [double]$Config.Settings.cache_minutes)
}

function Save-Cache {
    param([hashtable]$CacheMap)
    if ($Config.DryRun) { return }
    $CacheMap | ConvertTo-Json -Depth 8 | Set-Content -Path $Config.CacheFile
}

# ===================================================================
# 5. HISTORIAL
# ===================================================================

function Add-History {
    param([object]$Item, [object]$Best, [array]$AllOffers)
    if ($Config.DryRun) { return }

    $history = @()
    if (Test-Path $Config.HistoryFile) {
        try { $history = @(Get-Content $Config.HistoryFile -Raw | ConvertFrom-Json) } catch { $history = @() }
    }

    $record = [ordered]@{
        timestamp    = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
        id           = $Item.id
        name         = $Item.name
        best_price   = $Best.price
        best_store   = $Best.store
        best_url     = $Best.url
        target_price = $Item.target_price
        below_target = ($Best.price -le [int64]$Item.target_price)
        offer_count  = $AllOffers.Count
    }
    $history += $record
    $history | ConvertTo-Json -Depth 8 | Set-Content -Path $Config.HistoryFile
}

# ===================================================================
# 6. NOTION (opcional — registra el mejor precio)
# ===================================================================

function Sync-PriceToNotion {
    param([object]$Item, [object]$Best)

    if (-not $Item.notify_notion) { return }
    $dbId = $Config.Settings.notion_db
    if ([string]::IsNullOrWhiteSpace($dbId)) {
        Write-Log "notify_notion=true pero settings.notion_db vacío. Se omite Notion." "WARN"
        return
    }
    $token = Get-Secret "NOTION_API_KEY"
    if (!$token) { Write-Log "NOTION_API_KEY no encontrada. Se omite Notion." "WARN"; return }
    if ($Config.DryRun) { Write-Log "[DRY RUN] Registraría en Notion: $($Item.name) = $($Best.price)" "INFO"; return }

    $headers = @{
        "Authorization"  = "Bearer $token"
        "Notion-Version" = "2022-06-28"
        "Content-Type"   = "application/json"
    }
    $body = @{
        parent = @{ database_id = $dbId }
        properties = @{
            "Producto"    = @{ title = @( @{ text = @{ content = $Item.name } } ) }
            "Precio"      = @{ number = $Best.price }
            "Tienda"      = @{ rich_text = @( @{ text = @{ content = "$($Best.store)" } } ) }
            "URL"         = @{ url = "$($Best.url)" }
            "Bajo objetivo" = @{ checkbox = ($Best.price -le [int64]$Item.target_price) }
        }
    } | ConvertTo-Json -Depth 10

    try {
        Invoke-RestMethod -Uri "https://api.notion.com/v1/pages" -Method POST -Headers $headers -Body $body -ErrorAction Stop | Out-Null
        Write-Log "Notion: registrado $($Item.name) = $($Best.price)" "INFO"
    }
    catch {
        Write-Log "Notion falló: $_" "ERROR"
    }
}

# ===================================================================
# 7. PROCESAMIENTO POR PRODUCTO
# ===================================================================

function Invoke-PriceCheck {
    param([object]$Item, [object]$Cache, [hashtable]$CacheMap)

    Write-Log "─────────────────────────────────────────────" "INFO"
    Write-Log "Producto: $($Item.name) [$($Item.id)]" "INFO"

    if (Test-CacheFresh -Cache $Cache -Id $Item.id) {
        $cached = $Cache.$($Item.id)
        Write-Log "Caché fresca (<$($Config.Settings.cache_minutes) min). Mejor: `$$($cached.best_price) en $($cached.best_store)" "INFO"
        $CacheMap[$Item.id] = $cached
        return
    }

    $offers = @()

    # Fuentes sin scraping primero
    if ($Item.sources.mercadolibre) { $offers += Get-FromMercadoLibre -Item $Item }
    if ($Item.sources.solotodo)     { $offers += Get-FromSoloTodo -Item $Item }

    # URLs específicas: intento directo y, si no da precio, fallback scraping-API
    foreach ($url in $Item.sources.urls) {
        $direct = Get-FromDirectUrl -Url $url
        if ($direct.Count -gt 0) {
            $offers += $direct
        }
        else {
            $offers += Get-FromScraperApi -Url $url
        }
    }

    if ($offers.Count -eq 0) {
        Write-Log "Sin precios obtenidos para $($Item.name). Revisa fuentes / API keys." "WARN"
        return
    }

    $best = $offers | Sort-Object { $_.price } | Select-Object -First 1
    $belowTarget = $best.price -le [int64]$Item.target_price
    $flag = if ($belowTarget) { "✅ BAJO OBJETIVO" } else { "sobre objetivo" }

    Write-Log "MEJOR PRECIO: `$$('{0:N0}' -f $best.price) en $($best.store)  ($flag, objetivo `$$('{0:N0}' -f [int64]$Item.target_price))" "INFO"
    Write-Log "URL: $($best.url)" "INFO"
    Write-Log "Total ofertas comparadas: $($offers.Count)" "DEBUG"

    if ($belowTarget) {
        Write-Log "🔔 ALERTA: $($Item.name) alcanzó `$$('{0:N0}' -f $best.price) (objetivo `$$('{0:N0}' -f [int64]$Item.target_price))" "ALERT"
    }

    Add-History -Item $Item -Best $best -AllOffers $offers
    Sync-PriceToNotion -Item $Item -Best $best

    $CacheMap[$Item.id] = [ordered]@{
        timestamp  = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
        best_price = $best.price
        best_store = $best.store
        best_url   = $best.url
    }
}

# ===================================================================
# 8. EJECUCIÓN PRINCIPAL
# ===================================================================

Write-Log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" "INFO"
Write-Log "NUVAUS PRICE FETCHER — Iniciando" "INFO"
Write-Log "Modo: $(if ($Config.DryRun) { 'DRY RUN' } else { 'PRODUCCIÓN' }) | Productos: $($Config.Watchlist.Count)" "INFO"
Write-Log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" "INFO"

$cache = Get-Cache
$cacheMap = @{}

try {
    foreach ($item in $Config.Watchlist) {
        if ($OnlyId -and $item.id -ne $OnlyId) { continue }
        Invoke-PriceCheck -Item $item -Cache $cache -CacheMap $cacheMap
    }
    # Preservar entradas de caché no tocadas en esta corrida
    if ($cache) {
        foreach ($prop in $cache.PSObject.Properties) {
            if (-not $cacheMap.ContainsKey($prop.Name)) { $cacheMap[$prop.Name] = $prop.Value }
        }
    }
    Save-Cache -CacheMap $cacheMap
}
catch {
    Write-Log "Error fatal: $_" "ERROR"
}

Write-Log "Price fetcher finalizado." "INFO"
