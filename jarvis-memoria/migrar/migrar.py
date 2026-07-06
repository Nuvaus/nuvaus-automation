#!/usr/bin/env python3
"""Migración de las 3 capas de memoria a jarvis-memoria (NV-NUV-0222).

Corre en la máquina donde viven los datos (el Mac). Idempotente: usa checksum
por item, re-ejecutar no duplica. Solo stdlib (chromadb opcional para agentmemory).

Uso:
  export JARVIS_MEMORY_MCP_TOKEN=...   # mismo token del servidor
  python3 migrar.py wiki --dir ~/Nuvaus/wiki/01-projects/nuvaus/specs --dir ~/Nuvaus/wiki/03-knowledge
  python3 migrar.py bitacora --file ~/ruta/al/feed-agent-log.jsonl
  python3 migrar.py agentmemory --dir ~/ruta/persistencia-chroma
Opcional: --url https://memoria.nuvaus.com/mcp (default)
"""
import argparse
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

URL_DEFAULT = "https://memoria.nuvaus.com/mcp"


def llamar(url: str, token: str, herramienta: str, argumentos: dict) -> dict:
    cuerpo = json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": herramienta, "arguments": argumentos},
    }).encode()
    req = urllib.request.Request(url, data=cuerpo, headers={
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Authorization": f"Bearer {token}",
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        datos = json.loads(r.read().decode())
    if "error" in datos:
        raise RuntimeError(datos["error"])
    contenido = datos["result"]["content"][0]["text"]
    return json.loads(contenido)


def importar_lotes(url: str, token: str, items: list[dict], lote: int = 50) -> None:
    total = {"nuevos": 0, "duplicados": 0, "errores": []}
    for i in range(0, len(items), lote):
        res = llamar(url, token, "importar", {"items": items[i:i + lote]})
        total["nuevos"] += res["nuevos"]
        total["duplicados"] += res["duplicados"]
        total["errores"].extend(res["errores"])
        print(f"  lote {i // lote + 1}: +{res['nuevos']} nuevos, {res['duplicados']} duplicados")
    print(f"TOTAL: {total['nuevos']} nuevos, {total['duplicados']} duplicados, {len(total['errores'])} errores")
    if total["errores"]:
        print(json.dumps(total["errores"][:5], ensure_ascii=False, indent=2))


def _checksum(texto: str) -> str:
    return hashlib.sha256(texto.encode()).hexdigest()


def migrar_wiki(dirs: list[str]) -> list[dict]:
    items = []
    for d in dirs:
        base = Path(d).expanduser()
        for md in sorted(base.rglob("*.md")):
            texto = md.read_text(encoding="utf-8", errors="replace").strip()
            if not texto:
                continue
            items.append({
                "contenido": texto[:20000], "tipo": "nota", "origen": "wiki",
                "titulo": str(md.relative_to(base)),
                "meta": {"checksum": _checksum(texto), "ruta": str(md)},
            })
    print(f"wiki: {len(items)} notas encontradas")
    return items


def migrar_bitacora(archivo: str) -> list[dict]:
    """Feed de agent_log.py: se asume una entrada por línea (JSONL o texto)."""
    items = []
    for linea in Path(archivo).expanduser().read_text(encoding="utf-8", errors="replace").splitlines():
        linea = linea.strip()
        if not linea:
            continue
        try:
            e = json.loads(linea)
            evento = e.get("evento") or e.get("event") or e.get("tipo") or "run"
            agente = e.get("agente") or e.get("agent") or "desconocido"
            detalle = e.get("detalle") or e.get("msg") or e.get("mensaje") or json.dumps(e, ensure_ascii=False)
            proyecto = e.get("proyecto") or e.get("project")
        except json.JSONDecodeError:
            evento, agente, detalle, proyecto = "run", "desconocido", linea, None
        if evento not in ("run", "avance", "bug", "mejora", "blocker"):
            evento = "run"
        items.append({
            "contenido": detalle, "tipo": "bitacora", "evento": evento, "agente": agente,
            "proyecto": proyecto, "origen": "agent_log",
            "meta": {"checksum": _checksum(linea)},
        })
    print(f"bitacora: {len(items)} eventos encontrados")
    return items


def migrar_agentmemory(dir_persistencia: str) -> list[dict]:
    try:
        import chromadb  # instalado junto a agentmemory
    except ImportError:
        sys.exit("chromadb no disponible: pip install chromadb, o exporta agentmemory a JSONL y usa `bitacora --file`")
    cliente = chromadb.PersistentClient(path=str(Path(dir_persistencia).expanduser()))
    items = []
    for col in cliente.list_collections():
        datos = cliente.get_collection(col.name).get(include=["documents", "metadatas"])
        for doc, meta in zip(datos["documents"], datos["metadatas"]):
            if not doc:
                continue
            items.append({
                "contenido": doc, "tipo": "hecho", "origen": "agentmemory",
                "etiquetas": (meta or {}).get("category"),
                "meta": {"checksum": _checksum(doc), "coleccion": col.name, **(meta or {})},
            })
    print(f"agentmemory: {len(items)} memorias encontradas")
    return items


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("capa", choices=["wiki", "bitacora", "agentmemory"])
    p.add_argument("--dir", action="append", default=[], help="directorio fuente (repetible)")
    p.add_argument("--file", help="archivo fuente (bitacora)")
    p.add_argument("--url", default=URL_DEFAULT)
    args = p.parse_args()

    token = os.environ.get("JARVIS_MEMORY_MCP_TOKEN", "")
    if not token:
        sys.exit("define JARVIS_MEMORY_MCP_TOKEN en el entorno")

    if args.capa == "wiki":
        items = migrar_wiki(args.dir or ["~/Nuvaus/wiki/01-projects/nuvaus/specs", "~/Nuvaus/wiki/03-knowledge"])
    elif args.capa == "bitacora":
        if not args.file:
            sys.exit("bitacora requiere --file <feed de agent_log>")
        items = migrar_bitacora(args.file)
    else:
        if not args.dir:
            sys.exit("agentmemory requiere --dir <persistencia chroma>")
        items = migrar_agentmemory(args.dir[0])

    if items:
        importar_lotes(args.url, token, items)


if __name__ == "__main__":
    main()
