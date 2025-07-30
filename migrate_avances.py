# migrate_avances.py
# Script para migrar la base de datos con las nuevas funcionalidades de avances

import psycopg2
import os
from datetime import datetime

# Configuración de base de datos
DB_NAME = os.getenv("DB_NAME", "telegrambot")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "contraseña CAMBIAR")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

def get_connection():
    """Establece conexión con la base de datos."""
    return psycopg2.connect(
        dbname=DB_NAME, 
        user=DB_USER, 
        password=DB_PASS, 
        host=DB_HOST, 
        port=DB_PORT
    )

def check_if_migrated():
    """Verifica si la migración ya fue aplicada."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Verificar si la tabla tipos_trabajo existe
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'tipos_trabajo'
                );
            """)
            return cur.fetchone()[0]
    except Exception as e:
        print(f"Error verificando migración: {e}")
        return False
    finally:
        conn.close()

def run_migration():
    """Ejecuta la migración de la base de datos."""
    if check_if_migrated():
        print("✅ La migración ya fue aplicada anteriormente.")
        return True
    
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            print("🔄 Iniciando migración de base de datos...")
            
            # 1. Crear tabla tipos_trabajo
            print("📋 Creando tabla tipos_trabajo...")
            cur.execute("""
                CREATE TABLE tipos_trabajo (
                    id SERIAL PRIMARY KEY,
                    nombre VARCHAR(255) NOT NULL UNIQUE,
                    emoji VARCHAR(10) DEFAULT '🔧',
                    activo BOOLEAN DEFAULT TRUE,
                    orden INTEGER DEFAULT 0,
                    creado_por BIGINT REFERENCES usuarios(user_id),
                    fecha_creacion TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """)
            
            # 2. Insertar tipos de trabajo por defecto
            print("🔧 Insertando tipos de trabajo por defecto...")
            tipos_default = [
                ('Albañilería', '🧱', 1),
                ('Electricidad', '⚡', 2),
                ('Fontanería', '🔧', 3),
                ('Pintura', '🎨', 4),
                ('Carpintería', '🪚', 5),
                ('Limpieza', '🧹', 6),
                ('Inspección', '🔍', 7),
                ('Otro', '📝', 8)
            ]
            
            for nombre, emoji, orden in tipos_default:
                cur.execute("""
                    INSERT INTO tipos_trabajo (nombre, emoji, orden) 
                    VALUES (%s, %s, %s);
                """, (nombre, emoji, orden))
            
            # 3. Agregar nuevas columnas a la tabla avances
            print("📊 Actualizando tabla avances...")
            
            # Verificar si las columnas ya existen
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'avances' AND column_name IN ('tipo_trabajo_id', 'observaciones');
            """)
            existing_columns = [row[0] for row in cur.fetchall()]
            
            if 'tipo_trabajo_id' not in existing_columns:
                cur.execute("""
                    ALTER TABLE avances 
                    ADD COLUMN tipo_trabajo_id INTEGER REFERENCES tipos_trabajo(id);
                """)
                print("  ✅ Columna tipo_trabajo_id agregada")
            
            if 'observaciones' not in existing_columns:
                cur.execute("""
                    ALTER TABLE avances 
                    ADD COLUMN observaciones TEXT;
                """)
                print("  ✅ Columna observaciones agregada")
            
            # 4. Crear índices para mejorar rendimiento
            print("🚀 Creando índices para optimización...")
            indices = [
                ("idx_avances_tipo_trabajo", "avances", "tipo_trabajo_id"),
                ("idx_avances_fecha_trabajo", "avances", "fecha_trabajo"),
                ("idx_avances_estado", "avances", "estado"),
                ("idx_avances_ubicacion_edificio", "avances", "ubicacion_edificio"),
                ("idx_tipos_trabajo_activo", "tipos_trabajo", "activo"),
                ("idx_tipos_trabajo_orden", "tipos_trabajo", "orden")
            ]
            
            for idx_name, table, column in indices:
                try:
                    cur.execute(f"""
                        CREATE INDEX IF NOT EXISTS {idx_name} 
                        ON {table} ({column});
                    """)
                    print(f"  ✅ Índice {idx_name} creado")
                except Exception as e:
                    print(f"  ⚠️ Error creando índice {idx_name}: {e}")
            
            # 5. Crear directorio para fotos de avances si no existe
            print("📁 Creando directorios necesarios...")
            import os
            os.makedirs('data/fotos_avances', exist_ok=True)
            print("  ✅ Directorio data/fotos_avances creado")
            
            # Confirmar cambios
            conn.commit()
            print("✅ Migración completada exitosamente!")
            
            # Mostrar resumen
            cur.execute("SELECT COUNT(*) FROM tipos_trabajo;")
            count_tipos = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM avances;")
            count_avances = cur.fetchone()[0]
            
            print(f"""
📊 RESUMEN DE MIGRACIÓN:
  • {count_tipos} tipos de trabajo configurados
  • {count_avances} avances existentes (compatibles)
  • Nuevas funcionalidades habilitadas:
    ✅ Jerarquía dinámica de ubicaciones
    ✅ Tipos de trabajo configurables
    ✅ Campo de observaciones
    ✅ Integración con calendario
    ✅ Sistema optimizado de registro
            """)
            
            return True
            
    except Exception as e:
        conn.rollback()
        print(f"❌ Error durante la migración: {e}")
        return False
    finally:
        conn.close()

def verify_migration():
    """Verifica que la migración se aplicó correctamente."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            print("🔍 Verificando migración...")
            
            # Verificar tabla tipos_trabajo
            cur.execute("SELECT COUNT(*) FROM tipos_trabajo WHERE activo = TRUE;")
            tipos_activos = cur.fetchone()[0]
            
            # Verificar columnas en avances
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'avances' 
                AND column_name IN ('tipo_trabajo_id', 'observaciones');
            """)
            columnas_nuevas = len(cur.fetchall())
            
            if tipos_activos >= 8 and columnas_nuevas == 2:
                print("✅ Migración verificada correctamente!")
                print(f"  • {tipos_activos} tipos de trabajo activos")
                print("  • Nuevas columnas en tabla avances: OK")
                return True
            else:
                print("❌ La migración no se completó correctamente")
                return False
                
    except Exception as e:
        print(f"❌ Error verificando migración: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("🚀 MIGRACIÓN DEL SISTEMA DE AVANCES")
    print("=" * 50)
    
    try:
        # Ejecutar migración
        if run_migration():
            # Verificar migración
            if verify_migration():
                print("\n🎉 ¡Migración completada exitosamente!")
                print("\nEl sistema de avances mejorado está listo para usar.")
                print("\nNuevas funcionalidades disponibles:")
                print("• Técnicos: Gestionar estructura jerárquica y tipos de trabajo")
                print("• Encargados: Registro optimizado con mínimos clicks")
                print("• Gerentes: Visualización completa de avances")
            else:
                print("\n⚠️ La migración se ejecutó pero hay problemas en la verificación.")
        else:
            print("\n❌ Error durante la migración.")
            
    except Exception as e:
        print(f"\n💥 Error crítico: {e}")
    
    print("\n" + "=" * 50)
