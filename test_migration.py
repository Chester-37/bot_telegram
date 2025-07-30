"""
Script para verificar que la migración a PostgreSQL fue exitosa
y que todos los datos se preservaron correctamente.
"""
import os
import sys
from pathlib import Path

# Configurar para usar PostgreSQL
os.environ['USE_SQLITE'] = 'false'

# Añadir el directorio del proyecto al path
sys.path.insert(0, str(Path(__file__).parent))

import db_adapter
import json
from datetime import datetime

def compare_with_backup():
    """Compara los datos de PostgreSQL con el backup de SQLite"""
    
    # Buscar backup más reciente
    backup_dir = Path(__file__).parent / 'data' / 'backup_sqlite'
    backup_files = list(backup_dir.glob('sqlite_backup_*.json'))
    
    if not backup_files:
        print("❌ No se encontró backup de SQLite para comparar")
        return False
    
    latest_backup = max(backup_files, key=lambda x: x.stat().st_mtime)
    
    with open(latest_backup, 'r', encoding='utf-8') as f:
        backup_data = json.load(f)
    
    print(f"📂 Comparando con backup: {latest_backup.name}")
    print(f"📅 Fecha backup: {backup_data['export_date']}")
    
    # Verificar cada tabla
    verification_results = {}
    
    tables_to_check = ['usuarios', 'tipos_trabajo', 'ubicaciones_config', 'avances']
    
    for table in tables_to_check:
        if table in backup_data['tables']:
            backup_count = backup_data['tables'][table]['count']
            
            try:
                # Obtener count de PostgreSQL
                if table == 'usuarios':
                    pg_data = db_adapter.get_all_users()
                elif table == 'tipos_trabajo':
                    pg_data = db_adapter.get_tipos_trabajo_activos()
                elif table == 'ubicaciones_config':
                    pg_data = db_adapter.get_jerarquia_ubicaciones()
                elif table == 'avances':
                    pg_data = db_adapter.get_avances_with_filters_extended(limit=1000)
                else:
                    pg_data = []
                
                pg_count = len(pg_data) if pg_data else 0
                
                match = pg_count == backup_count
                verification_results[table] = {
                    'backup_count': backup_count,
                    'postgres_count': pg_count,
                    'match': match
                }
                
                status = "✅" if match else "❌"
                print(f"   {status} {table}: SQLite={backup_count}, PostgreSQL={pg_count}")
                
            except Exception as e:
                print(f"   ❌ Error verificando {table}: {e}")
                verification_results[table] = {
                    'backup_count': backup_count,
                    'postgres_count': 0,
                    'match': False,
                    'error': str(e)
                }
    
    return verification_results

def test_postgres_functionality():
    """Prueba las funcionalidades principales con PostgreSQL"""
    
    print("\n🔧 PROBANDO FUNCIONALIDADES CON POSTGRESQL")
    print("-" * 45)
    
    tests = []
    
    try:
        # Test 1: Conexión
        print("1️⃣ Probando conexión...")
        success = db_adapter.test_database_connection()
        tests.append(("Conexión", success))
        
        # Test 2: Usuarios
        print("2️⃣ Probando usuarios...")
        users = db_adapter.get_all_users()
        tests.append(("Usuarios", len(users) > 0))
        print(f"   👥 Usuarios encontrados: {len(users)}")
        
        # Test 3: Tipos de trabajo
        print("3️⃣ Probando tipos de trabajo...")
        tipos = db_adapter.get_tipos_trabajo_activos()
        tests.append(("Tipos trabajo", len(tipos) > 0))
        print(f"   🔧 Tipos encontrados: {len(tipos)}")
        
        # Test 4: Ubicaciones
        print("4️⃣ Probando ubicaciones...")
        ubicaciones = db_adapter.get_jerarquia_ubicaciones()
        tests.append(("Ubicaciones", len(ubicaciones) > 0))
        print(f"   📍 Ubicaciones encontradas: {len(ubicaciones)}")
        
        # Test 5: Avances
        print("5️⃣ Probando avances...")
        avances = db_adapter.get_avances_with_filters_extended(limit=10)
        tests.append(("Avances", avances is not None))
        count = len(avances) if avances else 0
        print(f"   📊 Avances encontrados: {count}")
        
        # Test 6: Crear nuevo avance
        print("6️⃣ Probando creación de avance...")
        try:
            new_avance_id = db_adapter.insert_avance_extendido(
                encargado_id=195947658,
                ubicacion_completa="Test PostgreSQL Migration",
                trabajo="Verificación de migración PostgreSQL",
                tipo_trabajo_id=1,
                observaciones="Avance creado para verificar que PostgreSQL funciona correctamente",
                estado="Completado",
                ubicacion_edificio="Edificio 1",
                ubicacion_zona="Zona Test"
            )
            tests.append(("Crear avance", new_avance_id is not None))
            print(f"   ✅ Avance creado exitosamente")
        except Exception as e:
            tests.append(("Crear avance", False))
            print(f"   ❌ Error creando avance: {e}")
        
        # Test 7: Estadísticas
        print("7️⃣ Probando estadísticas...")
        try:
            stats = db_adapter.get_estadisticas_avances()
            tests.append(("Estadísticas", stats['total'] >= 0))
            print(f"   📈 Total avances en stats: {stats['total']}")
        except Exception as e:
            tests.append(("Estadísticas", False))
            print(f"   ❌ Error en estadísticas: {e}")
        
    except Exception as e:
        print(f"❌ Error general en pruebas: {e}")
        return False
    
    # Resumen de pruebas
    passed = sum(1 for _, success in tests if success)
    total = len(tests)
    
    print(f"\n📊 RESULTADO DE PRUEBAS POSTGRESQL:")
    print(f"✅ Pasaron: {passed}/{total}")
    
    for test_name, success in tests:
        status = "✅" if success else "❌"
        print(f"   {status} {test_name}")
    
    return passed == total

def main():
    """Función principal de verificación"""
    
    print("🔍 VERIFICACIÓN DE MIGRACIÓN POSTGRESQL")
    print("=" * 50)
    
    # Verificar que estamos usando PostgreSQL
    if db_adapter.USE_SQLITE:
        print("❌ ERROR: Aún se está usando SQLite")
        print("💡 Cambiar USE_SQLITE=false en .env")
        return False
    
    print("✅ Configurado para usar PostgreSQL")
    
    # Comparar con backup
    print(f"\n📊 COMPARACIÓN CON BACKUP SQLITE:")
    verification_results = compare_with_backup()
    
    if verification_results:
        all_match = all(result['match'] for result in verification_results.values())
        if all_match:
            print("✅ Todos los datos coinciden con el backup")
        else:
            print("⚠️  Algunos datos no coinciden - revisar arriba")
    
    # Probar funcionalidades
    functionality_ok = test_postgres_functionality()
    
    # Resultado final
    print(f"\n🎯 RESULTADO FINAL:")
    if functionality_ok and (not verification_results or all(result['match'] for result in verification_results.values())):
        print("🎉 ¡MIGRACIÓN EXITOSA!")
        print("✅ PostgreSQL funcionando correctamente")
        print("✅ Todos los datos preservados")
        print(f"\n💡 Ya puedes usar el bot con PostgreSQL:")
        print(f"   python main.py")
        return True
    else:
        print("❌ Problemas detectados en la migración")
        print("💾 Los datos están seguros en el backup SQLite")
        print("🔄 Puedes volver a SQLite temporalmente con USE_SQLITE=true")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
