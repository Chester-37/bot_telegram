"""
Script de prueba completo para verificar que el sistema de avances funciona correctamente.
Prueba todas las funcionalidades nuevas implementadas.
"""
import os
import sys
from pathlib import Path

# Añadir el directorio del proyecto al path
sys.path.insert(0, str(Path(__file__).parent))

# Configurar variable de entorno para usar SQLite
os.environ['USE_SQLITE'] = 'true'

import db_adapter
from avances import avances_utils
from datetime import datetime, date

def test_database_connection():
    """Prueba la conexión a la base de datos"""
    print("🔧 Probando conexión de base de datos...")
    return db_adapter.test_database_connection()

def test_tipos_trabajo():
    """Prueba las funciones de tipos de trabajo"""
    print("\n🔧 Probando tipos de trabajo...")
    
    try:
        # Obtener tipos de trabajo
        tipos = db_adapter.get_tipos_trabajo_activos()
        print(f"✅ Tipos de trabajo obtenidos: {len(tipos)}")
        
        for tipo in tipos[:3]:  # Mostrar solo los primeros 3
            if db_adapter.USE_SQLITE:
                print(f"   - {tipo['emoji']} {tipo['nombre']}")
            else:
                print(f"   - {tipo[1]} {tipo[2]}")  # emoji, nombre
        
        return True
    except Exception as e:
        print(f"❌ Error en tipos de trabajo: {e}")
        return False

def test_ubicaciones():
    """Prueba las funciones de ubicaciones"""
    print("\n📍 Probando ubicaciones...")
    
    try:
        # Obtener jerarquía completa
        jerarquia = db_adapter.get_jerarquia_ubicaciones()
        print(f"✅ Ubicaciones obtenidas: {len(jerarquia)}")
        
        # Agrupar por tipo
        tipos = {}
        for ub in jerarquia:
            if db_adapter.USE_SQLITE:
                tipo = ub['tipo']
                nombre = ub['nombre']
            else:
                tipo = ub[0]
                nombre = ub[1]
            
            if tipo not in tipos:
                tipos[tipo] = []
            tipos[tipo].append(nombre)
        
        for tipo, nombres in tipos.items():
            print(f"   {tipo}: {len(nombres)} opciones")
        
        return True
    except Exception as e:
        print(f"❌ Error en ubicaciones: {e}")
        return False

def test_avances_creation():
    """Prueba la creación de avances"""
    print("\n📊 Probando creación de avances...")
    
    try:
        # Crear un avance de prueba
        resultado = db_adapter.insert_avance_extendido(
            encargado_id=195947658,  # Nico (admin)
            ubicacion_completa="Edificio 1 > Planta 1 > Zona 1",
            trabajo="Prueba de sistema",
            tipo_trabajo_id=1,  # Albañilería
            observaciones="Avance de prueba del sistema nuevo",
            estado="Completado",
            fecha_trabajo=date.today(),
            ubicacion_edificio="Edificio 1",
            ubicacion_zona="Zona 1",
            ubicacion_planta="Planta 1",
            ubicacion_nucleo=None
        )
        
        print(f"✅ Avance creado exitosamente")
        return True
    except Exception as e:
        print(f"❌ Error creando avance: {e}")
        return False

def test_avances_query():
    """Prueba las consultas de avances"""
    print("\n📋 Probando consultas de avances...")
    
    try:
        # Obtener avances con filtros
        avances = db_adapter.get_avances_with_filters_extended(limit=5)
        print(f"✅ Avances obtenidos: {len(avances)}")
        
        for avance in avances:
            if db_adapter.USE_SQLITE:
                fecha = avance['fecha_trabajo'] or avance['fecha_registro'][:10]
                trabajo = avance['trabajo']
                tipo = avance['tipo_trabajo_nombre'] or 'Sin tipo'
                emoji = avance['emoji'] or '📝'
            else:
                fecha = str(avance[13] or avance[11])[:10]  # fecha_trabajo o fecha_registro
                trabajo = avance[6]
                tipo = avance[-2] or 'Sin tipo'
                emoji = avance[-1] or '📝'
            
            print(f"   {emoji} {fecha}: {trabajo} ({tipo})")
        
        return True
    except Exception as e:
        print(f"❌ Error consultando avances: {e}")
        return False

def test_estadisticas():
    """Prueba las estadísticas de avances"""
    print("\n📈 Probando estadísticas...")
    
    try:
        stats = db_adapter.get_estadisticas_avances()
        print(f"✅ Estadísticas generadas")
        print(f"   Total avances: {stats['total']}")
        print(f"   Tipos de trabajo: {len(stats['por_tipo'])}")
        print(f"   Encargados: {len(stats['por_encargado'])}")
        
        return True
    except Exception as e:
        print(f"❌ Error en estadísticas: {e}")
        return False

def test_avances_utils():
    """Prueba las utilidades de avances"""
    print("\n🛠️  Probando utilidades...")
    
    try:
        # Probar construcción de ubicación
        ubicacion_data = {
            'edificio': 'Edificio 1',
            'zona': 'Zona 2', 
            'planta': 'Planta 1',
            'nucleo': 'Núcleo A'
        }
        ubicacion = avances_utils.build_ubicacion_string(ubicacion_data)
        print(f"✅ Ubicación construida: {ubicacion}")
        
        # Probar validación de descripción de trabajo
        trabajo_valido = avances_utils.validate_work_description("Instalación de tubería")
        print(f"✅ Validación de trabajo: {trabajo_valido}")
        
        # Probar permisos de usuario
        puede_gestionar = avances_utils.can_user_manage_avances("Tecnico")
        print(f"✅ Permisos técnico: {puede_gestionar}")
        
        return True
    except Exception as e:
        print(f"❌ Error en utilidades: {e}")
        return False

def run_all_tests():
    """Ejecuta todas las pruebas"""
    print("🚀 INICIANDO PRUEBAS DEL SISTEMA DE AVANCES")
    print("=" * 50)
    
    tests = [
        ("Conexión de base de datos", test_database_connection),
        ("Tipos de trabajo", test_tipos_trabajo),
        ("Ubicaciones", test_ubicaciones),
        ("Creación de avances", test_avances_creation),
        ("Consultas de avances", test_avances_query),
        ("Estadísticas", test_estadisticas),
        ("Utilidades", test_avances_utils)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Error inesperado en {test_name}: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print("📊 RESULTADOS DE LAS PRUEBAS")
    print(f"✅ Pasaron: {passed}")
    print(f"❌ Fallaron: {failed}")
    print(f"📋 Total: {len(tests)}")
    
    if failed == 0:
        print("\n🎉 ¡TODAS LAS PRUEBAS PASARON EXITOSAMENTE!")
        print("✅ El sistema de avances está listo para usar")
        return True
    else:
        print(f"\n⚠️  Algunas pruebas fallaron. Revisar los errores arriba.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    
    if success:
        print(f"\n💡 PRÓXIMOS PASOS:")
        print(f"1. Configurar BOT_TOKEN en .env")
        print(f"2. Ejecutar: python main.py")
        print(f"3. Probar funcionalidades en Telegram")
        print(f"4. Opcional: Migrar a PostgreSQL más tarde")
    
    sys.exit(0 if success else 1)
