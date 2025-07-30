"""
Script para probar la migración usando SQLite como alternativa temporal.
Esto nos permite probar el sistema sin PostgreSQL.
"""
import sqlite3
import os
from pathlib import Path
from datetime import datetime

def create_sqlite_database():
    """Crear base de datos SQLite y ejecutar migración adaptada"""
    
    db_path = Path(__file__).parent / 'data' / 'bot_telegram.db'
    
    # Crear directorio data si no existe
    db_path.parent.mkdir(exist_ok=True)
    
    try:
        print("🔄 Creando base de datos SQLite...")
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Leer init.sql y adaptar para SQLite
        init_sql_path = Path(__file__).parent / 'init.sql'
        with open(init_sql_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Adaptaciones básicas para SQLite
        sql_adapted = sql_content.replace('SERIAL PRIMARY KEY', 'INTEGER PRIMARY KEY AUTOINCREMENT')
        sql_adapted = sql_adapted.replace('BIGINT', 'INTEGER')
        sql_adapted = sql_adapted.replace('TIMESTAMP WITH TIME ZONE', 'TIMESTAMP')
        sql_adapted = sql_adapted.replace('DEFAULT NOW()', "DEFAULT CURRENT_TIMESTAMP")
        
        # Ejecutar por bloques (SQLite no soporta múltiples statements)
        statements = [stmt.strip() for stmt in sql_adapted.split(';') if stmt.strip()]
        
        for statement in statements:
            if statement and not statement.startswith('--'):
                try:
                    cursor.execute(statement)
                except sqlite3.Error as e:
                    if 'already exists' not in str(e):
                        print(f"⚠️  Advertencia en: {statement[:50]}... - {e}")
        
        conn.commit()
        
        # Verificar tablas creadas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        
        print(f"✅ Base de datos SQLite creada: {db_path}")
        print(f"📋 Tablas creadas ({len(tables)}):")
        for table in tables:
            print(f"   - {table[0]}")
        
        # Probar una consulta básica
        cursor.execute("SELECT COUNT(*) FROM tipos_trabajo")
        tipos_count = cursor.fetchone()[0]
        print(f"🔧 Tipos de trabajo insertados: {tipos_count}")
        
        cursor.close()
        conn.close()
        
        print(f"\n🎉 ¡Base de datos SQLite lista!")
        print(f"📁 Ubicación: {db_path}")
        print("\n💡 Para usar PostgreSQL más tarde:")
        print("1. Instalar PostgreSQL")
        print("2. Ejecutar setup_database.py")
        print("3. Actualizar configuración en .env")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    create_sqlite_database()
