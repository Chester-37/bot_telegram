# avances/avances_keyboards.py
# Teclados optimizados con emojis y MarkdownV2

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_cancel_keyboard():
    """Teclado de cancelación universal."""
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_conversation")]])

def get_nav_keyboard():
    """Teclado de navegación al menú principal."""
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Menú Principal", callback_data="back_to_main_menu")]])

def build_dynamic_keyboard(items, callback_prefix, max_cols=2):
    """Construye teclado dinámico con elementos organizados en columnas."""
    keyboard = []
    row = []
    
    for item in items:
        # Agregar emoji si existe en el item
        emoji = item.get('emoji', '')
        nombre = item.get('nombre', str(item))
        
        # Formato del botón
        button_text = f"{emoji} {nombre}" if emoji else nombre
        button_data = f"{callback_prefix}{item.get('id', nombre)}"
        
        row.append(InlineKeyboardButton(button_text, callback_data=button_data))
        
        if len(row) == max_cols:
            keyboard.append(row)
            row = []
    
    # Agregar fila restante si existe
    if row:
        keyboard.append(row)
    
    # Botón de cancelar
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancel_conversation")])
    
    return InlineKeyboardMarkup(keyboard)

def build_ubicacion_keyboard(ubicaciones, nivel, callback_prefix="ubic_"):
    """Construye teclado de ubicaciones con navegación jerárquica."""
    keyboard = []
    
    # Agrupar en filas de 2
    row = []
    for ubicacion in ubicaciones:
        emoji_nivel = get_nivel_emoji(nivel)
        button_text = f"{emoji_nivel} {ubicacion['nombre']}"
        button_data = f"{callback_prefix}{nivel}_{ubicacion['id']}"
        
        row.append(InlineKeyboardButton(button_text, callback_data=button_data))
        
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    # Opciones especiales
    keyboard.append([
        InlineKeyboardButton("📝 Registrar en este nivel", callback_data=f"registro_nivel_{nivel}"),
    ])
    
    # Navegación
    keyboard.append([
        InlineKeyboardButton("⬅️ Atrás", callback_data="avance_back"),
        InlineKeyboardButton("❌ Cancelar", callback_data="cancel_conversation")
    ])
    
    return InlineKeyboardMarkup(keyboard)

def get_nivel_emoji(nivel):
    """Devuelve emoji según el nivel de ubicación."""
    emojis = {
        'Edificio': '🏢',
        'Zona': '📍', 
        'Planta': '🏗️',
        'Trabajo': '⚙️',
        'Elemento': '🔧'
    }
    return emojis.get(nivel, '📋')

def build_tipos_trabajo_keyboard(tipos_trabajo, callback_prefix="tipo_"):
    """Construye teclado de tipos de trabajo con emojis."""
    keyboard = []
    row = []
    
    for tipo in tipos_trabajo:
        button_text = f"{tipo['emoji']} {tipo['nombre']}"
        button_data = f"{callback_prefix}{tipo['id']}"
        
        row.append(InlineKeyboardButton(button_text, callback_data=button_data))
        
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    # Opción de texto libre
    keyboard.append([
        InlineKeyboardButton("✏️ Escribir tipo personalizado", callback_data="tipo_custom")
    ])
    
    # Navegación
    keyboard.append([
        InlineKeyboardButton("⬅️ Atrás", callback_data="avance_back"),
        InlineKeyboardButton("❌ Cancelar", callback_data="cancel_conversation")
    ])
    
    return InlineKeyboardMarkup(keyboard)

def build_confirmation_keyboard():
    """Teclado de confirmación para guardar avance."""
    keyboard = [
        [
            InlineKeyboardButton("✅ Confirmar y Guardar", callback_data="avance_confirm"),
            InlineKeyboardButton("✏️ Editar", callback_data="avance_edit")
        ],
        [
            InlineKeyboardButton("❌ Cancelar", callback_data="cancel_conversation")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def build_options_keyboard():
    """Teclado de opciones adicionales (foto, incidencia, observaciones)."""
    keyboard = [
        [
            InlineKeyboardButton("📸 Añadir Foto", callback_data="avance_add_photo"),
            InlineKeyboardButton("⚠️ Reportar Incidencia", callback_data="avance_add_incidencia")
        ],
        [
            InlineKeyboardButton("📝 Añadir Observaciones", callback_data="avance_add_observaciones")
        ],
        [
            InlineKeyboardButton("✅ Continuar", callback_data="avance_continue"),
            InlineKeyboardButton("❌ Cancelar", callback_data="cancel_conversation")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def build_management_keyboard():
    """Teclado de gestión para técnicos."""
    keyboard = [
        [
            InlineKeyboardButton("🏗️ Gestionar Ubicaciones", callback_data="manage_ubicaciones"),
            InlineKeyboardButton("🔧 Gestionar Tipos de Trabajo", callback_data="manage_tipos_trabajo")
        ],
        [
            InlineKeyboardButton("📊 Ver Todos los Avances", callback_data="view_all_avances"),
            InlineKeyboardButton("📈 Generar Informes", callback_data="generate_reports")
        ],
        [
            InlineKeyboardButton("⬅️ Menú Principal", callback_data="back_to_main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def build_visualization_keyboard():
    """Teclado de visualización para gerentes."""
    keyboard = [
        [
            InlineKeyboardButton("📊 Ver Avances", callback_data="view_avances_gerente"),
            InlineKeyboardButton("📈 Informes Ejecutivos", callback_data="view_reports_gerente")
        ],
        [
            InlineKeyboardButton("📅 Avances por Fecha", callback_data="avances_by_date"),
            InlineKeyboardButton("🏗️ Avances por Ubicación", callback_data="avances_by_location")
        ],
        [
            InlineKeyboardButton("⬅️ Menú Principal", callback_data="back_to_main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def build_registro_keyboard():
    """Teclado principal de registro para encargados."""
    keyboard = [
        [
            InlineKeyboardButton("➕ Nuevo Avance", callback_data="nuevo_avance"),
            InlineKeyboardButton("📋 Mis Avances", callback_data="mis_avances")
        ],
        [
            InlineKeyboardButton("📊 Ver Avances del Equipo", callback_data="avances_equipo"),
            InlineKeyboardButton("⚠️ Incidencias Pendientes", callback_data="incidencias_pendientes")
        ],
        [
            InlineKeyboardButton("⬅️ Menú Principal", callback_data="back_to_main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def build_pagination_keyboard(current_page, total_pages, callback_prefix="page_"):
    """Construye teclado de paginación."""
    keyboard = []
    
    # Fila de navegación
    nav_row = []
    if current_page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f"{callback_prefix}{current_page - 1}"))
    
    nav_row.append(InlineKeyboardButton(f"📄 {current_page + 1}/{total_pages}", callback_data="page_info"))
    
    if current_page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("➡️ Siguiente", callback_data=f"{callback_prefix}{current_page + 1}"))
    
    keyboard.append(nav_row)
    
    # Botón de regreso
    keyboard.append([InlineKeyboardButton("⬅️ Atrás", callback_data="back_to_avances")])
    
    return InlineKeyboardMarkup(keyboard)
