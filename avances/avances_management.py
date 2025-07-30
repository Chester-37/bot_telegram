# avances/avances_management.py
# Gestión de estructura jerárquica y tipos de trabajo (solo para Técnicos)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CallbackQueryHandler,
    MessageHandler, filters
)
import db_adapter as db
from bot_navigation import end_and_return_to_menu
from .avances_keyboards import *
from .avances_utils import escape, clean_text_input

# Estados de conversación para gestión
(
    MANAGEMENT_MENU, MANAGE_UBICACIONES, MANAGE_TIPOS_TRABAJO,
    ADDING_TIPO_TRABAJO, EDITING_TIPO_TRABAJO, CONFIRMING_DELETE_TIPO
) = range(6)

async def start_avances_management(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menú principal de gestión para técnicos."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    user_role = db.get_user_role(user.id)
    
    if user_role != 'Técnico':
        await query.edit_message_text(
            "❌ *Acceso Denegado*\n\nSolo los técnicos pueden gestionar la configuración de avances\\.",
            reply_markup=get_nav_keyboard(),
            parse_mode='MarkdownV2'
        )
        return ConversationHandler.END
    
    text = (
        "🛠️ *Gestión de Avances \\- Panel Técnico*\n\n"
        "Desde aquí puedes configurar:\n"
        "• Estructura jerárquica de ubicaciones\n"
        "• Tipos de trabajo disponibles\n"
        "• Ver estadísticas generales\n\n"
        "¿Qué deseas gestionar?"
    )
    
    await query.edit_message_text(
        text,
        reply_markup=build_management_keyboard(),
        parse_mode='MarkdownV2'
    )
    return MANAGEMENT_MENU

async def show_tipos_trabajo_management(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Muestra la gestión de tipos de trabajo."""
    query = update.callback_query
    await query.answer()
    
    tipos = db.get_all_tipos_trabajo()
    
    text = "🔧 *Gestión de Tipos de Trabajo*\n\n"
    
    if tipos:
        text += "*Tipos configurados:*\n"
        for tipo in tipos:
            status = "✅" if tipo['activo'] else "❌"
            text += f"{status} {tipo['emoji']} {escape(tipo['nombre'])}\n"
    else:
        text += "No hay tipos de trabajo configurados\\."
    
    keyboard = [
        [
            InlineKeyboardButton("➕ Añadir Tipo", callback_data="add_tipo_trabajo"),
            InlineKeyboardButton("✏️ Editar Tipo", callback_data="edit_tipo_trabajo")
        ],
        [
            InlineKeyboardButton("🔄 Reordenar", callback_data="reorder_tipos_trabajo"),
            InlineKeyboardButton("🗑️ Desactivar", callback_data="deactivate_tipo_trabajo")
        ],
        [
            InlineKeyboardButton("⬅️ Atrás", callback_data="back_to_management"),
            InlineKeyboardButton("🏠 Menú Principal", callback_data="back_to_main_menu")
        ]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='MarkdownV2'
    )
    return MANAGE_TIPOS_TRABAJO

async def start_add_tipo_trabajo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el proceso de añadir un nuevo tipo de trabajo."""
    query = update.callback_query
    await query.answer()
    
    context.user_data['adding_tipo'] = {}
    
    await query.edit_message_text(
        "➕ *Añadir Nuevo Tipo de Trabajo*\n\n"
        "Escribe el nombre del nuevo tipo de trabajo:\n\n"
        "_Ejemplo: Soldadura, Instalación eléctrica, etc\\._",
        reply_markup=get_cancel_keyboard(),
        parse_mode='MarkdownV2'
    )
    return ADDING_TIPO_TRABAJO

async def process_tipo_trabajo_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa el nombre del nuevo tipo de trabajo."""
    nombre = clean_text_input(update.message.text)
    
    if len(nombre) < 2:
        await update.message.reply_text(
            "❌ El nombre debe tener al menos 2 caracteres\\. Intenta de nuevo:",
            reply_markup=get_cancel_keyboard(),
            parse_mode='MarkdownV2'
        )
        return ADDING_TIPO_TRABAJO
    
    context.user_data['adding_tipo']['nombre'] = nombre
    
    # Sugerir emojis comunes
    emojis_sugeridos = ['🔧', '⚡', '🔨', '🎨', '🧱', '💡', '🪚', '🧹', '🔍']
    
    keyboard = []
    row = []
    for emoji in emojis_sugeridos:
        row.append(InlineKeyboardButton(emoji, callback_data=f"emoji_{emoji}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("✏️ Escribir emoji personalizado", callback_data="emoji_custom")])
    keyboard.append([InlineKeyboardButton("📝 Sin emoji", callback_data="emoji_none")])
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancel_conversation")])
    
    await update.message.reply_text(
        f"✅ Nombre: *{escape(nombre)}*\n\n"
        "Ahora selecciona un emoji para el tipo de trabajo:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='MarkdownV2'
    )
    return ADDING_TIPO_TRABAJO

async def process_tipo_trabajo_emoji(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa la selección del emoji."""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("emoji_"):
        emoji_selected = query.data.replace("emoji_", "")
        
        if emoji_selected == "custom":
            await query.edit_message_text(
                "Escribe el emoji que quieres usar:\n\n"
                "_Puedes usar cualquier emoji o dejar vacío\\._",
                reply_markup=get_cancel_keyboard(),
                parse_mode='MarkdownV2'
            )
            context.user_data['awaiting_custom_emoji'] = True
            return ADDING_TIPO_TRABAJO
        
        elif emoji_selected == "none":
            emoji_selected = "🔧"  # Default
        
        context.user_data['adding_tipo']['emoji'] = emoji_selected
        
        # Guardar en base de datos
        user = update.effective_user
        nombre = context.user_data['adding_tipo']['nombre']
        
        tipo_id = db.add_tipo_trabajo(nombre, emoji_selected, user.id)
        
        if tipo_id:
            await query.edit_message_text(
                f"✅ *Tipo de trabajo creado exitosamente*\n\n"
                f"{emoji_selected} {escape(nombre)}\n\n"
                "¿Quieres añadir otro tipo?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ Añadir otro", callback_data="add_tipo_trabajo")],
                    [InlineKeyboardButton("⬅️ Volver a gestión", callback_data="manage_tipos_trabajo")],
                    [InlineKeyboardButton("🏠 Menú Principal", callback_data="back_to_main_menu")]
                ]),
                parse_mode='MarkdownV2'
            )
        else:
            await query.edit_message_text(
                f"❌ *Error al crear tipo de trabajo*\n\n"
                f"Es posible que ya exista un tipo con el nombre '{escape(nombre)}'\\.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Intentar de nuevo", callback_data="add_tipo_trabajo")],
                    [InlineKeyboardButton("⬅️ Volver", callback_data="manage_tipos_trabajo")]
                ]),
                parse_mode='MarkdownV2'
            )
        
        # Limpiar datos temporales
        context.user_data.pop('adding_tipo', None)
        context.user_data.pop('awaiting_custom_emoji', None)
        
        return MANAGE_TIPOS_TRABAJO
    
    return ADDING_TIPO_TRABAJO

async def process_custom_emoji(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa emoji personalizado."""
    if context.user_data.get('awaiting_custom_emoji'):
        emoji = update.message.text.strip()
        if not emoji:
            emoji = "🔧"
        
        context.user_data['adding_tipo']['emoji'] = emoji
        context.user_data.pop('awaiting_custom_emoji', None)
        
        # Guardar en base de datos
        user = update.effective_user
        nombre = context.user_data['adding_tipo']['nombre']
        
        tipo_id = db.add_tipo_trabajo(nombre, emoji, user.id)
        
        if tipo_id:
            await update.message.reply_text(
                f"✅ *Tipo de trabajo creado exitosamente*\n\n"
                f"{emoji} {escape(nombre)}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Volver a gestión", callback_data="manage_tipos_trabajo")]
                ]),
                parse_mode='MarkdownV2'
            )
        else:
            await update.message.reply_text(
                f"❌ Error al crear el tipo de trabajo\\.",
                reply_markup=get_nav_keyboard(),
                parse_mode='MarkdownV2'
            )
        
        context.user_data.pop('adding_tipo', None)
        return MANAGE_TIPOS_TRABAJO
    
    return ADDING_TIPO_TRABAJO

async def show_edit_tipos_trabajo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Muestra lista de tipos para editar."""
    query = update.callback_query
    await query.answer()
    
    tipos = db.get_all_tipos_trabajo()
    
    if not tipos:
        await query.edit_message_text(
            "❌ No hay tipos de trabajo para editar\\.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Atrás", callback_data="manage_tipos_trabajo")]
            ]),
            parse_mode='MarkdownV2'
        )
        return MANAGE_TIPOS_TRABAJO
    
    keyboard = []
    for tipo in tipos:
        status = "✅" if tipo['activo'] else "❌"
        button_text = f"{status} {tipo['emoji']} {tipo['nombre']}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"edit_tipo_{tipo['id']}")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Atrás", callback_data="manage_tipos_trabajo")])
    
    await query.edit_message_text(
        "✏️ *Editar Tipos de Trabajo*\n\n"
        "Selecciona el tipo que quieres editar:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='MarkdownV2'
    )
    return EDITING_TIPO_TRABAJO

async def show_deactivate_tipos_trabajo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Muestra lista de tipos para desactivar."""
    query = update.callback_query
    await query.answer()
    
    tipos = [t for t in db.get_all_tipos_trabajo() if t['activo']]
    
    if not tipos:
        await query.edit_message_text(
            "❌ No hay tipos de trabajo activos para desactivar\\.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Atrás", callback_data="manage_tipos_trabajo")]
            ]),
            parse_mode='MarkdownV2'
        )
        return MANAGE_TIPOS_TRABAJO
    
    keyboard = []
    for tipo in tipos:
        button_text = f"{tipo['emoji']} {tipo['nombre']}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"deactivate_tipo_{tipo['id']}")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Atrás", callback_data="manage_tipos_trabajo")])
    
    await query.edit_message_text(
        "🗑️ *Desactivar Tipos de Trabajo*\n\n"
        "⚠️ Los tipos desactivados no aparecerán en nuevos registros\\.\n\n"
        "Selecciona el tipo que quieres desactivar:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='MarkdownV2'
    )
    return CONFIRMING_DELETE_TIPO

async def confirm_deactivate_tipo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirma la desactivación de un tipo de trabajo."""
    query = update.callback_query
    await query.answer()
    
    tipo_id = int(query.data.split('_')[2])
    
    # Obtener info del tipo
    tipos = db.get_all_tipos_trabajo()
    tipo = next((t for t in tipos if t['id'] == tipo_id), None)
    
    if not tipo:
        await query.edit_message_text(
            "❌ Tipo de trabajo no encontrado\\.",
            reply_markup=get_nav_keyboard(),
            parse_mode='MarkdownV2'
        )
        return ConversationHandler.END
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Sí, desactivar", callback_data=f"confirm_deactivate_{tipo_id}"),
            InlineKeyboardButton("❌ Cancelar", callback_data="manage_tipos_trabajo")
        ]
    ]
    
    await query.edit_message_text(
        f"⚠️ *Confirmar Desactivación*\n\n"
        f"¿Estás seguro de que quieres desactivar:\n"
        f"{tipo['emoji']} {escape(tipo['nombre'])}?\n\n"
        f"_Este tipo ya no aparecerá en nuevos registros\\._",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='MarkdownV2'
    )
    return CONFIRMING_DELETE_TIPO

async def execute_deactivate_tipo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ejecuta la desactivación del tipo de trabajo."""
    query = update.callback_query
    await query.answer()
    
    tipo_id = int(query.data.split('_')[2])
    
    success = db.update_tipo_trabajo(tipo_id, activo=False)
    
    if success:
        await query.edit_message_text(
            "✅ *Tipo de trabajo desactivado exitosamente*",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Volver a gestión", callback_data="manage_tipos_trabajo")]
            ]),
            parse_mode='MarkdownV2'
        )
    else:
        await query.edit_message_text(
            "❌ Error al desactivar el tipo de trabajo\\.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Volver", callback_data="manage_tipos_trabajo")]
            ]),
            parse_mode='MarkdownV2'
        )
    
    return MANAGE_TIPOS_TRABAJO

# Función para obtener el handler completo
def get_avances_management_handler():
    """Devuelve el ConversationHandler para gestión de avances."""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(start_avances_management, pattern="^manage_avances$")],
        states={
            MANAGEMENT_MENU: [
                CallbackQueryHandler(show_tipos_trabajo_management, pattern="^manage_tipos_trabajo$"),
                CallbackQueryHandler(lambda u, c: end_and_return_to_menu(u, c), pattern="^back_to_main_menu$")
            ],
            MANAGE_TIPOS_TRABAJO: [
                CallbackQueryHandler(start_add_tipo_trabajo, pattern="^add_tipo_trabajo$"),
                CallbackQueryHandler(show_edit_tipos_trabajo, pattern="^edit_tipo_trabajo$"),
                CallbackQueryHandler(show_deactivate_tipos_trabajo, pattern="^deactivate_tipo_trabajo$"),
                CallbackQueryHandler(start_avances_management, pattern="^back_to_management$")
            ],
            ADDING_TIPO_TRABAJO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_tipo_trabajo_name),
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_custom_emoji),
                CallbackQueryHandler(process_tipo_trabajo_emoji, pattern="^emoji_"),
                CallbackQueryHandler(start_add_tipo_trabajo, pattern="^add_tipo_trabajo$")
            ],
            EDITING_TIPO_TRABAJO: [
                CallbackQueryHandler(show_tipos_trabajo_management, pattern="^manage_tipos_trabajo$")
            ],
            CONFIRMING_DELETE_TIPO: [
                CallbackQueryHandler(confirm_deactivate_tipo, pattern="^deactivate_tipo_"),
                CallbackQueryHandler(execute_deactivate_tipo, pattern="^confirm_deactivate_"),
                CallbackQueryHandler(show_tipos_trabajo_management, pattern="^manage_tipos_trabajo$")
            ]
        },
        fallbacks=[
            CallbackQueryHandler(lambda u, c: end_and_return_to_menu(u, c), pattern="^cancel_conversation$"),
            CallbackQueryHandler(lambda u, c: end_and_return_to_menu(u, c), pattern="^back_to_main_menu$")
        ],
        name="avances_management",
        persistent=False
    )
