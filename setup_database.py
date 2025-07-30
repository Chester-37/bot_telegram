"""
Script para crear la base de datos PostgreSQL local y ejecutar la migración.
Esto es una alternativa cuando no tenemos Docker disponible.
"""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from pathlib import Path

def create_database_and_migrate():
    """Crear base de datos y ejecutar migración"""
    
    # Configuración de conexión
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'user': 'postgres',  # Usuario por defecto de PostgreSQL
        'password': 'postgres',  # Cambiar por la contraseña real
    }
    
    target_db = 'bot_telegram_db'
    
    try:
        print("🔄 Conectando a PostgreSQL...")
        
        # Conectar como superusuario para crear la base de datos
        conn = psycopg2.connect(**db_config)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Verificar si la base de datos existe
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target_db,))
        exists = cursor.fetchone()
        
        if not exists:
            print(f"📦 Creando base de datos '{target_db}'...")
            cursor.execute(f'CREATE DATABASE "{target_db}"')
            print("✅ Base de datos creada exitosamente")
        else:
            print(f"✅ Base de datos '{target_db}' ya existe")
        
        cursor.close()
        conn.close()
        
        # Ahora conectar a la base de datos específica para ejecutar init.sql
        db_config['database'] = target_db
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        print("🔄 Ejecutando script init.sql...")
        
        # Leer y ejecutar init.sql
        init_sql_path = Path(__file__).parent / 'init.sql'
        with open(init_sql_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        cursor.execute(sql_content)
        conn.commit()
        
        print("✅ Script init.sql ejecutado exitosamente")
        
        # Verificar que las tablas se crearon
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """)
        
        tables = cursor.fetchall()
        print(f"📋 Tablas creadas ({len(tables)}):")
        for table in tables:
            print(f"   - {table[0]}")
        
        cursor.close()
        conn.close()
        
        print("\n🎉 ¡Base de datos configurada exitosamente!")
        print(f"🔗 Conexión: postgresql://postgres:postgres@localhost:5432/{target_db}")
        
    except psycopg2.OperationalError as e:
        print(f"❌ Error de conexión: {e}")
        print("\n💡 Posibles soluciones:")
        print("1. Verificar que PostgreSQL esté instalado y ejecutándose")
        print("2. Verificar usuario/contraseña (por defecto postgres/postgres)")
        print("3. Verificar que el puerto 5432 esté disponible")
        print("4. Instalar PostgreSQL desde: https://www.postgresql.org/download/")
        
    except Exception as e:
        print(f"❌ Error inesperado: {e}")

if __name__ == "__main__":
    create_database_and_migrate()
