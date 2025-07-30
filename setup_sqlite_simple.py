"""
Script simplificado para crear una base de datos SQLite funcional
adaptando mejor el schema de PostgreSQL.
"""
import sqlite3
import os
from pathlib import Path

def create_working_sqlite():
    """Crear base de datos SQLite funcional"""
    
    db_path = Path(__file__).parent / 'data' / 'bot_telegram.db'
    db_path.parent.mkdir(exist_ok=True)
    
    # Eliminar base de datos anterior si existe
    if db_path.exists():
        db_path.unlink()
    
    try:
        print("🔄 Creando base de datos SQLite funcional...")
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Schema adaptado para SQLite
        sqlite_schema = """
        -- Tabla usuarios
        CREATE TABLE usuarios (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('Encargado', 'Tecnico', 'Gerente', 'Almacen', 'RRHH', 'Prevencion', 'Admin'))
        );

        -- Tabla tipos_trabajo
        CREATE TABLE tipos_trabajo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            emoji TEXT DEFAULT '🔧',
            activo BOOLEAN DEFAULT TRUE,
            orden INTEGER DEFAULT 0,
            creado_por INTEGER REFERENCES usuarios(user_id),
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Tabla ubicaciones_config
        CREATE TABLE ubicaciones_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,
            nombre TEXT NOT NULL,
            UNIQUE (tipo, nombre)
        );

        -- Tabla avances (simplificada)
        CREATE TABLE avances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            encargado_id INTEGER REFERENCES usuarios(user_id),
            ubicacion_edificio TEXT,
            ubicacion_zona TEXT,
            ubicacion_planta TEXT,
            ubicacion_nucleo TEXT,
            ubicacion_completa TEXT NOT NULL,
            trabajo TEXT NOT NULL,
            tipo_trabajo_id INTEGER REFERENCES tipos_trabajo(id),
            observaciones TEXT,
            foto_path TEXT,
            estado TEXT,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_trabajo DATE
        );

        -- Tabla almacen_items
        CREATE TABLE almacen_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            cantidad INTEGER NOT NULL DEFAULT 0,
            descripcion TEXT,
            tipo TEXT NOT NULL CHECK (tipo IN ('Herramienta', 'EPI', 'Fungible'))
        );
        """
        
        # Ejecutar schema
        cursor.executescript(sqlite_schema)
        
        # Insertar datos iniciales
        print("📝 Insertando datos iniciales...")
        
        # Tipos de trabajo
        tipos_trabajo = [
            ('Albañilería', '🧱', 1),
            ('Electricidad', '⚡', 2),
            ('Fontanería', '🔧', 3),
            ('Pintura', '🎨', 4),
            ('Carpintería', '🪚', 5),
            ('Limpieza', '🧹', 6),
            ('Inspección', '🔍', 7),
            ('Otro', '📝', 8)
        ]
        
        cursor.executemany(
            "INSERT INTO tipos_trabajo (nombre, emoji, orden) VALUES (?, ?, ?)",
            tipos_trabajo
        )
        
        # Ubicaciones
        ubicaciones = [
            ('Edificio', 'Edificio 1'),
            ('Edificio', 'Edificio 2'),
            ('Edificio', 'Edificio 3'),
            ('Planta', 'Planta 0'),
            ('Planta', 'Planta 1'),
            ('Planta', 'Planta 2'),
            ('Planta', 'Planta 3'),
            ('Zona', 'Zona 1'),
            ('Zona', 'Zona 2'),
            ('Zona', 'Zona 3'),
            ('Zona', 'Zona 4'),
            ('Trabajo', 'Trabajo 1'),
            ('Trabajo', 'Trabajo 2'),
            ('Trabajo', 'Trabajo 3')
        ]
        
        cursor.executemany(
            "INSERT INTO ubicaciones_config (tipo, nombre) VALUES (?, ?)",
            ubicaciones
        )
        
        # Usuarios de ejemplo
        usuarios = [
            (1108686086, 'tecnico_chemi', 'Chemi', 'Admin'),
            (195947658, 'nico_', 'Nico', 'Admin')
        ]
        
        cursor.executemany(
            "INSERT INTO usuarios (user_id, username, first_name, role) VALUES (?, ?, ?, ?)",
            usuarios
        )
        
        conn.commit()
        
        # Verificar instalación
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        
        cursor.execute("SELECT COUNT(*) FROM tipos_trabajo")
        tipos_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM ubicaciones_config")
        ubicaciones_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        usuarios_count = cursor.fetchone()[0]
        
        print(f"✅ Base de datos SQLite creada: {db_path}")
        print(f"📋 Tablas creadas: {len(tables)}")
        print(f"🔧 Tipos de trabajo: {tipos_count}")
        print(f"📍 Ubicaciones: {ubicaciones_count}")
        print(f"👥 Usuarios: {usuarios_count}")
        
        cursor.close()
        conn.close()
        
        print(f"\n🎉 ¡Base de datos SQLite lista para pruebas!")
        print(f"📁 Archivo: {db_path}")
        
        return str(db_path)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    db_path = create_working_sqlite()
    if db_path:
        print(f"\n💡 Para usar esta base de datos:")
        print(f"1. Actualizar db_manager.py para usar SQLite")
        print(f"2. Cambiar connection string a: sqlite:///{db_path}")
        print(f"3. Probar el bot con: python main.py")
