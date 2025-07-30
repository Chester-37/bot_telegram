"""
Script para exportar datos de SQLite antes de migrar a PostgreSQL.
Esto asegura que no perdamos ningún dato durante la migración.
"""
import sqlite3
import json
import os
from pathlib import Path
from datetime import datetime

def export_sqlite_data():
    """Exporta todos los datos de SQLite a archivos JSON"""
    
    db_path = Path(__file__).parent / 'data' / 'bot_telegram.db'
    backup_dir = Path(__file__).parent / 'data' / 'backup_sqlite'
    backup_dir.mkdir(exist_ok=True)
    
    if not db_path.exists():
        print("❌ Base de datos SQLite no encontrada")
        return False
    
    try:
        print("🔍 Conectando a SQLite...")
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row  # Para acceder por nombre de columna
        cursor = conn.cursor()
        
        # Obtener lista de tablas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"📋 Tablas encontradas: {len(tables)}")
        
        backup_data = {
            'export_date': datetime.now().isoformat(),
            'database_type': 'SQLite',
            'tables': {}
        }
        
        total_records = 0
        
        for table in tables:
            if table == 'sqlite_sequence':
                continue
                
            print(f"📤 Exportando tabla: {table}")
            
            # Obtener estructura de la tabla
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [col[1] for col in cursor.fetchall()]
            
            # Obtener datos
            cursor.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()
            
            # Convertir a formato JSON serializable
            table_data = []
            for row in rows:
                row_dict = {}
                for i, col in enumerate(columns):
                    value = row[i]
                    # Convertir fechas y otros tipos
                    if value is not None and isinstance(value, str):
                        row_dict[col] = value
                    else:
                        row_dict[col] = value
                table_data.append(row_dict)
            
            backup_data['tables'][table] = {
                'columns': columns,
                'rows': table_data,
                'count': len(table_data)
            }
            
            total_records += len(table_data)
            print(f"   ✅ {len(table_data)} registros exportados")
        
        # Guardar backup principal
        backup_file = backup_dir / f'sqlite_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n📦 BACKUP COMPLETADO")
        print(f"📁 Archivo: {backup_file}")
        print(f"📊 Total registros: {total_records}")
        print(f"📋 Tablas: {len(tables)}")
        
        # Crear también backups individuales por tabla
        for table, data in backup_data['tables'].items():
            table_file = backup_dir / f'{table}.json'
            with open(table_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        
        conn.close()
        
        # Mostrar resumen de datos importantes
        print(f"\n📊 RESUMEN DE DATOS:")
        for table, data in backup_data['tables'].items():
            if data['count'] > 0:
                print(f"   📋 {table}: {data['count']} registros")
        
        return backup_file
        
    except Exception as e:
        print(f"❌ Error exportando datos: {e}")
        return False

if __name__ == "__main__":
    print("🔄 EXPORTANDO DATOS DE SQLITE")
    print("=" * 40)
    
    backup_file = export_sqlite_data()
    
    if backup_file:
        print(f"\n✅ Datos exportados exitosamente!")
        print(f"📁 Backup guardado en: {backup_file}")
        print(f"\n💡 Próximo paso: Instalar PostgreSQL y ejecutar migración")
    else:
        print(f"\n❌ Error en la exportación")
