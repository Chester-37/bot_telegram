from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_cancel_keyboard(callback_data="cancel_almacen"):
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("❌ Cancelar", callback_data=callback_data)]]
    )

def get_nav_keyboard():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("⬅️ Menú Principal", callback_data="back_to_main_menu")]]
    )

def get_category_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🛠️ Herramientas", callback_data="view_cat_Herramienta"),
            InlineKeyboardButton("🛡️ EPIs", callback_data="view_cat_EPI"),
            InlineKeyboardButton("📦 Fungibles", callback_data="view_cat_Fungible"),
        ],
        [InlineKeyboardButton("⬅️ Volver", callback_data="back_to_almacen_menu")],
    ])

def get_main_almacen_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Añadir/Actualizar Stock", callback_data="almacen_add_start")],
        [InlineKeyboardButton("📋 Ver/Gestionar Inventario", callback_data="almacen_view_start")],
        [InlineKeyboardButton("⬅️ Menú Principal", callback_data="back_to_main_menu")],
    ])

def get_item_type_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🛠️ Herramienta", callback_data="tipo_Herramienta"),
            InlineKeyboardButton("🛡️ EPI", callback_data="tipo_EPI"),
        ],
        [InlineKeyboardButton("📦 Fungible", callback_data="tipo_Fungible")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_almacen")],
    ])

def get_save_or_restart_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Sí, Guardar", callback_data="save_almacen_item")],
        [InlineKeyboardButton("❌ No, Empezar de Nuevo", callback_data="almacen_add_start")],
    ])

def get_empty_category_keyboard():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("⬅️ Volver a Categorías", callback_data="back_to_view_start")]]
    )

def get_item_detail_keyboard(item_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✏️ Editar Cantidad", callback_data=f"mod_item_qty_{item_id}"),
            InlineKeyboardButton("📝 Editar Nombre", callback_data=f"mod_item_name_{item_id}"),
        ],
        [InlineKeyboardButton("🗑️ Eliminar Artículo", callback_data=f"mod_item_del_{item_id}")],
        [InlineKeyboardButton("⬅️ Volver a la lista", callback_data="back_to_list")],
    ])

def get_confirm_delete_keyboard(item_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Sí, Eliminar", callback_data=f"del_confirm_yes_{item_id}"),
            InlineKeyboardButton("❌ No, Cancelar", callback_data=f"del_confirm_no_{item_id}"),
        ]
    ])

def get_pagination_keyboard(page, total_pages):
    buttons = []
    if page > 0:
        buttons.append(InlineKeyboardButton("⬅️ Anterior", callback_data="view_page_prev"))
    if page < total_pages - 1:
        buttons.append(InlineKeyboardButton("Siguiente ➡️", callback_data="view_page_next"))
    return InlineKeyboardMarkup([buttons]) if buttons else None
    ])

def get_pagination_keyboard(page, total_pages):
    """Teclado de paginación para la lista de artículos."""
    buttons = []
    if page > 0:
        buttons.append(InlineKeyboardButton("⬅️ Anterior", callback_data="view_page_prev"))
    if page < total_pages - 1:
        buttons.append(InlineKeyboardButton("Siguiente ➡️", callback_data="view_page_next"))
    return InlineKeyboardMarkup([buttons]) if buttons else None
