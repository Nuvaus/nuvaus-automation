# PRICE WATCH — Monitor de Precios Multi-Tienda

Módulo para consultar y comparar precios de productos en tiendas chilenas
**sin caer en los bloqueos anti-bot** (403 de Falabella, Líder, SoloTodo, etc.).

> **Plataforma:** escrito en **Python 3** (stdlib, sin dependencias). Corre nativo en
> **macOS** (Python viene incluido) y Linux. No requiere `pip install`.

## Por qué existe

Las tiendas grandes (Falabella, Líder, LG, Ripley) y comparadores como SoloTodo
usan protección anti-bot (Cloudflare / Akamai / DataDome). Un `GET` simple recibe
**403 Forbidden** porque no ejecuta JavaScript, tiene fingerprint de bot y a veces
falta IP chilena. Este módulo resuelve eso con una **cadena de fuentes en orden de
preferencia**, cayendo a scraping gestionado solo cuando es necesario.

## Estrategia (cadena de resiliencia)

Por cada producto, `price-fetcher.py` intenta en este orden y **agrega** todo lo que encuentre:

| # | Fuente | Cómo | Requiere |
|---|--------|------|----------|
| 1 | **MercadoLibre** | API oficial `api.mercadolibre.com` (sitio MLC) | Nada (token opcional) |
| 2 | **SoloTodo** | API pública `publicapi.solotodo.com` | Nada |
| 3 | **Fetch directo** | `urllib` con cabeceras de navegador | Nada |
| 4 | **Scraping-API** | ScraperAPI / ZenRows con `render=true` + `country=cl` | API key en `.secrets` |

Luego toma el **precio más bajo** de todas las fuentes, lo guarda en historial y
alerta si quedó **bajo el precio objetivo**.

> El paso 4 es el que vence el anti-bot: renderiza JS y usa proxy residencial
> chileno. Solo se activa para las `urls` específicas que el fetch directo no pudo leer.

## Configuración — `config/price-watch.json`

```json
{
  "settings": {
    "currency": "CLP",
    "country": "CL",
    "cache_minutes": 360,
    "scraper_provider": "auto",
    "mercadolibre_site": "MLC",
    "solotodo_api_base": "https://publicapi.solotodo.com",
    "notify_notion": false,
    "notion_db": ""
  },
  "watchlist": [
    {
      "id": "robot-dreame-l40-ultra",
      "name": "Dreame L40 Ultra Robot Aspiradora",
      "query": "Dreame L40 Ultra robot aspiradora",
      "model": "L40 Ultra",
      "target_price": 600000,
      "sources": {
        "mercadolibre": true,
        "solotodo": true,
        "urls": ["https://www.falabella.com/falabella-cl/product/..."]
      },
      "notify_notion": false
    }
  ]
}
```

### Campos de cada producto (watchlist)

| Campo | Obligatorio | Descripción |
|-------|------------|-------------|
| `id` | ✅ | Identificador único (para caché/historial) |
| `name` | ✅ | Nombre legible del producto |
| `query` | ✅ | Texto de búsqueda para MercadoLibre / SoloTodo |
| `model` | ❌ | Código de modelo; filtra resultados que no lo contengan (evita accesorios) |
| `target_price` | ✅ | Precio objetivo en CLP; dispara alerta al alcanzarlo |
| `sources.mercadolibre` | ❌ | `true` para consultar la API de MercadoLibre |
| `sources.solotodo` | ❌ | `true` para consultar la API de SoloTodo |
| `sources.urls` | ❌ | URLs de fichas específicas (Falabella, Líder…) a leer con fallback |
| `notify_notion` | ❌ | Registrar el mejor precio en Notion (requiere `settings.notion_db`) |

### `settings`

| Campo | Descripción |
|-------|-------------|
| `cache_minutes` | Minutos que un resultado se considera fresco (evita re-consultar) |
| `scraper_provider` | `auto` \| `scraperapi` \| `zenrows` \| `none` |
| `mercadolibre_site` | `MLC` = Chile (MLA Argentina, MLM México, etc.) |
| `solotodo_api_base` | Base de la API pública de SoloTodo |
| `notify_notion` / `notion_db` | Sync global a Notion (por defecto apagado) |

## Secrets (en `~/.claude/.secrets`)

Mismo archivo que usa la integración de Notion. Formato `CLAVE=valor`, una por línea.
Agrega **una** de estas para habilitar el fallback anti-bot:

```
SCRAPER_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxx     # ScraperAPI (recomendado)
ZENROWS_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxx     # o ZenRows
ML_ACCESS_TOKEN=APP_USR-xxxxxxxx            # opcional, sube el límite de MercadoLibre
NOTION_API_KEY=ntn_xxxxxxxx                 # opcional, para notify_notion
```

Sin ninguna API key de scraping, los pasos 1–3 igual funcionan; solo se omite el
paso 4 (las tiendas con anti-bot fuerte podrían no dar precio).

## Uso (macOS / Linux)

```bash
cd ~/nuvaus-automation

# DRY RUN (no escribe historial/caché/Notion)
python3 scripts/price-fetcher.py --dry-run

# Ejecutar de verdad
python3 scripts/price-fetcher.py

# Un solo producto
python3 scripts/price-fetcher.py --only-id robot-dreame-l40-ultra

# Sin salida por consola (solo al log)
python3 scripts/price-fetcher.py --quiet
```

Opcional, hacerlo ejecutable:
```bash
chmod +x scripts/price-fetcher.py
./scripts/price-fetcher.py --dry-run
```

### Ver historial de precios
(disponible después de la primera ejecución sin `--dry-run`)
```bash
python3 -c "import json;[print(r['timestamp'], r['name'], r['best_price'], r['best_store'], r['below_target']) for r in json.load(open('logs/price-history.json'))]" 2>/dev/null || echo "Aún no hay historial: ejecuta primero python3 scripts/price-fetcher.py"
```

## Salidas

| Archivo | Contenido |
|---------|-----------|
| `logs/price-fetcher.log` | Log de cada corrida (incluye líneas `[ALERT]` bajo objetivo) |
| `logs/price-history.json` | Serie histórica: precio, tienda y URL por producto/fecha |
| `logs/price-cache.json` | Caché para no re-consultar dentro de `cache_minutes` |

> `logs/` está en `.gitignore`, así que el historial y las keys nunca se suben.

## Automatización en macOS (launchd)

El instalador del repo lo programa por ti (diario a las 9:00), junto con el File Manager:

```bash
bash scripts/setup-mac.sh --install-agents
```

Verificar / desinstalar:
```bash
launchctl list | grep nuvaus
bash scripts/setup-mac.sh --uninstall-agents
```

> Alternativa manual con cron: `crontab -e` y agregar
> `0 9 * * * cd "$HOME/nuvaus-automation" && /usr/bin/python3 scripts/price-fetcher.py --quiet`

## Notas de honestidad / mantenimiento

- **Probado end-to-end** en dry-run y con tests de las funciones núcleo (`to_clp`,
  `prices_from_html`, selección de mejor precio + historial). El flujo y la
  degradación ante fallos están verificados.
- **La regex de precios** (paso 3/4) es best-effort: extrae `"price"` de JSON-LD y
  el patrón `$399.990`. Si una tienda cambia su HTML, puede requerir ajuste. Las
  fuentes API (pasos 1–2) son estables y deberían ser la base.
- **SoloTodo**: su API pública puede requerir ajustar el endpoint o un token según
  su versión; el script degrada con `WARN` sin romper la corrida.
- **Legalidad**: preferir siempre las APIs oficiales. Respetar `robots.txt` y los
  Términos de Servicio de cada tienda; usar `cache_minutes` alto para no abusar.
- El fallback de scraping-API tiene **costo por request** — por eso solo se usa
  cuando el fetch directo falla, y detrás de caché.

---

**¿Dudas?** Ver `README.md` o contactar ariel@nuvaus.com
