"""jarvis-memoria — servidor MCP de memoria unificada (Nuvaus, NV-NUV-0222).

Transporte: MCP HTTP streamable en /mcp.
Auth: Authorization: Bearer <token>  o  token embebido en la ruta /mcp/<token>
(este último para el conector personalizado de claude.ai, que no permite headers).
El token vive en la variable de entorno JARVIS_MEMORY_MCP_TOKEN (via .secrets).
"""
import os
import secrets as _secrets
import sys

import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.responses import JSONResponse

import db

TOKEN = os.environ.get("JARVIS_MEMORY_MCP_TOKEN", "")
HOST = os.environ.get("JARVIS_MEMORIA_HOST", "127.0.0.1")
PORT = int(os.environ.get("JARVIS_MEMORIA_PORT", "8931"))

mcp = FastMCP(
    "jarvis-memoria",
    instructions=(
        "Memoria unificada de Ariel/Nuvaus (Jarvis F4). Usa `recordar` al iniciar una sesión "
        "para cargar contexto, `buscar` para consultas puntuales, `guardar` para nueva información "
        "duradera (hechos, preferencias, decisiones, notas), `actualizar` para corregir, y "
        "`bitacora` para registrar eventos de agentes. Responde y guarda en español neutro."
    ),
    host=HOST,
    port=PORT,
    streamable_http_path="/mcp",
    stateless_http=True,
    json_response=True,
)


@mcp.tool()
def buscar(consulta: str, tipo: str | None = None, proyecto: str | None = None, limite: int = 10) -> dict:
    """Busca en la memoria unificada (texto completo FTS5 + recencia).

    tipo: nota | hecho | preferencia | decision | bitacora (opcional).
    proyecto: filtra por proyecto (opcional). limite: máximo de resultados (1-50).
    """
    return {"resultados": db.buscar(consulta, tipo=tipo, proyecto=proyecto, limite=limite)}


@mcp.tool()
def recordar(tema: str | None = None, proyecto: str | None = None, limite: int = 20) -> dict:
    """Carga un paquete de contexto para arrancar sesión: preferencias, hechos y
    decisiones activas (relevantes a `tema` si se entrega) más la bitácora reciente."""
    return db.recordar(tema=tema, proyecto=proyecto, limite=limite)


@mcp.tool()
def guardar(
    contenido: str,
    tipo: str = "nota",
    titulo: str | None = None,
    etiquetas: str | None = None,
    proyecto: str | None = None,
    agente: str | None = None,
) -> dict:
    """Guarda una memoria nueva. tipo: nota | hecho | preferencia | decision.
    etiquetas separadas por coma. Devuelve el id asignado."""
    if tipo == "bitacora":
        raise ValueError("para eventos de bitácora usa la herramienta `bitacora`")
    return db.guardar(contenido, tipo=tipo, titulo=titulo, etiquetas=etiquetas,
                      proyecto=proyecto, agente=agente)


@mcp.tool()
def actualizar(id: int, contenido: str | None = None, etiquetas: str | None = None,
               activo: bool | None = None) -> dict:
    """Actualiza una memoria: crea versión nueva y conserva la anterior enlazada
    (nunca destruye). Con activo=false la desactiva (olvido suave)."""
    return db.actualizar(id, contenido=contenido, etiquetas=etiquetas, activo=activo)


@mcp.tool()
def bitacora(evento: str, agente: str, detalle: str = "", proyecto: str | None = None,
             dias: int = 1) -> dict:
    """Registra un evento en la bitácora unificada de agentes.

    evento: run | avance | bug | mejora | blocker — registra el evento.
    evento: reporte — devuelve el resumen de los últimos `dias` días (paridad agent_log.py --report).
    """
    if evento == "reporte":
        return db.bitacora_reporte(dias=dias)
    res = db.guardar(detalle or evento, tipo="bitacora", agente=agente,
                     proyecto=proyecto, evento=evento)
    return {"id": res["id"], "evento": evento, "agente": agente}


@mcp.tool()
def importar(items: list[dict]) -> dict:
    """Importa memorias en lote (uso: migración). Cada item: {contenido, tipo, titulo?,
    etiquetas?, proyecto?, agente?, evento?, origen?, meta?}. Si meta.checksum ya existe
    para ese origen, el item se salta (idempotente). Devuelve conteos."""
    nuevos, duplicados, errores = 0, 0, []
    for i, it in enumerate(items):
        try:
            res = db.guardar(
                it["contenido"], tipo=it.get("tipo", "nota"), titulo=it.get("titulo"),
                etiquetas=it.get("etiquetas"), proyecto=it.get("proyecto"),
                agente=it.get("agente"), evento=it.get("evento"),
                origen=it.get("origen", "migracion"), meta=it.get("meta"),
            )
            duplicados += 1 if res.get("duplicado") else 0
            nuevos += 0 if res.get("duplicado") else 1
        except Exception as e:  # noqa: BLE001 — reportar item fallido sin abortar el lote
            errores.append({"indice": i, "error": str(e)})
    return {"nuevos": nuevos, "duplicados": duplicados, "errores": errores}


async def salud(request):  # noqa: ARG001
    con = db.conectar()
    try:
        n = con.execute("SELECT COUNT(*) FROM memoria").fetchone()[0]
    finally:
        con.close()
    return JSONResponse({"estado": "ok", "memorias": n})


class AuthPorTokenASGI:
    """Middleware ASGI puro: exige Bearer token o token embebido en la ruta.

    /salud queda libre (solo estado, sin datos). Todo lo demás: 401 sin detalle.
    """

    def __init__(self, app, token: str):
        self.app = app
        self.token = token

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        path = scope.get("path", "")
        if path == "/salud":
            return await self.app(scope, receive, send)

        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        auth = headers.get("authorization", "")
        if auth.startswith("Bearer ") and _secrets.compare_digest(auth[7:], self.token):
            return await self.app(scope, receive, send)

        prefijo = f"/mcp/{self.token}"
        if path == prefijo or path.startswith(prefijo + "/"):
            resto = path[len(prefijo):] or ""
            scope = dict(scope)
            scope["path"] = "/mcp" + resto
            scope["raw_path"] = scope["path"].encode()
            return await self.app(scope, receive, send)

        respuesta = JSONResponse({"error": "no autorizado"}, status_code=401)
        return await respuesta(scope, receive, send)


def crear_app():
    app = mcp.streamable_http_app()
    from starlette.routing import Route
    app.router.routes.append(Route("/salud", salud))
    return AuthPorTokenASGI(app, TOKEN)


if __name__ == "__main__":
    if not TOKEN or len(TOKEN) < 32:
        print("ERROR: define JARVIS_MEMORY_MCP_TOKEN (>=32 chars) en el entorno/.secrets", file=sys.stderr)
        sys.exit(1)
    print(f"jarvis-memoria escuchando en {HOST}:{PORT} (db: {db.DB_PATH})")
    uvicorn.run(crear_app(), host=HOST, port=PORT, log_level="info")
