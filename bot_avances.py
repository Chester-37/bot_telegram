# bot_avances.py

import os
from datetime import datetime, date
from telegram import InputFile, InlineKeyboardButton, InlineKeyboardMarkup, Update
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


# Estados de Conversación
(
    # Flujo de registro
    SELECTING_EDIFICIO, SELECTING_ZONA, SELECTING_PLANTA, SELECTING_NUCLEO,
    SELECTING_TRABAJO, ASKING_FECHA, GETTING_FECHA, ASKING_FOTO, GETTING_FOTO,
    ASKING_INCIDENCIA, GETTING_INCIDENCIA_DESC,
    # Flujo de resolución
    AWAITING_RESOLUTION_DESC,
    # Flujo de ver avances finalizados
    VIEWING_AVANCES_LIST, VIEWING_AVANCE_DETAIL
) = range(14)

ITEMS_PER_PAGE = 5 # Constante para la paginación

# --- Helpers ---
def get_cancel_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_conversation")]])

def get_nav_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Menú Principal", callback_data="back_to_main_menu")]])

def build_dynamic_keyboard(items, callback_prefix):
    keyboard = []
    row = []
    for item in items:
        row.append(InlineKeyboardButton(item['nombre'], callback_data=f"{callback_prefix}{item['nombre']}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancel_conversation")])
    return InlineKeyboardMarkup(keyboard)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer("Operación cancelada.")
        await query.edit_message_text("Operación cancelada.")
    else:
        await update.message.reply_text("Operación cancelada.")
    
    context.user_data.clear()
    await start(update, context)
    return ConversationHandler.END

async def ver_foto_avance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    try:
        avance_id = int(query.data.split('_')[3])
    except (IndexError, ValueError):
        await query.message.reply_text("Error: ID de avance no válido.")
        return
    foto_path = db.get_foto_path_by_avance_id(avance_id)
    if foto_path and os.path.exists(foto_path):
        try:
            with open(foto_path, 'rb') as photo_file:
                await context.bot.send_photo(chat_id=query.from_user.id, photo=InputFile(photo_file))
        except Exception as e:
            await query.message.reply_text(f"No se pudo enviar la foto: {e}")
    else:
        await query.message.reply_text("No se encontró la foto para este avance o el archivo fue eliminado.")

# =============================================================================
# FLUJO 1: REGISTRO DE AVANCE
# =============================================================================
async def start_registro(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['current_avance'] = {}
    edificios = db.get_ubicaciones_by_tipo('Edificio')
    if not edificios:
        await query.edit_message_text("❌ No hay 'Edificios' configurados.", reply_markup=get_nav_keyboard())
        return ConversationHandler.END
    keyboard = build_dynamic_keyboard(edificios, "E_")
    await query.edit_message_text("Paso 1: Selecciona la ubicación\n\nElige el Edificio:", reply_markup=keyboard)
    return SELECTING_ZONA

async def select_zona(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['current_avance']['edificio'] = query.data.split('_', 1)[1]
    zonas = db.get_ubicaciones_by_tipo('Zona')
    if not zonas:
        await query.edit_message_text("❌ No hay 'Zonas' configuradas.", reply_markup=get_nav_keyboard())
        return ConversationHandler.END
    keyboard = build_dynamic_keyboard(zonas, "Z_")
    await query.edit_message_text("Selecciona la Zona:", reply_markup=keyboard)
    return SELECTING_PLANTA

async def select_planta(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['current_avance']['zona'] = query.data.split('_', 1)[1]
    plantas = db.get_ubicaciones_by_tipo('Planta')
    if not plantas:
        await query.edit_message_text("❌ No hay 'Plantas' configuradas.", reply_markup=get_nav_keyboard())
        return ConversationHandler.END
    keyboard = build_dynamic_keyboard(plantas, "P_")
    await query.edit_message_text("Selecciona la Planta:", reply_markup=keyboard)
    return SELECTING_NUCLEO

async def select_nucleo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['current_avance']['planta'] = query.data.split('_', 1)[1]
    nucleos = db.get_ubicaciones_by_tipo('Nucleo')
    if not nucleos:
        await query.edit_message_text("❌ No hay 'Núcleos' configurados.", reply_markup=get_nav_keyboard())
        return ConversationHandler.END
    keyboard = build_dynamic_keyboard(nucleos, "N_")
    await query.edit_message_text("Selecciona el Núcleo:", reply_markup=keyboard)
    return SELECTING_TRABAJO

async def select_trabajo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['current_avance']['nucleo'] = query.data.split('_', 1)[1]
    keyboard = [
        [InlineKeyboardButton("Encofrado primera cara", callback_data='Encofrado primera cara')],
        [InlineKeyboardButton("Armado", callback_data='Armado')],
        [InlineKeyboardButton("Hormigonado", callback_data='Hormigonado')],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_conversation")]
    ]
    await query.edit_message_text("Paso 2: Selecciona el tipo de trabajo", reply_markup=InlineKeyboardMarkup(keyboard))
    return ASKING_FECHA

async def ask_fecha(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['current_avance']['trabajo'] = query.data
    
    now = datetime.now()
    calendar_markup = await create_calendar(now.year, now.month, allow_past_dates=True)
    
    calendar_keyboard_list = list(calendar_markup.inline_keyboard)
    calendar_keyboard_list.insert(2, [InlineKeyboardButton("🗓️ Usar Fecha de Hoy", callback_data="date_today")])
    
    reply_markup = InlineKeyboardMarkup(calendar_keyboard_list)
    
    await query.edit_message_text(
        text="Paso 3: Selecciona la fecha en la que se realizó el trabajo.",
        reply_markup=reply_markup
    )
    return GETTING_FECHA

async def process_date_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    
    if query.data == "date_today":
        await query.answer()
        fecha_obj = datetime.now().date()
        
        context.user_data['current_avance']['fecha_trabajo'] = fecha_obj
        
        keyboard = [
            [InlineKeyboardButton("Añadir foto", callback_data='add_photo')],
            [InlineKeyboardButton("Continuar sin foto", callback_data='skip_photo')],
            [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_conversation")]
        ]
        
        await query.edit_message_text(
            text=f"Fecha seleccionada: *{fecha_obj.strftime('%d/%m/%Y')}*.\n\nPaso 4: ¿Deseas añadir foto del avance?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return ASKING_FOTO

    result = await process_calendar_selection(update, context)

    # --- INICIO DE LA CORRECCIÓN ---
    # Se comprueba contra 'date' directamente, no 'datetime.date'
    if isinstance(result, date):
    # --- FIN DE LA CORRECCIÓN ---
        fecha_obj = result
        context.user_data['current_avance']['fecha_trabajo'] = fecha_obj
        
        keyboard = [
            [InlineKeyboardButton("Añadir foto", callback_data='add_photo')],
            [InlineKeyboardButton("Continuar sin foto", callback_data='skip_photo')],
            [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_conversation")]
        ]
        
        await query.edit_message_text(
            text=f"Fecha seleccionada: *{fecha_obj.strftime('%d/%m/%Y')}*.\n\nPaso 4: ¿Deseas añadir foto del avance?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return ASKING_FOTO
    
    return GETTING_FECHA

    # Si no es "Hoy", procesa el calendario
    # La función del helper se encarga de editar el mensaje si se navega
    result = await process_calendar_selection(update, context)

    # Si el resultado es un objeto de fecha (date), significa que se pulsó un día
    if isinstance(result, datetime.date):
        fecha_obj = result
        context.user_data['current_avance']['fecha_trabajo'] = fecha_obj
        
        # Prepara y muestra el siguiente paso
        keyboard = [
            [InlineKeyboardButton("Añadir foto", callback_data='add_photo')],
            [InlineKeyboardButton("Continuar sin foto", callback_data='skip_photo')],
            [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_conversation")]
        ]
        
        await query.edit_message_text(
            text=f"Fecha seleccionada: *{fecha_obj.strftime('%d/%m/%Y')}*.\n\nPaso 4: ¿Deseas añadir foto del avance?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return ASKING_FOTO
    
    # Si el resultado no es una fecha (es True o False), significa que el usuario
    # está navegando o ha pulsado un botón sin acción. Nos mantenemos en el mismo estado.
    return GETTING_FECHA

async def get_foto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()
        if query.data == 'add_photo':
            await query.edit_message_text("Por favor, envía la foto ahora.", reply_markup=get_cancel_keyboard())
            return GETTING_FOTO
        else:
            context.user_data['current_avance']['foto_path'] = None
            return await ask_incidencia(update, context)
    else:
        photo_file = await update.message.photo[-1].get_file()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"avance_{update.effective_user.id}_{timestamp}.jpg"
        os.makedirs('avances_fotos', exist_ok=True)
        file_path = os.path.join('avances_fotos', file_name)
        await photo_file.download_to_drive(file_path)
        context.user_data['current_avance']['foto_path'] = file_path
        return await ask_incidencia(update, context)

async def ask_incidencia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message_source = update.callback_query.message if update.callback_query else update.message
    keyboard = [
        [InlineKeyboardButton("Sí, añadir incidencia", callback_data='add_incidencia')],
        [InlineKeyboardButton("No, finalizar registro", callback_data='no_incidencia')],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_conversation")]
    ]
    await message_source.reply_text("Paso 5: ¿Hay alguna incidencia que reportar?", reply_markup=InlineKeyboardMarkup(keyboard))
    return GETTING_INCIDENCIA_DESC

async def get_incidencia_desc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()
        if query.data == 'add_incidencia':
            await query.edit_message_text("Describe brevemente la incidencia detectada:", reply_markup=get_cancel_keyboard())
            return GETTING_INCIDENCIA_DESC
        else:
            await query.edit_message_text("Registrando avance...")
            await save_avance(update, context, has_incidencia=False)
            return ConversationHandler.END
    else:
        context.user_data['current_avance']['incidencia_desc'] = update.message.text
        await update.message.reply_text("Registrando avance e incidencia...")
        await save_avance(update, context, has_incidencia=True)
        return ConversationHandler.END

async def save_avance(update: Update, context: ContextTypes.DEFAULT_TYPE, has_incidencia: bool):
    user = update.effective_user
    avance_data = context.user_data['current_avance']
    message_source = update.callback_query.message if update.callback_query else update.message

    # Se construye la cadena de texto de ubicación como se hacía originalmente
    ubicacion_str = f"{avance_data['edificio']} / {avance_data['zona']} / {avance_data['planta']} / {avance_data['nucleo']}"
    
    # Se llama a `create_avance` pasando la cadena de texto, no un diccionario.
    # Esto soluciona el error `TypeError`.
    avance_id = db.create_avance(
        user.id,
        ubicacion_str,
        avance_data['trabajo'],
        avance_data.get('foto_path'),
        'Con Incidencia' if has_incidencia else 'Finalizado',
        avance_data['fecha_trabajo'],
        tipo_trabajo_id=None,  # Mantener compatibilidad con sistema anterior
        observaciones=None     # No se usan observaciones en el sistema anterior
    )

    fecha_formateada = avance_data['fecha_trabajo'].strftime('%d/%m/%Y')
    
    if has_incidencia:
        incidencia_id = db.create_incidencia(avance_id, avance_data['incidencia_desc'], user.id)
        report_text = (
            f"🚨 *Reporte: Nuevo Avance con Incidencia* 🚨\n\n"
            f"*ID Incidencia:* `{incidencia_id}`\n"
            f"*ID Avance:* `{avance_id}`\n"
            f"*Reportado por:* {format_user(user)}\n"
            f"*Ubicación:* {escape(ubicacion_str)}\n"
            f"*Trabajo:* {escape(avance_data['trabajo'])}\n"
            f"*Fecha Trabajo:* {escape(fecha_formateada)}\n\n"
            f"*Descripción Incidencia:*\n_{escape(avance_data['incidencia_desc'])}_"
        )
        await message_source.reply_text(f"Avance #{avance_id} e incidencia #{incidencia_id} registrados.", reply_markup=get_nav_keyboard())
    else:
        report_text = (
            f"✅ *Reporte: Nuevo Avance de Obra* ✅\n\n"
            f"*ID Avance:* `{avance_id}`\n"
            f"*Encargado:* {format_user(user)}\n"
            f"*Ubicación:* {escape(ubicacion_str)}\n"
            f"*Trabajo:* {escape(avance_data['trabajo'])}\n"
            f"*Fecha Trabajo:* {escape(fecha_formateada)}"
        )
        await message_source.reply_text("El avance ha sido registrado correctamente. ¡Buen trabajo!", reply_markup=get_nav_keyboard())
    
    photo_to_send = avance_data.get('foto_path')    
    await send_report(context, report_text, photo_path=photo_to_send)
    context.user_data.clear()

# =============================================================================
# FLUJO 2: RESOLUCIÓN DE INCIDENCIAS
# =============================================================================
async def start_resolution(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    incidencia_id = int(query.data.split('_')[1])
    context.user_data['resolving_incidencia_id'] = incidencia_id
    await query.edit_message_text("Por favor, escribe la descripción de la resolución:", reply_markup=get_cancel_keyboard())
    return AWAITING_RESOLUTION_DESC

async def save_resolution_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    resolution_desc = update.message.text
    incidencia_id = context.user_data['resolving_incidencia_id']
    user = update.effective_user
    db.resolve_incidencia(incidencia_id, user.id, resolution_desc)
    await update.message.reply_text(f"✅ Incidencia #{incidencia_id} marcada como resuelta.", reply_markup=get_nav_keyboard())
    report_text = (
        f"🛠️ *Reporte: Incidencia Resuelta* 🛠️\n\n"
        f"*ID Incidencia:* `{incidencia_id}`\n"
        f"*Resuelta por:* {format_user(user)}\n\n"
        f"*Notas de Resolución:*\n_{escape(resolution_desc)}_"
    )
    await send_report(context, report_text)
    context.user_data.clear()
    return ConversationHandler.END

# =============================================================================
# FLUJO 3: VER AVANCES FINALIZADOS
# =============================================================================
async def start_ver_finalizados(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Punto de entrada para ver la lista de avances finalizados."""
    query = update.callback_query
    await query.answer()
    context.user_data['avances_page'] = 0
    await show_avances_page(update, context)
    return VIEWING_AVANCES_LIST

async def change_avances_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cambia la página de la lista de avances."""
    query = update.callback_query
    await query.answer()
    direction = query.data.split('_')[1]
    page = context.user_data.get('avances_page', 0)
    context.user_data['avances_page'] = page + 1 if direction == 'next' else page - 1
    await show_avances_page(update, context)
    return VIEWING_AVANCES_LIST

async def show_avances_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra una página de la lista de avances finalizados, editando el mensaje actual."""
    query = update.callback_query
    page = context.user_data.get('avances_page', 0)
    
    avances, total_pages = db.get_finalizados_paginated(page, ITEMS_PER_PAGE)

    if not avances and page == 0:
        await query.edit_message_text("✅ No hay avances finalizados para mostrar.", reply_markup=get_nav_keyboard())
        return

    keyboard = []
    for avance in avances:
        button_text = f"ID:{avance['id']} - {avance['trabajo']} ({avance['fecha_trabajo'].strftime('%d/%m')})"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"view_avance_{avance['id']}")])
        
    pagination_row = []
    if page > 0:
        pagination_row.append(InlineKeyboardButton("⬅️ Anterior", callback_data="avpag_prev"))
    if page < total_pages - 1:
        pagination_row.append(InlineKeyboardButton("Siguiente ➡️", callback_data="avpag_next"))
    if pagination_row:
        keyboard.append(pagination_row)
        
    keyboard.append([InlineKeyboardButton("⬅️ Menú Principal", callback_data="back_to_main_menu")])
    
    # --- INICIO DE LA CORRECCIÓN ---
    # Se escapan los paréntesis para que sean compatibles con MarkdownV2
    message_text = f"📖 *Avances Finalizados* \\(Página {page + 1}/{total_pages}\\)\n\nSelecciona un avance para ver sus detalles:"
    # --- FIN DE LA CORRECCIÓN ---
    
    await query.edit_message_text(
        text=message_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='MarkdownV2'
    )

async def show_avance_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Muestra los detalles de un avance, enviando la foto y editando el mensaje con el texto."""
    query = update.callback_query
    await query.answer()
    avance_id = int(query.data.split('_')[2])
    
    details = db.get_avance_details(avance_id)
    
    if not details:
        await query.edit_message_text("❌ Error: No se encontraron los detalles de este avance.", reply_markup=get_nav_keyboard())
        return ConversationHandler.END

    details_text = (
        f"*Detalle del Avance \\#{details['id']}*\n\n"
        f"👤 *Encargado:* {escape(details['encargado_name'])}\n"
        f"📍 *Ubicación:* {escape(details['ubicacion'])}\n"
        f"🛠️ *Trabajo:* {escape(details['trabajo'])}\n"
        f"🗓️ *Fecha:* {details['fecha_trabajo'].strftime('%d/%m/%Y')}"
    )
    
    if details['foto_path'] and os.path.exists(details['foto_path']):
        try:
            with open(details['foto_path'], 'rb') as photo_file:
                await context.bot.send_photo(chat_id=query.from_user.id, photo=photo_file)
        except Exception as e:
            await query.message.reply_text(f"No se pudo cargar la foto: {e}")

    keyboard = [[InlineKeyboardButton("⬅️ Volver a la lista", callback_data="back_to_avances_list")]]
    await query.edit_message_text(
        text=details_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='MarkdownV2'
    )
    
    return VIEWING_AVANCE_DETAIL

async def back_to_avances_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Vuelve a la vista de lista de avances editando el mensaje actual."""
    query = update.callback_query
    await query.answer()
    await show_avances_page(update, context)
    return VIEWING_AVANCES_LIST



# =============================================================================
# HANDLERS
# =============================================================================
def get_avances_handlers():
    """Devuelve una lista con todos los ConversationHandlers de este módulo."""
    
    registro_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_registro, pattern='^registrar_avance$')],
        states={
            SELECTING_ZONA: [CallbackQueryHandler(select_zona, pattern='^E_')],
            SELECTING_PLANTA: [CallbackQueryHandler(select_planta, pattern='^Z_')],
            SELECTING_NUCLEO: [CallbackQueryHandler(select_nucleo, pattern='^P_')],
            SELECTING_TRABAJO: [CallbackQueryHandler(select_trabajo, pattern='^N_')],
            ASKING_FECHA: [CallbackQueryHandler(ask_fecha)],
            GETTING_FECHA: [
                CallbackQueryHandler(process_date_selection, pattern=r'^(cal_|date_today$)')
            ],
            ASKING_FOTO: [CallbackQueryHandler(get_foto, pattern='^(add_photo|skip_photo)$')],
            GETTING_FOTO: [MessageHandler(filters.PHOTO, get_foto)],
            ASKING_INCIDENCIA: [CallbackQueryHandler(ask_incidencia)],
            GETTING_INCIDENCIA_DESC: [
                CallbackQueryHandler(get_incidencia_desc, pattern='^(add_incidencia|no_incidencia)$'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_incidencia_desc)
            ],
        },
        fallbacks=[CallbackQueryHandler(cancel, pattern='^cancel_conversation$')],
        map_to_parent={ConversationHandler.END: ConversationHandler.END}
    )

    # --- INICIO DE LA CORRECCIÓN: AÑADIR LAS DEFINICIONES QUE FALTAN ---
    
    resolution_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_resolution, pattern='^resolve_')],
        states={
            AWAITING_RESOLUTION_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_resolution_notes)]
        },
        fallbacks=[CallbackQueryHandler(cancel, pattern='^cancel_conversation$')],
        map_to_parent={ConversationHandler.END: ConversationHandler.END}
    )

    ver_avances_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_ver_finalizados, pattern='^ver_avances_sin_incidencias$')],
        states={
            VIEWING_AVANCES_LIST: [
                CallbackQueryHandler(change_avances_page, pattern='^avpag_'),
                CallbackQueryHandler(show_avance_details, pattern='^view_avance_')
            ],
            VIEWING_AVANCE_DETAIL: [
                CallbackQueryHandler(back_to_avances_list, pattern='^back_to_avances_list$'),
            ],
        },
        fallbacks=[CallbackQueryHandler(end_and_return_to_menu, pattern='^back_to_main_menu$')],
        map_to_parent={ConversationHandler.END: ConversationHandler.END}
    )
    
    # --- FIN DE LA CORRECCIÓN ---

    # Ahora que todas las variables están definidas, esta línea funcionará
    return [registro_handler, resolution_handler, ver_avances_handler]
