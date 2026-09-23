-- ============================================
-- HadaAI Memory System V1 - SQLite Schema
-- ============================================

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

-- Triggers para updated_at automatico
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

-- Vistas utiles
CREATE VIEW IF NOT EXISTS v_memory_full AS
SELECT 
    m.memory_id, m.tipo, m.contenido, m.resumen, m.importancia, m.confianza, m.origen,
    m.created_at, m.updated_at, m.last_accessed_at,
    p.nombre AS persona_nombre, p.apodo AS persona_apodo,
    d.fecha AS diary_fecha, d.resumen AS diary_resumen
FROM Memory m
LEFT JOIN Persona p ON m.persona_id = p.persona_id
LEFT JOIN Diary d ON m.diary_id = d.diary_id;

CREATE VIEW IF NOT EXISTS v_memory_links AS
SELECT 
    ml.link_id, ml.tipo_relacion, ml.created_at,
    mo.memory_id AS origen_id, mo.resumen AS origen_resumen,
    md.memory_id AS destino_id, md.resumen AS destino_resumen
FROM MemoryLink ml
JOIN Memory mo ON ml.memory_origen_id = mo.memory_id
JOIN Memory md ON ml.memory_destino_id = md.memory_id;