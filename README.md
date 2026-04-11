# Nuvaus Automation — File Manager

Sistema automático de gestión de archivos para Nuvaus. Monitorea descargas, clasifica, renombra y sincroniza con Notion.

## Características

✅ **Monitoreo automático** — Detecta nuevos archivos en Descargas  
✅ **Clasificación inteligente** — Aplica reglas según tipo de archivo  
✅ **Renombrado automático** — Patrón: `NV-PROP-{Cliente}-{DD-MM-YYYY}`  
✅ **Organización en carpetas** — Mueve a estructura definida  
✅ **Sincronización Notion** — Actualiza BD Propuestas/Interacciones  
✅ **Archivado automático** — Propuestas antiguas → propuestas-archivo/{YYYY}  
✅ **Logs detallados** — Auditoría completa de qué se movió y cuándo  

## Estructura

```
.automation/
├── scripts/
│   ├── file-manager.ps1      ← Core de automatización
│   └── notion-sync.ps1       ← Sincronización Notion
├── config/
│   ├── paths.json            ← Rutas del sistema
│   └── rules.json            ← Reglas de clasificación
├── logs/
│   └── file-manager.log      ← Log de operaciones
├── README.md                 ← Este archivo
├── SETUP.md                  ← Instalación
├── RULES.md                  ← Cómo modificar reglas
└── .gitignore
```

## Requisitos

- **Windows 10+** con PowerShell 5.1+
- **Acceso a** `C:\Users\ariel\.secrets` (para NOTION_API_KEY)
- **Notion Integration Token** guardado en `.secrets`

## Inicio Rápido

```bash
# 1. Clonar repositorio
git clone https://github.com/ariel-meneses/nuvaus-automation.git

# 2. Copiar a Desktop/Nuvaus/.automation/
cp -r nuvaus-automation/* "C:\Users\ariel\Desktop\Nuvaus\.automation\"

# 3. Crear carpetas faltantes (las define Task Scheduler)
New-Item "C:\Users\ariel\Desktop\Nuvaus\descargas-ordenadas" -ItemType Directory
New-Item "C:\Users\ariel\Desktop\Nuvaus\propuestas-archivo" -ItemType Directory

# 4. Verificar configuración
. "C:\Users\ariel\Desktop\Nuvaus\.automation\scripts\file-manager.ps1" -DryRun $true

# 5. Programar Task Scheduler (ver SETUP.md)
```

## Uso

### Manual — Test sin ejecutar
```powershell
# DRY RUN: ver qué haría sin ejecutar
& "C:\Users\ariel\Desktop\Nuvaus\.automation\scripts\file-manager.ps1" -DryRun $true
```

### Manual — Ejecutar ahora
```powershell
# Ejecutar inmediatamente
& "C:\Users\ariel\Desktop\Nuvaus\.automation\scripts\file-manager.ps1"
```

### Automático — Task Scheduler
Ver `SETUP.md` para configurar ejecución cada 15 minutos.

## Configuración

### `paths.json`
Define dónde busca y dónde mueve archivos.

```json
{
  "nuvaus_base": "C:\\Users\\ariel\\Desktop\\Nuvaus",
  "monitored_downloads": "C:\\Users\\ariel\\Downloads",
  "propuestas_activas": "C:\\Users\\ariel\\Desktop\\Nuvaus\\propuestas",
  ...
}
```

### `rules.json`
Define reglas de clasificación. Ver `RULES.md` para agregar nuevas.

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
    },
    ...
  ]
}
```

## Logs

Todos los movimientos se registran en `logs/file-manager.log`:

```
[2026-04-10 14:32:15] [INFO] Analizando: NV-PROP-CECA-2026.pdf
[2026-04-10 14:32:15] [INFO] Regla coincide: Propuestas Nuvaus (PDF)
[2026-04-10 14:32:16] [INFO] Movido: C:\Users\ariel\Downloads\NV-PROP-CECA-2026.pdf → C:\Users\ariel\Desktop\Nuvaus\propuestas\NV-PROP-CECA-10-04-2026.pdf
[2026-04-10 14:32:16] [INFO] Notion sync queued: NV-PROP-CECA-10-04-2026.pdf | Client: CECA
```

## Notion Sync

Cuando se mueve una propuesta con `notify_notion: true`, se crea automáticamente una entrada en:

- **DB Interacciones** (`896da7d5-0b9c-4f4e-ad4b-750cef851389`)
  - Tipo: Propuesta
  - Cliente: [código extraído del nombre]
  - Resultado: Propuesta Enviada
  - Próximo paso: Seguimiento en 7 días

Esto permite trackear automáticamente cuándo se mueven propuestas sin tocar Notion manualmente.

## Troubleshooting

### "NOTION_API_KEY no encontrada"
Verifica que existe en `~/.claude/.secrets`:
```bash
cat $env:USERPROFILE\.claude\.secrets | grep NOTION_API_KEY
```

### Archivos no se mueven
1. Ejecutar en **DRY RUN** para ver qué haría
2. Revisar `rules.json` — ¿el patrón coincide?
3. Revisar logs — ver error específico
4. Probar manualmente: `Test-RuleMatch`

### Task Scheduler no ejecuta
1. Abrir Task Scheduler → buscar "Nuvaus File Manager"
2. Verificar permisos → debe ejecutarse con tu usuario
3. Revisar "Historial" de la tarea → ver error
4. Re-crear la tarea (ver SETUP.md)

## Desarrollo

### Agregar nueva regla
Editar `config/rules.json` — ver `RULES.md` para detalles.

### Modificar script
- `scripts/file-manager.ps1` — Core de automatización
- `scripts/notion-sync.ps1` — Integración Notion
- Después de cambios, ejecutar DRY RUN para validar

### Versioning
```bash
git add scripts/ config/ docs/
git commit -m "feat: nueva regla para facturas"
git push origin main
```

## Roadmap

- [ ] Web UI para editar reglas sin tocar JSON
- [ ] Sincronización bidireccional con Notion (marcar en Notion → archiva)
- [ ] Integración WhatsApp — notificación cuando se mueve propuesta
- [ ] Analytics — dashboard de cuántos archivos se movieron/mes
- [ ] Búsqueda fuzzy — encontrar archivos sin conocer nombre exacto

## Contacto

**Creador**: Ariel Meneses  
**Email**: ariel@nuvaus.com  
**Repo**: https://github.com/ariel-meneses/nuvaus-automation

---

**Última actualización**: 10-04-2026  
**Versión**: 1.0.0
