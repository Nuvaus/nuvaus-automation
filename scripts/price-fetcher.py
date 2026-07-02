#!/usr/bin/env python3
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
#
# Cross-platform (macOS / Linux). Solo requiere Python 3.8+ (stdlib).
# Versión: 1.0 | Autor: Ariel Meneses | GitHub: nuvaus-automation
# ===================================================================

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime

# ------------------------------------------------------------------
# Rutas base (relativas al repo, no hardcodeadas)
# ------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(SCRIPT_DIR)
CONFIG_PATH = os.path.join(REPO_DIR, "config", "price-watch.json")
LOG_DIR = os.path.join(REPO_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "price-fetcher.log")
HISTORY_FILE = os.path.join(LOG_DIR, "price-history.json")
CACHE_FILE = os.path.join(LOG_DIR, "price-cache.json")
SECRETS_FILE = os.path.join(os.path.expanduser("~"), ".claude", ".secrets")

VERBOSE = True
DRY_RUN = False


# ===================================================================
# 1. UTILIDADES (logging / secrets / precios)
# ===================================================================

def log(message, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {message}"
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    if VERBOSE:
        print(line)


def get_secret(key):
    """Lee KEY=valor desde ~/.claude/.secrets (mismo patrón que notion-sync)."""
    if not os.path.exists(SECRETS_FILE):
        return None
    with open(SECRETS_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    m = re.search(rf"^{re.escape(key)}=(.+)$", content, re.MULTILINE)
    return m.group(1).strip() if m else None


def to_clp(raw):
    """'$399.990' / '399.990 CLP' / '1.199.990' -> 399990 (int) o None."""
    if raw is None:
        return None
    s = str(raw)
    clean = re.sub(r"[^\d.,]", "", s)
    if not clean:
        return None
    digits = re.sub(r"[.,]", "", clean)  # CLP: '.' es separador de miles
    return int(digits) if digits.isdigit() else None


def prices_from_html(html, source_url):
    """Extrae precios de HTML: JSON-LD '"price"' y patrón chileno $399.990."""
    found = []
    if not html:
        return found
    for m in re.finditer(r'"price"\s*:\s*"?([0-9]{4,9})(?:\.[0-9]+)?"?', html):
        val = int(m.group(1))
        if val >= 1000:
            found.append(val)
    for m in re.finditer(r'\$\s?([0-9]{1,3}(?:\.[0-9]{3})+)', html):
        val = to_clp(m.group(1))
        if val and val >= 1000:
            found.append(val)
    if not found:
        log(f"Sin precios detectables en HTML de: {source_url}", "DEBUG")
    return sorted(set(found))


def http_get(url, headers=None, timeout=30):
    """GET simple. Devuelve (status, text) o (None, None) si falla."""
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            return resp.status, resp.read().decode(charset, errors="replace")
    except Exception as e:  # noqa: BLE001 — degradar con gracia
        return None, str(e)


# ===================================================================
# 2. FUENTES DE PRECIO
#    Cada una devuelve lista de dicts: {store, price, url, title}
# ===================================================================

def from_mercadolibre(item, settings):
    """MercadoLibre — API oficial, sin scraping."""
    offers = []
    site = settings.get("mercadolibre_site", "MLC")
    q = urllib.parse.quote(item["query"])
    url = f"https://api.mercadolibre.com/sites/{site}/search?q={q}&limit=15"

    headers = {"User-Agent": settings["user_agent"]}
    token = get_secret("ML_ACCESS_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    status, body = http_get(url, headers, settings["request_timeout_sec"])
    if status != 200 or not body:
        log(f"MercadoLibre falló para '{item['query']}': {body}", "WARN")
        return offers

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        log(f"MercadoLibre respuesta no-JSON para '{item['query']}'", "WARN")
        return offers

    model = item.get("model")
    for r in data.get("results", []):
        title = r.get("title", "")
        if model and model.lower() not in title.lower():
            continue  # filtra accesorios / otros modelos
        price = r.get("price")
        if price and int(price) >= 1000:
            offers.append({
                "store": "MercadoLibre",
                "price": int(price),
                "url": r.get("permalink", ""),
                "title": title,
            })
    log(f"MercadoLibre: {len(offers)} oferta(s) para '{item['query']}'")
    return offers


def from_solotodo(item, settings):
    """SoloTodo — API pública, sin scraping."""
    offers = []
    base = settings.get("solotodo_api_base", "https://publicapi.solotodo.com")
    q = urllib.parse.quote(item["query"])
    url = f"{base}/products/?search={q}&page_size=5"
    headers = {"User-Agent": settings["user_agent"]}

    status, body = http_get(url, headers, settings["request_timeout_sec"])
    if status != 200 or not body:
        log(f"SoloTodo falló para '{item['query']}' (endpoint puede requerir ajuste): {body}", "WARN")
        return offers

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        log(f"SoloTodo respuesta no-JSON para '{item['query']}'", "WARN")
        return offers

    results = data.get("results", data if isinstance(data, list) else [])
    for p in results:
        price = to_clp(p.get("min_price") or p.get("price"))
        if price and price >= 1000:
            offers.append({
                "store": "SoloTodo (min)",
                "price": price,
                "url": p.get("url", "https://www.solotodo.cl"),
                "title": p.get("name", ""),
            })
    log(f"SoloTodo: {len(offers)} oferta(s) para '{item['query']}'")
    return offers


def from_direct(url, settings):
    """Fetch directo con cabeceras de navegador."""
    offers = []
    headers = {
        "User-Agent": settings["user_agent"],
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-CL,es;q=0.9",
    }
    status, body = http_get(url, headers, settings["request_timeout_sec"])
    if status != 200 or not body:
        log(f"Directo bloqueado/falló ({url}): {body}", "DEBUG")
        return offers
    host = urllib.parse.urlparse(url).netloc
    for pr in prices_from_html(body, url):
        offers.append({"store": f"Directo ({host})", "price": pr, "url": url, "title": ""})
    log(f"Directo OK ({url}): {len(offers)} precio(s)")
    return offers


def from_scraperapi(url, settings):
    """Fallback: scraping-API con render JS + proxy geo-Chile."""
    offers = []
    provider = settings.get("scraper_provider", "auto")
    scraper_key = get_secret("SCRAPER_API_KEY")
    zen_key = get_secret("ZENROWS_API_KEY")

    use = None
    if provider == "scraperapi" and scraper_key:
        use = "scraperapi"
    elif provider == "zenrows" and zen_key:
        use = "zenrows"
    elif provider == "auto":
        use = "scraperapi" if scraper_key else ("zenrows" if zen_key else None)

    if not use:
        log(f"Sin API key de scraping en .secrets (SCRAPER_API_KEY / ZENROWS_API_KEY). Se omite fallback para {url}", "WARN")
        return offers

    encoded = urllib.parse.quote(url, safe="")
    if use == "scraperapi":
        api = f"https://api.scraperapi.com/?api_key={scraper_key}&country_code=cl&render=true&url={encoded}"
    else:
        api = f"https://api.zenrows.com/v1/?apikey={zen_key}&js_render=true&proxy_country=cl&url={encoded}"

    status, body = http_get(api, {}, settings["request_timeout_sec"] * 3)
    if status != 200 or not body:
        log(f"Scraper-API ({use}) falló ({url}): {body}", "ERROR")
        return offers
    host = urllib.parse.urlparse(url).netloc
    for pr in prices_from_html(body, url):
        offers.append({"store": f"{host} (via {use})", "price": pr, "url": url, "title": ""})
    log(f"Scraper-API ({use}) OK ({url}): {len(offers)} precio(s)")
    return offers


# ===================================================================
# 3. CACHÉ / HISTORIAL / NOTION
# ===================================================================

def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return default
    return default


def cache_fresh(cache, item_id, cache_minutes):
    entry = cache.get(item_id)
    if not entry:
        return False
    try:
        ts = datetime.strptime(entry["timestamp"], "%Y-%m-%d %H:%M:%S")
    except (KeyError, ValueError):
        return False
    return (datetime.now() - ts).total_seconds() / 60 < cache_minutes


def add_history(item, best, all_offers):
    if DRY_RUN:
        return
    history = load_json(HISTORY_FILE, [])
    history.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "id": item["id"],
        "name": item["name"],
        "best_price": best["price"],
        "best_store": best["store"],
        "best_url": best["url"],
        "target_price": item["target_price"],
        "below_target": best["price"] <= int(item["target_price"]),
        "offer_count": len(all_offers),
    })
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def sync_to_notion(item, best, settings):
    if not item.get("notify_notion"):
        return
    db_id = settings.get("notion_db", "")
    if not db_id:
        log("notify_notion=true pero settings.notion_db vacío. Se omite Notion.", "WARN")
        return
    token = get_secret("NOTION_API_KEY")
    if not token:
        log("NOTION_API_KEY no encontrada. Se omite Notion.", "WARN")
        return
    if DRY_RUN:
        log(f"[DRY RUN] Registraría en Notion: {item['name']} = {best['price']}")
        return

    payload = {
        "parent": {"database_id": db_id},
        "properties": {
            "Producto": {"title": [{"text": {"content": item["name"]}}]},
            "Precio": {"number": best["price"]},
            "Tienda": {"rich_text": [{"text": {"content": str(best["store"])}}]},
            "URL": {"url": str(best["url"]) or None},
            "Bajo objetivo": {"checkbox": best["price"] <= int(item["target_price"])},
        },
    }
    req = urllib.request.Request(
        "https://api.notion.com/v1/pages",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        },
    )
    try:
        urllib.request.urlopen(req, timeout=30)
        log(f"Notion: registrado {item['name']} = {best['price']}")
    except Exception as e:  # noqa: BLE001
        log(f"Notion falló: {e}", "ERROR")


# ===================================================================
# 4. PROCESAMIENTO POR PRODUCTO
# ===================================================================

def check_item(item, cache, cache_map, settings):
    log("─────────────────────────────────────────────")
    log(f"Producto: {item['name']} [{item['id']}]")

    if cache_fresh(cache, item["id"], settings["cache_minutes"]):
        c = cache[item["id"]]
        log(f"Caché fresca (<{settings['cache_minutes']} min). Mejor: ${c['best_price']:,} en {c['best_store']}")
        cache_map[item["id"]] = c
        return

    offers = []
    src = item.get("sources", {})
    if src.get("mercadolibre"):
        offers += from_mercadolibre(item, settings)
    if src.get("solotodo"):
        offers += from_solotodo(item, settings)

    for url in src.get("urls", []):
        direct = from_direct(url, settings)
        offers += direct if direct else from_scraperapi(url, settings)

    if not offers:
        log(f"Sin precios obtenidos para {item['name']}. Revisa fuentes / API keys.", "WARN")
        return

    best = min(offers, key=lambda o: o["price"])
    target = int(item["target_price"])
    below = best["price"] <= target
    flag = "✅ BAJO OBJETIVO" if below else "sobre objetivo"

    log(f"MEJOR PRECIO: ${best['price']:,} en {best['store']}  ({flag}, objetivo ${target:,})")
    log(f"URL: {best['url']}")
    log(f"Total ofertas comparadas: {len(offers)}", "DEBUG")
    if below:
        log(f"🔔 ALERTA: {item['name']} alcanzó ${best['price']:,} (objetivo ${target:,})", "ALERT")

    add_history(item, best, offers)
    sync_to_notion(item, best, settings)

    cache_map[item["id"]] = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "best_price": best["price"],
        "best_store": best["store"],
        "best_url": best["url"],
    }


# ===================================================================
# 5. MAIN
# ===================================================================

def main():
    global VERBOSE, DRY_RUN

    parser = argparse.ArgumentParser(description="Nuvaus Price Fetcher — monitor de precios multi-tienda")
    parser.add_argument("--dry-run", action="store_true", help="No escribe historial/caché/Notion")
    parser.add_argument("--quiet", action="store_true", help="Sin salida por consola (solo log)")
    parser.add_argument("--only-id", default="", help="Procesar un solo producto por su id")
    parser.add_argument("--config", default=CONFIG_PATH, help="Ruta a price-watch.json")
    args = parser.parse_args()

    DRY_RUN = args.dry_run
    VERBOSE = not args.quiet

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    settings = cfg["settings"]
    watchlist = cfg["watchlist"]

    log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    log("NUVAUS PRICE FETCHER — Iniciando")
    log(f"Modo: {'DRY RUN' if DRY_RUN else 'PRODUCCIÓN'} | Productos: {len(watchlist)}")
    log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    cache = load_json(CACHE_FILE, {})
    cache_map = {}

    try:
        for item in watchlist:
            if args.only_id and item["id"] != args.only_id:
                continue
            check_item(item, cache, cache_map, settings)
        # Preservar entradas de caché no tocadas en esta corrida
        for k, v in cache.items():
            cache_map.setdefault(k, v)
        if not DRY_RUN:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(cache_map, f, ensure_ascii=False, indent=2)
    except Exception as e:  # noqa: BLE001
        log(f"Error fatal: {e}", "ERROR")
        sys.exit(1)

    log("Price fetcher finalizado.")


if __name__ == "__main__":
    main()
