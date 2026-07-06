# CLAUDE.md — nuvaus-automation

## Protocolo de memoria (obligatorio en toda sesión)

Existe UNA fuente canónica de memoria. Toda sesión de Claude (Claude.ai, Claude
Desktop, Claude Code local o web, Jarvis) debe leerla al inicio y escribir en
ella en tiempo real. No crear memorias paralelas (archivos sueltos, notas
locales, resúmenes duplicados).

### Fuente canónica por orden de precedencia

1. **jarvis-memoria MCP** — DESPLEGADO en vps-hub (06-jul-2026): systemd
   `jarvis-memoria.service`, escucha en `10.0.1.1:8931`, auth por
   `JARVIS_MEMORY_MCP_TOKEN` (solo en `.secrets`). Herramientas: `buscar`,
   `recordar`, `guardar`, `actualizar`, `bitacora`. Es la memoria unificada de
   Jarvis F4 (ticket NV-NUV-0222; diseño en `docs/NV-NUV-0222-F1-diseno.md`,
   rama `claude/jarvis-f4-memory-mcp-iet824`).
   - URL pública `https://memoria.nuvaus.com/mcp` — activa cuando exista el
     registro A en Porkbun (`memoria → 5.78.107.39`). Declarado en `.mcp.json`
     de este repo (requiere `JARVIS_MEMORY_MCP_TOKEN` en el entorno).
   - Conector claude.ai: URL `https://memoria.nuvaus.com/mcp/<token>`.
   - Acceso alternativo desde entornos con tailnet: SSH a `jarvis@vps-hub` y
     llamar a `http://10.0.1.1:8931/mcp/<token>` (token en `.secrets` del VPS).
   - Al iniciar sesión con este MCP disponible: llamar `recordar()` primero.
   - Pendiente para cierre total: migración de las 3 capas desde el Mac
     (`/home/jarvis/jarvis-memoria/migrar/migrar.py`) y conexión de clientes.
2. **Notion (vigente hoy)** — mientras jarvis-memoria no esté en producción:
   - **DB "Pendientes Claude"**: registro operativo de tareas, decisiones y
     resultados de todas las sesiones.
     - Database: `48b0a720-b74d-8303-b37c-8196ef82e6af`
     - Data source: `collection://4890a720-b74d-82eb-bd3b-072280642832`
   - **Página "Memoria Claude.ai — Historial de chats"**: síntesis de contexto
     personal y de proyectos.
     - Page ID: `3950a720-b74d-810b-af3c-f904ef9963ee`

### Reglas de operación

- **Al iniciar sesión**: leer la página de Memoria vía Notion MCP y consultar
  la DB "Pendientes Claude" para el contexto del tema en curso. Buscar SIEMPRE
  en ambas antes de declarar que algo no existe o no se ha hecho.
- **Durante la sesión**: toda decisión, resultado o dato durable se escribe de
  inmediato en la fuente canónica (no al final, no "después").
- **Correcciones del usuario**: si Ariel corrige un dato de la memoria, la
  corrección se aplica en Notion en el momento.
- **Secretos**: nunca en la memoria ni versionados. Solo en `.secrets`
  (Mac: `~/.claude/.secrets`; VPS: `/home/jarvis/.claude/.secrets`) o en
  variables de entorno del entorno remoto.

## Preferencias del usuario

- Responder en español latinoamericano neutro, sin chilenismos.
- Conciso y práctico.

## Herramientas de acceso a sitios con bloqueo anti-bot

Para precios/scraping (Mercado Libre, SoloTodo, Falabella, etc.):

- **Firecrawl MCP** — instalado en el Mac (key en `.secrets`, plan free
  500 páginas/mes). En este repo queda declarado en `.mcp.json`: se activa
  automáticamente donde exista `FIRECRAWL_API_KEY` en el entorno.
- **Playwright MCP** — instalado en el Mac (bootstrap-mac-extras.sh).
- Complementos según plan de MCPs: Exa (pendiente, falta `EXA_API_KEY`),
  Apify (Tier 3, solo si Firecrawl no alcanza).
- En el entorno remoto de Claude Code web estos dominios requieren permitirse
  en la política de red del entorno (hoy bloqueados por defecto).
