# bot_navigation.py

import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
import db_manager as db
from usuarios.bot_usuarios import notify_admin_of_new_user
from reporter import escape


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat = update.effective_chat
    
    if update.message and update.message.text:
        match = re.match(r'/start group_(-?\d+)', update.message.text)
        if match:
            group_chat_id = match.group(1)
            context.user_data['group_chat_id'] = int(group_chat_id)

    if chat.type in ['group', 'supergroup']:
        bot_username = context.bot.username
        url = f"https://t.me/{bot_username}?start=group_{chat.id}"
        keyboard = [[InlineKeyboardButton("💬 Hablar con el bot", url=url)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"Para interactuar conmigo y ver tus opciones, por favor, haz clic en el botón para abrir un chat privado (Grupo {chat.id}).",
            reply_markup=reply_markup
        )
        return

    user_role = db.get_user_role(user.id)
    if not user_role:
        # Escapamos el nombre del usuario para evitar errores de formato
        safe_first_name = escape(user.first_name)
        await update.message.reply_text(
            f"Hola {safe_first_name}\\. Tu ID de Telegram es: `{user.id}`\\.\n"
            f"Aún no tienes un rol asignado\\. Se ha notificado a un administrador para que active tu cuenta\\.",
            parse_mode='MarkdownV2'  # Cambiamos a MarkdownV2 para consistencia
        )
        # Llama a la función que notifica a los administradores
        await notify_admin_of_new_user(context, user)
        return

    keyboard = []
    text = f"¡Hola {user.first_name}! (Rol: {user_role})\n\nSelecciona una opción:"

    if user_role == 'Encargado':
        keyboard.extend([
            [InlineKeyboardButton("🆕 Gestionar Órdenes", callback_data='gestionar_ordenes')],
            [InlineKeyboardButton("🆕 Crear Orden", callback_data='crear_orden')],
            [InlineKeyboardButton("📝 Registrar Avance", callback_data='registrar_avance')],
            [InlineKeyboardButton("🛠️ Reportar Avería", callback_data='crear_incidencia')],
            [InlineKeyboardButton("📦 Solicitar Material al Almacén", callback_data='solicitar_material')],
            [InlineKeyboardButton("👤 Solicitar Personal", callback_data='rrhh_solicitar')],
            [InlineKeyboardButton("📋 Mis Solicitudes de Personal", callback_data='rrhh_mis_solicitudes')],
            [InlineKeyboardButton("📊 Registrar Personal Diario", callback_data='registro_personal_start')],
            [InlineKeyboardButton("📊 Consultar Informes", callback_data='consultar_informes')]
        ])
    elif user_role == 'Tecnico':
        keyboard.extend([
            [InlineKeyboardButton("📝 Registrar Avance", callback_data='registrar_avance')],
            [InlineKeyboardButton("🛠️ Reportar Avería", callback_data='crear_incidencia')],
            [InlineKeyboardButton("🆕 Gestionar Órdenes", callback_data='gestionar_ordenes')],
            [InlineKeyboardButton("🆕 Crear Orden", callback_data='crear_orden')],
            #[InlineKeyboardButton("‼️ Gestionar Averías", callback_data='gestionar_averias')],
            [InlineKeyboardButton("📦 Gestión de Almacén", callback_data='gestion_almacen')],
            [InlineKeyboardButton("📦 Aprobar Pedidos de Material", callback_data='aprobar_pedidos')],
            [InlineKeyboardButton("👍 Aprobar Solicitudes de Personal", callback_data='rrhh_aprobar')],
            [InlineKeyboardButton("📋 Mis Solicitudes de Personal", callback_data='rrhh_mis_solicitudes')],
            [InlineKeyboardButton("🛠️ Gestionar Ubicaciones", callback_data='manage_ubicaciones')],
            [InlineKeyboardButton("📊 Consultar Informes", callback_data='consultar_informes')]
        ])
    elif user_role == 'Gerente':
        keyboard.extend([
            [InlineKeyboardButton("🆕 Gestionar Órdenes", callback_data='gestionar_ordenes')],
            [InlineKeyboardButton("🆕 Crear Orden", callback_data='crear_orden')],
            [InlineKeyboardButton("📦 Aprobar Pedidos de Material", callback_data='aprobar_pedidos')],
            [InlineKeyboardButton("📊 Consultar Informes", callback_data='consultar_informes')],
            [InlineKeyboardButton("📈 Gestionar Solicitudes de Personal", callback_data='rrhh_gestionar')]
        ])
    elif user_role == 'Almacen':
        keyboard.extend([
            [InlineKeyboardButton("📦 Gestión de Almacén", callback_data='gestion_almacen')],
            [InlineKeyboardButton("📋 Ver Inventario Completo", callback_data='almacen_ver_inventario')],
            [InlineKeyboardButton("🏗️ Listar Material en Obra", callback_data='almacen_listar_obra')]
        ])
    elif user_role == 'RRHH':
        keyboard.extend([
            [InlineKeyboardButton("🔍 Buscar Candidatos", callback_data='rrhh_buscar')]
        ])
    elif user_role == 'Prevencion':
        keyboard.extend([
            [InlineKeyboardButton("🕵️‍♂️ Reportar Incidencia", callback_data='prevencion_reportar')],
            [InlineKeyboardButton("📢 Enviar Comunicado General", callback_data='prevencion_comunicado')],
            [InlineKeyboardButton("📋 Mis Incidencias Reportadas", callback_data='prevencion_mis_incidencias')],
            [InlineKeyboardButton("📋 Historial de Incidencias", callback_data='prevencion_ver_incidencias')]
        ])
    elif user_role == 'Admin':
        keyboard.extend([
            [InlineKeyboardButton("👤 Gestionar Roles de Usuario", callback_data='manage_roles_start')]
        ])
    
    if not keyboard:
        text = f"Hola {user.first_name}. Tu rol ({user_role}) no tiene acciones configuradas."
    else:
        keyboard.append([InlineKeyboardButton("❌ Salir", callback_data='exit_bot')])

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)

async def exit_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="¡Hasta luego! 👋")

async def end_and_return_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()
    context.user_data.clear()
    await start(update, context)
    return ConversationHandler.END
    return ConversationHandler.END
