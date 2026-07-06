"""Capa de datos de jarvis-memoria: SQLite WAL + FTS5."""
import json
import os
import sqlite3

DB_PATH = os.environ.get("JARVIS_MEMORIA_DB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "memoria.db"))

TIPOS = ("nota", "hecho", "preferencia", "decision", "bitacora")
EVENTOS = ("run", "avance", "bug", "mejora", "blocker")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS memoria (
  id             INTEGER PRIMARY KEY,
  tipo           TEXT NOT NULL CHECK (tipo IN ('nota','hecho','preferencia','decision','bitacora')),
  origen         TEXT NOT NULL DEFAULT 'mcp',
  agente         TEXT,
  proyecto       TEXT,
  titulo         TEXT,
  contenido      TEXT NOT NULL,
  etiquetas      TEXT,
  evento         TEXT,
  creado_en      TEXT NOT NULL DEFAULT (datetime('now')),
  actualizado_en TEXT,
  reemplazada_por INTEGER REFERENCES memoria(id),
  activo         INTEGER NOT NULL DEFAULT 1,
  meta           TEXT
);
CREATE INDEX IF NOT EXISTS idx_memoria_tipo ON memoria(tipo, activo);
CREATE INDEX IF NOT EXISTS idx_memoria_proyecto ON memoria(proyecto);
CREATE INDEX IF NOT EXISTS idx_memoria_creado ON memoria(creado_en);

CREATE VIRTUAL TABLE IF NOT EXISTS memoria_fts USING fts5(
  titulo, contenido, etiquetas, content='memoria', content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS memoria_ai AFTER INSERT ON memoria BEGIN
  INSERT INTO memoria_fts(rowid, titulo, contenido, etiquetas)
  VALUES (new.id, new.titulo, new.contenido, new.etiquetas);
END;
CREATE TRIGGER IF NOT EXISTS memoria_ad AFTER DELETE ON memoria BEGIN
  INSERT INTO memoria_fts(memoria_fts, rowid, titulo, contenido, etiquetas)
  VALUES ('delete', old.id, old.titulo, old.contenido, old.etiquetas);
END;
CREATE TRIGGER IF NOT EXISTS memoria_au AFTER UPDATE ON memoria BEGIN
  INSERT INTO memoria_fts(memoria_fts, rowid, titulo, contenido, etiquetas)
  VALUES ('delete', old.id, old.titulo, old.contenido, old.etiquetas);
  INSERT INTO memoria_fts(rowid, titulo, contenido, etiquetas)
  VALUES (new.id, new.titulo, new.contenido, new.etiquetas);
END;
"""


def conectar() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    con.executescript(_SCHEMA)
    return con


def _fila_a_dict(fila: sqlite3.Row, extracto: bool = False) -> dict:
    d = {k: fila[k] for k in fila.keys() if k != "meta"}
    if extracto and d.get("contenido") and len(d["contenido"]) > 400:
        d["contenido"] = d["contenido"][:400] + "…"
    return d


def _consulta_fts(texto: str) -> str:
    """Convierte texto libre en consulta FTS5 segura (términos entre comillas, OR implícito AND)."""
    terminos = [t.replace('"', "") for t in texto.split() if t.replace('"', "").strip()]
    return " ".join(f'"{t}"' for t in terminos) if terminos else '""'


def buscar(consulta: str, tipo: str | None = None, proyecto: str | None = None, limite: int = 10) -> list[dict]:
    con = conectar()
    try:
        sql = (
            "SELECT m.* FROM memoria_fts f JOIN memoria m ON m.id = f.rowid "
            "WHERE memoria_fts MATCH ? AND m.activo = 1"
        )
        params: list = [_consulta_fts(consulta)]
        if tipo:
            sql += " AND m.tipo = ?"
            params.append(tipo)
        if proyecto:
            sql += " AND m.proyecto = ?"
            params.append(proyecto)
        # bm25 (menor = mejor) con leve boost de recencia
        sql += " ORDER BY bm25(memoria_fts) + (julianday('now') - julianday(m.creado_en)) * 0.005 LIMIT ?"
        params.append(max(1, min(int(limite), 50)))
        return [_fila_a_dict(f, extracto=True) for f in con.execute(sql, params)]
    finally:
        con.close()


def recordar(tema: str | None = None, proyecto: str | None = None, limite: int = 20) -> dict:
    """Paquete de contexto: preferencias + hechos + decisiones activas y bitácora reciente."""
    limite = max(1, min(int(limite), 50))
    if tema:
        relevantes = buscar(tema, proyecto=proyecto, limite=limite)
    else:
        con = conectar()
        try:
            sql = "SELECT * FROM memoria WHERE activo = 1 AND tipo IN ('preferencia','hecho','decision')"
            params: list = []
            if proyecto:
                sql += " AND proyecto = ?"
                params.append(proyecto)
            sql += " ORDER BY creado_en DESC LIMIT ?"
            params.append(limite)
            relevantes = [_fila_a_dict(f, extracto=True) for f in con.execute(sql, params)]
        finally:
            con.close()
    con = conectar()
    try:
        sql = "SELECT * FROM memoria WHERE tipo = 'bitacora'"
        params = []
        if proyecto:
            sql += " AND proyecto = ?"
            params.append(proyecto)
        sql += " ORDER BY creado_en DESC LIMIT 10"
        bitacora_reciente = [_fila_a_dict(f, extracto=True) for f in con.execute(sql, params)]
    finally:
        con.close()
    return {"memorias": relevantes, "bitacora_reciente": bitacora_reciente}


def guardar(
    contenido: str,
    tipo: str = "nota",
    titulo: str | None = None,
    etiquetas: str | None = None,
    proyecto: str | None = None,
    agente: str | None = None,
    evento: str | None = None,
    origen: str = "mcp",
    meta: dict | None = None,
) -> dict:
    if tipo not in TIPOS:
        raise ValueError(f"tipo inválido: {tipo!r}; usa uno de {TIPOS}")
    if tipo == "bitacora" and evento not in EVENTOS:
        raise ValueError(f"evento inválido para bitácora: {evento!r}; usa uno de {EVENTOS}")
    con = conectar()
    try:
        # Idempotencia de migración: si llega meta.checksum, no duplicar.
        checksum = (meta or {}).get("checksum")
        if checksum:
            fila = con.execute(
                "SELECT id FROM memoria WHERE origen = ? AND json_extract(meta,'$.checksum') = ?",
                (origen, checksum),
            ).fetchone()
            if fila:
                return {"id": fila["id"], "duplicado": True}
        cur = con.execute(
            "INSERT INTO memoria (tipo, origen, agente, proyecto, titulo, contenido, etiquetas, evento, meta)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (tipo, origen, agente, proyecto, titulo, contenido, etiquetas, evento,
             json.dumps(meta, ensure_ascii=False) if meta else None),
        )
        con.commit()
        return {"id": cur.lastrowid, "duplicado": False}
    finally:
        con.close()


def actualizar(id: int, contenido: str | None = None, etiquetas: str | None = None, activo: bool | None = None) -> dict:
    con = conectar()
    try:
        fila = con.execute("SELECT * FROM memoria WHERE id = ?", (id,)).fetchone()
        if not fila:
            raise ValueError(f"no existe memoria con id {id}")
        if contenido is None and etiquetas is None and activo is None:
            raise ValueError("nada que actualizar: entrega contenido, etiquetas o activo")
        if activo is not None and contenido is None and etiquetas is None:
            con.execute(
                "UPDATE memoria SET activo = ?, actualizado_en = datetime('now') WHERE id = ?",
                (1 if activo else 0, id),
            )
            con.commit()
            return {"id": id, "activo": bool(activo)}
        # Versionado suave: nueva fila, la anterior queda inactiva y enlazada.
        cur = con.execute(
            "INSERT INTO memoria (tipo, origen, agente, proyecto, titulo, contenido, etiquetas, evento, meta)"
            " SELECT tipo, origen, agente, proyecto, titulo, ?, ?, evento, meta FROM memoria WHERE id = ?",
            (contenido if contenido is not None else fila["contenido"],
             etiquetas if etiquetas is not None else fila["etiquetas"], id),
        )
        nuevo_id = cur.lastrowid
        con.execute(
            "UPDATE memoria SET activo = 0, reemplazada_por = ?, actualizado_en = datetime('now') WHERE id = ?",
            (nuevo_id, id),
        )
        con.commit()
        return {"id": nuevo_id, "reemplaza_a": id}
    finally:
        con.close()


def bitacora_reporte(dias: int = 1) -> dict:
    con = conectar()
    try:
        filas = con.execute(
            "SELECT evento, COUNT(*) AS n FROM memoria WHERE tipo='bitacora'"
            " AND creado_en >= datetime('now', ?) GROUP BY evento",
            (f"-{max(1, int(dias))} days",),
        ).fetchall()
        ultimos = con.execute(
            "SELECT * FROM memoria WHERE tipo='bitacora' AND creado_en >= datetime('now', ?)"
            " ORDER BY creado_en DESC LIMIT 25",
            (f"-{max(1, int(dias))} days",),
        ).fetchall()
        return {
            "dias": dias,
            "totales": {f["evento"]: f["n"] for f in filas},
            "eventos": [_fila_a_dict(f, extracto=True) for f in ultimos],
        }
    finally:
        con.close()
