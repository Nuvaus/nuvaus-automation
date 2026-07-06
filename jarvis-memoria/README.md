# jarvis-memoria — MCP de memoria unificada (NV-NUV-0222)

Servidor MCP remoto que unifica las 3 capas de memoria (archivos/wiki, agentmemory,
bitácora) para que claude.ai (conector personalizado), Claude Code y jarvis-listener
compartan la misma memoria. Diseño completo: `docs/NV-NUV-0222-F1-diseno.md`.

## Componentes

- `server.py` / `db.py` — servidor MCP (HTTP streamable, `/mcp`) + SQLite WAL/FTS5.
- `systemd/` — `jarvis-memoria.service` + backup diario (`.timer`, retención 14 días).
- `traefik/memoria.yaml` — HTTPS `memoria.nuvaus.com` vía proxy Coolify (Traefik).
- `deploy-vps.sh` — despliegue idempotente a vps-hub vía Tailscale SSH.
- `migrar/migrar.py` — migración idempotente de las 3 capas (corre en el Mac).

## Herramientas MCP

`buscar`, `recordar`, `guardar`, `actualizar`, `bitacora` (+ `importar` para migración).

## Autenticación

Token `JARVIS_MEMORY_MCP_TOKEN` (hex 64) en `/home/jarvis/.claude/.secrets` — se
genera en el primer deploy y **nunca** se versiona ni se imprime.

- Header: `Authorization: Bearer <token>` (Claude Code, scripts, jarvis-listener).
- Ruta: `https://memoria.nuvaus.com/mcp/<token>` (conector personalizado claude.ai).
- `/salud` sin auth (solo estado, para Uptime Kuma / vigía).

## Operación

```bash
systemctl status|restart jarvis-memoria     # en vps-hub
journalctl -u jarvis-memoria -f
```

Rotación de token: generar hex 64 nuevo → reemplazar en `.secrets` → `systemctl
restart jarvis-memoria` → actualizar los clientes (Claude Code, claude.ai, listener).

## Requisitos previos del deploy

1. Registro DNS A: `memoria.nuvaus.com → 5.78.107.39` (Porkbun).
2. Nodo con Tailscale SSH hacia vps-hub (jarvis y root).
