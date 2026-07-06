# NV-NUV-0222 · Jarvis F4 — Memoria unificada · FASE 1: Diseño

**Fecha**: 2026-07-06 · **Estado**: propuesta para aprobación de Ariel antes de implementar/desplegar.

## Objetivo

Un servidor MCP remoto de memoria ("jarvis-memoria") en vps-hub, para que claude.ai (conector personalizado, incluida la app móvil), Claude Code y jarvis-listener lean y escriban **la misma memoria**, unificando las 3 capas actuales (archivos/wiki, agentmemory, bitácora).

## Arquitectura

```
claude.ai (móvil/web) ─┐
Claude Code ───────────┼─ HTTPS ─→ memoria.nuvaus.com (Coolify/Traefik, TLS)
scripts de migración ──┘              │ proxy → 127.0.0.1:8931
                                      ▼
                          jarvis-memoria.service (systemd, usuario jarvis)
                          Python + SDK MCP oficial (FastMCP, HTTP streamable)
                                      │
                                      ▼
                          SQLite WAL + FTS5: /home/jarvis/jarvis-memoria/memoria.db
jarvis-listener (mismo VPS) ── http://127.0.0.1:8931 (sin salir a internet)
```

- **Servicio**: `jarvis-memoria.service`, patrón idéntico a `jarvis-listener.service` (usuario `jarvis`, `Restart=always`, `EnvironmentFile=/home/jarvis/.claude/.secrets`).
- **Transporte**: MCP HTTP streamable en `/mcp`, bind solo a `127.0.0.1:8931`; Coolify termina TLS en `memoria.nuvaus.com` y hace proxy al puerto local. Sin nginx/caddy manual.
- **Backend**: SQLite en modo WAL + FTS5. Un solo archivo, respaldable: backups automáticos de Hetzner + timer systemd diario con `sqlite3 .backup` (retención 14 días en `/home/jarvis/jarvis-memoria/backups/`).

## Autenticación

- Token `JARVIS_MEMORY_MCP_TOKEN` (hex de 64, mismo patrón que `NUVAUS_KNOWLEDGE_MCP_TOKEN` ya operado y rotado en NV-NUV-0184).
- Vive solo en `.secrets` (VPS) y en los clientes; **nunca versionado**.
- El servidor acepta dos formas equivalentes:
  1. Header `Authorization: Bearer <token>` (Claude Code, scripts, jarvis-listener).
  2. Segmento de ruta `https://memoria.nuvaus.com/mcp/<token>` — necesario porque el conector personalizado de claude.ai no permite headers custom; la URL actúa como capability secreta.
- Requests sin token válido → 401 sin detalle. Rotación trimestral (procedimiento en FASE 4).

## Esquema de datos (unifica las 3 capas)

```sql
CREATE TABLE memoria (
  id             INTEGER PRIMARY KEY,
  tipo           TEXT NOT NULL CHECK (tipo IN ('nota','hecho','preferencia','decision','bitacora')),
  origen         TEXT NOT NULL,   -- wiki | voz-claude | agentmemory | agent_log | jarvis | claude-code | claude-app | migracion
  agente         TEXT,            -- jarvis | ariel | licitaciones-watcher | ...
  proyecto       TEXT,
  titulo         TEXT,
  contenido      TEXT NOT NULL,
  etiquetas      TEXT,            -- separadas por coma
  evento         TEXT,            -- solo tipo='bitacora': run|avance|bug|mejora|blocker
  creado_en      TEXT NOT NULL DEFAULT (datetime('now')),
  actualizado_en TEXT,
  reemplazada_por INTEGER REFERENCES memoria(id),
  activo         INTEGER NOT NULL DEFAULT 1,
  meta           TEXT             -- JSON libre (checksum de migración, ruta original, etc.)
);
CREATE VIRTUAL TABLE memoria_fts USING fts5(titulo, contenido, etiquetas,
  content='memoria', content_rowid='id');
```

Mapeo de capas: **archivos/wiki y voz-claude** → `tipo='nota'`; **agentmemory** → `hecho`/`preferencia`; **agent_log.py** → `tipo='bitacora'` + `evento`. Las actualizaciones nunca destruyen: se crea versión nueva y la anterior queda `reemplazada_por` (historia auditable).

**RAG Fase B (del ticket)**: fuera del MVP. El esquema lo soporta después agregando tabla `embeddings` (sqlite-vec) sin migrar nada.

## Herramientas MCP expuestas

| Herramienta | Firma | Comportamiento |
|---|---|---|
| `buscar` | `(consulta, tipo?, proyecto?, limite=10)` | FTS5 con ranking bm25 + boost por recencia; devuelve id, título, extracto, tipo, origen, fecha |
| `recordar` | `(tema?, proyecto?, limite=20)` | Paquete de contexto para arrancar sesión: preferencias y hechos activos relevantes + últimas decisiones + bitácora reciente |
| `guardar` | `(contenido, tipo='nota', titulo?, etiquetas?, proyecto?, agente?)` | Alta de memoria; devuelve id |
| `actualizar` | `(id, contenido?, etiquetas?, activo?)` | Versiona (marca la anterior como reemplazada); `activo=false` = olvido suave |
| `bitacora` | `(evento, agente, detalle?, proyecto?)` | Append de evento; `evento='reporte'` devuelve resumen día/semana (paridad con `agent_log.py --report`) |

## Migración (FASE 2)

Scripts idempotentes (marca `origen='migracion'` + checksum en `meta` — re-ejecutables sin duplicar), que corren desde donde están los datos (el Mac, alcanzable vía tailnet):

1. `migrar_wiki.py` — markdown seleccionado de `~/Nuvaus/wiki` (specs + knowledge) → notas.
2. `migrar_agentmemory.py` — export de la colección `nuvaus` de AgentMemory → hechos/preferencias.
3. `migrar_bitacora.py` — feed de `agent_log.py` → eventos bitácora.

## Conexión de clientes (FASE 3)

- **Claude Code**: `claude mcp add --transport http jarvis-memoria https://memoria.nuvaus.com/mcp --header "Authorization: Bearer $JARVIS_MEMORY_MCP_TOKEN"`.
- **claude.ai / app móvil**: Ajustes → Conectores → "Agregar conector personalizado" → URL `https://memoria.nuvaus.com/mcp/<token>`.
- **jarvis-listener**: cliente HTTP a `127.0.0.1:8931` con el mismo token (tráfico local, cero latencia extra). Su lógica de memoria actual se redirige a `recordar`/`guardar`/`bitacora`.

## Operación (FASE 4)

- Restart: `systemctl restart jarvis-memoria` · Logs: `journalctl -u jarvis-memoria -f`.
- Backup: timer diario + backups Hetzner; restore = copiar `.db` y reiniciar.
- Rotación de token: generar hex 64 → actualizar `.secrets` → restart → actualizar 3 clientes (procedimiento heredado de NV-NUV-0184).
- Health-check: endpoint `/salud` (sin auth, solo estado) integrable al vigía jarvis-proactivo / Uptime Kuma.

## Despliegue

Vía git (este repo, carpeta `jarvis-memoria/`) + script `deploy-vps.sh` — corrige de paso el riesgo documentado del deploy manual por scp (incidente 15-jun). Puerto 8931 a confirmar libre durante FASE 2.
