# ubicaciones/bot_ubicaciones.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
import telegram.error
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
import db_manager as db
from bot_navigation import end_and_return_to_menu
from reporter import escape

# Estados de la conversación
(
    SELECTING_TYPE, SELECTING_ACTION,
    LISTING_TO_DELETE,
    LISTING_TO_RENAME, AWAITING_NEW_NAME,
    AWAITING_NEW_NAME_ADD
) = range(6)

# --- Funciones de Ayuda ---

def get_ubicaciones_menu(tipo):
    """Genera el menú de acciones para un tipo de ubicación."""
    label = tipo[:-1] if tipo.endswith('s') else tipo
    keyboard = [
        [InlineKeyboardButton(f"➕ Añadir {label}", callback_data=f"ubicacion_add")],
        [InlineKeyboardButton(f"✏️ Renombrar {label}", callback_data=f"ubicacion_rename")],
        [InlineKeyboardButton(f"🗑️ Eliminar {label}", callback_data=f"ubicacion_delete")],
        [InlineKeyboardButton("<< Volver a Tipos", callback_data="ubicacion_back_to_type_select")]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- Lógica de la Conversación ---

async def start_manage_ubicaciones(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Punto de entrada: Muestra los tipos de ubicación a gestionar.
    """
    query = update.callback_query
    await query.answer()

    tipos_de_ubicacion = db.get_distinct_ubicacion_tipos()

    # --- INICIO DE LA CORRECCIÓN ---
    # Definimos el orden deseado
    order_preference = ['Edificio', 'Planta', 'Zona', 'Trabajo']
    
    # Ordenamos la lista obtenida de la BD según nuestra preferencia
    # Esto asegura que el orden sea consistente sin importar cómo lo devuelva la BD.
    tipos_de_ubicacion.sort(key=lambda tipo: order_preference.index(tipo) if tipo in order_preference else len(order_preference))
    # --- FIN DE LA CORRECCIÓN ---

    keyboard = []
    if tipos_de_ubicacion:
        for tipo in tipos_de_ubicacion:
            nombre_boton = f"{tipo}s" if not tipo.endswith('s') else tipo
            keyboard.append([InlineKeyboardButton(nombre_boton, callback_data=f"ubicacion_type_{tipo}")])

    keyboard.append([InlineKeyboardButton("⬅️ Menú Principal", callback_data="back_to_main_menu")])

    texto_mensaje = "🛠️ *Gestionar Ubicaciones*\n\nSelecciona qué tipo de ubicación quieres gestionar:"
    if not tipos_de_ubicacion:
        texto_mensaje = "🛠️ *Gestionar Ubicaciones*\n\nNo se encontraron tipos de ubicación en la base de datos."

    await query.edit_message_text(
        texto_mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    return SELECTING_TYPE


async def select_ubicacion_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Muestra las acciones disponibles para el tipo seleccionado."""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("ubicacion_type_"):
        tipo = query.data.split('_')[2]
        context.user_data['ubicacion_tipo'] = tipo
    else:
        tipo = context.user_data.get('ubicacion_tipo', 'Ubicación')

    try:
        titulo = f"{tipo}s" if not tipo.endswith('s') else tipo
        await query.edit_message_text(
            f"Gestionando: *{escape(titulo)}*\n\n¿Qué quieres hacer?",
            reply_markup=get_ubicaciones_menu(titulo),
            parse_mode='MarkdownV2'
        )
    except telegram.error.BadRequest as e:
        if "Message is not modified" not in str(e):
            raise
    return SELECTING_ACTION

# --- Flujo de Añadir ---

async def ask_for_new_name_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    tipo = context.user_data['ubicacion_tipo']
    await query.edit_message_text(f"Introduce el nombre para el nuevo *{tipo}*:", parse_mode='Markdown')
    return AWAITING_NEW_NAME_ADD

async def save_new_ubicacion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    tipo = context.user_data['ubicacion_tipo']
    nombre = update.message.text
    
    if db.add_ubicacion(tipo, nombre):
        await update.message.reply_text(f"✅ \\¡*{escape(nombre)}* añadido a *{escape(tipo)}s* con éxito\\!", parse_mode='MarkdownV2')
    else:
        await update.message.reply_text(f"❌ Error: Ya existe un {escape(tipo)} con el nombre '{escape(nombre)}'\\.", parse_mode='MarkdownV2')
    titulo = f"{tipo}s" if not tipo.endswith('s') else tipo
    await update.message.reply_text(
        f"Gestionando: *{escape(titulo)}*\n\n¿Qué más quieres hacer?",
        reply_markup=get_ubicaciones_menu(titulo),
        parse_mode='MarkdownV2'
    )
    return SELECTING_ACTION

# --- Flujo de Listar (para Eliminar/Renombrar) ---

async def list_items_for_action(update: Update, context: ContextTypes.DEFAULT_TYPE, mode: str) -> int:
    """Función genérica para listar ubicaciones para una acción específica."""
    query = update.callback_query
    await query.answer()
    tipo = context.user_data['ubicacion_tipo']
    
    action_word = "eliminar" if mode == "delete" else "renombrar"
    emoji = "🗑️" if mode == "delete" else "✏️"
    callback_prefix = "ubicacion_del_" if mode == "delete" else "ubicacion_ren_"
    
    items = db.get_ubicaciones_by_tipo(tipo)
    if not items:
        try:
            titulo = f"{tipo}s" if not tipo.endswith('s') else tipo
            await query.edit_message_text(f"✅ No hay {titulo.lower()} para {action_word}.", reply_markup=get_ubicaciones_menu(titulo))
        except telegram.error.BadRequest as e:
            if "Message is not modified" not in str(e):
                raise
        return SELECTING_ACTION

    keyboard = []
    row = []
    for item in items:
        callback_data = f"{callback_prefix}{item['id']}"
        if mode == 'rename':
             callback_data += f"_{item['nombre']}"
        row.append(InlineKeyboardButton(f"{emoji} {item['nombre']}", callback_data=callback_data))
        if len(row) >= 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("<< Volver", callback_data="ubicacion_back_to_action_select")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = f"Selecciona el *{escape(tipo)}* que quieres {action_word}:"

    try:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='MarkdownV2')
    except telegram.error.BadRequest as e:
        if "Message is not modified" not in str(e):
            raise

    return LISTING_TO_DELETE if mode == "delete" else LISTING_TO_RENAME

# --- Flujo de Eliminar ---

async def list_ubicaciones_to_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await list_items_for_action(update, context, "delete")

async def confirm_delete_ubicacion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    ubicacion_id = int(query.data.split('_')[2])
    db.delete_ubicacion(ubicacion_id)
    await query.answer("✅ Eliminado con éxito")
    
    return await list_items_for_action(update, context, "delete")

# --- Flujo de Renombrar ---

async def list_ubicaciones_to_rename(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await list_items_for_action(update, context, "rename")

async def ask_for_new_name_rename(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    _, _, ubicacion_id, old_name = query.data.split('_', 3)
    context.user_data['ubicacion_id_to_rename'] = int(ubicacion_id)
    
    # Se escapa el carácter ':' al final del texto fijo
    await query.edit_message_text(f"Introduce el nuevo nombre para *{escape(old_name)}*\\:", parse_mode='MarkdownV2')
    
    return AWAITING_NEW_NAME


async def save_renamed_ubicacion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    nuevo_nombre = update.message.text
    ubicacion_id = context.user_data['ubicacion_id_to_rename']
    tipo = context.user_data['ubicacion_tipo']

    if db.rename_ubicacion(ubicacion_id, nuevo_nombre):
        await update.message.reply_text("✅ \\¡Nombre actualizado con éxito\\!", parse_mode='MarkdownV2')
    else:
        await update.message.reply_text(f"❌ Error: Ya existe un {escape(tipo)} con el nombre '{escape(nuevo_nombre)}'\\.", parse_mode='MarkdownV2')
    
    titulo = f"{tipo}s" if not tipo.endswith('s') else tipo
    await update.message.reply_text(
        f"Gestionando: *{escape(titulo)}*\n\n¿Qué más quieres hacer?",
        reply_markup=get_ubicaciones_menu(titulo),
        parse_mode='MarkdownV2'
    )
    return SELECTING_ACTION

# --- CONVERSATION HANDLER ---

def get_ubicaciones_handler():
    """Crea y devuelve el ConversationHandler para gestionar ubicaciones."""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(start_manage_ubicaciones, pattern='^manage_ubicaciones$')],
        states={
            SELECTING_TYPE: [CallbackQueryHandler(select_ubicacion_type, pattern='^ubicacion_type_')],
            SELECTING_ACTION: [
                CallbackQueryHandler(ask_for_new_name_add, pattern='^ubicacion_add$'),
                CallbackQueryHandler(list_ubicaciones_to_delete, pattern='^ubicacion_delete$'),
                CallbackQueryHandler(list_ubicaciones_to_rename, pattern='^ubicacion_rename$'),
                CallbackQueryHandler(start_manage_ubicaciones, pattern='^ubicacion_back_to_type_select$')
            ],
            AWAITING_NEW_NAME_ADD: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_new_ubicacion)],
            LISTING_TO_DELETE: [
                CallbackQueryHandler(confirm_delete_ubicacion, pattern='^ubicacion_del_'),
                CallbackQueryHandler(select_ubicacion_type, pattern='^ubicacion_back_to_action_select$')
            ],
            LISTING_TO_RENAME: [
                CallbackQueryHandler(ask_for_new_name_rename, pattern='^ubicacion_ren_'),
                CallbackQueryHandler(select_ubicacion_type, pattern='^ubicacion_back_to_action_select$')
            ],
            AWAITING_NEW_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_renamed_ubicacion)],
        },
        fallbacks=[
            CallbackQueryHandler(end_and_return_to_menu, pattern='^back_to_main_menu$'),
        ],
        map_to_parent={
             ConversationHandler.END: ConversationHandler.END
        },
        allow_reentry=True
    )

