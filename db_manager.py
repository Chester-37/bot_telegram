import psycopg2
import os
from datetime import datetime
"""
DB_NAME = "telegrambot"
DB_USER = "postgres"
DB_PASS = "--"
DB_HOST = "localhost"
DB_PORT = "5432" 
""" # Añadido puerto 5433 Nico
DB_NAME = os.getenv("DB_NAME", "telegrambot")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "contraseña CAMBIAR") #TODO
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432") # Añadido puerto 5433 Nico

def get_connection():
    """Establece y devuelve una conexión con la base de datos."""
    return psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)

# =============================================================================
# FUNCIONES DE USUARIOS
# =============================================================================

def get_user_role(user_id):
    """Obtiene el rol de un usuario a partir de su ID."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT role FROM usuarios WHERE user_id = %s", (user_id,))
            result = cur.fetchone()
            return result[0] if result else None
    finally:
        conn.close()

def get_users_by_role(role):
    """Obtiene todos los usuarios con un rol específico."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id, first_name, username FROM usuarios WHERE role = %s", (role,))
            users = [{"id": row[0], "name": row[1], "username": row[2]} for row in cur.fetchall()]
            return users
    finally:
        conn.close()

def add_user_with_role(user_id, first_name, username, role):
    """Añade un nuevo usuario o actualiza el rol, nombre y username de uno existente."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = """
                INSERT INTO usuarios (user_id, first_name, username, role)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    first_name = EXCLUDED.first_name,
                    username = EXCLUDED.username,
                    role = EXCLUDED.role;
            """
            cur.execute(sql, (user_id, first_name, username, role))
            conn.commit()
    finally:
        conn.close()

def get_all_users():
    """Obtiene todos los usuarios registrados en la base de datos, ordenados por nombre."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id, first_name, role FROM usuarios ORDER BY first_name ASC")
            users = [{"id": row[0], "name": row[1], "role": row[2]} for row in cur.fetchall()]
            return users
    finally:
        conn.close()

def get_user_details(user_id):
    """Obtiene los detalles (nombre, username, rol) de un usuario específico."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id, first_name, username, role FROM usuarios WHERE user_id = %s", (user_id,))
            res = cur.fetchone()
            if not res:
                return None
            return {"id": res[0], "name": res[1], "username": res[2], "role": res[3]}
    finally:
        conn.close()

def update_user_role(user_id, new_role):
    """Actualiza únicamente el rol de un usuario existente."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE usuarios SET role = %s WHERE user_id = %s", (new_role, user_id))
            conn.commit()
    finally:
        conn.close()

# =============================================================================
# FUNCIONES DE GESTIÓN DE UBICACIONES
# =============================================================================

def get_ubicaciones_by_tipo(tipo):
    """Obtiene todas las ubicaciones de un tipo específico (ej: 'Edificio')."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, nombre FROM ubicaciones_config WHERE tipo = %s ORDER BY nombre", (tipo,))
            return [{"id": row[0], "nombre": row[1]} for row in cur.fetchall()]
    finally:
        conn.close()

def add_ubicacion(tipo, nombre):
    """Añade una nueva ubicación. Devuelve True si tiene éxito, False si ya existe."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO ubicaciones_config (tipo, nombre) VALUES (%s, %s)", (tipo, nombre))
            conn.commit()
    except psycopg2.IntegrityError:
        conn.rollback()
        return False
    finally:
        conn.close()
    return True

def delete_ubicacion(ubicacion_id):
    """Elimina una ubicación por su ID."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM ubicaciones_config WHERE id = %s", (ubicacion_id,))
            conn.commit()
    finally:
        conn.close()

def rename_ubicacion(ubicacion_id, nuevo_nombre):
    """Renombra una ubicación por su ID. Devuelve True si tiene éxito, False si el nuevo nombre ya existe."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE ubicaciones_config SET nombre = %s WHERE id = %s", (nuevo_nombre, ubicacion_id))
            conn.commit()
    except psycopg2.IntegrityError:
        conn.rollback()
        return False
    finally:
        conn.close()
    return True

# =============================================================================
# FUNCIONES DE GESTIÓN DE ALMACÉN
# =============================================================================
def add_or_update_almacen_item(nombre, cantidad, descripcion, tipo):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = """
                INSERT INTO almacen_items (nombre, cantidad, descripcion, tipo)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (nombre) DO UPDATE SET
                    cantidad = almacen_items.cantidad + EXCLUDED.cantidad,
                    descripcion = EXCLUDED.descripcion,
                    tipo = EXCLUDED.tipo;
            """
            cur.execute(sql, (nombre, cantidad, descripcion, tipo))
            conn.commit()
    finally:
        conn.close()

def get_almacen_items_paginated(item_type, page=0, items_per_page=5):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            offset = page * items_per_page
            if isinstance(item_type, str):
                item_type = [item_type]
            sql_items = "SELECT id, nombre, cantidad FROM almacen_items WHERE tipo = ANY(%s) ORDER BY nombre ASC LIMIT %s OFFSET %s;"
            sql_count = "SELECT COUNT(*) FROM almacen_items WHERE tipo = ANY(%s);"
            cur.execute(sql_items, (item_type, items_per_page, offset))
            items = [{"id": row[0], "nombre": row[1], "cantidad": row[2]} for row in cur.fetchall()]
            cur.execute(sql_count, (item_type,))
            total_items = cur.fetchone()[0]
            total_pages = (total_items + items_per_page - 1) // items_per_page if items_per_page > 0 else 0
            return items, total_pages
    finally:
        conn.close()

def get_almacen_item_details(item_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, nombre, cantidad, descripcion, tipo FROM almacen_items WHERE id = %s", (item_id,))
            res = cur.fetchone()
            if not res:
                return None
            return {"id": res[0], "nombre": res[1], "cantidad": res[2], "descripcion": res[3], "tipo": res[4]}
    finally:
        conn.close()

def update_almacen_item_quantity(item_id, nueva_cantidad):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE almacen_items SET cantidad = %s WHERE id = %s", (nueva_cantidad, item_id))
            conn.commit()
    finally:
        conn.close()

# =============================================================================
# FUNCIONES DE AVANCES E INCIDENCIAS
# =============================================================================
def create_avance(encargado_id, ubicacion_completa, trabajo, foto_path, estado, fecha_trabajo):
    """
    Inserta un nuevo avance en la base de datos, desglosando la ubicación en sus componentes
    y manteniendo la cadena completa.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            try:
                edificio, zona, planta, nucleo = [x.strip() for x in ubicacion_completa.split("/")]
            except ValueError:
                raise ValueError("La ubicación no está bien formada. Se esperaba el formato: 'Edificio / Zona / Planta / Núcleo'")

            sql = """
                INSERT INTO avances (
                    encargado_id,
                    ubicacion_edificio,
                    ubicacion_zona,
                    ubicacion_planta,
                    ubicacion_nucleo,
                    ubicacion_completa,
                    trabajo,
                    foto_path,
                    estado,
                    fecha_registro,
                    fecha_trabajo
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s)
                RETURNING id;
            """
            cur.execute(sql, (
                encargado_id,
                edificio,
                zona,
                planta,
                nucleo,
                ubicacion_completa,
                trabajo,
                foto_path,
                estado,
                fecha_trabajo
            ))
            avance_id = cur.fetchone()[0]
            conn.commit()
            return avance_id
    finally:
        conn.close()
        
def create_incidencia(avance_id, descripcion, reporta_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = "INSERT INTO incidencias (avance_id, descripcion, estado, fecha_reporte, reporta_id) VALUES (%s, %s, 'Pendiente', NOW(), %s) RETURNING id;"
            cur.execute(sql, (avance_id, descripcion, reporta_id))
            incidencia_id = cur.fetchone()[0]
            conn.commit()
            return incidencia_id
    finally:
        conn.close()

def create_tool_incidencia(reporta_id, item_id, descripcion, foto_path):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = "INSERT INTO incidencias (reporta_id, item_id, descripcion, foto_path, estado, fecha_reporte) VALUES (%s, %s, %s, %s, 'Pendiente', NOW()) RETURNING id;"
            cur.execute(sql, (reporta_id, item_id, descripcion, foto_path))
            incidencia_id = cur.fetchone()[0]
            conn.commit()
            return incidencia_id
    finally:
        conn.close()

def get_incidencias_by_estado(estados):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = """
                SELECT
                    i.id, i.descripcion, i.foto_path,
                    reporter.first_name AS reporter_name,
                    resolver.username AS resolver_username,
                    a.ubicacion_completa AS avance_ubicacion,
                    item.nombre AS item_name,
                    i.resolucion_desc, i.fecha_reporte 
                FROM incidencias i
                JOIN usuarios reporter ON i.reporta_id = reporter.user_id
                LEFT JOIN avances a ON i.avance_id = a.id
                LEFT JOIN almacen_items item ON i.item_id = item.id
                LEFT JOIN usuarios resolver ON i.tecnico_resolutor_id = resolver.user_id
                WHERE i.estado = ANY(%s)
                ORDER BY i.fecha_reporte DESC;
            """
            cur.execute(sql, (estados,))
            incidencias = []
            for row in cur.fetchall():
                incidencias.append({
                    "incidencia_id": row[0], "descripcion": row[1], "has_foto": bool(row[2]),
                    "reporter_name": row[3], "resolutor": row[4], "avance_ubicacion": row[5],
                    "item_name": row[6], "resolucion_desc": row[7], "fecha_reporte": row[8]
                })
            return incidencias
    finally:
        conn.close()

def get_incidencia_details(incidencia_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = "SELECT i.id, i.reporta_id, a.encargado_id FROM incidencias i LEFT JOIN avances a ON i.avance_id = a.id WHERE i.id = %s;"
            cur.execute(sql, (incidencia_id,))
            res = cur.fetchone()
            if not res: return None
            return {"id": res[0], "reporta_id": res[1], "encargado_id": res[2]}
    finally:
        conn.close()

def resolve_incidencia(incidencia_id, resolutor_id, resolucion_desc):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = "UPDATE incidencias SET estado = 'Resuelta', tecnico_resolutor_id = %s, resolucion_desc = %s, fecha_resolucion = NOW() WHERE id = %s;"
            cur.execute(sql, (resolutor_id, resolucion_desc, incidencia_id))
            conn.commit()
    finally:
        conn.close()
        
def get_foto_path_by_incidencia_id(incidencia_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT foto_path FROM incidencias WHERE id = %s", (incidencia_id,))
            result = cur.fetchone()
            return result[0] if result else None
    finally:
        conn.close()

def get_foto_path_by_avance_id(avance_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT foto_path FROM avances WHERE id = %s", (avance_id,))
            result = cur.fetchone()
            return result[0] if result else None
    finally:
        conn.close()

def add_incidencia_comentario(incidencia_id, usuario_id, comentario):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = "INSERT INTO incidencia_comentarios (incidencia_id, usuario_id, comentario) VALUES (%s, %s, %s);"
            cur.execute(sql, (incidencia_id, usuario_id, comentario))
            conn.commit()
    finally:
        conn.close()

# =============================================================================
# FUNCIONES DE GESTIÓN DE PEDIDOS
# =============================================================================
def create_pedido(solicitante_id, notas, group_chat_id=None):
    """Crea un nuevo registro de pedido, incluyendo el group_chat_id, y devuelve su ID."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            try:
                cur.execute("ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS group_chat_id BIGINT;")
                conn.commit()
            except psycopg2.Error as e:
                print(f"Advertencia: No se pudo añadir la columna group_chat_id a la tabla pedidos: {e}")
                conn.rollback()

            sql = "INSERT INTO pedidos (solicitante_id, notas_solicitud, estado, group_chat_id) VALUES (%s, %s, %s, %s) RETURNING id;"
            cur.execute(sql, (solicitante_id, notas, 'Pendiente Aprobacion', group_chat_id))
            pedido_id = cur.fetchone()[0]
            conn.commit()
            return pedido_id
    finally:
        conn.close()

def add_item_to_pedido(pedido_id, item_id, cantidad):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT nombre FROM almacen_items WHERE id = %s", (item_id,))
            item_res = cur.fetchone()
            if not item_res:
                print(f"Error: Item con ID {item_id} no encontrado para añadir al pedido {pedido_id}")
                return
            nombre_item = item_res[0]
            sql = "INSERT INTO pedido_items (pedido_id, item_id, cantidad_solicitada, nombre_item) VALUES (%s, %s, %s, %s);"
            cur.execute(sql, (pedido_id, item_id, cantidad, nombre_item))
            conn.commit()
    finally:
        conn.close()

def get_solicitante_id_by_pedido(pedido_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT solicitante_id FROM pedidos WHERE id = %s", (pedido_id,))
            result = cur.fetchone()
            return result[0] if result else None
    finally:
        conn.close()

def get_pedidos_by_estado(estado):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = "SELECT p.id, u.first_name, p.fecha_solicitud FROM pedidos p JOIN usuarios u ON p.solicitante_id = u.user_id WHERE p.estado = %s ORDER BY p.fecha_solicitud ASC;"
            cur.execute(sql, (estado,))
            pedidos = [{"id": row[0], "solicitante": row[1], "fecha": row[2].strftime('%d/%m/%y %H:%M')} for row in cur.fetchall()]
            return pedidos
    finally:
        conn.close()

def get_pedido_details(pedido_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql_pedido = "SELECT p.id, u.first_name, p.estado, p.notas_solicitud, p.notas_decision, p.fecha_solicitud, p.solicitante_id FROM pedidos p JOIN usuarios u ON p.solicitante_id = u.user_id WHERE p.id = %s;"
            cur.execute(sql_pedido, (pedido_id,))
            pedido_res = cur.fetchone()
            if not pedido_res: return None
            details = {"id": pedido_res[0], "solicitante": pedido_res[1], "estado": pedido_res[2], "notas_solicitud": pedido_res[3], "notas_decision": pedido_res[4], "fecha": pedido_res[5].strftime('%d/%m/%Y'), "solicitante_id": pedido_res[6], "items": []}
            sql_items = "SELECT nombre_item, cantidad_solicitada FROM pedido_items WHERE pedido_id = %s;"
            cur.execute(sql_items, (pedido_id,))
            for item_row in cur.fetchall():
                details["items"].append({"nombre": item_row[0], "cantidad_solicitada": item_row[1]})
            return details
    finally:
        conn.close()

def update_pedido_status(pedido_id, nuevo_estado, user_id, notas=""):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if nuevo_estado in ['Aprobado', 'Rechazado']:
                sql = "UPDATE pedidos SET estado = %s, aprobador_id = %s, notas_decision = %s, fecha_decision = NOW() WHERE id = %s;"
                cur.execute(sql, (nuevo_estado, user_id, notas, pedido_id))
            elif nuevo_estado == 'Listo para Recoger':
                sql = "UPDATE pedidos SET estado = %s, almacen_id = %s, fecha_preparado = NOW() WHERE id = %s;"
                cur.execute(sql, (nuevo_estado, user_id, pedido_id))
            else:
                sql = "UPDATE pedidos SET estado = %s WHERE id = %s;"
                cur.execute(sql, (nuevo_estado, pedido_id))
            conn.commit()
    finally:
        conn.close()

# =============================================================================
# FUNCIONES DE RRHH
# =============================================================================
def create_solicitud_personal(solicitante_id, puestos_data, fecha, notas, group_chat_id=None):
    """
    Crea una nueva solicitud de personal con múltiples puestos.
    :param puestos_data: Una lista de diccionarios, ej: [{'puesto': 'Oficial', 'cantidad': 2}]
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Paso 1: Crear la solicitud principal para obtener un ID
            sql_solicitud = """
                INSERT INTO solicitudes_personal (solicitante_id, fecha_incorporacion, notas_solicitud, estado)
                VALUES (%s, %s, %s, 'Pendiente Aprobacion') RETURNING id;
            """
            cur.execute(sql_solicitud, (solicitante_id, fecha, notas))
            solicitud_id = cur.fetchone()[0]

            # Paso 2: Insertar cada puesto en la nueva tabla de items
            sql_item = "INSERT INTO solicitud_personal_items (solicitud_id, puesto, cantidad) VALUES (%s, %s, %s);"
            for item in puestos_data:
                cur.execute(sql_item, (solicitud_id, item['puesto'], item['cantidad']))

            conn.commit()
            return solicitud_id
    finally:
        conn.close()

def get_solicitudes_by_solicitante(solicitante_id):
    """
    Obtiene las solicitudes de un usuario específico, agregando los puestos en un string.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # La consulta ahora une las tablas y usa STRING_AGG
            sql = """
                SELECT 
                    s.id, 
                    s.fecha_incorporacion, 
                    s.estado,
                    STRING_AGG(spi.cantidad || 'x ' || spi.puesto, ', ') AS puestos_agregados
                FROM solicitudes_personal s
                JOIN solicitud_personal_items spi ON s.id = spi.solicitud_id
                WHERE s.solicitante_id = %s
                GROUP BY s.id, s.fecha_incorporacion, s.estado
                ORDER BY s.fecha_solicitud DESC;
            """
            cur.execute(sql, (solicitante_id,))
            solicitudes = []
            for row in cur.fetchall():
                # Mapeamos los nuevos resultados al diccionario
                solicitudes.append({
                    "id": row[0], 
                    "fecha": row[1].strftime('%d/%m/%Y'), 
                    "estado": row[2],
                    # La clave 'puesto' ahora contiene el texto combinado
                    "puesto": row[3] 
                })
            return solicitudes
    finally:
        conn.close()

def get_solicitudes_by_estado(estados):
    """Obtiene solicitudes por estado, agregando los puestos en un solo string."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # MODIFICADO: Usamos STRING_AGG para concatenar los puestos de cada solicitud
            sql = """
                SELECT 
                    s.id, 
                    u.first_name,
                    STRING_AGG(spi.cantidad || 'x ' || spi.puesto, ', ') AS puestos_agregados
                FROM solicitudes_personal s
                JOIN usuarios u ON s.solicitante_id = u.user_id
                JOIN solicitud_personal_items spi ON s.id = spi.solicitud_id
                WHERE s.estado = ANY(%s)
                GROUP BY s.id, u.first_name
                ORDER BY s.fecha_solicitud ASC;
            """
            cur.execute(sql, (estados,))
            solicitudes = []
            for row in cur.fetchall():
                # El campo 'puesto' ahora contiene la cadena agregada
                solicitudes.append({"id": row[0], "solicitante": row[1], "puesto": row[2]})
            return solicitudes
    finally:
        conn.close()

def get_solicitud_details(solicitud_id):
    """Obtiene los detalles de una solicitud, incluyendo la lista de todos los puestos."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Consulta principal sin cambios
            sql_main = "SELECT s.id, s.fecha_incorporacion, s.estado, s.notas_solicitud, s.notas_decision, u_solicitante.first_name, u_tecnico.first_name, u_gerente.first_name, s.solicitante_id, s.tecnico_id FROM solicitudes_personal s JOIN usuarios u_solicitante ON s.solicitante_id = u_solicitante.user_id LEFT JOIN usuarios u_tecnico ON s.tecnico_id = u_tecnico.user_id LEFT JOIN usuarios u_gerente ON s.gerente_id = u_gerente.user_id WHERE s.id = %s;"
            cur.execute(sql_main, (solicitud_id,))
            res = cur.fetchone()
            if not res: return None
            
            # Inicializamos el diccionario de detalles
            details = {
                "id": res[0], "fecha": res[1].strftime('%d/%m/%Y'), "estado": res[2], 
                "notas_solicitud": res[3], "notas_decision": res[4], 
                "solicitante_name": res[5], "tecnico_name": res[6], "gerente_name": res[7], 
                "solicitante_id": res[8], "tecnico_id": res[9], 
                "puestos": [], # NUEVO: Lista para almacenar los puestos
                "historial_notas_rrhh": []
            }

            # NUEVO: Consulta para obtener todos los puestos de la solicitud
            sql_items = "SELECT puesto, cantidad FROM solicitud_personal_items WHERE solicitud_id = %s ORDER BY id;"
            cur.execute(sql_items, (solicitud_id,))
            for item_row in cur.fetchall():
                details["puestos"].append({"puesto": item_row[0], "cantidad": item_row[1]})

            # Consulta de notas sin cambios
            sql_notes = "SELECT n.nota, n.fecha_nota, u.first_name FROM solicitud_personal_notas n JOIN usuarios u ON n.rrhh_id = u.user_id WHERE n.solicitud_id = %s ORDER BY n.fecha_nota ASC;"
            cur.execute(sql_notes, (solicitud_id,))
            for nota_row in cur.fetchall():
                details["historial_notas_rrhh"].append({"nota": nota_row[0], "fecha": nota_row[1].strftime('%d/%m/%y %H:%M'), "autor": nota_row[2]})
            
            return details
    finally:
        conn.close()

def update_solicitud_status(solicitud_id, user_id, nuevo_estado, notas, rol_usuario):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            id_field = None
            if rol_usuario == 'Tecnico':
                id_field = "tecnico_id"
            elif rol_usuario == 'Gerente':
                id_field = "gerente_id"
            if id_field:
                sql = f"UPDATE solicitudes_personal SET estado = %s, {id_field} = %s, notas_decision = %s, fecha_decision = NOW() WHERE id = %s;"
                cur.execute(sql, (nuevo_estado, user_id, notas, solicitud_id))
            else:
                sql = "UPDATE solicitudes_personal SET estado = %s, notas_decision = %s, fecha_decision = NOW() WHERE id = %s;"
                cur.execute(sql, (nuevo_estado, notas, solicitud_id))
            conn.commit()
    finally:
        conn.close()

def create_prevencion_incidencia(reporta_id, ubicacion, descripcion, foto_path):
    """Crea una nueva incidencia de prevención y devuelve su ID."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = """
                INSERT INTO prevencion_incidencias (reporta_id, ubicacion, descripcion, foto_path, estado)
                VALUES (%s, %s, %s, %s, 'Abierta') RETURNING id;
            """
            cur.execute(sql, (reporta_id, ubicacion, descripcion, foto_path))
            incidencia_id = cur.fetchone()[0]
            conn.commit()
            return incidencia_id
    finally:
        conn.close()

def get_prevencion_incidencias_by_estado(estados):
    """Obtiene incidencias de prevención por uno o más estados."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = """
                SELECT
                    pi.id, pi.ubicacion, pi.descripcion, pi.estado,
                    pi.fecha_reporte, u_reporter.first_name, pi.foto_path IS NOT NULL AS has_foto
                FROM prevencion_incidencias pi
                JOIN usuarios u_reporter ON pi.reporta_id = u_reporter.user_id
                WHERE pi.estado = ANY(%s)
                ORDER BY pi.fecha_reporte DESC;
            """
            cur.execute(sql, (estados,))
            incidencias = []
            for row in cur.fetchall():
                incidencias.append({
                    "id": row[0], "ubicacion": row[1], "descripcion": row[2],
                    "estado": row[3], "fecha": row[4].strftime('%d/%m/%Y %H:%M'),
                    "reporta_nombre": row[5], "has_foto": row[6]
                })
            return incidencias
    finally:
        conn.close()

def get_prevencion_incidencia_details(incidencia_id):
    """Obtiene los detalles completos de una incidencia de prevención."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = "SELECT reporta_id, foto_path FROM prevencion_incidencias WHERE id = %s;"
            cur.execute(sql, (incidencia_id,))
            res = cur.fetchone()
            if not res: return None
            return {"reporta_id": res[0], "foto_path": res[1]}
    finally:
        conn.close()

def add_prevencion_comentario(incidencia_id, usuario_id, comentario):
    """Añade un comentario a una incidencia de prevención y actualiza el estado si es necesario."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Inserta el comentario
            sql_comment = "INSERT INTO prevencion_incidencia_comentarios (incidencia_id, usuario_id, comentario) VALUES (%s, %s, %s);"
            cur.execute(sql_comment, (incidencia_id, usuario_id, comentario))

            # Actualiza el estado de la incidencia a 'En Disputa'
            sql_update = "UPDATE prevencion_incidencias SET estado = 'En Disputa' WHERE id = %s;"
            cur.execute(sql_update, (incidencia_id,))
            conn.commit()
    finally:
        conn.close()

def close_prevencion_incidencia(incidencia_id, user_id):
    """Marca una incidencia de prevención como 'Cerrada'."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = "UPDATE prevencion_incidencias SET estado = 'Cerrada', cerrado_por_id = %s, fecha_cierre = NOW() WHERE id = %s;"
            cur.execute(sql, (user_id, incidencia_id))
            conn.commit()
    finally:
        conn.close()

def get_finalizados_paginated(page=0, items_per_page=5):
    """Obtiene una lista paginada de avances con estado 'Finalizado'."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            offset = page * items_per_page
            
            # Consulta para obtener los avances de la página actual
            sql_items = """
                SELECT id, trabajo, ubicacion_completa, fecha_trabajo
                FROM avances
                WHERE estado = 'Finalizado'
                ORDER BY fecha_trabajo DESC, id DESC
                LIMIT %s OFFSET %s;
            """
            cur.execute(sql_items, (items_per_page, offset))
            avances = [{"id": row[0], "trabajo": row[1], "ubicacion": row[2], "fecha_trabajo": row[3]} for row in cur.fetchall()]
            
            # Consulta para contar el total de avances finalizados
            sql_count = "SELECT COUNT(*) FROM avances WHERE estado = 'Finalizado';"
            cur.execute(sql_count)
            total_items = cur.fetchone()[0]
            total_pages = (total_items + items_per_page - 1) // items_per_page if items_per_page > 0 else 0
            
            return avances, total_pages
    finally:
        conn.close()

def get_avance_details(avance_id):
    """Obtiene los detalles completos de un avance específico."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = """
                SELECT a.id, a.ubicacion_completa, a.trabajo, a.foto_path, a.fecha_trabajo, u.first_name 
                FROM avances a
                JOIN usuarios u ON a.encargado_id = u.user_id
                WHERE a.id = %s;
            """
            cur.execute(sql, (avance_id,))
            res = cur.fetchone()
            if not res:
                return None
            return {
                "id": res[0], "ubicacion": res[1], "trabajo": res[2], 
                "foto_path": res[3], "fecha_trabajo": res[4], "encargado_name": res[5]
            }
    finally:
        conn.close()

def get_averias_by_estado(estados):
    """Obtiene todas las averías que coinciden con uno de los estados proporcionados."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Seleccionamos los campos necesarios para la lista en bot_averias.py
            sql = """
                SELECT id, maquina, fecha_reporte
                FROM averias
                WHERE estado = ANY(%s)
                ORDER BY fecha_reporte DESC;
            """
            cur.execute(sql, (estados,))
            averias = []
            for row in cur.fetchall():
                averias.append({
                    "id": row[0],
                    "maquina": row[1],
                    "fecha_reporte": row[2]
                })
            return averias
    finally:
        conn.close()

def get_full_inventory():
    """Obtiene todos los artículos del inventario, ordenados por tipo y nombre."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = "SELECT nombre, cantidad, tipo FROM almacen_items ORDER BY tipo, nombre;"
            cur.execute(sql)
            # Devuelve una lista de diccionarios para un manejo fácil
            return [{"nombre": row[0], "cantidad": row[1], "tipo": row[2]} for row in cur.fetchall()]
    finally:
        conn.close()

def get_material_en_obra():
    """
    Obtiene una lista agregada de todo el material que ha sido aprobado para obra,
    sumando las cantidades de cada artículo.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Seleccionamos los estados que indican que el material ya no está en el almacén.
            # Sumamos las cantidades por nombre de item para obtener un total consolidado.
            sql = """
                SELECT
                    pi.nombre_item,
                    SUM(pi.cantidad_solicitada) as total_cantidad
                FROM pedido_items pi
                JOIN pedidos p ON pi.pedido_id = p.id
                WHERE p.estado IN ('Aprobado', 'Listo para Recoger', 'Entregado')
                GROUP BY pi.nombre_item
                ORDER BY pi.nombre_item ASC;
            """
            cur.execute(sql)
            # Devolvemos los resultados como una lista de diccionarios para un manejo fácil.
            return [{"nombre": row[0], "cantidad": row[1]} for row in cur.fetchall()]
    finally:
        conn.close()

def get_tool_incidencias_by_estado(estados):
    """Obtiene incidencias de herramientas por estado, con el nombre de la herramienta."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = """
                SELECT
                    i.id,
                    i.descripcion,
                    i.fecha_reporte,
                    item.nombre as item_name
                FROM incidencias i
                JOIN almacen_items item ON i.item_id = item.id
                WHERE i.item_id IS NOT NULL AND i.estado = ANY(%s)
                ORDER BY i.fecha_reporte DESC;
            """
            cur.execute(sql, (estados,))
            return [{"id": row[0], "descripcion": row[1], "fecha": row[2], "herramienta": row[3]} for row in cur.fetchall()]
    finally:
        conn.close()

def get_tool_incidencia_details(incidencia_id):
    """Obtiene los detalles completos de una incidencia de herramienta."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = """
                SELECT
                    i.id, i.descripcion, i.estado, i.fecha_reporte, i.resolucion_desc, i.fecha_resolucion,
                    reporter.first_name as reporter_name,
                    resolver.first_name as resolver_name,
                    item.nombre as item_name,
                    i.foto_path
                FROM incidencias i
                JOIN usuarios reporter ON i.reporta_id = reporter.user_id
                JOIN almacen_items item ON i.item_id = item.id
                LEFT JOIN usuarios resolver ON i.tecnico_resolutor_id = resolver.user_id
                WHERE i.id = %s;
            """
            cur.execute(sql, (incidencia_id,))
            res = cur.fetchone()
            if not res: return None
            return {
                "id": res[0], "descripcion": res[1], "estado": res[2],
                "fecha_reporte": res[3], "resolucion_desc": res[4], "fecha_resolucion": res[5],
                "reporter_name": res[6], "resolver_name": res[7], "item_name": res[8],
                "has_foto": bool(res[9])
            }
    finally:
        conn.close()

def get_avances_for_report(filters, start_date=None, end_date=None):
    """
    Obtiene avances para un informe, usando filtros de ubicación y un rango de fechas opcional.
    MODIFICADO: Acepta start_date y end_date.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            base_sql = """
                SELECT a.id, a.ubicacion_completa, a.trabajo, a.estado, a.fecha_trabajo, u.first_name, u.username
                FROM avances a
                JOIN usuarios u ON a.encargado_id = u.user_id
            """
            where_clauses = []
            params = []

            # --- Filtro de Ubicación (sin cambios) ---
            pattern_parts = []
            filter_keys_ordered = ['edificio', 'planta', 'zona', 'trabajo']
            for key in filter_keys_ordered:
                if filters.get(key):
                    pattern_parts.append(filters.get(key))
                else:
                    break
            
            if pattern_parts:
                like_pattern = " / ".join(pattern_parts) + "%"
                where_clauses.append("a.ubicacion_completa LIKE %s")
                params.append(like_pattern)

            # --- NUEVO: Filtro de Fechas ---
            if start_date and end_date:
                where_clauses.append("a.fecha_trabajo BETWEEN %s AND %s")
                params.append(start_date)
                params.append(end_date)
            
            if where_clauses:
                base_sql += " WHERE " + " AND ".join(where_clauses)
            
            base_sql += " ORDER BY a.fecha_trabajo DESC, a.id DESC;"
            
            cur.execute(base_sql, tuple(params))
            
            avances = []
            for row in cur.fetchall():
                avances.append({
                    "id": row[0], "ubicacion": row[1], "trabajo": row[2],
                    "estado": row[3], "fecha": row[4], "encargado_nombre": row[5],
                    "encargado_username": row[6]
                })
            return avances
    finally:
        conn.close()

def get_incidencias_for_avances(avance_ids):
    """
    Obtiene todas las incidencias asociadas a una lista de IDs de avance.
    """
    if not avance_ids:
        return {}
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = """
                SELECT avance_id, id, descripcion, estado, fecha_reporte
                FROM incidencias
                WHERE avance_id = ANY(%s)
                ORDER BY fecha_reporte ASC;
            """
            cur.execute(sql, (avance_ids,))
            incidencias_map = {}
            for row in cur.fetchall():
                avance_id = row[0]
                if avance_id not in incidencias_map:
                    incidencias_map[avance_id] = []
                incidencias_map[avance_id].append({
                    "id": row[1], "descripcion": row[2], "estado": row[3], "fecha": row[4]
                })
            return incidencias_map
    finally:
        conn.close()

def get_distinct_ubicacion_tipos():
    """Obtiene una lista de todos los tipos de ubicación distintos en la base de datos."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Consulta para obtener los valores únicos de la columna 'tipo'
            #cur.execute("SELECT DISTINCT tipo FROM ubicaciones_config ORDER BY tipo ASC;")
            cur.execute("SELECT DISTINCT tipo FROM ubicaciones_config;")

            # La consulta devuelve una lista de tuplas, la convertimos a una lista simple
            tipos = [row[0] for row in cur.fetchall()]
            return tipos
    finally:
        conn.close()

# =============================================================================
# FUNCIONES DE REGISTRO DE PERSONAL
# =============================================================================

def create_personal_registro(fecha, en_obra, faltas, bajas, user_id):
    """Crea un nuevo registro de personal para una fecha específica."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = """
                INSERT INTO registros_personal (fecha, en_obra, faltas, bajas, registrado_por_id)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (fecha) DO UPDATE SET
                    en_obra = EXCLUDED.en_obra,
                    faltas = EXCLUDED.faltas,
                    bajas = EXCLUDED.bajas,
                    registrado_por_id = EXCLUDED.registrado_por_id,
                    fecha_registro = NOW();
            """
            cur.execute(sql, (fecha, en_obra, faltas, bajas, user_id))
            conn.commit()
    finally:
        conn.close()

def check_personal_registro_today():
    """Comprueba si ya existe un registro de personal para el día de hoy."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # CURRENT_DATE se refiere a la fecha actual del servidor de la BD
            cur.execute("SELECT id FROM registros_personal WHERE fecha = CURRENT_DATE;")
            return cur.fetchone() is not None
    finally:
        conn.close()

def get_personal_registros_for_report(start_date, end_date):
    """Obtiene todos los registros de personal dentro de un rango de fechas."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = """
                SELECT r.fecha, r.en_obra, r.faltas, r.bajas, u.first_name
                FROM registros_personal r
                JOIN usuarios u ON r.registrado_por_id = u.user_id
                WHERE r.fecha BETWEEN %s AND %s
                ORDER BY r.fecha ASC;
            """
            cur.execute(sql, (start_date, end_date))
            registros = []
            for row in cur.fetchall():
                registros.append({
                    "fecha": row[0], "en_obra": row[1], "faltas": row[2],
                    "bajas": row[3], "registrado_por": row[4]
                })
            return registros
    finally:
        conn.close()


def add_rrhh_note_to_solicitud(solicitud_id, rrhh_user_id, nota):
    """Añade una nota de RRHH a una solicitud de personal existente."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Primero, insertamos la nota en la tabla de notas
            sql_note = """
                INSERT INTO solicitud_personal_notas (solicitud_id, rrhh_id, nota)
                VALUES (%s, %s, %s);
            """
            cur.execute(sql_note, (solicitud_id, rrhh_user_id, nota))

            # Luego, actualizamos el estado de la solicitud principal a 'En Busqueda'
            # para reflejar que se está trabajando en ella.
            sql_update = """
                UPDATE solicitudes_personal SET estado = 'En Busqueda' WHERE id = %s;
            """
            cur.execute(sql_update, (solicitud_id,))
            conn.commit()
    finally:
        conn.close()

# =============================================================================
# FUNCIONES DE ÓRDENES DE TRABAJO
# =============================================================================

def create_orden(creador_id, descripcion, foto_path=None):
    """Crea una nueva orden de trabajo en la base de datos."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = """
                INSERT INTO ordenes_trabajo (creador_id, descripcion, foto_path, estado)
                VALUES (%s, %s, %s, 'Pendiente') RETURNING id;
            """
            cur.execute(sql, (creador_id, descripcion, foto_path))
            orden_id = cur.fetchone()[0]
            conn.commit()
            return orden_id
    finally:
        conn.close()

def get_ordenes_by_status(status_list):
    """Obtiene órdenes de trabajo por uno o más estados, incluyendo el nombre del creador."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = """
                SELECT o.id, o.descripcion, u.first_name as creador_nombre, o.fecha_creacion
                FROM ordenes_trabajo o
                JOIN usuarios u ON o.creador_id = u.user_id
                WHERE o.estado = ANY(%s)
                ORDER BY o.fecha_creacion ASC;
            """
            cur.execute(sql, (status_list,))
            return [{
                "id": row[0],
                "descripcion": row[1],
                "creador": row[2],
                "fecha": row[3]
            } for row in cur.fetchall()]
    finally:
        conn.close()

def get_orden_details(orden_id):
    """Obtiene los detalles completos de una orden de trabajo específica."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = """
                SELECT o.id, o.descripcion, o.foto_path, o.estado, o.fecha_creacion, 
                       u_creador.first_name as creador_nombre,
                       u_resolutor.first_name as resolutor_nombre, o.fecha_resolucion
                FROM ordenes_trabajo o
                JOIN usuarios u_creador ON o.creador_id = u_creador.user_id
                LEFT JOIN usuarios u_resolutor ON o.resolutor_id = u_resolutor.user_id
                WHERE o.id = %s;
            """
            cur.execute(sql, (orden_id,))
            res = cur.fetchone()
            if not res:
                return None
            return {
                "id": res[0], "descripcion": res[1], "foto_path": res[2],
                "estado": res[3], "fecha_creacion": res[4], "creador": res[5],
                "resolutor": res[6], "fecha_resolucion": res[7]
            }
    finally:
        conn.close()

def resolve_orden(orden_id, resolutor_id):
    """Marca una orden de trabajo como 'Realizada'."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = """
                UPDATE ordenes_trabajo 
                SET estado = 'Realizada', resolutor_id = %s, fecha_resolucion = NOW() 
                WHERE id = %s;
            """
            cur.execute(sql, (resolutor_id, orden_id))
            conn.commit()
    finally:
        conn.close()


def get_prevencion_incidencias_by_reporter(reporter_id):
    """Obtiene todas las incidencias de prevención reportadas por un usuario específico."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = """
                SELECT id, descripcion, estado, fecha_reporte
                FROM prevencion_incidencias
                WHERE reporta_id = %s
                ORDER BY fecha_reporte DESC;
            """
            cur.execute(sql, (reporter_id,))
            return [{
                "id": row[0],
                "descripcion": row[1],
                "estado": row[2],
                "fecha": row[3].strftime('%d/%m/%Y')
            } for row in cur.fetchall()]
    finally:
        conn.close()


def get_prevencion_incidencia_details(incidencia_id):
    """Obtiene los detalles completos de una incidencia de prevención."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = """
                SELECT 
                    pi.id, pi.ubicacion, pi.descripcion, pi.estado, pi.fecha_reporte, 
                    pi.foto_path, pi.reporta_id,
                    u_cerrado.first_name as resolutor_nombre, pi.fecha_cierre
                FROM prevencion_incidencias pi
                LEFT JOIN usuarios u_cerrado ON pi.cerrado_por_id = u_cerrado.user_id
                WHERE pi.id = %s;
            """
            cur.execute(sql, (incidencia_id,))
            res = cur.fetchone()
            if not res: return None
            return {
                "id": res[0], "ubicacion": res[1], "descripcion": res[2],
                "estado": res[3], "fecha_creacion": res[4], "foto_path": res[5],
                "reporta_id": res[6], "resolutor": res[7], "fecha_cierre": res[8]
            }
    finally:
        conn.close()

def update_almacen_item_details(item_id, nombre, descripcion):
    """Actualiza el nombre y la descripción de un artículo del almacén."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = "UPDATE almacen_items SET nombre = %s, descripcion = %s WHERE id = %s"
            cur.execute(sql, (nombre, descripcion, item_id))
            conn.commit()
            # Devuelve True si la actualización fue exitosa
            return cur.rowcount > 0
    except psycopg2.IntegrityError:
        # Esto ocurriría si el nuevo nombre ya existe (debido a la restricción UNIQUE)
        conn.rollback()
        return False
    finally:
        conn.close()


def delete_almacen_item(item_id):
    """
    Elimina un artículo del almacén por su ID.
    Lanzará una excepción psycopg2.IntegrityError si el artículo está
    referenciado en otras tablas (pedidos, incidencias).
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM almacen_items WHERE id = %s", (item_id,))
            conn.commit()
            # Devuelve True si se eliminó una fila
            return cur.rowcount > 0
    finally:
        conn.close()