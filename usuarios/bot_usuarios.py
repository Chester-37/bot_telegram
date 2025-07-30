# usuarios/bot_usuarios.py

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, User
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
import db_manager as db
from reporter import escape

# --- INICIO DE LA CORRECCIÓN ---
# Se elimina la importación de la parte superior para romper el círculo.
# from bot_navigation import start, end_and_return_to_menu
# --- FIN DE LA CORRECCIÓN ---


# =============================================================================
# CONSTANTES
# =============================================================================

ROLES_ASIGNABLES = ['Encargado', 'Tecnico', 'Gerente', 'Almacen', 'RRHH', 'Prevencion', 'Admin']
CALLBACK_DELIMITER = "_::_"
SELECTING_USER, SELECTING_ROLE, CONFIRMING_ROLE_CHANGE = range(3)

# =============================================================================
# GESTIÓN DE NUEVOS USUARIOS (SIN ROL)
# =============================================================================

async def notify_admin_of_new_user(context: ContextTypes.DEFAULT_TYPE, new_user: User):
    """Notifica a los administradores sobre un nuevo usuario sin rol."""
    admins = db.get_users_by_role('Admin')
    if not admins:
        print(f"ADVERTENCIA: Nuevo usuario ID: {new_user.id}, pero no hay admins.")
        return

    user_info_text = (
        f"👤 *Nuevo Usuario Sin Rol Detectado*\n\n"
        f"*Nombre:* {escape(new_user.first_name)}\n"
        f"*Username:* @{escape(new_user.username or 'N/A')}\n"
        f"*ID:* `{new_user.id}`\n\n"
        "Por favor, asígnale un rol:"
    )

    keyboard = []
    for role in ROLES_ASIGNABLES:
        callback_data = f"assignrole{CALLBACK_DELIMITER}{new_user.id}{CALLBACK_DELIMITER}{role}"
        keyboard.append([InlineKeyboardButton(f"Asignar Rol: {role}", callback_data=callback_data)])
    
    reply_markup = InlineKeyboardMarkup(keyboard)

    for admin in admins:
        try:
            await context.bot.send_message(
                chat_id=admin['id'], text=user_info_text,
                reply_markup=reply_markup, parse_mode='MarkdownV2'
            )
        except Exception as e:
            print(f"Error al notificar al admin {admin['id']}: {e}")

async def assign_role_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador para asignar un rol a un NUEVO usuario."""
    query = update.callback_query
    await query.answer()

    parts = query.data.split(CALLBACK_DELIMITER)
    
    try:
        _, new_user_id_str, role_to_assign = parts
        new_user_id = int(new_user_id_str)
    except ValueError:
        await query.edit_message_text("❌ Error: Los datos del botón son inválidos.")
        return

    try:
        user_chat = await context.bot.get_chat(chat_id=new_user_id)
        new_user_first_name = user_chat.first_name or "N/A"
        new_user_username = user_chat.username
    except Exception as e:
        await query.edit_message_text(f"❌ Error: No se pudo obtener la información del usuario con ID {new_user_id}.\nRazón: {e}")
        return

    db.add_user_with_role(new_user_id, new_user_first_name, new_user_username, role_to_assign)

    admin_user = query.from_user
    await query.edit_message_text(
        text=f"✅ Rol *{escape(role_to_assign)}* asignado a *{escape(new_user_first_name)}* por {escape(admin_user.first_name)}\\.",
        parse_mode='MarkdownV2'
    )

    try:
        notification_text = (
            f"¡Hola {escape(new_user_first_name)}\\! Tu cuenta ha sido activada con el rol de *{escape(role_to_assign)}*\\.\n\n"
            f"Ahora puedes usar el comando /start para ver tus opciones\\."
        )
        await context.bot.send_message(
            chat_id=new_user_id,
            text=notification_text,
            parse_mode='MarkdownV2'
        )
    except Exception as e:
        print(f"No se pudo notificar al nuevo usuario {new_user_id}: {e}")

# =============================================================================
# GESTIÓN DE ROLES DE USUARIOS EXISTENTES (CONVERSACIÓN CON CONFIRMACIÓN)
# =============================================================================

async def start_manage_roles(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Punto de entrada: Muestra la lista de todos los usuarios registrados en la BD."""
    query = update.callback_query
    await query.answer()

    all_users = db.get_all_users()
    if not all_users:
        await query.edit_message_text("No hay usuarios registrados en la base de datos.")
        return ConversationHandler.END

    keyboard = []
    for user in all_users:
        button_text = f"{user['name']} ({user['role']})"
        callback_data = f"mngrole_select_{user['id']}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
    
    keyboard.append([InlineKeyboardButton("⬅️ Volver al Menú", callback_data="back_to_main_menu")])
    
    await query.edit_message_text(
        "👤 *Gestionar Roles*\n\nSelecciona un usuario para ver o cambiar su rol:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    return SELECTING_USER

async def select_user_to_manage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Muestra el rol actual del usuario y las opciones para cambiarlo."""
    query = update.callback_query
    await query.answer()
    
    user_id = int(query.data.split('_')[2])
    user_details = db.get_user_details(user_id)
    
    if not user_details:
        await query.edit_message_text("❌ Error: Usuario no encontrado.")
        return await start_manage_roles(update, context)

    context.user_data['selected_user_id'] = user_details['id']
    context.user_data['selected_user_name'] = user_details['name']

    keyboard = []
    for role in ROLES_ASIGNABLES:
        button_text = f"✅ {role}" if role == user_details['role'] else role
        callback_data = f"mngrole_set_{role}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
    
    keyboard.append([InlineKeyboardButton("<< Volver a la lista", callback_data="mngrole_back_to_list")])

    await query.edit_message_text(
        f"Editando a: *{escape(user_details['name'])}*\n"
        f"Rol actual: `{escape(user_details['role'])}`\n\n"
        "Selecciona el nuevo rol:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='MarkdownV2'
    )
    return SELECTING_ROLE

async def ask_for_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Pide confirmación antes de cambiar el rol."""
    query = update.callback_query
    await query.answer()

    new_role = query.data.split('_')[2]
    user_name = context.user_data['selected_user_name']
    
    context.user_data['new_role_to_assign'] = new_role

    keyboard = [
        [InlineKeyboardButton("✅ Confirmar Cambio", callback_data="mngrole_confirm")],
        [InlineKeyboardButton("❌ Cancelar", callback_data=f"mngrole_select_{context.user_data['selected_user_id']}")]
    ]

    await query.edit_message_text(
        f"⚠️ ¿Estás seguro?\n\n"
        f"Vas a cambiar el rol de *{escape(user_name)}* a *{escape(new_role)}*\\.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='MarkdownV2'
    )
    return CONFIRMING_ROLE_CHANGE

async def update_user_role_confirmed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Aplica el cambio de rol, notifica y vuelve directamente al menú principal."""
    # --- INICIO DE LA CORRECCIÓN ---
    # Se importa 'start' localmente dentro de la función
    from bot_navigation import start
    # --- FIN DE LA CORRECCIÓN ---
    
    query = update.callback_query
    
    new_role = context.user_data['new_role_to_assign']
    user_id_to_update = context.user_data['selected_user_id']
    
    await query.answer(f"Actualizando rol a {new_role}...")
    
    db.update_user_role(user_id_to_update, new_role)
    
    try:
        await context.bot.send_message(
            chat_id=user_id_to_update,
            text=f"ℹ️ Un administrador ha actualizado tu rol a *{escape(new_role)}*\\. "
                 f"Usa /start para ver tus nuevas opciones\\.",
            parse_mode='MarkdownV2'
        )
    except Exception as e:
        print(f"No se pudo notificar al usuario {user_id_to_update} sobre el cambio de rol: {e}")

    context.user_data.clear()
    
    await start(update, context)
    
    return ConversationHandler.END

# =============================================================================
# EXPORTACIÓN DE HANDLERS
# =============================================================================

def get_user_management_handlers():
    """Devuelve todos los manejadores para la gestión de usuarios."""
    
    from bot_navigation import end_and_return_to_menu

    manage_roles_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_manage_roles, pattern='^manage_roles_start$')],
        states={
            SELECTING_USER: [
                CallbackQueryHandler(select_user_to_manage, pattern='^mngrole_select_')
            ],
            SELECTING_ROLE: [
                CallbackQueryHandler(ask_for_confirmation, pattern='^mngrole_set_'),
                CallbackQueryHandler(start_manage_roles, pattern='^mngrole_back_to_list$')
            ],
            CONFIRMING_ROLE_CHANGE: [
                CallbackQueryHandler(update_user_role_confirmed, pattern='^mngrole_confirm$'),
                CallbackQueryHandler(select_user_to_manage, pattern='^mngrole_select_')
            ],
        },
        fallbacks=[
            CallbackQueryHandler(end_and_return_to_menu, pattern='^back_to_main_menu$')
        ],
        map_to_parent={
            ConversationHandler.END: ConversationHandler.END
        }
    )

    assign_new_user_handler = CallbackQueryHandler(assign_role_callback, pattern=f'^assignrole')

    return [manage_roles_handler, assign_new_user_handler]
