#!/usr/bin/env python3
"""
HadaAI MCP Memory Server
Servidor MCP para gestion de memoria persistente de HadaAI usando SQLite.
Compatible con hada_client.py via stdio.
"""

import os
import json
import sqlite3
from datetime import datetime
from contextlib import closing
from mcp.server.fastmcp import FastMCP

# ─── Configuracion ────────────────────────────────────────────────────────────
DB_PATH = os.environ.get("MEMORY_DB_PATH", "hadaai_memory.db")

# ─── Schema SQL ───────────────────────────────────────────────────────────────
SCHEMA_SQL = """
-- Tabla: Persona
CREATE TABLE IF NOT EXISTS Persona (
    persona_id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    apellido TEXT,
    apodo TEXT,
    fecha_primer_contacto DATE,
    relacion_nivel INTEGER NOT NULL DEFAULT 5 CHECK (relacion_nivel BETWEEN 0 AND 10),
    gustos TEXT NOT NULL DEFAULT '',
    disgustos TEXT NOT NULL DEFAULT '',
    hechos TEXT NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
    updated_at DATETIME NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_persona_nombre ON Persona(nombre);
CREATE INDEX IF NOT EXISTS idx_persona_apellido ON Persona(apellido);
CREATE INDEX IF NOT EXISTS idx_persona_apodo ON Persona(apodo);

-- Tabla: Diary
CREATE TABLE IF NOT EXISTS Diary (
    diary_id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha DATE NOT NULL,
    redaccion TEXT NOT NULL DEFAULT '',
    resumen TEXT NOT NULL DEFAULT '',
    categoria TEXT NOT NULL DEFAULT 'normal' CHECK (categoria IN ('extrano', 'raro', 'normal', 'divertido', 'especial')),
    sentimiento TEXT NOT NULL DEFAULT 'indiferencia' CHECK (sentimiento IN ('furia', 'enojo', 'aburrimiento', 'sorpresa', 'locura', 'indiferencia', 'tristeza', 'amor', 'diversion', 'felicidad', 'nerviosismo', 'asco')),
    importancia INTEGER NOT NULL DEFAULT 5 CHECK (importancia BETWEEN 0 AND 10),
    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
    updated_at DATETIME NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_diary_fecha ON Diary(fecha);
CREATE INDEX IF NOT EXISTS idx_diary_categoria ON Diary(categoria);

-- Tabla: Memory
CREATE TABLE IF NOT EXISTS Memory (
    memory_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT NOT NULL DEFAULT 'hecho' CHECK (tipo IN ('persona', 'preferencia', 'hecho', 'evento', 'conversacion', 'recordatorio')),
    contenido TEXT NOT NULL DEFAULT '',
    resumen TEXT NOT NULL DEFAULT '',
    persona_id INTEGER,
    diary_id INTEGER,
    importancia INTEGER NOT NULL DEFAULT 5 CHECK (importancia BETWEEN 0 AND 10),
    confianza REAL NOT NULL DEFAULT 0.5 CHECK (confianza BETWEEN 0.0 AND 1.0),
    origen TEXT NOT NULL DEFAULT 'usuario' CHECK (origen IN ('usuario', 'inferido', 'sistema')),
    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
    updated_at DATETIME NOT NULL DEFAULT (datetime('now')),
    last_accessed_at DATETIME,
    FOREIGN KEY (persona_id) REFERENCES Persona(persona_id) ON DELETE SET NULL ON UPDATE CASCADE,
    FOREIGN KEY (diary_id) REFERENCES Diary(diary_id) ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_memory_tipo ON Memory(tipo);
CREATE INDEX IF NOT EXISTS idx_memory_persona ON Memory(persona_id);
CREATE INDEX IF NOT EXISTS idx_memory_diary ON Memory(diary_id);
CREATE INDEX IF NOT EXISTS idx_memory_importancia ON Memory(importancia);
CREATE INDEX IF NOT EXISTS idx_memory_created ON Memory(created_at);
CREATE INDEX IF NOT EXISTS idx_memory_last_accessed ON Memory(last_accessed_at);

-- Tabla: MemoryLink
CREATE TABLE IF NOT EXISTS MemoryLink (
    link_id INTEGER PRIMARY KEY AUTOINCREMENT,
    memory_origen_id INTEGER NOT NULL,
    memory_destino_id INTEGER NOT NULL,
    tipo_relacion TEXT NOT NULL DEFAULT 'related_to' CHECK (tipo_relacion IN ('related_to', 'caused_by', 'about_person', 'contradicts')),
    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (memory_origen_id) REFERENCES Memory(memory_id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (memory_destino_id) REFERENCES Memory(memory_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CHECK (memory_origen_id != memory_destino_id)
);

CREATE INDEX IF NOT EXISTS idx_link_origen ON MemoryLink(memory_origen_id);
CREATE INDEX IF NOT EXISTS idx_link_destino ON MemoryLink(memory_destino_id);

-- Triggers updated_at
CREATE TRIGGER IF NOT EXISTS trg_persona_updated
AFTER UPDATE ON Persona
FOR EACH ROW
BEGIN
    UPDATE Persona SET updated_at = datetime('now') WHERE persona_id = NEW.persona_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_diary_updated
AFTER UPDATE ON Diary
FOR EACH ROW
BEGIN
    UPDATE Diary SET updated_at = datetime('now') WHERE diary_id = NEW.diary_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_memory_updated
AFTER UPDATE ON Memory
FOR EACH ROW
BEGIN
    UPDATE Memory SET updated_at = datetime('now') WHERE memory_id = NEW.memory_id;
END;
"""

# ─── Helpers ─────────────────────────────────────────────────────────────────
def _dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = _dict_factory
    return conn


def init_db():
    with closing(get_db()) as db:
        db.executescript(SCHEMA_SQL)
        db.commit()
    print(f"[HadaAI Memory] Base de datos inicializada: {DB_PATH}")


# ─── Inicializar al importar ─────────────────────────────────────────────────
init_db()

# ─── MCP Server ──────────────────────────────────────────────────────────────
mcp = FastMCP("HadaAI-Memory")


# ─────── PERSONA ──────────────────────────────────────────────────────────────

@mcp.tool()
def read_persona(persona_id: int) -> str:
    """Leer los datos de una persona por su ID."""
    with closing(get_db()) as db:
        row = db.execute("SELECT * FROM Persona WHERE persona_id = ?", (persona_id,)).fetchone()
    return json.dumps(row, ensure_ascii=False, default=str) if row else "{\"error\": \"Persona no encontrada\"}"


@mcp.tool()
def create_persona(
    nombre: str,
    apellido: str = None,
    apodo: str = None,
    fecha_primer_contacto: str = None,
    relacion_nivel: int = 5,
    gustos: str = "",
    disgustos: str = "",
    hechos: str = ""
) -> str:
    """Crear una nueva persona en la base de datos."""
    with closing(get_db()) as db:
        cur = db.execute(
            """INSERT INTO Persona (nombre, apellido, apodo, fecha_primer_contacto, relacion_nivel, gustos, disgustos, hechos)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (nombre, apellido, apodo, fecha_primer_contacto, relacion_nivel, gustos, disgustos, hechos)
        )
        db.commit()
        persona_id = cur.lastrowid
    return json.dumps({"persona_id": persona_id, "status": "creada"}, ensure_ascii=False)


@mcp.tool()
def update_persona(
    persona_id: int,
    nombre: str = None,
    apellido: str = None,
    apodo: str = None,
    fecha_primer_contacto: str = None,
    relacion_nivel: int = None,
    gustos: str = None,
    disgustos: str = None,
    hechos: str = None
) -> str:
    """Actualizar campos de una persona existente. Solo modifica los campos proporcionados."""
    fields = []
    values = []
    if nombre is not None:
        fields.append("nombre = ?")
        values.append(nombre)
    if apellido is not None:
        fields.append("apellido = ?")
        values.append(apellido)
    if apodo is not None:
        fields.append("apodo = ?")
        values.append(apodo)
    if fecha_primer_contacto is not None:
        fields.append("fecha_primer_contacto = ?")
        values.append(fecha_primer_contacto)
    if relacion_nivel is not None:
        fields.append("relacion_nivel = ?")
        values.append(relacion_nivel)
    if gustos is not None:
        fields.append("gustos = ?")
        values.append(gustos)
    if disgustos is not None:
        fields.append("disgustos = ?")
        values.append(disgustos)
    if hechos is not None:
        fields.append("hechos = ?")
        values.append(hechos)

    if not fields:
        return json.dumps({"error": "No se proporcionaron campos para actualizar"}, ensure_ascii=False)

    values.append(persona_id)
    sql = f"UPDATE Persona SET {', '.join(fields)} WHERE persona_id = ?"

    with closing(get_db()) as db:
        db.execute(sql, values)
        db.commit()
    return json.dumps({"persona_id": persona_id, "status": "actualizada"}, ensure_ascii=False)


@mcp.tool()
def search_persona(query: str) -> str:
    """Buscar personas por nombre, apellido o apodo."""
    q = f"%{query}%"
    with closing(get_db()) as db:
        rows = db.execute(
            "SELECT * FROM Persona WHERE nombre LIKE ? OR apellido LIKE ? OR apodo LIKE ?",
            (q, q, q)
        ).fetchall()
    return json.dumps(rows, ensure_ascii=False, default=str)


# ─────── DIARY ──────────────────────────────────────────────────────────────

@mcp.tool()
def read_diary(diary_id: int = None, fecha: str = None) -> str:
    """Leer una entrada del diario por ID o por fecha (YYYY-MM-DD)."""
    with closing(get_db()) as db:
        if diary_id is not None:
            row = db.execute("SELECT * FROM Diary WHERE diary_id = ?", (diary_id,)).fetchone()
            return json.dumps(row, ensure_ascii=False, default=str) if row else json.dumps({"error": "Entrada no encontrada"}, ensure_ascii=False)
        elif fecha is not None:
            rows = db.execute("SELECT * FROM Diary WHERE fecha = ?", (fecha,)).fetchall()
            return json.dumps(rows, ensure_ascii=False, default=str)
        else:
            return json.dumps({"error": "Debes proporcionar diary_id o fecha"}, ensure_ascii=False)


@mcp.tool()
def create_diary(
    fecha: str,
    redaccion: str = "",
    resumen: str = "",
    categoria: str = "normal",
    sentimiento: str = "indiferencia",
    importancia: int = 5
) -> str:
    """Crear una nueva entrada en el diario."""
    with closing(get_db()) as db:
        cur = db.execute(
            """INSERT INTO Diary (fecha, redaccion, resumen, categoria, sentimiento, importancia)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (fecha, redaccion, resumen, categoria, sentimiento, importancia)
        )
        db.commit()
        diary_id = cur.lastrowid
    return json.dumps({"diary_id": diary_id, "status": "creada"}, ensure_ascii=False)


@mcp.tool()
def update_diary(
    diary_id: int,
    fecha: str = None,
    redaccion: str = None,
    resumen: str = None,
    categoria: str = None,
    sentimiento: str = None,
    importancia: int = None
) -> str:
    """Actualizar una entrada del diario. Solo modifica los campos proporcionados."""
    fields = []
    values = []
    if fecha is not None:
        fields.append("fecha = ?"); values.append(fecha)
    if redaccion is not None:
        fields.append("redaccion = ?"); values.append(redaccion)
    if resumen is not None:
        fields.append("resumen = ?"); values.append(resumen)
    if categoria is not None:
        fields.append("categoria = ?"); values.append(categoria)
    if sentimiento is not None:
        fields.append("sentimiento = ?"); values.append(sentimiento)
    if importancia is not None:
        fields.append("importancia = ?"); values.append(importancia)

    if not fields:
        return json.dumps({"error": "No se proporcionaron campos para actualizar"}, ensure_ascii=False)

    values.append(diary_id)
    sql = f"UPDATE Diary SET {', '.join(fields)} WHERE diary_id = ?"

    with closing(get_db()) as db:
        db.execute(sql, values)
        db.commit()
    return json.dumps({"diary_id": diary_id, "status": "actualizada"}, ensure_ascii=False)


@mcp.tool()
def search_diary(query: str = None, categoria: str = None, fecha: str = None) -> str:
    """Buscar entradas del diario por texto, categoria o fecha."""
    conditions = []
    values = []
    if query is not None:
        q = f"%{query}%"
        conditions.append("(redaccion LIKE ? OR resumen LIKE ?)")
        values.extend([q, q])
    if categoria is not None:
        conditions.append("categoria = ?")
        values.append(categoria)
    if fecha is not None:
        conditions.append("fecha = ?")
        values.append(fecha)

    if not conditions:
        return json.dumps({"error": "Proporciona al menos un criterio de busqueda"}, ensure_ascii=False)

    sql = "SELECT * FROM Diary WHERE " + " AND ".join(conditions)
    with closing(get_db()) as db:
        rows = db.execute(sql, values).fetchall()
    return json.dumps(rows, ensure_ascii=False, default=str)


# ─────── MEMORY ─────────────────────────────────────────────────────────────

@mcp.tool()
def read_memory(memory_id: int) -> str:
    """Leer una memoria por su ID."""
    with closing(get_db()) as db:
        row = db.execute("""
            SELECT m.*, p.nombre as persona_nombre, p.apodo as persona_apodo,
                   d.fecha as diary_fecha, d.resumen as diary_resumen
            FROM Memory m
            LEFT JOIN Persona p ON m.persona_id = p.persona_id
            LEFT JOIN Diary d ON m.diary_id = d.diary_id
            WHERE m.memory_id = ?
        """, (memory_id,)).fetchone()
    return json.dumps(row, ensure_ascii=False, default=str) if row else json.dumps({"error": "Memoria no encontrada"}, ensure_ascii=False)


@mcp.tool()
def create_memory(
    contenido: str,
    resumen: str = "",
    tipo: str = "hecho",
    persona_id: int = None,
    diary_id: int = None,
    importancia: int = 5,
    confianza: float = 0.5,
    origen: str = "usuario"
) -> str:
    """Crear una nueva memoria persistente para HadaAI."""
    with closing(get_db()) as db:
        cur = db.execute(
            """INSERT INTO Memory (tipo, contenido, resumen, persona_id, diary_id, importancia, confianza, origen)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (tipo, contenido, resumen, persona_id, diary_id, importancia, confianza, origen)
        )
        db.commit()
        memory_id = cur.lastrowid
    return json.dumps({"memory_id": memory_id, "status": "creada"}, ensure_ascii=False)


@mcp.tool()
def update_memory(
    memory_id: int,
    contenido: str = None,
    resumen: str = None,
    tipo: str = None,
    persona_id: int = None,
    diary_id: int = None,
    importancia: int = None,
    confianza: float = None,
    origen: str = None
) -> str:
    """Actualizar una memoria existente. Solo modifica los campos proporcionados."""
    fields = []
    values = []
    if contenido is not None:
        fields.append("contenido = ?"); values.append(contenido)
    if resumen is not None:
        fields.append("resumen = ?"); values.append(resumen)
    if tipo is not None:
        fields.append("tipo = ?"); values.append(tipo)
    if persona_id is not None:
        fields.append("persona_id = ?"); values.append(persona_id)
    if diary_id is not None:
        fields.append("diary_id = ?"); values.append(diary_id)
    if importancia is not None:
        fields.append("importancia = ?"); values.append(importancia)
    if confianza is not None:
        fields.append("confianza = ?"); values.append(confianza)
    if origen is not None:
        fields.append("origen = ?"); values.append(origen)

    if not fields:
        return json.dumps({"error": "No se proporcionaron campos para actualizar"}, ensure_ascii=False)

    values.append(memory_id)
    sql = f"UPDATE Memory SET {', '.join(fields)} WHERE memory_id = ?"

    with closing(get_db()) as db:
        db.execute(sql, values)
        db.commit()
    return json.dumps({"memory_id": memory_id, "status": "actualizada"}, ensure_ascii=False)


@mcp.tool()
def search_memory(keyword: str = None, tipo: str = None, persona_id: int = None, fecha: str = None) -> str:
    """Buscar memorias por keyword, tipo, persona o fecha de creacion."""
    conditions = []
    values = []
    if keyword is not None:
        q = f"%{keyword}%"
        conditions.append("(contenido LIKE ? OR resumen LIKE ?)")
        values.extend([q, q])
    if tipo is not None:
        conditions.append("tipo = ?")
        values.append(tipo)
    if persona_id is not None:
        conditions.append("persona_id = ?")
        values.append(persona_id)
    if fecha is not None:
        conditions.append("date(created_at) = ?")
        values.append(fecha)

    if not conditions:
        return json.dumps({"error": "Proporciona al menos un criterio de busqueda"}, ensure_ascii=False)

    sql = """
        SELECT m.*, p.nombre as persona_nombre, p.apodo as persona_apodo,
               d.fecha as diary_fecha, d.resumen as diary_resumen
        FROM Memory m
        LEFT JOIN Persona p ON m.persona_id = p.persona_id
        LEFT JOIN Diary d ON m.diary_id = d.diary_id
        WHERE """ + " AND ".join(conditions) + " ORDER BY m.importancia DESC, m.created_at DESC"

    with closing(get_db()) as db:
        rows = db.execute(sql, values).fetchall()
    return json.dumps(rows, ensure_ascii=False, default=str)


@mcp.tool()
def reinforce_memory(memory_id: int) -> str:
    """Reforzar una memoria: aumenta importancia (max 10) y actualiza last_accessed_at."""
    with closing(get_db()) as db:
        db.execute(
            "UPDATE Memory SET importancia = MIN(importancia + 1, 10), last_accessed_at = datetime('now') WHERE memory_id = ?",
            (memory_id,)
        )
        db.commit()
    return json.dumps({"memory_id": memory_id, "status": "reforzada"}, ensure_ascii=False)


# ─────── MEMORY LINK ──────────────────────────────────────────────────────────

@mcp.tool()
def link_memories(memory_origen_id: int, memory_destino_id: int, tipo_relacion: str = "related_to") -> str:
    """Crear un vinculo entre dos memorias."""
    with closing(get_db()) as db:
        cur = db.execute(
            """INSERT INTO MemoryLink (memory_origen_id, memory_destino_id, tipo_relacion)
               VALUES (?, ?, ?)""",
            (memory_origen_id, memory_destino_id, tipo_relacion)
        )
        db.commit()
        link_id = cur.lastrowid
    return json.dumps({"link_id": link_id, "status": "vinculo creado"}, ensure_ascii=False)


@mcp.tool()
def get_memory_links(memory_id: int) -> str:
    """Ver todas las relaciones de una memoria (como origen o destino)."""
    with closing(get_db()) as db:
        rows = db.execute("""
            SELECT ml.*,
                   mo.resumen as origen_resumen,
                   md.resumen as destino_resumen
            FROM MemoryLink ml
            JOIN Memory mo ON ml.memory_origen_id = mo.memory_id
            JOIN Memory md ON ml.memory_destino_id = md.memory_id
            WHERE ml.memory_origen_id = ? OR ml.memory_destino_id = ?
        """, (memory_id, memory_id)).fetchall()
    return json.dumps(rows, ensure_ascii=False, default=str)


# ─── Entry point ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run(transport="stdio")
