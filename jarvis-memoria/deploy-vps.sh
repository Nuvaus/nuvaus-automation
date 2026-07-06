#!/usr/bin/env bash
# Despliegue de jarvis-memoria en vps-hub via Tailscale SSH (NV-NUV-0222).
# Idempotente: se puede re-ejecutar para actualizar código sin perder datos.
# Requiere: nodo en el tailnet con acceso SSH a vps-hub (jarvis y root).
set -euo pipefail

VPS=vps-hub
DIR_REMOTO=/home/jarvis/jarvis-memoria
AQUI="$(cd "$(dirname "$0")" && pwd)"

tssh() { tailscale ssh "$1@$VPS" "$2"; }

echo "[1/7] Copiando código a $VPS:$DIR_REMOTO"
tssh jarvis "mkdir -p $DIR_REMOTO"
tar -C "$AQUI" -czf - server.py db.py requirements.txt migrar |
  tailscale ssh jarvis@$VPS "tar -C $DIR_REMOTO -xzf -"

echo "[2/7] Creando venv e instalando dependencias"
tssh jarvis "cd $DIR_REMOTO && python3 -m venv venv && venv/bin/pip install -q --upgrade pip && venv/bin/pip install -q -r requirements.txt"

echo "[3/7] Token: generar si no existe (nunca se imprime)"
tssh jarvis 'grep -q "^JARVIS_MEMORY_MCP_TOKEN=" ~/.claude/.secrets || printf "JARVIS_MEMORY_MCP_TOKEN=%s\n" "$(head -c32 /dev/urandom | xxd -p -c64)" >> ~/.claude/.secrets'

echo "[4/7] Instalando unidades systemd"
tar -C "$AQUI/systemd" -czf - . | tailscale ssh root@$VPS "tar -C /etc/systemd/system -xzf -"
tssh root "systemctl daemon-reload && systemctl enable --now jarvis-memoria.service jarvis-memoria-backup.timer"

echo "[5/7] Configurando Traefik (Coolify) para memoria.nuvaus.com"
cat "$AQUI/traefik/memoria.yaml" | tailscale ssh root@$VPS "cat > /data/coolify/proxy/dynamic/memoria.yaml"
# Traefik vigila el directorio dinámico: recarga sola, sin reiniciar el proxy.

echo "[6/7] Verificando servicio local"
sleep 2
tssh jarvis "systemctl is-active jarvis-memoria && curl -sS http://10.0.1.1:8931/salud"

echo
echo "[7/7] Verificación pública (requiere DNS memoria.nuvaus.com -> 5.78.107.39)"
tssh jarvis "curl -sS --max-time 15 https://memoria.nuvaus.com/salud || echo 'AUN SIN DNS/CERT — reintentar tras crear el registro A'"
echo
echo "Listo. Operación: systemctl {status|restart} jarvis-memoria · journalctl -u jarvis-memoria -f"
