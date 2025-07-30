# rrhh/bot_rrhh.py
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from telegram.helpers import escape_markdown
import db_manager as db
from bot_navigation import end_and_return_to_menu, start
from reporter import send_report, escape, format_user
from calendar_helper import create_calendar, process_calendar_selection

# Estados
(
    SELECTING_PUESTO, AWAITING_CANTIDAD, ASKING_MORE_PUESTOS, SELECTING_FECHA, # ASKING_MORE_PUESTOS es nuevo
    AWAITING_NOTAS_SOLICITUD, SELECTING_SOLICITUD_MANAGE, VIEWING_SOLICITUD_MANAGE, 
    AWAITING_DECISION_NOTES, LISTING_MY_SOLICITUDES, VIEWING_MY_SOLICITUD,
    LISTING_APPROVED_REQUESTS, VIEWING_APPROVED_REQUEST, AWAITING_RRHH_NOTE
) = range(13)


# --- Helpers ---
def get_cancel_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_conversation")]])

def get_nav_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Menú Principal", callback_data="back_to_main_menu")]])

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer("Operación cancelada.")
        await query.edit_message_text(text="Operación cancelada.")
    else:
        await update.message.reply_text("Operación cancelada.")
    context.user_data.clear()
    await start(update, context)
    return ConversationHandler.END

# =========================================================================
# FLUJO 1: CREAR SOLICITUD DE PERSONAL
# =========================================================================

def _build_puestos_summary(puestos_list: list) -> str:
    """Construye un texto resumen de los puestos añadidos."""
    if not puestos_list:
        return ""
    summary = "\n\n*Puestos añadidos hasta ahora:*\n"
    for item in puestos_list:
        summary += f"\\- {item['cantidad']} x {escape(item['puesto'])}\n"
    return summary

async def start_solicitud(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    context.user_data['new_solicitud'] = {'puestos': []}
    
    keyboard = [
        [InlineKeyboardButton("Oficial Encofrador", callback_data="puesto_Oficial Encofrador")],
        [InlineKeyboardButton("Oficial Ferralla", callback_data="puesto_Oficial Ferralla")],
        [InlineKeyboardButton("Oficial Albañil", callback_data="puesto_Oficial Albañil")],
        [InlineKeyboardButton("Ayudante", callback_data="puesto_Ayudante")],
        [InlineKeyboardButton("Gruista", callback_data="puesto_Gruista")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_conversation")]
    ]
    
    await query.edit_message_text(
        "✍️ *Creando Solicitud de Personal*\n\nPaso 1: Selecciona el puesto de trabajo que necesitas:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='MarkdownV2'
    )
    return SELECTING_PUESTO

async def get_puesto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    puesto = query.data.split('_', 1)[1]
    # MODIFICADO: Guardamos el puesto actual de forma temporal
    context.user_data['current_puesto'] = puesto
    
    summary_text = _build_puestos_summary(context.user_data['new_solicitud']['puestos'])
    
    await query.edit_message_text(
        f"Puesto seleccionado: *{escape(puesto)}*\\.\n\nPaso 2: ¿Cuántas personas necesitas para este puesto?{summary_text}",
        parse_mode='MarkdownV2',
        reply_markup=get_cancel_keyboard()
    )
    return AWAITING_CANTIDAD

async def get_cantidad(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cantidad = update.message.text
    if not cantidad.isdigit() or int(cantidad) <= 0:
        await update.message.reply_text("❌ Por favor, introduce un número válido.", reply_markup=get_cancel_keyboard())
        return AWAITING_CANTIDAD
        
    # MODIFICADO: Añadimos el puesto y cantidad a la lista
    puesto_actual = context.user_data.pop('current_puesto')
    context.user_data['new_solicitud']['puestos'].append({
        'puesto': puesto_actual,
        'cantidad': int(cantidad)
    })
    
    summary_text = _build_puestos_summary(context.user_data['new_solicitud']['puestos'])

    # MODIFICADO: Preguntamos si quiere añadir más
    keyboard = [
        [InlineKeyboardButton("✅ Sí, añadir otro puesto", callback_data="add_more_puestos")],
        [InlineKeyboardButton("➡️ No, continuar", callback_data="continue_to_date")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_conversation")]
    ]
    
    await update.message.reply_text(
        text=f"Añadido\\. {summary_text}\n\n¿Deseas añadir otro puesto a esta solicitud?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='MarkdownV2'
    )
    return ASKING_MORE_PUESTOS

async def ask_more_puestos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la decisión de añadir más puestos o continuar."""
    query = update.callback_query
    await query.answer()

    if query.data == 'add_more_puestos':
        # Vuelve a mostrar la selección de puestos
        keyboard = [
            [InlineKeyboardButton("Oficial Encofrador", callback_data="puesto_Oficial Encofrador")],
            [InlineKeyboardButton("Oficial Ferralla", callback_data="puesto_Oficial Ferralla")],
            [InlineKeyboardButton("Oficial Albañil", callback_data="puesto_Oficial Albañil")],
            [InlineKeyboardButton("Ayudante", callback_data="puesto_Ayudante")],
            [InlineKeyboardButton("Gruista", callback_data="puesto_Gruista")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_conversation")]
        ]
        summary_text = _build_puestos_summary(context.user_data['new_solicitud']['puestos'])
        await query.edit_message_text(
            f"Selecciona el siguiente puesto a añadir:{summary_text}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='MarkdownV2'
        )
        return SELECTING_PUESTO
    else: # 'continue_to_date'
        # Continúa al siguiente paso: la fecha
        today = datetime.date.today()
        summary_text = _build_puestos_summary(context.user_data['new_solicitud']['puestos'])
        await query.edit_message_text(
            text=f"Paso 3: ¿Para qué fecha se necesitan?{summary_text}",
            reply_markup=await create_calendar(today.year, today.month),
            parse_mode='MarkdownV2'
        )
        return SELECTING_FECHA

async def get_fecha(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Esta función ahora se llama desde ask_more_puestos
    query = update.callback_query
    result = await process_calendar_selection(update, context)
    
    if isinstance(result, datetime.date):
        selected_date = result
        context.user_data['new_solicitud']['fecha'] = selected_date
        
        keyboard = [[InlineKeyboardButton("Omitir notas", callback_data="skip_notes")], [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_conversation")]]
        
        summary_text = _build_puestos_summary(context.user_data['new_solicitud']['puestos'])
        texto_mensaje = f"Fecha seleccionada: *{escape(selected_date.strftime('%d/%m/%Y'))}*\\.\n\nPaso 4: Añade notas adicionales \\(opcional\\)\\.{summary_text}"
        
        await query.edit_message_text(
            texto_mensaje,
            parse_mode='MarkdownV2',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return AWAITING_NOTAS_SOLICITUD
        
    return SELECTING_FECHA

async def get_notas_solicitud(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query and query.data == "skip_notes":
        await query.answer()
        context.user_data['new_solicitud']['notas'] = "Ninguna"
        await query.edit_message_text("Registrando solicitud sin notas...")
    else:
        context.user_data['new_solicitud']['notas'] = update.message.text
        await update.message.reply_text("Registrando solicitud...")
    return await save_solicitud(update, context)

async def save_solicitud(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    data = context.user_data['new_solicitud']
    message_source = update.callback_query.message if update.callback_query else update.message
    
    group_chat_id = context.user_data.get('group_chat_id')
    
    # MODIFICADO: Pasamos la lista de puestos a la función de la BD
    solicitud_id = db.create_solicitud_personal(
        user.id, 
        data['puestos'], 
        data['fecha'], 
        data.get('notas'), 
        group_chat_id
    )
    
    await message_source.reply_text(f"✅ Solicitud #{solicitud_id} creada y enviada para aprobación.", reply_markup=get_nav_keyboard())
    
    # MODIFICADO: El reporte ahora muestra una lista de puestos
    puestos_str = ""
    for item in data['puestos']:
        puestos_str += f"\\- {item['cantidad']} x {escape(item['puesto'])}\n"

    report_text = (
        f"👤 *Reporte: Nueva Solicitud de Personal* 👤\n\n"
        f"*ID Solicitud:* `{solicitud_id}`\n"
        f"*Solicitante:* {format_user(user)}\n"
        f"*Puestos Solicitados:*\n{puestos_str}"
        f"*Fecha Incorporación:* {escape(data['fecha'].strftime('%d/%m/%Y'))}\n"
        f"*Notas:* {escape(data.get('notas'))}"
    )
    await send_report(context, report_text)

    tecnicos = db.get_users_by_role('Tecnico')
    if tecnicos:
        texto_notificacion = f"🔔 *Nueva Solicitud de Personal \\(ID: {solicitud_id}\\)* requiere tu aprobación\\."
        keyboard = [[InlineKeyboardButton("👍 Aprobar Solicitudes", callback_data='rrhh_aprobar')]]
        for tecnico in tecnicos:
            await context.bot.send_message(tecnico['id'], texto_notificacion, parse_mode='MarkdownV2', reply_markup=InlineKeyboardMarkup(keyboard))
            
    context.user_data.clear()
    return ConversationHandler.END

# =========================================================================
# FLUJO 2: VER MIS SOLICITUDES
# =========================================================================
async def show_my_requests_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    solicitudes = db.get_solicitudes_by_solicitante(user_id)
    if not solicitudes:
        await query.edit_message_text("✅ No has realizado ninguna solicitud de personal.", reply_markup=get_nav_keyboard())
        return ConversationHandler.END

    keyboard = []
    for s in solicitudes:
        status_emoji = {'Aprobada': '✅', 'Rechazada': '❌', 'Cancelada': '⛔'}.get(s['estado'], '⏳')
        
        # --- LÍNEA A MODIFICAR ---
        # ANTES: button_text = f"{status_emoji} ID:{s['id']} - {s['cantidad']} {s['puesto']}"
        # AHORA: (ya que s['puesto'] contiene todo el texto)
        button_text = f"{status_emoji} ID:{s['id']} - {s['puesto']}"
        # --- FIN DE LA MODIFICACIÓN ---

        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"my_req_view_{s['id']}")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Menú Principal", callback_data="back_to_main_menu")])
    await query.edit_message_text("Aquí están tus solicitudes de personal. Selecciona una para ver los detalles:", reply_markup=InlineKeyboardMarkup(keyboard))
    return LISTING_MY_SOLICITUDES

async def view_my_request_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    solicitud_id = int(query.data.split('_')[3])
    
    details = db.get_solicitud_details(solicitud_id)
    if not details:
        await query.edit_message_text("❌ Error: No se encontró la solicitud.", reply_markup=get_nav_keyboard())
        return ConversationHandler.END
        
    texto = (f"📄 *Detalle de tu Solicitud \\#{details['id']}*\n\n"
             f"▪️ *Puesto:* {escape(details['puesto'])}\n"
             f"▪️ *Cantidad:* {details['cantidad']}\n"
             f"▪️ *Fecha Incorp\\.:* {escape(details['fecha'])}\n"
             f"▪️ *Estado:* `{escape(details['estado'])}`\n\n"
             f"▪️ *Tus Notas:* _{escape(details.get('notas_solicitud') or 'Ninguna')}_\n")

    if details.get('notas_decision'):
        texto += f"▪️ *Notas de Decisión:* _{escape(details.get('notas_decision'))}_\n"

    keyboard = [[InlineKeyboardButton("<< Volver a la lista", callback_data="back_to_my_list")]]
    await query.edit_message_text(texto, parse_mode='MarkdownV2', reply_markup=InlineKeyboardMarkup(keyboard))
    return VIEWING_MY_SOLICITUD

# =========================================================================
# FLUJO 3: GESTIONAR SOLICITUDES (Tecnico/Gerente)
# =========================================================================
async def show_solicitudes_to_manage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_role = db.get_user_role(query.from_user.id)
    
    estados_map = {'Tecnico': ['Pendiente Aprobacion'], 'Gerente': ['Pendiente Aprobacion', 'Aprobada', 'En Busqueda', 'Problemas Notificados']}
    estados = estados_map.get(user_role)
    if not estados:
        await query.edit_message_text("No tienes permisos para esta acción.", reply_markup=get_nav_keyboard())
        return ConversationHandler.END

    solicitudes = db.get_solicitudes_by_estado(estados)
    if not solicitudes:
        await query.edit_message_text("✅ No hay solicitudes activas para gestionar.", reply_markup=get_nav_keyboard())
        return ConversationHandler.END

    keyboard = [[InlineKeyboardButton(f"ID:{s['id']} - {s['cantidad']} {s['puesto']}", callback_data=f"manage_view_{s['id']}")] for s in solicitudes]
    keyboard.append([InlineKeyboardButton("⬅️ Menú Principal", callback_data="back_to_main_menu")])
    await query.edit_message_text("Selecciona una solicitud para gestionar:", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECTING_SOLICITUD_MANAGE

async def view_solicitud_to_manage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    solicitud_id = int(query.data.split('_')[2])
    context.user_data['managing_solicitud_id'] = solicitud_id
    details = db.get_solicitud_details(solicitud_id)
    if not details:
        await query.edit_message_text("❌ Error: No se encontró la solicitud.", reply_markup=get_nav_keyboard())
        return ConversationHandler.END
    
    puestos_str = ""
    for item in details['puestos']:
        puestos_str += f"\\- {item['cantidad']} x {escape(item['puesto'])}\n"

    texto = (f"📄 *Detalle Solicitud \\#{details['id']}*\n\n"
             f"▪️ *Solicitante:* {escape(details['solicitante_name'])}\n"
             f"▪️ *Puestos:*\n{puestos_str}"
             f"▪️ *Estado:* `{escape(details['estado'])}`\n"
             f"▪️ *Notas:* _{escape(details.get('notas_solicitud') or 'Ninguna')}_\n")
    
    keyboard = []
    user_role = db.get_user_role(query.from_user.id)
    if user_role == 'Tecnico' and details['estado'] == 'Pendiente Aprobacion':
        keyboard.append([InlineKeyboardButton("✅ Aprobar", callback_data="decision_Aprobada")])
        keyboard.append([InlineKeyboardButton("❌ Rechazar", callback_data="decision_Rechazada")])
    if user_role == 'Gerente' and details['estado'] not in ['Cancelada', 'Rechazada']:
        keyboard.append([InlineKeyboardButton("⛔️ CANCELAR SOLICITUD", callback_data="decision_Cancelada")])
    
    keyboard.append([InlineKeyboardButton("<< Volver a la lista", callback_data="back_to_manage_list")])
    await query.edit_message_text(texto, parse_mode='MarkdownV2', reply_markup=InlineKeyboardMarkup(keyboard))
    return VIEWING_SOLICITUD_MANAGE

async def ask_for_decision_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    decision = query.data.split('_')[1]
    context.user_data['decision'] = decision
    await query.edit_message_text(f"Has decidido: *{escape(decision)}*\\.\n\nPor favor, añade notas para justificar tu decisión\\.", parse_mode='MarkdownV2', reply_markup=get_cancel_keyboard())
    return AWAITING_DECISION_NOTES

async def save_decision(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    notes = update.message.text
    solicitud_id = context.user_data['managing_solicitud_id']
    decision = context.user_data['decision']
    user = update.effective_user
    user_role = db.get_user_role(user.id)

    db.update_solicitud_status(solicitud_id, user.id, decision, notes, user_role)
    await update.message.reply_text(f"✅ Decisión '{escape(decision)}' registrada para la solicitud \\#{solicitud_id}\\.", parse_mode='MarkdownV2', reply_markup=get_nav_keyboard())
    
    details = db.get_solicitud_details(solicitud_id)
    if not details:
        context.user_data.clear()
        return ConversationHandler.END

    await context.bot.send_message(
        chat_id=details['solicitante_id'],
        text=f"🗣️ *Actualización sobre tu solicitud de personal \\#{solicitud_id}*:\nHa sido marcada como *{escape(decision)}*\\.\n*Notas:* {escape(notes)}",
        parse_mode='MarkdownV2'
    )

    emoji = {'Aprobada': '✅', 'Rechazada': '❌', 'Cancelada': '⛔'}.get(decision, '🗣️')
    report_text = (
        f"{emoji} *Reporte: Decisión sobre Solicitud de Personal* {emoji}\n\n"
        f"*ID Solicitud:* `{solicitud_id}`\n"
        f"*Decisión:* *{escape(decision)}*\n"
        f"*Gestionada por:* {format_user(user)}\n"
        f"*Notas:* {escape(notes)}"
    )
    await send_report(context, report_text)

    context.user_data.clear()
    return ConversationHandler.END

# =========================================================================
# FLUJO 4: BUSCAR CANDIDATOS (RRHH)
# =========================================================================
async def _show_rrhh_requests_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Función de ayuda para mostrar la lista de solicitudes a RRHH."""
    estados_a_buscar = ['Aprobada', 'En Busqueda', 'Problemas Notificados']
    solicitudes = db.get_solicitudes_by_estado(estados_a_buscar)
    
    if not solicitudes:
        text = "✅ No hay solicitudes de personal aprobadas pendientes de gestión."
        markup = get_nav_keyboard()
    else:
        text = "Selecciona una solicitud para añadir una nota o actualizar su estado:"
        keyboard = []
        for s in solicitudes:
            keyboard.append([InlineKeyboardButton(
                f"ID:{s['id']} - {s['cantidad']} {s['puesto']} (Solicita: {s['solicitante']})",
                callback_data=f"rrhh_view_{s['id']}"
            )])
        keyboard.append([InlineKeyboardButton("⬅️ Menú Principal", callback_data="back_to_main_menu")])
        markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=markup)
    else:
        await update.message.reply_text(text, reply_markup=markup)

    if not solicitudes:
        return ConversationHandler.END
    
    return LISTING_APPROVED_REQUESTS

async def _show_rrhh_request_details(update: Update, context: ContextTypes.DEFAULT_TYPE, solicitud_id: int) -> int:
    """Función de ayuda para mostrar los detalles de una solicitud a RRHH."""
    details = db.get_solicitud_details(solicitud_id)
    if not details:
        await update.effective_message.reply_text("❌ Error: No se encontró la solicitud.", reply_markup=get_nav_keyboard())
        return ConversationHandler.END

    texto = (f"📄 *Gestionando Solicitud \\#{details['id']}*\n\n"
             f"▪️ *Solicitante:* {escape(details['solicitante_name'])}\n"
             f"▪️ *Puesto:* {escape(details['puesto'])} \\({details['cantidad']}\\)\n"
             f"▪️ *Estado Actual:* `{escape(details['estado'])}`\n"
             f"▪️ *Notas Solicitud:* _{escape(details.get('notas_solicitud') or 'Ninguna')}_\n")
    
    if details['historial_notas_rrhh']:
        texto += "\n*Historial de Notas de RRHH:*\n"
        for nota in details['historial_notas_rrhh']:
            texto += f"\\- _{escape(nota['nota'])}_ \\({nota['fecha']} por {escape(nota['autor'])}\\)\n"

    keyboard = [
        [InlineKeyboardButton("💬 Añadir Nota/Comentario", callback_data="rrhh_add_note")],
        [InlineKeyboardButton("✅ Personal Encontrado (Cubierta)", callback_data="rrhh_status_Cubierta")],
        [InlineKeyboardButton("⚠️ Notificar Problemas", callback_data="rrhh_status_Problemas Notificados")],
        [InlineKeyboardButton("<< Volver a la lista", callback_data="back_to_rrhh_list")]
    ]
    
    if update.callback_query:
        await update.callback_query.edit_message_text(texto, parse_mode='MarkdownV2', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(texto, parse_mode='MarkdownV2', reply_markup=InlineKeyboardMarkup(keyboard))

    return VIEWING_APPROVED_REQUEST

async def start_buscar_candidatos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Punto de entrada para la búsqueda de candidatos. Llama a la función de ayuda de la lista."""
    query = update.callback_query
    await query.answer()
    return await _show_rrhh_requests_list(update, context)

async def show_request_to_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Obtiene el ID de la solicitud y llama a la función de ayuda de detalles."""
    query = update.callback_query
    await query.answer()
    solicitud_id = int(query.data.split('_')[2])
    context.user_data['rrhh_solicitud_id'] = solicitud_id
    return await _show_rrhh_request_details(update, context, solicitud_id)

async def ask_for_rrhh_note(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Pide a RRHH que escriba su nota."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "Por favor, escribe la nota o comentario que deseas añadir:",
        reply_markup=get_cancel_keyboard()
    )
    return AWAITING_RRHH_NOTE

async def save_rrhh_note(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda la nota de RRHH y vuelve a mostrar los detalles de la solicitud."""
    nota = update.message.text
    solicitud_id = context.user_data['rrhh_solicitud_id']
    user_id = update.effective_user.id
    
    db.add_rrhh_note_to_solicitud(solicitud_id, user_id, nota)
    
    await update.message.reply_text("✅ Nota añadida correctamente.")
    
    return await _show_rrhh_request_details(update, context, solicitud_id)

async def update_search_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Actualiza el estado de una solicitud y vuelve a la lista principal."""
    query = update.callback_query
    await query.answer()
    
    nuevo_estado = query.data.split('_')[2]
    solicitud_id = context.user_data['rrhh_solicitud_id']
    user = update.effective_user
    
    db.update_solicitud_status(solicitud_id, user.id, nuevo_estado, f"Estado actualizado por RRHH a '{nuevo_estado}'", "RRHH")
    
    await query.edit_message_text(f"✅ Estado de la solicitud #{solicitud_id} actualizado a '{nuevo_estado}'.")
    
    details = db.get_solicitud_details(solicitud_id)
    if details:
        # Notificar al solicitante original
        await context.bot.send_message(
            chat_id=details['solicitante_id'],
            text=f"🗣️ *Actualización de RRHH sobre tu solicitud \\#{details['id']}*:\nEl estado ha cambiado a *{escape(nuevo_estado)}*\\.",
            parse_mode='MarkdownV2'
        )
        
        # --- INICIO DE LA MODIFICACIÓN ---
        # Notificar al grupo si la solicitud ha sido cubierta
        if nuevo_estado == 'Cubierta':
            report_text = (
                f"🥳 *Reporte: Solicitud de Personal Cubierta* 🥳\n\n"
                f"*ID Solicitud:* `{solicitud_id}`\n"
                f"*Puesto:* {escape(details['puesto'])} \\({details['cantidad']}\\)\n"
                f"*Solicitante Original:* {escape(details['solicitante_name'])}\n"
                f"*Gestionada por:* {format_user(user)}"
            )
            await send_report(context, report_text)
        # --- FIN DE LA MODIFICACIÓN ---

    # Vuelve a mostrar la lista de solicitudes
    return await _show_rrhh_requests_list(update, context)

# =========================================================================
# HANDLERS
# =========================================================================
def get_rrhh_conversation_handlers():
    creation_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_solicitud, pattern='^rrhh_solicitar$')],
        states={
            SELECTING_PUESTO: [CallbackQueryHandler(get_puesto, pattern='^puesto_')],
            AWAITING_CANTIDAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_cantidad)],
            # NUEVO ESTADO Y HANDLER
            ASKING_MORE_PUESTOS: [CallbackQueryHandler(ask_more_puestos, pattern='^(add_more_puestos|continue_to_date)$')],
            SELECTING_FECHA: [CallbackQueryHandler(get_fecha, pattern='^cal_')],
            AWAITING_NOTAS_SOLICITUD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_notas_solicitud),
                CallbackQueryHandler(get_notas_solicitud, pattern='^skip_notes$')
            ],
        },
        fallbacks=[
            CallbackQueryHandler(end_and_return_to_menu, pattern='^back_to_main_menu$'),
            CallbackQueryHandler(cancel, pattern='^cancel_conversation$')
        ],
        map_to_parent={ConversationHandler.END: ConversationHandler.END}
    )

    my_requests_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(show_my_requests_list, pattern='^rrhh_mis_solicitudes$')],
        states={
            LISTING_MY_SOLICITUDES: [CallbackQueryHandler(view_my_request_details, pattern='^my_req_view_')],
            VIEWING_MY_SOLICITUD: [CallbackQueryHandler(show_my_requests_list, pattern='^back_to_my_list$')]
        },
        fallbacks=[
            CallbackQueryHandler(end_and_return_to_menu, pattern='^back_to_main_menu$'),
            CallbackQueryHandler(cancel, pattern='^cancel_conversation$')
        ],
        map_to_parent={ConversationHandler.END: ConversationHandler.END}
    )

    management_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(show_solicitudes_to_manage, pattern='^rrhh_aprobar$'),
            CallbackQueryHandler(show_solicitudes_to_manage, pattern='^rrhh_gestionar$')
        ],
        states={
            SELECTING_SOLICITUD_MANAGE: [CallbackQueryHandler(view_solicitud_to_manage, pattern='^manage_view_')],
            VIEWING_SOLICITUD_MANAGE: [
                CallbackQueryHandler(ask_for_decision_notes, pattern='^decision_'),
                CallbackQueryHandler(show_solicitudes_to_manage, pattern='^back_to_manage_list$')
            ],
            AWAITING_DECISION_NOTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_decision)],
        },
        fallbacks=[
            CallbackQueryHandler(end_and_return_to_menu, pattern='^back_to_main_menu$'),
            CallbackQueryHandler(cancel, pattern='^cancel_conversation$')
        ],
        map_to_parent={ConversationHandler.END: ConversationHandler.END}
    )
    
    search_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_buscar_candidatos, pattern='^rrhh_buscar$')],
        states={
            LISTING_APPROVED_REQUESTS: [
                CallbackQueryHandler(show_request_to_search, pattern='^rrhh_view_')
            ],
            VIEWING_APPROVED_REQUEST: [
                CallbackQueryHandler(ask_for_rrhh_note, pattern='^rrhh_add_note$'),
                CallbackQueryHandler(update_search_status, pattern='^rrhh_status_'),
                CallbackQueryHandler(start_buscar_candidatos, pattern='^back_to_rrhh_list$')
            ],
            AWAITING_RRHH_NOTE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_rrhh_note)
            ],
        },
        fallbacks=[
            CallbackQueryHandler(end_and_return_to_menu, pattern='^back_to_main_menu$'),
            CallbackQueryHandler(cancel, pattern='^cancel_conversation$')
        ],
        map_to_parent={ConversationHandler.END: ConversationHandler.END}
    )
    
    return [creation_handler, my_requests_handler, management_handler, search_handler]
