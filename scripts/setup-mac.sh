#!/bin/bash
# ===================================================================
# NUVAUS SETUP (macOS) — prepara carpetas, valida el entorno y
# opcionalmente instala los agentes launchd de automatización.
#
# Uso:
#   bash scripts/setup-mac.sh                    # setup + dry-run de prueba
#   bash scripts/setup-mac.sh --install-agents   # además programa launchd
#   bash scripts/setup-mac.sh --uninstall-agents # quita la automatización
# ===================================================================
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE="$HOME/Desktop/Nuvaus"
AGENTS_DIR="$HOME/Library/LaunchAgents"
SECRETS="$HOME/.claude/.secrets"
PY="$(command -v python3 || true)"

bold() { printf '\n\033[1m%s\033[0m\n' "$*"; }
ok()   { printf '  ✓ %s\n' "$*"; }
warn() { printf '  ⚠ %s\n' "$*"; }

if [[ -z "$PY" ]]; then
  echo "✗ python3 no encontrado. Instala las Command Line Tools de Apple:"
  echo "    xcode-select --install"
  exit 1
fi

MODE="${1:-setup}"
case "$MODE" in
  setup|--install-agents|--uninstall-agents) ;;
  *)
    echo "Argumento desconocido: $MODE"
    echo "Uso: bash scripts/setup-mac.sh [--install-agents | --uninstall-agents]"
    exit 1
    ;;
esac

xml_escape() {  # escapa & < > para que rutas raras no rompan el plist
  local s="$1"
  s="${s//&/&amp;}"; s="${s//</&lt;}"; s="${s//>/&gt;}"
  printf '%s' "$s"
}
PY_X="$(xml_escape "$PY")"
REPO_X="$(xml_escape "$REPO_DIR")"
MACLOGS="$HOME/Library/Logs"   # ruta estable: sobrevive si mueves el repo
MACLOGS_X="$(xml_escape "$MACLOGS")"

install_agent() {  # $1 = nombre; el plist llega por stdin
  local name="$1" plist="$AGENTS_DIR/$1.plist"
  mkdir -p "$AGENTS_DIR"
  launchctl unload "$plist" >/dev/null 2>&1 || true
  cat > "$plist"
  if command -v plutil >/dev/null 2>&1 && ! plutil -lint "$plist" >/dev/null; then
    rm -f "$plist"
    warn "plist inválido para $name (¿la ruta del repo tiene caracteres extraños?)"
    exit 1
  fi
  if ! launchctl load -w "$plist"; then
    rm -f "$plist"
    warn "No se pudo cargar $name — ¿estás en una sesión gráfica de macOS?"
    exit 1
  fi
  ok "Agente cargado: $name"
}

uninstall_agent() {
  local plist="$AGENTS_DIR/$1.plist"
  launchctl unload "$plist" >/dev/null 2>&1 || true
  rm -f "$plist"
  ok "Agente eliminado: $1"
}

if [[ "$MODE" == "--uninstall-agents" ]]; then
  bold "Desinstalando agentes launchd…"
  uninstall_agent "com.nuvaus.file-manager"
  uninstall_agent "com.nuvaus.price-watch"
  exit 0
fi

bold "== Nuvaus Setup (macOS) =="
echo "  Repo:   $REPO_DIR"
echo "  Python: $PY ($("$PY" --version 2>&1))"

bold "1) Creando estructura de carpetas en $BASE…"
for d in \
  "$BASE/propuestas" \
  "$BASE/propuestas-archivo" \
  "$BASE/clientes" \
  "$BASE/descargas-ordenadas/diseños" \
  "$BASE/descargas-ordenadas/artículos" \
  "$BASE/documentos/invoices" \
  "$BASE/documentos/contratos" \
  "$BASE/temp/reportes" \
  "$REPO_DIR/logs"; do
  mkdir -p "$d"
done
ok "Carpetas listas"

bold "2) Verificando secrets ($SECRETS)…"
if [[ -f "$SECRETS" ]]; then
  if grep -q '^NOTION_API_KEY=' "$SECRETS"; then
    ok "NOTION_API_KEY presente"
  else
    warn "Sin NOTION_API_KEY (la sincronización con Notion queda desactivada)"
  fi
  if grep -Eq '^(SCRAPER_API_KEY|ZENROWS_API_KEY)=' "$SECRETS"; then
    ok "API key de scraping presente (fallback anti-bot activo)"
  else
    warn "Sin SCRAPER_API_KEY/ZENROWS_API_KEY (price-watch funciona, pero sin fallback anti-bot)"
  fi
else
  warn "No existe $SECRETS — créalo si usarás Notion o el fallback de precios:"
  echo '      mkdir -p ~/.claude && touch ~/.claude/.secrets'
fi

bold "3) DRY RUN de prueba del File Manager…"
"$PY" "$REPO_DIR/scripts/file-manager.py" --dry-run

if [[ "$MODE" == "--install-agents" ]]; then
  bold "4) Instalando agentes launchd…"

  # File Manager: cada 15 minutos (y al iniciar sesión)
  install_agent "com.nuvaus.file-manager" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>com.nuvaus.file-manager</string>
    <key>ProgramArguments</key>
    <array>
        <string>${PY_X}</string>
        <string>${REPO_X}/scripts/file-manager.py</string>
        <string>--quiet</string>
    </array>
    <key>WorkingDirectory</key><string>${REPO_X}</string>
    <key>StartInterval</key><integer>900</integer>
    <key>RunAtLoad</key><true/>
    <key>StandardOutPath</key><string>${MACLOGS_X}/nuvaus-file-manager.log</string>
    <key>StandardErrorPath</key><string>${MACLOGS_X}/nuvaus-file-manager.log</string>
</dict>
</plist>
PLIST

  # Price Watch: todos los días a las 9:00
  install_agent "com.nuvaus.price-watch" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>com.nuvaus.price-watch</string>
    <key>ProgramArguments</key>
    <array>
        <string>${PY_X}</string>
        <string>${REPO_X}/scripts/price-fetcher.py</string>
        <string>--quiet</string>
    </array>
    <key>WorkingDirectory</key><string>${REPO_X}</string>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key><integer>9</integer>
        <key>Minute</key><integer>0</integer>
    </dict>
    <key>RunAtLoad</key><false/>
    <key>StandardOutPath</key><string>${MACLOGS_X}/nuvaus-price-watch.log</string>
    <key>StandardErrorPath</key><string>${MACLOGS_X}/nuvaus-price-watch.log</string>
</dict>
</plist>
PLIST

  echo
  echo "  Verifica con:  launchctl list | grep nuvaus"
fi

bold "✅ Setup completo."
echo "  • Probar a mano:      python3 scripts/file-manager.py --dry-run"
echo "  • Ejecutar de verdad: python3 scripts/file-manager.py"
echo "  • Precios:            python3 scripts/price-fetcher.py --dry-run"
if [[ "$MODE" != "--install-agents" ]]; then
  echo "  • Automatizar:        bash scripts/setup-mac.sh --install-agents"
fi
