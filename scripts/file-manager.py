#!/usr/bin/env python3
# ===================================================================
# NUVAUS FILE MANAGER — Automatización de archivos + Notion Sync
# ===================================================================
# Monitorea Descargas, clasifica, renombra y sincroniza con Notion.
# Port a Python del file-manager.ps1 original (Windows), pensado para
# macOS / Linux. Solo stdlib (Python 3.8+), sin dependencias.
#
# Uso:
#   python3 scripts/file-manager.py --dry-run    # ver qué haría
#   python3 scripts/file-manager.py              # ejecutar de verdad
#
# Versión: 2.0 | Autor: Ariel Meneses | GitHub: nuvaus-automation
# ===================================================================

import argparse
import fnmatch
import json
import os
import shutil
import sys
import unicodedata
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, SCRIPT_DIR)

import notion_sync  # noqa: E402  (módulo local)

LOG_DIR = os.path.join(REPO_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "file-manager.log")

VERBOSE = True
DRY_RUN = False

# Archivos que nunca se procesan (basura del SO / descargas a medias)
IGNORED_NAMES = {".DS_Store", ".localized", "Thumbs.db", "desktop.ini"}
IN_PROGRESS_SUFFIXES = (".crdownload", ".download", ".part", ".partial", ".opdownload")


# ===================================================================
# 1. UTILIDADES
# ===================================================================

def log(message, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {message}"
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    if VERBOSE:
        print(line)


def nfc(s):
    """Normaliza Unicode a NFC. Crítico en macOS: el filesystem entrega
    nombres en NFD, así que 'artículo' del config no coincidiría con
    'artículo' del disco sin esto."""
    return unicodedata.normalize("NFC", s)


def expand(path):
    """Expande ~ y variables de entorno en rutas del config."""
    return os.path.expandvars(os.path.expanduser(path))


def load_json_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        log(f"JSON inválido en {path}: {e}", "ERROR")
        sys.exit(1)
    except OSError as e:
        log(f"No se pudo leer {path}: {e}", "ERROR")
        sys.exit(1)


def load_config(config_dir):
    """Carga paths.json y rules.json. Si existe *.local.json, lo usa en
    su lugar (override local, ignorado por git)."""
    def pick(name):
        local = os.path.join(config_dir, name.replace(".json", ".local.json"))
        if os.path.exists(local):
            log(f"Usando override local: {os.path.basename(local)}")
            return local
        return os.path.join(config_dir, name)

    paths = load_json_file(pick("paths.json"))
    rules_doc = load_json_file(pick("rules.json"))

    return {
        "base": expand(paths["nuvaus_base"]),
        "downloads": expand(paths["monitored_downloads"]),
        "rules": rules_doc["rules"],
        "clients": rules_doc["clients"],
        "gs": rules_doc.get("global_settings", {}),
    }


# ===================================================================
# 2. CLASIFICACIÓN
# ===================================================================

def resolve_client(filename, clients):
    """Detecta el cliente por código o nombre dentro del nombre de archivo
    (case-insensitive, como el original)."""
    f = nfc(filename).lower()
    for client in clients:
        if nfc(client["code"]).lower() in f or nfc(client["name"]).lower() in f:
            return client
    return None


def rule_matches(filename, rule):
    """True si la extensión y algún patrón glob de la regla coinciden.
    Patrones según RULES.md: '*' comodín; sin asteriscos = coincidencia exacta."""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in [e.lower() for e in rule["extensions"]]:
        return False
    base = nfc(os.path.splitext(filename)[0]).lower()
    for pattern in rule["patterns"]:
        if fnmatch.fnmatchcase(base, nfc(pattern).lower()):
            return True
    return False


def render_pattern(pattern, client, base_name=""):
    """Rellena las variables de plantilla ({CLIENT}, {FILENAME}, fechas)."""
    now = datetime.now()
    out = pattern
    out = out.replace("{CLIENT}", client["code"] if client else "UNKNOWN")
    out = out.replace("{FILENAME}", base_name)
    out = out.replace("{DD-MM-YYYY}", now.strftime("%d-%m-%Y"))
    out = out.replace("{YYYY-MM-DD}", now.strftime("%Y-%m-%d"))
    out = out.replace("{YYYY}", now.strftime("%Y"))
    return out


# ===================================================================
# 3. MOVIMIENTO DE ARCHIVOS
# ===================================================================

def unique_path(dest_dir, name):
    """Evita sobrescrituras: si el destino existe, agrega timestamp (+contador)."""
    path = os.path.join(dest_dir, name)
    if not os.path.exists(path):
        return path, name
    stem, ext = os.path.splitext(name)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    candidate = f"{stem}-{ts}{ext}"
    n = 1
    while os.path.exists(os.path.join(dest_dir, candidate)):
        candidate = f"{stem}-{ts}-{n}{ext}"
        n += 1
    return os.path.join(dest_dir, candidate), candidate


def move_file(src, dest_dir, new_name, skip_existing=False):
    """Mueve src → dest_dir/new_name con logging. Devuelve el nombre final
    o None si se saltó / falló."""
    if not DRY_RUN and not os.path.isdir(dest_dir):
        os.makedirs(dest_dir, exist_ok=True)
        log(f"Carpeta creada: {dest_dir}")

    if skip_existing and os.path.exists(os.path.join(dest_dir, new_name)):
        log(f"Ya existe en destino, se salta (skip_existing_files): {new_name}", "WARN")
        return None

    dest_path, final_name = unique_path(dest_dir, new_name)
    if final_name != new_name:
        log(f"Archivo existe. Renombrado con timestamp: {final_name}", "WARN")

    if DRY_RUN:
        log(f"[DRY RUN] Movería: {src} → {dest_path}")
        return final_name
    try:
        shutil.move(src, dest_path)
        log(f"Movido: {src} → {dest_path}")
        return final_name
    except OSError as e:
        log(f"Error moviendo {src}: {e}", "ERROR")
        return None


# ===================================================================
# 4. PROCESAMIENTO DE DESCARGAS
# ===================================================================

def should_skip(entry_path, filename, min_age_sec):
    """Filtra basura del SO, descargas a medias y archivos recién escritos."""
    if filename in IGNORED_NAMES or filename.startswith("."):
        return "oculto/sistema"
    if filename.lower().endswith(IN_PROGRESS_SUFFIXES):
        return "descarga en progreso"
    if not os.path.isfile(entry_path):
        return "no es archivo"
    age = datetime.now().timestamp() - os.path.getmtime(entry_path)
    if age < min_age_sec:
        return f"muy reciente ({int(age)}s < {min_age_sec}s)"
    return None


def process_downloads(cfg):
    downloads = cfg["downloads"]
    if not os.path.isdir(downloads):
        log(f"Carpeta Downloads no existe: {downloads}", "ERROR")
        return []

    min_age = int(cfg["gs"].get("min_file_age_seconds", 60))
    skip_existing = bool(cfg["gs"].get("skip_existing_files", False))

    entries = sorted(os.listdir(downloads))
    candidates = []
    for name in entries:
        path = os.path.join(downloads, name)
        reason = should_skip(path, name, min_age)
        if reason:
            log(f"Omitido ({reason}): {name}", "DEBUG")
        else:
            candidates.append((path, name))

    if not candidates:
        log("Sin archivos nuevos en Downloads")
        return []

    log(f"Procesando {len(candidates)} archivo(s)")
    moved = []

    for path, name in candidates:
        log(f"Analizando: {name}", "DEBUG")
        matched = False
        for rule in cfg["rules"]:
            if not rule_matches(name, rule):
                continue
            log(f"Regla coincide: {rule['name']}")
            client = resolve_client(name, cfg["clients"])
            base = os.path.splitext(name)[0]
            ext = os.path.splitext(name)[1]
            new_name = render_pattern(rule["rename_pattern"], client, base) + ext
            dest_dir = os.path.join(cfg["base"], render_pattern(rule["destination"], client, base))

            final_name = move_file(path, dest_dir, new_name, skip_existing)
            if final_name:
                moved.append({"rule": rule, "new_name": final_name, "client": client})
                if rule.get("notify_notion") and not DRY_RUN:
                    try:
                        notion_sync.sync_moved_file(
                            {"rule": rule, "new_name": final_name}, client,
                            logger=lambda m: log(m),
                        )
                    except Exception as e:  # noqa: BLE001 — Notion nunca debe frenar el flujo
                        log(f"Notion sync falló (continuo): {e}", "ERROR")
            matched = True
            break

        if not matched:
            log(f"Sin regla coincidente para: {name}", "WARN")

    log(f"Procesamiento completado. {len(moved)} archivo(s) movido(s).")
    return moved


# ===================================================================
# 5. ARCHIVADO Y LIMPIEZA
# ===================================================================

def archive_old_proposals(cfg):
    """Propuestas con más de N días → propuestas-archivo/{año}."""
    src_dir = os.path.join(cfg["base"], "propuestas")
    dst_root = os.path.join(cfg["base"], "propuestas-archivo")
    if not os.path.isdir(src_dir):
        return

    days = int(cfg["gs"].get("archive_propuestas_after_days", 180))
    cutoff = datetime.now().timestamp() - days * 86400

    for name in sorted(os.listdir(src_dir)):
        path = os.path.join(src_dir, name)
        if not os.path.isfile(path) or name.startswith("."):
            continue
        mtime = os.path.getmtime(path)
        if mtime >= cutoff:
            continue
        year = datetime.fromtimestamp(mtime).strftime("%Y")
        dest_dir = os.path.join(dst_root, year)
        if DRY_RUN:
            log(f"[DRY RUN] Archivaría: {name} → propuestas-archivo/{year}")
            continue
        os.makedirs(dest_dir, exist_ok=True)
        dest_path, _ = unique_path(dest_dir, name)
        try:
            shutil.move(path, dest_path)
            log(f"Archivado: {name} → propuestas-archivo/{year}")
        except OSError as e:
            log(f"Error archivando {name}: {e}", "ERROR")


def cleanup_auto_delete(cfg):
    """Borra archivos más antiguos que auto_delete_days en las carpetas
    de las reglas que lo definan (documentado en RULES.md)."""
    for rule in cfg["rules"]:
        days = rule.get("auto_delete_days")
        if not days:
            continue
        if "{CLIENT}" in rule["destination"]:
            log(f"auto_delete_days no soporta destinos con {{CLIENT}} ({rule['id']}), se omite", "WARN")
            continue
        target = os.path.join(cfg["base"], rule["destination"])
        if not os.path.isdir(target):
            continue
        cutoff = datetime.now().timestamp() - int(days) * 86400
        for name in sorted(os.listdir(target)):
            path = os.path.join(target, name)
            if not os.path.isfile(path) or name.startswith("."):
                continue
            if os.path.getmtime(path) >= cutoff:
                continue
            if DRY_RUN:
                log(f"[DRY RUN] Eliminaría (> {days} días): {rule['destination']}/{name}")
                continue
            try:
                os.remove(path)
                log(f"Eliminado (> {days} días): {rule['destination']}/{name}")
            except OSError as e:
                log(f"Error eliminando {name}: {e}", "ERROR")


# ===================================================================
# 6. MAIN
# ===================================================================

def main():
    global VERBOSE, DRY_RUN

    parser = argparse.ArgumentParser(description="Nuvaus File Manager — clasificación automática de descargas")
    parser.add_argument("--dry-run", action="store_true", help="Muestra qué haría sin mover nada")
    parser.add_argument("--quiet", action="store_true", help="Sin salida por consola (solo log)")
    parser.add_argument("--config", default=os.path.join(REPO_DIR, "config"), help="Directorio de configuración")
    args = parser.parse_args()

    DRY_RUN = args.dry_run
    VERBOSE = not args.quiet

    cfg = load_config(args.config)

    log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    log("NUVAUS FILE MANAGER — Iniciando procesamiento")
    log(f"Modo: {'DRY RUN' if DRY_RUN else 'PRODUCCIÓN'}")
    log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    try:
        process_downloads(cfg)
        archive_old_proposals(cfg)
        cleanup_auto_delete(cfg)
    except Exception as e:  # noqa: BLE001
        log(f"Error fatal: {e}", "ERROR")
        sys.exit(1)

    log("Procesamiento finalizado.")


if __name__ == "__main__":
    main()
