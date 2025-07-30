"""
Adaptador de base de datos que permite usar SQLite o PostgreSQL
según la disponibilidad. Optimizado para Synology DS1520+ / DSM 7.2
"""
import os
import sqlite3
import time
import logging
from datetime import datetime
from pathlib import Path

# Configuración de logging para Synology
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/db_adapter.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuración de base de datos con variables de entorno para Synology
USE_SQLITE = os.getenv("USE_SQLITE", "false").lower() == "true"  # PostgreSQL por defecto para Synology
SQLITE_PATH = Path(__file__).parent / 'data' / 'bot_telegram.db'

if USE_SQLITE:
    logger.info(f"🔄 Usando SQLite: {SQLITE_PATH}")
else:
    logger.info("🔄 Usando PostgreSQL para Synology DS1520+")
    try:
        import psycopg2
        import psycopg2.extras
    except ImportError:
        logger.error("❌ psycopg2 no está instalado. Instalar con: pip install psycopg2-binary")
        raise

# Configuración PostgreSQL optimizada para Synology
DB_NAME = os.getenv("POSTGRES_DB", "bot_telegram_db")
DB_USER = os.getenv("POSTGRES_USER", "bot_admin")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_HOST = os.getenv("POSTGRES_HOST", "db")  # Nombre del servicio en docker-compose
DB_PORT = os.getenv("POSTGRES_PORT", "5432")

# Configuración de conexión para Synology (más robusta)
CONNECTION_POOL_SIZE = int(os.getenv("POOL_SIZE", "10"))
MAX_OVERFLOW = int(os.getenv("MAX_OVERFLOW", "20"))
CONNECTION_TIMEOUT = int(os.getenv("CONNECTION_TIMEOUT", "30"))

def get_connection(retries=3, delay=5):
    """
    Establece y devuelve una conexión con la base de datos.
    Incluye reintentos para mayor robustez en Synology.
    """
    if USE_SQLITE:
        try:
            # Asegurar que el directorio existe
            SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(SQLITE_PATH))
            conn.row_factory = sqlite3.Row  # Para acceder por nombre de columna
            return conn
        except Exception as e:
            logger.error(f"❌ Error conectando a SQLite: {e}")
            raise
    else:
        # PostgreSQL con reintentos para Synology
        for attempt in range(retries):
            try:
                conn = psycopg2.connect(
                    dbname=DB_NAME, 
                    user=DB_USER, 
                    password=DB_PASS, 
                    host=DB_HOST, 
                    port=DB_PORT,
                    connect_timeout=CONNECTION_TIMEOUT
                )
                logger.info(f"✅ Conectado a PostgreSQL (intento {attempt + 1})")
                return conn
            except psycopg2.OperationalError as e:
                logger.warning(f"⚠️  Intento {attempt + 1} fallido: {e}")
                if attempt < retries - 1:
                    logger.info(f"⏳ Reintentando en {delay} segundos...")
                    time.sleep(delay)
                else:
                    logger.error(f"❌ No se pudo conectar a PostgreSQL después de {retries} intentos")
                    raise
            except Exception as e:
                logger.error(f"❌ Error inesperado conectando a PostgreSQL: {e}")
                raise

def execute_query(query, params=None, fetch_one=False, fetch_all=False):
    """Ejecuta una consulta adaptada para SQLite/PostgreSQL"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # Adaptar query para SQLite si es necesario
        if USE_SQLITE:
            query = query.replace('%s', '?')
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        if fetch_one:
            result = cursor.fetchone()
            return dict(result) if result and USE_SQLITE else result
        elif fetch_all:
            results = cursor.fetchall()
            return [dict(row) for row in results] if USE_SQLITE else results
        else:
            conn.commit()
            return cursor.rowcount
    finally:
        conn.close()

# =============================================================================
# FUNCIONES DE USUARIOS
# =============================================================================

def get_user_role(user_id):
    """Obtiene el rol de un usuario a partir de su ID."""
    result = execute_query("SELECT role FROM usuarios WHERE user_id = %s", (user_id,), fetch_one=True)
    return result['role'] if result else None

def user_exists(user_id):
    """Verifica si un usuario existe en la base de datos."""
    result = execute_query("SELECT 1 FROM usuarios WHERE user_id = %s", (user_id,), fetch_one=True)
    return result is not None

def register_user(user_id, username, first_name, role):
    """Registra un usuario en la base de datos."""
    return execute_query(
        "INSERT INTO usuarios (user_id, username, first_name, role) VALUES (%s, %s, %s, %s)",
        (user_id, username, first_name, role)
    )

def get_all_users():
    """Obtiene todos los usuarios de la base de datos."""
    return execute_query("SELECT * FROM usuarios", fetch_all=True)

def update_user_role(user_id, new_role):
    """Actualiza el rol de un usuario."""
    return execute_query(
        "UPDATE usuarios SET role = %s WHERE user_id = %s",
        (new_role, user_id)
    )

def delete_user(user_id):
    """Elimina un usuario de la base de datos."""
    return execute_query("DELETE FROM usuarios WHERE user_id = %s", (user_id,))

# =============================================================================
# FUNCIONES DE ADMINISTRACIÓN (NUEVAS)
# =============================================================================

def reset_database_safely(preserve_admin_user_id=195947658):
    """
    Limpia todas las tablas pero preserva el usuario admin especificado.
    Solo usuarios con rol Admin pueden ejecutar esta función.
    """
    try:
        # Primero verificar que el usuario a preservar existe y es admin
        admin_user = execute_query(
            "SELECT user_id, username, first_name, role FROM usuarios WHERE user_id = %s AND role = 'Admin'",
            (preserve_admin_user_id,),
            fetch_one=True
        )
        
        if not admin_user:
            raise Exception(f"Usuario admin {preserve_admin_user_id} no encontrado o no es Admin")
        
        # Orden de limpieza (respetando dependencias)
        cleanup_queries = [
            "DELETE FROM avances",
            "DELETE FROM incidencias WHERE id IS NOT NULL",  # Si existe la tabla
            "DELETE FROM pedidos WHERE id IS NOT NULL",      # Si existe la tabla
            "DELETE FROM averias WHERE id IS NOT NULL",      # Si existe la tabla
            "DELETE FROM registros_personal WHERE id IS NOT NULL",  # Si existe la tabla
            "DELETE FROM usuarios WHERE user_id != %s",  # Preservar admin
            "DELETE FROM tipos_trabajo WHERE id IS NOT NULL",
            "DELETE FROM ubicaciones_config WHERE id IS NOT NULL",
            "DELETE FROM almacen_items WHERE id IS NOT NULL"
        ]
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Deshabilitar checks de foreign key temporalmente si es PostgreSQL
        if not USE_SQLITE:
            cursor.execute("SET session_replication_role = 'replica'")
        
        deleted_counts = {}
        
        for query in cleanup_queries:
            try:
                # Contar antes de eliminar
                table_name = query.split("FROM ")[1].split(" ")[0]
                count_query = f"SELECT COUNT(*) FROM {table_name}"
                if "WHERE" in query:
                    count_query += " " + query.split("WHERE", 1)[1]
                
                if USE_SQLITE:
                    count_query = count_query.replace('%s', '?')
                    
                if preserve_admin_user_id and "%s" in query:
                    cursor.execute(count_query, (preserve_admin_user_id,))
                else:
                    cursor.execute(count_query)
                    
                before_count = cursor.fetchone()[0]
                
                # Ejecutar limpieza
                if USE_SQLITE:
                    query = query.replace('%s', '?')
                    
                if preserve_admin_user_id and "%s" in query:
                    cursor.execute(query, (preserve_admin_user_id,))
                else:
                    cursor.execute(query)
                
                affected = cursor.rowcount
                deleted_counts[table_name] = {
                    'before': before_count,
                    'deleted': affected,
                    'remaining': before_count - affected
                }
                
            except Exception as e:
                # Algunas tablas pueden no existir, continuar
                print(f"⚠️ Error limpiando {table_name}: {e}")
                continue
        
        # Restablecer foreign key checks
        if not USE_SQLITE:
            cursor.execute("SET session_replication_role = 'origin'")
        
        # Reinsertar datos básicos
        print("📥 Reinsertando datos básicos...")
        
        # Tipos de trabajo por defecto
        tipos_trabajo_default = [
            ('Albañilería', '🧱', 1),
            ('Electricidad', '⚡', 2),
            ('Fontanería', '🔧', 3),
            ('Pintura', '🎨', 4),
            ('Carpintería', '🪚', 5),
            ('Limpieza', '🧹', 6),
            ('Inspección', '🔍', 7),
            ('Otro', '📝', 8)
        ]
        
        insert_tipo_query = "INSERT INTO tipos_trabajo (nombre, emoji, orden, creado_por) VALUES (%s, %s, %s, %s)"
        if USE_SQLITE:
            insert_tipo_query = insert_tipo_query.replace('%s', '?')
            
        for nombre, emoji, orden in tipos_trabajo_default:
            cursor.execute(insert_tipo_query, (nombre, emoji, orden, preserve_admin_user_id))
        
        # Ubicaciones por defecto
        ubicaciones_default = [
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
        
        insert_ub_query = "INSERT INTO ubicaciones_config (tipo, nombre) VALUES (%s, %s)"
        if USE_SQLITE:
            insert_ub_query = insert_ub_query.replace('%s', '?')
            
        for tipo, nombre in ubicaciones_default:
            cursor.execute(insert_ub_query, (tipo, nombre))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Resumen
        total_deleted = sum(info['deleted'] for info in deleted_counts.values())
        
        return {
            'success': True,
            'preserved_admin': admin_user,
            'deleted_counts': deleted_counts,
            'total_deleted': total_deleted,
            'message': f'Base de datos limpiada. {total_deleted} registros eliminados. Admin {admin_user["first_name"] if USE_SQLITE else admin_user[2]} preservado.'
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message': f'Error limpiando base de datos: {e}'
        }

def get_database_statistics():
    """Obtiene estadísticas generales de la base de datos."""
    try:
        tables_info = {}
        
        # Lista de tablas principales
        main_tables = ['usuarios', 'tipos_trabajo', 'ubicaciones_config', 'avances', 'almacen_items']
        
        for table in main_tables:
            try:
                count_result = execute_query(f"SELECT COUNT(*) FROM {table}", fetch_one=True)
                count = count_result[0] if not USE_SQLITE else count_result['COUNT(*)']
                tables_info[table] = count
            except:
                tables_info[table] = 0
        
        # Información adicional de avances
        try:
            avances_stats = get_estadisticas_avances()
            tables_info['avances_stats'] = avances_stats
        except:
            tables_info['avances_stats'] = {'total': 0, 'por_tipo': [], 'por_encargado': []}
        
        return {
            'success': True,
            'tables': tables_info,
            'database_type': 'SQLite' if USE_SQLITE else 'PostgreSQL'
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def backup_database_to_json():
    """Crea un backup completo de la base de datos en formato JSON."""
    try:
        from datetime import datetime
        import json
        
        backup_data = {
            'backup_date': datetime.now().isoformat(),
            'database_type': 'SQLite' if USE_SQLITE else 'PostgreSQL',
            'tables': {}
        }
        
        # Tablas a respaldar
        tables_to_backup = ['usuarios', 'tipos_trabajo', 'ubicaciones_config', 'avances', 'almacen_items']
        
        total_records = 0
        
        for table in tables_to_backup:
            try:
                data = execute_query(f"SELECT * FROM {table}", fetch_all=True)
                if data:
                    backup_data['tables'][table] = [dict(row) if USE_SQLITE else list(row) for row in data]
                    total_records += len(data)
                else:
                    backup_data['tables'][table] = []
            except Exception as e:
                backup_data['tables'][table] = []
                print(f"⚠️ Error respaldando {table}: {e}")
        
        # Guardar backup
        backup_dir = Path(__file__).parent / 'data' / 'backups'
        backup_dir.mkdir(exist_ok=True)
        
        backup_filename = f'backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        backup_path = backup_dir / backup_filename
        
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False, default=str)
        
        return {
            'success': True,
            'backup_path': str(backup_path),
            'total_records': total_records,
            'tables_backed_up': len(tables_to_backup)
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

# =============================================================================
# FUNCIONES DE TIPOS DE TRABAJO (NUEVAS)
# =============================================================================

def get_tipos_trabajo_activos():
    """Obtiene todos los tipos de trabajo activos ordenados por orden."""
    return execute_query(
        "SELECT * FROM tipos_trabajo WHERE activo = TRUE ORDER BY orden, nombre",
        fetch_all=True
    )

def create_tipo_trabajo(nombre, emoji, creado_por, orden=0):
    """Crea un nuevo tipo de trabajo."""
    return execute_query(
        "INSERT INTO tipos_trabajo (nombre, emoji, creado_por, orden) VALUES (%s, %s, %s, %s)",
        (nombre, emoji, creado_por, orden)
    )

def update_tipo_trabajo(tipo_id, nombre=None, emoji=None, activo=None, orden=None):
    """Actualiza un tipo de trabajo existente."""
    updates = []
    params = []
    
    if nombre is not None:
        updates.append("nombre = %s")
        params.append(nombre)
    if emoji is not None:
        updates.append("emoji = %s")
        params.append(emoji)
    if activo is not None:
        updates.append("activo = %s")
        params.append(activo)
    if orden is not None:
        updates.append("orden = %s")
        params.append(orden)
    
    if updates:
        params.append(tipo_id)
        query = f"UPDATE tipos_trabajo SET {', '.join(updates)} WHERE id = %s"
        return execute_query(query, params)
    return 0

def delete_tipo_trabajo(tipo_id):
    """Desactiva un tipo de trabajo."""
    return execute_query(
        "UPDATE tipos_trabajo SET activo = FALSE WHERE id = %s",
        (tipo_id,)
    )

# =============================================================================
# FUNCIONES DE UBICACIONES (NUEVAS)
# =============================================================================

def get_jerarquia_ubicaciones():
    """Obtiene la jerarquía completa de ubicaciones."""
    return execute_query(
        "SELECT tipo, nombre FROM ubicaciones_config ORDER BY tipo, nombre",
        fetch_all=True
    )

def get_ubicaciones_por_tipo(tipo):
    """Obtiene ubicaciones filtradas por tipo."""
    return execute_query(
        "SELECT nombre FROM ubicaciones_config WHERE tipo = %s ORDER BY nombre",
        (tipo,),
        fetch_all=True
    )

def add_ubicacion(tipo, nombre):
    """Añade una nueva ubicación."""
    return execute_query(
        "INSERT INTO ubicaciones_config (tipo, nombre) VALUES (%s, %s)",
        (tipo, nombre)
    )

def delete_ubicacion(tipo, nombre):
    """Elimina una ubicación."""
    return execute_query(
        "DELETE FROM ubicaciones_config WHERE tipo = %s AND nombre = %s",
        (tipo, nombre)
    )

# =============================================================================
# FUNCIONES DE AVANCES (EXTENDIDAS)
# =============================================================================

def insert_avance_extendido(encargado_id, ubicacion_completa, trabajo, tipo_trabajo_id=None, 
                           observaciones=None, foto_path=None, estado="Completado", 
                           fecha_trabajo=None, ubicacion_edificio=None, ubicacion_zona=None, 
                           ubicacion_planta=None, ubicacion_nucleo=None):
    """Inserta un avance con la estructura extendida."""
    return execute_query("""
        INSERT INTO avances (encargado_id, ubicacion_completa, trabajo, tipo_trabajo_id, 
                           observaciones, foto_path, estado, fecha_trabajo, 
                           ubicacion_edificio, ubicacion_zona, ubicacion_planta, ubicacion_nucleo)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (encargado_id, ubicacion_completa, trabajo, tipo_trabajo_id, observaciones, 
          foto_path, estado, fecha_trabajo, ubicacion_edificio, ubicacion_zona, 
          ubicacion_planta, ubicacion_nucleo))

def get_avances_with_filters_extended(fecha_inicio=None, fecha_fin=None, encargado_id=None, 
                                    tipo_trabajo_id=None, ubicacion_edificio=None, 
                                    ubicacion_zona=None, ubicacion_planta=None, 
                                    ubicacion_nucleo=None, limit=50):
    """Obtiene avances con filtros extendidos."""
    where_conditions = []
    params = []
    
    if fecha_inicio:
        where_conditions.append("fecha_trabajo >= %s")
        params.append(fecha_inicio)
    if fecha_fin:
        where_conditions.append("fecha_trabajo <= %s")
        params.append(fecha_fin)
    if encargado_id:
        where_conditions.append("encargado_id = %s")
        params.append(encargado_id)
    if tipo_trabajo_id:
        where_conditions.append("tipo_trabajo_id = %s")
        params.append(tipo_trabajo_id)
    if ubicacion_edificio:
        where_conditions.append("ubicacion_edificio = %s")
        params.append(ubicacion_edificio)
    if ubicacion_zona:
        where_conditions.append("ubicacion_zona = %s")
        params.append(ubicacion_zona)
    if ubicacion_planta:
        where_conditions.append("ubicacion_planta = %s")
        params.append(ubicacion_planta)
    if ubicacion_nucleo:
        where_conditions.append("ubicacion_nucleo = %s")
        params.append(ubicacion_nucleo)
    
    where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
    
    query = f"""
        SELECT a.*, u.first_name as encargado_nombre, tt.nombre as tipo_trabajo_nombre, tt.emoji
        FROM avances a
        LEFT JOIN usuarios u ON a.encargado_id = u.user_id
        LEFT JOIN tipos_trabajo tt ON a.tipo_trabajo_id = tt.id
        {where_clause}
        ORDER BY a.fecha_registro DESC
        LIMIT %s
    """
    
    params.append(limit)
    return execute_query(query, params, fetch_all=True)

def get_estadisticas_avances(fecha_inicio=None, fecha_fin=None):
    """Obtiene estadísticas de avances."""
    where_conditions = []
    params = []
    
    if fecha_inicio:
        where_conditions.append("fecha_trabajo >= %s")
        params.append(fecha_inicio)
    if fecha_fin:
        where_conditions.append("fecha_trabajo <= %s")
        params.append(fecha_fin)
    
    where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
    
    # Total avances
    total_query = f"SELECT COUNT(*) as total FROM avances{where_clause}"
    total_result = execute_query(total_query, params, fetch_one=True)
    total = total_result['total'] if total_result else 0
    
    # Por tipo de trabajo
    tipos_query = f"""
        SELECT tt.nombre, tt.emoji, COUNT(*) as cantidad
        FROM avances a
        LEFT JOIN tipos_trabajo tt ON a.tipo_trabajo_id = tt.id
        {where_clause}
        GROUP BY tt.nombre, tt.emoji
        ORDER BY cantidad DESC
    """
    tipos_result = execute_query(tipos_query, params, fetch_all=True)
    
    # Por encargado
    encargados_query = f"""
        SELECT u.first_name, COUNT(*) as cantidad
        FROM avances a
        LEFT JOIN usuarios u ON a.encargado_id = u.user_id
        {where_clause}
        GROUP BY u.first_name
        ORDER BY cantidad DESC
    """
    encargados_result = execute_query(encargados_query, params, fetch_all=True)
    
    return {
        'total': total,
        'por_tipo': tipos_result or [],
        'por_encargado': encargados_result or []
    }

# =============================================================================
# FUNCIONES EXISTENTES (mantener compatibilidad)
# =============================================================================

def insert_avance(encargado_id, ubicacion, trabajo, foto_path=None, estado="Completado", fecha_trabajo=None):
    """Función original de avances (mantener compatibilidad)."""
    return insert_avance_extendido(
        encargado_id=encargado_id,
        ubicacion_completa=ubicacion,
        trabajo=trabajo,
        foto_path=foto_path,
        estado=estado,
        fecha_trabajo=fecha_trabajo
    )

def get_avances():
    """Función original para obtener avances."""
    return get_avances_with_filters_extended(limit=100)

def get_avances_by_date_range(fecha_inicio, fecha_fin):
    """Función original para obtener avances por rango de fechas."""
    return get_avances_with_filters_extended(fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)

# Test function para verificar conectividad
def test_database_connection():
    """Prueba la conexión a la base de datos."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if USE_SQLITE:
            cursor.execute("SELECT COUNT(*) FROM tipos_trabajo")
        else:
            cursor.execute("SELECT COUNT(*) FROM tipos_trabajo")
        
        result = cursor.fetchone()
        count = result[0] if result else 0
        
        conn.close()
        
        print(f"✅ Conexión exitosa! Tipos de trabajo: {count}")
        return True
        
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False

if __name__ == "__main__":
    print(f"🔧 Probando conexión de base de datos...")
    test_database_connection()
