#!/usr/bin/env python3
# ===================================================================
# NOTION SYNC — Sincronización con bases de datos Notion
# ===================================================================
# Crea entradas de Interacción cuando se mueve una propuesta/contrato.
# Lee NOTION_API_KEY desde ~/.claude/.secrets.
# Módulo importable por file-manager.py (o ejecutable directo para test).
#
# Cross-platform (macOS / Linux). Solo stdlib (Python 3.8+).
# Versión: 1.0 | Autor: Ariel Meneses | GitHub: nuvaus-automation
# ===================================================================

import json
import os
import re
import urllib.request

SECRETS_FILE = os.path.join(os.path.expanduser("~"), ".claude", ".secrets")

# Bases de datos Notion (mismos IDs que la versión PowerShell)
DB_INTERACCIONES = "896da7d5-0b9c-4f4e-ad4b-750cef851389"
DB_PROSPECTOS = "f0e2667c-9471-4b07-b4a4-a41d6567e595"
DB_CLIENTES = "80d8624f-2461-4208-ad92-897df3e60379"

NOTION_VERSION = "2022-06-28"
BASE_URL = "https://api.notion.com/v1"


def get_secret(key):
    """Lee KEY=valor desde ~/.claude/.secrets."""
    if not os.path.exists(SECRETS_FILE):
        return None
    with open(SECRETS_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    m = re.search(rf"^{re.escape(key)}=(.+)$", content, re.MULTILINE)
    return m.group(1).strip() if m else None


def _headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def notion_request(endpoint, method="GET", body=None, token=None, timeout=30):
    """Llamada genérica a la API de Notion. Devuelve (ok, data|error)."""
    token = token or get_secret("NOTION_API_KEY")
    if not token:
        return False, "NOTION_API_KEY no encontrada en .secrets"

    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        f"{BASE_URL}{endpoint}", data=data, method=method, headers=_headers(token)
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return True, json.loads(resp.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        return False, str(e)


def create_interaction(client_code, item_name, status="Enviada", logger=print):
    """Crea una entrada en la DB Interacciones para una propuesta/contrato."""
    body = {
        "parent": {"database_id": DB_INTERACCIONES},
        "properties": {
            "Tipo": {"select": {"name": "Propuesta"}},
            "Cliente": {"rich_text": [{"text": {"content": client_code or "UNKNOWN"}}]},
            "Resultado": {"rich_text": [{"text": {"content": status}}]},
            "Proximo paso": {"rich_text": [{"text": {"content": "Seguimiento en 7 días"}}]},
        },
    }
    ok, res = notion_request("/pages", method="POST", body=body)
    if ok:
        logger(f"Notion: interacción creada — {item_name} | Cliente: {client_code}")
    else:
        logger(f"Notion: fallo creando interacción — {res}")
    return ok


def sync_moved_file(moved, client, logger=print):
    """Llamado desde file-manager cuando una regla tiene notify_notion=true."""
    rule = moved.get("rule", {})
    if not rule.get("notify_notion"):
        return False
    status = {
        "propuestas": "Propuesta Enviada",
        "contratos": "Contrato Recibido",
    }.get(rule.get("id"), "Archivo Movido")
    client_code = client.get("code") if client else "UNKNOWN"
    return create_interaction(client_code, moved.get("new_name", ""), status, logger)


def test_connection(logger=print):
    """Verifica conectividad consultando la DB Interacciones."""
    ok, res = notion_request(f"/databases/{DB_INTERACCIONES}", method="GET")
    if ok:
        logger("Notion: conexión OK")
    else:
        logger(f"Notion: sin conexión — {res}")
    return ok


if __name__ == "__main__":
    # Ejecución directa: prueba de conexión
    test_connection()
