#!/usr/bin/env bash
# Despliegue de jarvis-whatsapp en vps-hub via Tailscale SSH (migracion Telegram -> WhatsApp).
# Idempotente: re-ejecutable para actualizar codigo sin perder estado.
# Requiere: nodo en el tailnet con acceso SSH a vps-hub (jarvis y root).
# Patron heredado de jarvis-memoria/deploy-vps.sh (NV-NUV-0222).
set -euo pipefail

VPS=vps-hub
SCRIPTS_REMOTO=/home/jarvis/repos/nuvaus/scripts
AQUI="$(cd "$(dirname "$0")" && pwd)"
TAILSCALE="${TAILSCALE_BIN:-tailscale}"

tssh() { "$TAILSCALE" ssh "$1@$VPS" "$2"; }

echo "[1/7] Copiando puente a $VPS:$SCRIPTS_REMOTO/jarvis-whatsapp.py"
"$TAILSCALE" ssh jarvis@$VPS "cat > $SCRIPTS_REMOTO/jarvis-whatsapp.py && chmod +x $SCRIPTS_REMOTO/jarvis-whatsapp.py" < "$AQUI/jarvis-whatsapp.py"

echo "[2/7] Verify token del webhook: generar si no existe (nunca se imprime)"
tssh jarvis 'grep -q "^WHATSAPP_VERIFY_TOKEN=" ~/.claude/.secrets || printf "WHATSAPP_VERIFY_TOKEN=%s\n" "$(head -c32 /dev/urandom | xxd -p -c64)" >> ~/.claude/.secrets'

echo "[3/7] DNS: registro A whatsapp.nuvaus.com -> 5.78.107.39 (API Porkbun, keys del VPS)"
tssh jarvis 'python3 - <<PYEOF
import json, urllib.request
sec = {}
for line in open("/home/jarvis/.claude/.secrets"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, _, v = line.partition("="); sec[k.strip()] = v.strip()
auth = {"apikey": sec["PORKBUN_API_KEY"], "secretapikey": sec["PORKBUN_SECRET_KEY"]}
def post(path, extra=None):
    data = json.dumps({**auth, **(extra or {})}).encode()
    req = urllib.request.Request("https://api.porkbun.com/api/json/v3/" + path,
                                 data=data, headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())
registros = post("dns/retrieve/nuvaus.com").get("records", [])
existe = [r for r in registros if r["name"] == "whatsapp.nuvaus.com" and r["type"] == "A"]
if existe:
    print("DNS: whatsapp.nuvaus.com ya existe ->", existe[0]["content"])
else:
    r = post("dns/create/nuvaus.com", {"type": "A", "name": "whatsapp",
                                        "content": "5.78.107.39", "ttl": "600"})
    print("DNS: creado whatsapp.nuvaus.com ->", r.get("status"))
PYEOF'

echo "[4/7] Instalando unidad systemd"
"$TAILSCALE" ssh root@$VPS "cat > /etc/systemd/system/jarvis-whatsapp.service" < "$AQUI/systemd/jarvis-whatsapp.service"
tssh root "systemctl daemon-reload && systemctl enable --now jarvis-whatsapp.service"

echo "[5/7] Firewall: permitir 8932 solo desde la red interna de Coolify"
tssh root 'ufw status | grep -q 8932 || ufw allow from 10.0.1.0/24 to any port 8932 proto tcp comment "jarvis-whatsapp via Traefik"'

echo "[6/7] Traefik (Coolify) para whatsapp.nuvaus.com"
"$TAILSCALE" ssh root@$VPS "cat > /data/coolify/proxy/dynamic/whatsapp.yaml" < "$AQUI/traefik/whatsapp.yaml"
# Traefik vigila el directorio dinamico: recarga sola, sin reiniciar el proxy.

echo "[7/7] Verificacion"
sleep 3
tssh jarvis "systemctl is-active jarvis-whatsapp && curl -sS http://10.0.1.1:8932/salud && echo"
echo
echo "Publica (puede tardar mientras emite el certificado):"
tssh jarvis "curl -sS --max-time 20 https://whatsapp.nuvaus.com/salud || echo 'AUN SIN CERT — si persiste, retirar y re-copiar whatsapp.yaml en dynamic/'"
echo
echo "Listo. Falta el lado Meta (ver README): token, phone_number_id, app secret,"
echo "wa_id permitido en .secrets y configurar el webhook en developers.facebook.com."
