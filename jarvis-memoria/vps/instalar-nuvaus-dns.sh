#!/usr/bin/env bash
# Instala nuvaus-dns en vps-hub + sudoers para jarvis (correr como root en el VPS).
# Prerequisito: /etc/nuvaus/dns.env poblado por Ariel (ver README).
set -euo pipefail
AQUI="$(cd "$(dirname "$0")" && pwd)"
install -o root -g root -m 755 "$AQUI/nuvaus-dns" /usr/local/bin/nuvaus-dns
printf 'jarvis ALL=(root) NOPASSWD: /usr/local/bin/nuvaus-dns\n' > /etc/sudoers.d/nuvaus-dns
chmod 440 /etc/sudoers.d/nuvaus-dns
visudo -cf /etc/sudoers.d/nuvaus-dns
echo "instalado: jarvis puede ejecutar 'sudo nuvaus-dns ...' sin ver las llaves"
