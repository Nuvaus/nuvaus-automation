# RULES — Cómo Agregar y Modificar Reglas

Guía para personalizar `config/rules.json` sin tocar código.

## Estructura de una Regla

```json
{
  "id": "propuestas",
  "name": "Propuestas Nuvaus (PDF)",
  "patterns": ["NV-PROP-*", "NV-QUOT-*"],
  "extensions": [".pdf"],
  "destination": "propuestas",
  "rename_pattern": "NV-PROP-{CLIENT}-{DD-MM-YYYY}",
  "notify_notion": true,
  "notion_db": "896da7d5-0b9c-4f4e-ad4b-750cef851389"
}
```

## Explicación de Campos

| Campo | Obligatorio | Ejemplo | Descripción |
|-------|------------|---------|-------------|
| `id` | ✅ | `propuestas` | Identificador único (snake_case) |
| `name` | ✅ | `Propuestas Nuvaus (PDF)` | Nombre legible (para logs) |
| `patterns` | ✅ | `["NV-PROP-*"]` | Array de patrones glob para nombres |
| `extensions` | ✅ | `[".pdf", ".xlsx"]` | Array de extensiones (con punto) |
| `destination` | ✅ | `propuestas` | Carpeta relativa a `nuvaus_base` |
| `rename_pattern` | ✅ | `NV-PROP-{CLIENT}-{DD-MM-YYYY}` | Plantilla de renombrado |
| `notify_notion` | ❌ | `true` | Sincronizar con Notion (default: false) |
| `notion_db` | ❌ | `896da7d...` | DB ID de Notion (si notify_notion=true) |
| `auto_delete_days` | ❌ | `90` | Eliminar archivos más antiguos que N días |

## Plantillas de Renombrado

### Variables disponibles:
- `{CLIENT}` — Código del cliente (ej: CECA, AJJ)
- `{FILENAME}` — Nombre original del archivo (sin extensión)
- `{DD-MM-YYYY}` — Fecha actual (10-04-2026)
- `{YYYY-MM-DD}` — Fecha ISO (2026-04-10)
- `{YYYY}` — Año (2026)

### Ejemplos:
```
NV-PROP-{CLIENT}-{DD-MM-YYYY}        → NV-PROP-CECA-10-04-2026.pdf
{CLIENT}-{YYYY}-{FILENAME}           → CECA-2026-propuesta-servicios.pdf
{YYYY-MM-DD}-{FILENAME}              → 2026-04-10-reporte-analytics.pdf
invoice-{CLIENT}-{DD-MM-YYYY}        → invoice-AJJ-10-04-2026.pdf
```

## Patrones (Glob)

### Sintaxis:
- `*` = Cualquier carácter (comodín)
- Exacto = Sin asteriscos

### Ejemplos:
```
"NV-PROP-*"        → Coincide: NV-PROP-CECA, NV-PROP-AJJ-v2, etc.
"NV-*"             → Coincide: NV-PROP, NV-CONT, NV-FACT, etc.
"factura*"         → Coincide: factura-2026, factura_CECA, etc.
"reporte"          → Coincide exactamente: reporte (no "reporte-2026")
```

## Agregar Nueva Regla

Editar `config/rules.json` en la sección `"rules": [...]`

### Ejemplo: Agregar regla para "Certificados"

```json
{
  "id": "certificados",
  "name": "Certificados de clientes",
  "patterns": ["certificado*", "cert-*"],
  "extensions": [".pdf", ".png", ".jpg"],
  "destination": "clientes/{CLIENT}/certificados",
  "rename_pattern": "{CLIENT}-certificado-{YYYY-MM-DD}",
  "notify_notion": false
}
```

Esto significa:
- Buscar archivos que comiencen con "certificado" o "cert-"
- Que sean PNG, JPG o PDF
- Moverlos a `clientes/CECA/certificados/` (si es CECA)
- Renombrar a: `CECA-certificado-2026-04-10.pdf`
- NO notificar a Notion

## Casos de Uso

### 1. **Facturas por Cliente**

```json
{
  "id": "invoices",
  "name": "Facturas y recibos",
  "patterns": ["factura*", "invoice*", "recibo*"],
  "extensions": [".pdf", ".xlsx"],
  "destination": "clientes/{CLIENT}/documentos/invoices",
  "rename_pattern": "{CLIENT}-invoice-{YYYY-MM-DD}"
}
```

**Resultado:**
- Descarga: `factura-CECA-2026.pdf`
- Movido a: `clientes/CECA/documentos/invoices/CECA-invoice-2026-04-10.pdf`

---

### 2. **Artículos Recortados (Fecha)**

```json
{
  "id": "articles",
  "name": "Artículos y referencias",
  "patterns": ["artículo*", "article*"],
  "extensions": [".pdf", ".html"],
  "destination": "descargas-ordenadas/artículos",
  "rename_pattern": "{YYYY-MM-DD}-{FILENAME}"
}
```

**Resultado:**
- Descarga: `artículo-machine-learning.pdf`
- Movido a: `descargas-ordenadas/artículos/2026-04-10-artículo-machine-learning.pdf`

---

### 3. **Reportes Automáticos (Auto-Limpieza)**

```json
{
  "id": "lighthouse",
  "name": "Reportes Lighthouse",
  "patterns": ["lighthouse*"],
  "extensions": [".json", ".html"],
  "destination": "temp/reportes",
  "rename_pattern": "lighthouse-{YYYY-MM-DD}-{FILENAME}",
  "auto_delete_days": 30
}
```

**Resultado:**
- Descarga: `lighthouse-report-2026-04.json`
- Movido a: `temp/reportes/lighthouse-2026-04-10-lighthouse-report-2026-04.json`
- **Eliminado automáticamente después de 30 días**

---

### 4. **Propuestas Versioned**

```json
{
  "id": "propuestas_multi",
  "name": "Propuestas (todas las versiones)",
  "patterns": ["NV-PROP-*", "NV-QUOT-*", "propuesta*"],
  "extensions": [".pdf"],
  "destination": "propuestas",
  "rename_pattern": "NV-PROP-{CLIENT}-{DD-MM-YYYY}",
  "notify_notion": true,
  "notion_db": "896da7d5-0b9c-4f4e-ad4b-750cef851389"
}
```

**Resultado:**
- Descarga: `propuesta-servicios-v2.pdf` (automáticamente detecta que es CECA si lo menciona)
- Movido a: `propuestas/NV-PROP-CECA-10-04-2026.pdf`
- **Crea entrada en Notion automáticamente**

---

## Modificar Regla Existente

Ejemplo: Cambiar dónde van las facturas

**Original:**
```json
{
  "id": "invoices",
  ...
  "destination": "documentos/invoices",
  ...
}
```

**Modificado (por cliente):**
```json
{
  "id": "invoices",
  ...
  "destination": "clientes/{CLIENT}/invoices",
  ...
}
```

Ahora:
- Facturas CECA → `clientes/CECA/invoices/`
- Facturas AJJ → `clientes/AJJ/invoices/`

## Clientes Soportados

Definidos en `config/rules.json` bajo `"clients"`:

```json
"clients": [
  { "code": "CECA", "name": "CECA Salud", "folder": "ceca", "country": "CL" },
  { "code": "AJJ", "name": "AJJ Remodelaciones", "folder": "ajj", "country": "US" },
  { "code": "ALEP", "name": "Alepineda", "folder": "alepineda", "country": "CL" },
  { "code": "UNAB", "name": "Universidad Andrés Bello", "folder": "unab", "country": "CL" }
]
```

El script automáticamente detecta el cliente por:
1. Código en el nombre (`NV-PROP-CECA-...`)
2. Nombre en el nombre (`propuesta-CECA-Salud...`)

**Para agregar cliente nuevo:**
```json
{ "code": "NUEVO", "name": "Nombre Cliente", "folder": "nuevo", "country": "CL" }
```

Luego cualquier archivo con "NUEVO" o "Nombre Cliente" será detectado.

## Orden de Ejecución

Las reglas se aplican **en orden** de aparición en `rules.json`. La **primera que coincida gana**.

**Importante:** Si quieres que una regla específica tenga prioridad, colócala **arriba** en la lista.

Ejemplo:
```json
"rules": [
  { "id": "propuestas_urgentes", "patterns": ["URGENTE-*"], ... },  ← Arriba: prioridad
  { "id": "propuestas", "patterns": ["NV-PROP-*"], ... },           ← Después: default
  { "id": "otros_pdf", "patterns": ["*.pdf"], ... }                 ← Abajo: fallback
]
```

## Validar Cambios

Después de editar `rules.json`, **siempre ejecutar en DRY RUN**:

```bash
cd ~/nuvaus-automation
python3 scripts/file-manager.py --dry-run
```

Ver logs para errores:
```bash
tail -30 logs/file-manager.log
```

Si ve errores JSON, revisar:
- Comillas: deben ser `"` no `'`
- Comas: cada item en array excepto el último
- Llaves: todas abiertas deben tener cierre

## Referencia JSON Rápida

### Array válido:
```json
"patterns": ["NV-PROP-*", "NV-QUOT-*"]
```

### String válido:
```json
"destination": "propuestas"
```

### Booleano válido:
```json
"notify_notion": true
```

### Invalid (ERRORES):
```json
"patterns": ['NV-PROP-*']           ← ✗ Comillas simples
"destination": propuestas           ← ✗ Sin comillas
"notify_notion": True               ← ✗ Mayúscula (debe ser true)
"patterns": ["NV-PROP-*",]          ← ✗ Coma después del último
```

## Ejemplos Listos para Copiar

### Contratos
```json
{
  "id": "contratos",
  "name": "Contratos y acuerdos",
  "patterns": ["contrato*", "acuerdo*", "NV-CONT-*"],
  "extensions": [".pdf", ".docx"],
  "destination": "documentos/contratos",
  "rename_pattern": "NV-CONT-{CLIENT}-{DD-MM-YYYY}",
  "notify_notion": true,
  "notion_db": "896da7d5-0b9c-4f4e-ad4b-750cef851389"
}
```

### Presentaciones
```json
{
  "id": "presentations",
  "name": "Presentaciones y decks",
  "patterns": ["presentación*", "deck-*", "ppt-*"],
  "extensions": [".pptx", ".pdf", ".ppt"],
  "destination": "clientes/{CLIENT}/presentaciones",
  "rename_pattern": "{CLIENT}-presentacion-{DD-MM-YYYY}"
}
```

### Wireframes
```json
{
  "id": "wireframes",
  "name": "Wireframes y mockups",
  "patterns": ["wireframe*", "mockup*", "prototipo*"],
  "extensions": [".fig", ".xd", ".sketch", ".png"],
  "destination": "descargas-ordenadas/diseños",
  "rename_pattern": "{CLIENT}-wireframe-{YYYY-MM-DD}"
}
```

---

**¿Necesitas ayuda?** Contactar a ariel@nuvaus.com o revisar README.md
