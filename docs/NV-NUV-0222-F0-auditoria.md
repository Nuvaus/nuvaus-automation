# NV-NUV-0222 · Jarvis F4 — Memoria unificada · FASE 0: Auditoría

**Fecha**: 2026-07-06 · **Autor**: Claude Code (sesión remota, rama `claude/jarvis-f4-memory-mcp-iet824`)
**Alcance**: solo lectura. Fuentes: Notion (base "Pendientes Claude"), repo `nuvaus-automation`, pruebas de conectividad desde el entorno remoto.

---

## 1. Ticket NV-NUV-0222

- **Estado**: Pendiente · Prioridad Media · Proyecto "Asesor Personal" · Origen: chat Asesor F1.
- **Contexto del ticket**: "Una política para las 3 capas; Jarvis escritorio (voz-claude) lee/escribe las mismas. Evaluar RAG Fase B (embeddings) para nuvaus-knowledge."
- La página del ticket está en blanco (todo el contexto vive en propiedades de la BD).

## 2. Las 3 capas de memoria actuales

| Capa | Dónde vive | Formato / backend | Cómo se escribe |
|---|---|---|---|
| **Archivos** | Mac: `~/Nuvaus/wiki` (specs en `01-projects/nuvaus/specs/`, conocimiento en `03-knowledge/`) + `~/repos/voz-claude` (memoria curada + RAG sobre 317 sesiones / 1603 fragmentos, ticket NV-NUV-0205 "En progreso") | Markdown + índice RAG propio de voz-claude | Manual + scripts de voz-claude |
| **agentmemory** | Mac: Docker local, persistente vía launchd `com.nuvaus.agentmemory` | AgentMemory v0.9.24, `AGENT_ID=nuvaus`, scope isolated, embeddings locales (cero egress), bearer en loopback | MCP desde la Claude app (remember/recall validados en español) |
| **Bitácora** | Mac: `scripts/agent_log.py` — feed único de agentes | Eventos `run/avance/bug/mejora/blocker`, CLI `--report` | Invocado por agentes (wired en licitaciones-watcher); panel web pendiente (Supabase) |

**Dato clave para la migración**: las 3 capas viven en el Mac, no en el VPS. La migración de datos (FASE 2) tendrá que ejecutarse desde el Mac o subir dumps al VPS.

## 3. Configuración MCP actual

- `claude_desktop_config.json` / `~/.claude` del Mac **no son accesibles desde este entorno remoto** (esta sesión corre en un contenedor aislado con solo el repo clonado).
- Lo que consta en Notion:
  - **agentmemory MCP** conectado a la Claude app (local, loopback).
  - **DevFleet MCP** registrado user-scope.
  - **Ya existe un MCP remoto propio**: `nuvaus-knowledge` servido desde nuvaus.com (Vercel), autenticado con `NUVAUS_KNOWLEDGE_MCP_TOKEN` (hex 64, rotado el 24-jun, NV-NUV-0184). Es el patrón de referencia para el token del MCP de memoria.
- Antecedente de seguridad (NV-NUV-0184): 6 keys estuvieron hardcodeadas en `mcp_config.json`/`settings.json` y se rotaron. Regla vigente: secretos solo en `.secrets` (Mac: `~/.claude/.secrets`; VPS: `/home/jarvis/.claude/.secrets`), nunca versionados.

## 4. Estado del VPS (desde documentación; sin verificación en vivo)

- **vps-hub**: Hetzner CCX23 Hillsboro (Oregon), 4 vCPU / 16 GB / 160 GB NVMe, IPv4 `5.78.107.39`, USD 48/mes con backups automáticos de Hetzner. Server ID 133471305.
- **Corre hoy**: Coolify (panel.nuvaus.com), n8n, Vaultwarden, Uptime Kuma, Dify self-hosted + Postgres, gateway LiteLLM (Hermes en contenedor aislado), `jarvis-listener.service` (systemd, usuario `jarvis`), vigía `jarvis-proactivo.py` (timer 15 min).
- **Reverse proxy / HTTPS**: Coolify ya termina TLS para subdominios `*.nuvaus.com` → hay camino directo para exponer el MCP por HTTPS sin instalar nginx/caddy a mano.
- **Riesgo conocido** (ticket "Robustecer deploy", Pendiente): `/home/jarvis/repos/nuvaus` en el VPS **no es git** — es copia manual vía scp, y ya causó un incidente (deps no copiadas, 15-jun). F4 debería desplegarse vía git o script `deploy-vps.sh`, no scp suelto.
- Recursos: sobra capacidad para un MCP de memoria con SQLite (el CCX23 va holgado).

## 5. Bloqueos de acceso detectados (verificados hoy)

1. **Sin SSH desde este entorno**: no hay llaves en `~/.ssh` y la política de red bloquea TCP/22 hacia `5.78.107.39`.
2. **Sin HTTPS hacia nuvaus.com** desde este entorno: el proxy de salida responde 403 (dominio no permitido en la política de red de la sesión).
3. **El historial del chat de claude.ai no es accesible** desde Claude Code — no existe conector para leer conversaciones. El contexto se reconstruyó desde Notion.

**Implicancia**: FASES 2 y 3 (despliegue, migración, prueba E2E) no pueden ejecutarse desde esta sesión tal como está. Opciones: (a) ejecutar el despliegue desde Claude Code local en el Mac (tiene SSH al VPS y acceso a los datos a migrar), o (b) agregar a este entorno remoto una llave SSH como secreto + permitir el dominio/puerto en la política de red. Lo que sí puede hacerse 100% desde aquí: FASE 1 (diseño) y toda la implementación (código del servidor, unit systemd, scripts de deploy y migración) versionada en esta rama.

## 6. Insumos para FASE 1 (diseño)

- Transporte HTTP streamable + token bearer estilo `NUVAUS_KNOWLEDGE_MCP_TOKEN` (patrón ya operado y rotado con éxito).
- Backend SQLite (+FTS5 para búsqueda) en `/home/jarvis`: respaldable por los backups automáticos de Hetzner + dump periódico.
- Exponer vía Coolify en un subdominio (p. ej. `memoria.nuvaus.com`), servicio systemd usuario `jarvis` (patrón jarvis-listener).
- Esquema debe unificar: notas/archivos curados (capa 1), memorias semánticas de agentmemory (capa 2) y eventos de bitácora (capa 3), con origen (`source`) y agente (`agent_id`) por registro.
- El ticket pide además evaluar RAG Fase B (embeddings) para nuvaus-knowledge — se propone dejarlo fuera del MVP de F4 y diseñar el esquema para soportarlo después.
