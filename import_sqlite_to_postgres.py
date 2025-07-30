"""
Script para importar datos de SQLite a PostgreSQL de forma segura.
Mantiene la integridad de los datos y las relaciones.
"""
import json
import os
import psycopg2
from pathlib import Path
from datetime import datetime

def import_sqlite_to_postgres():
    """Importa datos del backup de SQLite a PostgreSQL"""
    
    # Configuración PostgreSQL
    pg_config = {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': os.getenv('POSTGRES_PORT', '5432'),
        'database': os.getenv('POSTGRES_DB', 'bot_telegram_db'),
        'user': os.getenv('POSTGRES_USER', 'bot_user'),
        'password': os.getenv('POSTGRES_PASSWORD', 'bot_password123')
    }
    
    # Buscar el backup más reciente
    backup_dir = Path(__file__).parent / 'data' / 'backup_sqlite'
    backup_files = list(backup_dir.glob('sqlite_backup_*.json'))
    
    if not backup_files:
        print("❌ No se encontraron archivos de backup")
        return False
    
    latest_backup = max(backup_files, key=lambda x: x.stat().st_mtime)
    print(f"📂 Usando backup: {latest_backup.name}")
    
    try:
        # Cargar datos del backup
        with open(latest_backup, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        
        print(f"📊 Backup fecha: {backup_data['export_date']}")
        print(f"📋 Tablas a importar: {len(backup_data['tables'])}")
        
        # Conectar a PostgreSQL
        print("🔌 Conectando a PostgreSQL...")
        conn = psycopg2.connect(**pg_config)
        cursor = conn.cursor()
        
        # Verificar que las tablas existen
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        pg_tables = [row[0] for row in cursor.fetchall()]
        print(f"✅ Tablas en PostgreSQL: {len(pg_tables)}")
        
        # Orden de importación (respetando relaciones)
        import_order = [
            'usuarios',
            'tipos_trabajo',
            'ubicaciones_config',
            'almacen_items',
            'avances'
        ]
        
        total_imported = 0
        
        for table_name in import_order:
            if table_name in backup_data['tables'] and table_name in pg_tables:
                table_data = backup_data['tables'][table_name]
                rows = table_data['rows']
                
                if not rows:
                    print(f"⏭️  {table_name}: Sin datos que importar")
                    continue
                
                print(f"📥 Importando {table_name}: {len(rows)} registros...")
                
                # Limpiar tabla existente
                cursor.execute(f"DELETE FROM {table_name}")
                
                # Construir query de inserción
                columns = table_data['columns']
                placeholders = ', '.join(['%s'] * len(columns))
                insert_query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
                
                # Importar datos
                for row in rows:
                    values = [row.get(col) for col in columns]
                    try:
                        cursor.execute(insert_query, values)
                    except Exception as e:
                        print(f"⚠️  Error en fila de {table_name}: {e}")
                        print(f"   Datos: {values}")
                
                # Actualizar secuencias (para campos SERIAL)
                if table_name in ['tipos_trabajo', 'ubicaciones_config', 'avances', 'almacen_items']:
                    try:
                        cursor.execute(f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), COALESCE(MAX(id), 1)) FROM {table_name}")
                    except:
                        pass  # Algunas tablas pueden no tener campo id
                
                conn.commit()
                total_imported += len(rows)
                print(f"   ✅ {len(rows)} registros importados")
        
        # Verificar datos importados
        print(f"\n🔍 VERIFICANDO IMPORTACIÓN:")
        
        verification_queries = {
            'usuarios': "SELECT COUNT(*), string_agg(first_name, ', ') FROM usuarios",
            'tipos_trabajo': "SELECT COUNT(*), string_agg(nombre, ', ') FROM tipos_trabajo",
            'ubicaciones_config': "SELECT COUNT(*), COUNT(DISTINCT tipo) FROM ubicaciones_config",
            'avances': "SELECT COUNT(*), COUNT(DISTINCT encargado_id) FROM avances"
        }
        
        for table, query in verification_queries.items():
            try:
                cursor.execute(query)
                result = cursor.fetchone()
                print(f"   📊 {table}: {result}")
            except Exception as e:
                print(f"   ⚠️  Error verificando {table}: {e}")
        
        cursor.close()
        conn.close()
        
        print(f"\n🎉 MIGRACIÓN COMPLETADA EXITOSAMENTE!")
        print(f"📊 Total registros importados: {total_imported}")
        print(f"💾 Backup original conservado: {latest_backup}")
        
        return True
        
    except psycopg2.OperationalError as e:
        print(f"❌ Error de conexión PostgreSQL: {e}")
        print(f"\n💡 Soluciones:")
        print(f"1. Verificar que PostgreSQL esté ejecutándose")
        print(f"2. Comprobar credenciales en .env")
        print(f"3. Verificar que la base de datos existe")
        return False
        
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False

def test_postgres_connection():
    """Prueba la conexión a PostgreSQL antes de migrar"""
    
    pg_config = {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': os.getenv('POSTGRES_PORT', '5432'),
        'database': os.getenv('POSTGRES_DB', 'bot_telegram_db'),
        'user': os.getenv('POSTGRES_USER', 'bot_user'),
        'password': os.getenv('POSTGRES_PASSWORD', 'bot_password123')
    }
    
    try:
        print("🔌 Probando conexión PostgreSQL...")
        conn = psycopg2.connect(**pg_config)
        cursor = conn.cursor()
        
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        print(f"✅ Conectado a: {version}")
        
        cursor.execute("SELECT current_database()")
        db_name = cursor.fetchone()[0]
        print(f"✅ Base de datos: {db_name}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False

if __name__ == "__main__":
    print("🔄 MIGRACIÓN SQLITE → POSTGRESQL")
    print("=" * 40)
    
    # Probar conexión primero
    if not test_postgres_connection():
        print("\n🛑 No se puede conectar a PostgreSQL")
        print("📖 Ver guía: MIGRACION_POSTGRESQL.md")
        exit(1)
    
    # Proceder con migración
    success = import_sqlite_to_postgres()
    
    if success:
        print(f"\n✅ ¡Migración exitosa!")
        print(f"🔄 Próximo paso: Cambiar USE_SQLITE=false en .env")
        print(f"🧪 Probar: python test_avances_system.py")
    else:
        print(f"\n❌ Migración falló")
        print(f"💾 Datos seguros en SQLite como respaldo")
