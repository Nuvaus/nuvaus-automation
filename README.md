# Nuvaus Automation

Sistema de automatización para Nuvaus en **macOS**: gestiona archivos descargados,
sincroniza con Notion y monitorea precios en tiendas chilenas.

## Características

✅ **Monitoreo automático** — Detecta nuevos archivos en Descargas  
✅ **Clasificación inteligente** — Aplica reglas según tipo de archivo  
✅ **Renombrado automático** — Patrón: `NV-PROP-{Cliente}-{DD-MM-YYYY}`  
✅ **Organización en carpetas** — Mueve a estructura definida (soporta `{CLIENT}` en destinos)  
✅ **Sincronización Notion** — Actualiza BD Propuestas/Interacciones  
✅ **Archivado automático** — Propuestas antiguas → propuestas-archivo/{YYYY}  
✅ **Auto-limpieza** — Borra reportes temporales tras N días (`auto_delete_days`)  
✅ **Monitor de precios** — Compara precios multi-tienda (Chile) evadiendo anti-bot → `PRICE-WATCH.md`  
✅ **Logs detallados** — Auditoría completa de qué se movió y cuándo  

Todo en **Python 3 puro** (sin dependencias, sin `pip install`) + `launchd` para la automatización.

## Estructura

```
nuvaus-automation/
├── scripts/
│   ├── file-manager.py       ← Core de automatización de archivos
│   ├── notion_sync.py        ← Integración con Notion
│   ├── price-fetcher.py      ← Monitor de precios multi-tienda
│   ├── run-tests.py          ← Suite de tests (no toca archivos reales)
│   └── setup-mac.sh          ← Instalador: carpetas + launchd
├── config/
│   ├── paths.json            ← Rutas del sistema (soporta ~)
│   ├── rules.json            ← Reglas de clasificación
│   └── price-watch.json      ← Productos a monitorear (precios)
├── logs/                     ← Generados en ejecución (git los ignora)
├── README.md                 ← Este archivo
├── SETUP.md                  ← Instalación (macOS)
├── RULES.md                  ← Cómo modificar reglas
├── PRICE-WATCH.md            ← Monitor de precios (uso + config)
└── .gitignore
```

## Requisitos

- **macOS 12+** con Python 3.8+ (`xcode-select --install` si falta)
- **Notion Integration Token** en `~/.claude/.secrets` (opcional)

## Inicio Rápido

```bash
# 1. Clonar (rama con la versión macOS)
cd ~
git clone -b claude/washing-machine-price-comparison-Jpfol https://github.com/Nuvaus/nuvaus-automation.git
cd nuvaus-automation

# 2. Setup (carpetas + verificación + dry-run de prueba)
bash scripts/setup-mac.sh

# 3. Probar de verdad
python3 scripts/file-manager.py

# 4. Automatizar (cada 15 min + precios diarios 9:00)
bash scripts/setup-mac.sh --install-agents
```

Ver `SETUP.md` para el detalle paso a paso.

## Uso

```bash
# DRY RUN: ver qué haría sin ejecutar
python3 scripts/file-manager.py --dry-run

# Ejecutar ahora
python3 scripts/file-manager.py

# Tests
python3 scripts/run-tests.py

# Monitor de precios
python3 scripts/price-fetcher.py --dry-run
```

## Configuración

### `config/paths.json`
Define dónde busca y dónde mueve archivos (acepta `~`):

```json
{
  "nuvaus_base": "~/Desktop/Nuvaus",
  "monitored_downloads": "~/Downloads"
}
```

> Para rutas personales sin tocar git, crea `config/paths.local.json`
> con el mismo formato — tiene prioridad y está en `.gitignore`.

### `config/rules.json`
Reglas de clasificación. Ver `RULES.md` para agregar nuevas.

```json
{
  "rules": [
    {
      "id": "propuestas",
      "name": "Propuestas Nuvaus (PDF)",
      "patterns": ["NV-PROP-*"],
      "extensions": [".pdf"],
      "destination": "propuestas",
      "rename_pattern": "NV-PROP-{CLIENT}-{DD-MM-YYYY}",
      "notify_notion": true
    }
  ]
}
```

## Logs

Todos los movimientos quedan en `logs/file-manager.log`:

```
[2026-07-06 14:32:15] [INFO] Analizando: NV-PROP-CECA-2026.pdf
[2026-07-06 14:32:15] [INFO] Regla coincide: Propuestas Nuvaus (PDF)
[2026-07-06 14:32:16] [INFO] Movido: ~/Downloads/NV-PROP-CECA-2026.pdf → ~/Desktop/Nuvaus/propuestas/NV-PROP-CECA-06-07-2026.pdf
[2026-07-06 14:32:16] [INFO] Notion: interacción creada — NV-PROP-CECA-06-07-2026.pdf | Cliente: CECA
```

## Notion Sync

Cuando se mueve una propuesta con `notify_notion: true`, se crea una entrada en
**DB Interacciones** (`896da7d5-0b9c-4f4e-ad4b-750cef851389`):
- Tipo: Propuesta · Cliente: [código] · Resultado: Propuesta Enviada · Próximo paso: Seguimiento en 7 días

Requiere `NOTION_API_KEY` en `~/.claude/.secrets`. Sin la key, el resto del
sistema funciona igual (solo se omite Notion, con aviso en el log).

## Troubleshooting

Ver la sección completa en `SETUP.md`. Resumen:
- **No mueve archivos** → correr `--dry-run` y revisar `logs/file-manager.log`
- **launchd no corre** → `launchctl list | grep nuvaus` y `cat logs/launchd-*.log`
- **Notion falla** → verificar `NOTION_API_KEY` en `~/.claude/.secrets`

## Desarrollo

- Agregar regla → editar `config/rules.json` (ver `RULES.md`), validar con `--dry-run`
- Modificar scripts → correr `python3 scripts/run-tests.py` antes de commitear

```bash
git add scripts/ config/
git commit -m "feat: nueva regla para facturas"
git push
```

## Historia

- **v2.0** — Port completo a macOS: Python 3 + launchd. Se retiraron los scripts
  PowerShell (la versión Windows vive en el historial de git).
- **v1.0** — Versión original Windows (PowerShell + Task Scheduler).

## Roadmap

- [ ] Web UI para editar reglas sin tocar JSON
- [ ] Sincronización bidireccional con Notion (marcar en Notion → archiva)
- [ ] Integración WhatsApp — notificación cuando se mueve propuesta
- [ ] Analytics — dashboard de cuántos archivos se movieron/mes
- [ ] Búsqueda fuzzy — encontrar archivos sin conocer nombre exacto

## Contacto

**Creador**: Ariel Meneses  
**Email**: ariel@nuvaus.com  
**Repo**: https://github.com/Nuvaus/nuvaus-automation

---

**Última actualización**: 06-07-2026  
**Versión**: 2.0.0
