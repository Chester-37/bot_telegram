# bot_informes.py
import os
import io
import csv
from datetime import datetime, date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
import telegram.error
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
)
import db_manager as db
from bot_navigation import start
from reporter import escape
from calendar_helper import create_calendar, process_calendar_selection
from pdf_reporter import PDFReport

(
    SELECTING_REPORT, SELECTING_AVANCE_FILTER_TYPE, SELECTING_UBICACION, 
    ASKING_DATE_FILTER, ASKING_START_DATE, ASKING_END_DATE, # <-- NUEVOS ESTADOS
    SELECTING_FORMAT, GENERATING_CSV, LISTING_AVANCES, VIEWING_AVANCE_DETAIL,
    ASKING_PERSONAL_START_DATE, ASKING_PERSONAL_END_DATE,
    SELECTING_INCIDENCIA_TYPE,
    SELECTING_PERSONAL_FORMAT, LISTING_PERSONAL
) = range(15)

ITEMS_PER_PAGE = 5


# --- Funciones de Ayuda ---

def get_main_menu_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Menú Principal", callback_data="back_to_main_menu")]])

async def back_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()
    context.user_data.clear()
    await start(update, context)
    return ConversationHandler.END

async def cancel_report_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Función genérica para cancelar la creación de un informe y volver al menú."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="❌ Solicitud de informe cancelada.")
    return await back_to_main_menu(update, context)

# --- Flujo Principal de la Conversación ---

async def start_informes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📊 Informes de Avances de Obra", callback_data="report_avances")],
        [InlineKeyboardButton("🚨 Informes de Incidencias", callback_data="report_incidencias")],
        [InlineKeyboardButton("📈 Informes de Personal", callback_data="report_personal")],
        [InlineKeyboardButton("⬅️ Volver al Menú Principal", callback_data="back_to_main_menu")]
    ]
    
    await query.edit_message_text(
        text="*Módulo de Informes*\n\nSelecciona qué tipo de informe deseas generar:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='MarkdownV2'
    )
    return SELECTING_REPORT

# =============================================================================
# SECCIÓN 1: INFORMES DE INCIDENCIAS
# =============================================================================

async def select_incidencia_report_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("🛠️ Herramientas (Pendientes)", callback_data="show_incidencias_tool_Pendiente")],
        [InlineKeyboardButton("✅ Herramientas (Resueltas)", callback_data="show_incidencias_tool_Resuelta")],
        [InlineKeyboardButton("🏗️ Avances (Pendientes)", callback_data="show_incidencias_avance_Pendiente")],
        [InlineKeyboardButton("✅ Avances (Resueltas)", callback_data="show_incidencias_avance_Resuelta")],
        [InlineKeyboardButton("⏪ Volver", callback_data="back_to_report_menu")]
    ]
    
    await query.edit_message_text(
        text="*Informes de Incidencias*\n\nElige qué tipo de incidencias deseas consultar:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SELECTING_INCIDENCIA_TYPE

async def show_incidencias_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    parts = query.data.split('_')
    incidencia_origen, estado = parts[2], parts[3]

    all_incidencias = db.get_incidencias_by_estado([estado])

    # Definimos el título y filtramos las incidencias en un solo paso
    if incidencia_origen == 'tool':
        # CORREGIDO: Escapamos los paréntesis en el título
        title = f"Incidencias de Herramientas \\({escape(estado)}\\)s"
        incidencias_to_show = [i for i in all_incidencias if i.get('item_name')]
    else: # 'avance'
        # CORREGIDO: Escapamos los paréntesis en el título
        title = f"Incidencias de Avances \\({escape(estado)}\\)s"
        incidencias_to_show = [i for i in all_incidencias if i.get('avance_ubicacion')]

    if not incidencias_to_show:
        # CORREGIDO: Usamos la función escape() en el título para asegurar que todo esté bien formateado
        # y escapamos el punto final.
        await query.edit_message_text(
            f"✅ No hay {escape(title.lower())}\\.",
            reply_markup=get_main_menu_keyboard(),
            parse_mode='MarkdownV2'
        )
        return ConversationHandler.END

    await query.edit_message_text(f"Mostrando: *{escape(title)}*\\.\\.\\.", parse_mode='MarkdownV2')

    for incidencia in incidencias_to_show:
        fecha_reporte_str = incidencia['fecha_reporte'].strftime('%d/%m/%Y %H:%M')
        
        # LÓGICA SIMPLIFICADA Y CORREGIDA: Construimos el texto en una sola sección
        texto_incidencia = ""
        if incidencia.get('item_name'):
            texto_incidencia = (
                f"🛠️ *Incidencia Herramienta ID: {incidencia['incidencia_id']}*\n"
                f"▪️ *Herramienta:* {escape(incidencia['item_name'])}\n"
            )
        elif incidencia.get('avance_ubicacion'):
            texto_incidencia = (
                f"🚨 *Incidencia Avance ID: {incidencia['incidencia_id']}*\n"
                f"📍 *Ubicación:* {escape(incidencia['avance_ubicacion'])}\n"
            )
        
        # Parte común a ambas incidencias
        texto_incidencia += (
            f"🗓️ *Fecha:* {escape(fecha_reporte_str)}\n"
            f"👤 *Reportada por:* {escape(incidencia['reporter_name'])}\n"
            f"▪️ *Descripción:* {escape(incidencia['descripcion'])}"
        )

        # Parte de la resolución
        if incidencia['resolutor']:
            texto_incidencia += f"\n\n✅ *Resuelta por:* @{escape(incidencia['resolutor'])}"
            if incidencia['resolucion_desc']:
                texto_incidencia += f"\n*Observaciones:* _{escape(incidencia['resolucion_desc'])}_"

        # Construcción del teclado (sin cambios, pero ahora es más claro)
        keyboard_buttons = []
        if estado == 'Pendiente':
            # Asumo que quieres el botón de resolver solo para las pendientes
            keyboard_buttons.append(InlineKeyboardButton("Resolver", callback_data=f"resolve_{incidencia['incidencia_id']}"))
        if incidencia['has_foto']:
            keyboard_buttons.append(InlineKeyboardButton("Ver Foto", callback_data=f"ver_foto_incidencia_{incidencia['incidencia_id']}"))
        
        reply_markup = InlineKeyboardMarkup([keyboard_buttons]) if keyboard_buttons else None
        
        await query.message.reply_text(
            text=texto_incidencia, 
            reply_markup=reply_markup, 
            parse_mode='MarkdownV2'
        )

    await query.message.reply_text("Fin de la lista\\.", reply_markup=get_main_menu_keyboard(), parse_mode='MarkdownV2')
    return ConversationHandler.END


# =============================================================================
# SECCIÓN 2: INFORMES DE AVANCES (JERÁRQUICOS Y DINÁMICOS)
# =============================================================================

async def select_avance_filter_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("📍 Por Ubicación", callback_data="filter_ubicacion")],
        [InlineKeyboardButton("⏪ Volver", callback_data="back_to_report_menu")]
    ]
    await query.edit_message_text(
        text="*Informes de Avances de Obra*\n\nElige un método de filtrado:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SELECTING_AVANCE_FILTER_TYPE

# --- INICIO DE LA MODIFICACIÓN ---

async def start_dynamic_ubicacion_filter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Inicia el filtro por ubicación obteniendo primero la jerarquía desde la BD.
    Esta función reemplaza la necesidad de una jerarquía fija.
    """
    query = update.callback_query
    await query.answer()

    hierarchy = db.get_distinct_ubicacion_tipos()
    if not hierarchy:
        await query.edit_message_text(
            "❌ Error: No hay tipos de ubicación definidos en la base de datos\\. No se puede filtrar\\.",
            reply_markup=get_main_menu_keyboard(),
            parse_mode='MarkdownV2'
        )
        # Vuelve al menú anterior si no hay nada que filtrar
        return await select_avance_filter_type(update, context)

    # Guarda la jerarquía real en el contexto para usarla en los siguientes pasos
    context.user_data['ubicacion_hierarchy'] = hierarchy
    context.user_data['report_filters'] = {}
    
    # Comienza el filtro con el primer nivel de la jerarquía obtenida
    first_level = hierarchy[0]
    return await start_ubicacion_filter(update, context, level=first_level)


async def process_ubicacion_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split('_')
    level, value = parts[2], parts[3]
    
    context.user_data.setdefault('report_filters', {})[level.lower()] = value

    hierarchy = context.user_data.get('ubicacion_hierarchy')
    try:
        current_index = hierarchy.index(level)
        if current_index + 1 < len(hierarchy):
            next_level = hierarchy[current_index + 1]
            return await start_ubicacion_filter(update, context, level=next_level)
        else:
            # Si es el último nivel, mostramos el menú de nuevo con los filtros finales
            return await start_ubicacion_filter(update, context, level="Finalizado")
    except (ValueError, IndexError):
         await query.edit_message_text("Error de jerarquía\\.", reply_markup=get_main_menu_keyboard(), parse_mode='MarkdownV2')
         return ConversationHandler.END

    try:
        current_index = hierarchy.index(level)
        # Si hay un siguiente nivel en la jerarquía, continúa
        if current_index + 1 < len(hierarchy):
            next_level = hierarchy[current_index + 1]
            return await start_ubicacion_filter(update, context, level=next_level)
        # Si es el último nivel, pasa a generar el informe
        else:
            return await generate_report_prompt(update, context)
    except ValueError:
         await query.edit_message_text("Error de jerarquía\\.", reply_markup=get_main_menu_keyboard(), parse_mode='MarkdownV2')
         return ConversationHandler.END

# --- FIN DE LA MODIFICACIÓN ---

async def start_ubicacion_filter(update: Update, context: ContextTypes.DEFAULT_TYPE, level: str) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['current_filter_level'] = level
    ubicaciones = db.get_ubicaciones_by_tipo(level)
    
    keyboard = [[InlineKeyboardButton(ubic['nombre'], callback_data=f"select_ubic_{level}_{ubic['nombre']}")] for ubic in ubicaciones]
    
    # MODIFICADO: Los botones de acción ahora preguntan por el siguiente paso
    keyboard.append([
        InlineKeyboardButton("🗓️ Añadir Filtro de Fecha", callback_data="ask_date_filter_yes"),
        InlineKeyboardButton("➡️ Ver Resultados (sin filtro fecha)", callback_data="ask_date_filter_no")
    ])
    keyboard.append([InlineKeyboardButton("⏪ Volver", callback_data="back_to_filter_type")])

    summary_text = _build_filter_summary_text(context)
    texto_mensaje = f"*Filtro por Ubicación*\n\n{summary_text}\n\nSelecciona un *{escape(level)}* para refinar más, o continúa al siguiente paso\\."
    
    try:
        await query.edit_message_text(text=texto_mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='MarkdownV2')
    except telegram.error.BadRequest as e:
        if "Message is not modified" not in str(e): raise
        
    return SELECTING_UBICACION # Cambiamos el estado de retorno

async def generate_report_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # (Sin cambios)
    query = update.callback_query
    await query.answer()
    
    filtros_actuales = context.user_data.get('report_filters', {})
    if not filtros_actuales:
        await query.edit_message_text("⚠️ No has seleccionado ningún filtro\\. Por favor, vuelve y elige al menos uno\\.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏪ Volver", callback_data="back_to_filter_type")]]), parse_mode='MarkdownV2')
        return SELECTING_AVANCE_FILTER_TYPE

    keyboard = [[InlineKeyboardButton("📄 Generar Informe CSV", callback_data="generate_csv")], [InlineKeyboardButton("⏪ Volver", callback_data="back_to_filter_type")]]
    await query.edit_message_text(
        text="Has finalizado la selección de filtros\\. ¿En qué formato deseas el informe?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='MarkdownV2'
    )
    #return GENERATING_REPORT #TODO
    return SELECTING_FORMAT

async def generate_csv_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("⏳ Procesando tu solicitud...")

    filters = context.user_data.get('report_filters', {})
    start_date = context.user_data.get('report_start_date')
    end_date = context.user_data.get('report_end_date')
    
    avances = db.get_avances_for_report(filters, start_date, end_date)

    if not avances:
        summary_text = _build_filter_summary_text(context)
        mensaje_error = f"✅ No se encontraron avances que coincidan con los filtros seleccionados\\.\n\n{summary_text}"
        await query.edit_message_text(mensaje_error, reply_markup=get_main_menu_keyboard(), parse_mode='MarkdownV2')
        return await back_to_main_menu(update, context)

    await query.edit_message_text(f"✅ Se encontraron {len(avances)} registros. Generando el archivo CSV...")

    avance_ids = [a['id'] for a in avances]
    incidencias_map = db.get_incidencias_for_avances(avance_ids)

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', quotechar='"', quoting=csv.QUOTE_ALL)
    
    headers = ["ID Avance", "Fecha Trabajo", "Ubicacion", "Trabajo", "Estado Avance", "Encargado", "ID Incidencia", "Fecha Incidencia", "Estado Incidencia", "Descripcion Incidencia"]
    writer.writerow(headers)
    
    for avance in avances:
        incidencias = incidencias_map.get(avance['id'])
        if incidencias:
            for incidencia in incidencias:
                writer.writerow([avance['id'], avance['fecha'].strftime('%Y-%m-%d'), avance['ubicacion'], avance['trabajo'], avance['estado'], avance['encargado_nombre'], incidencia['id'], incidencia['fecha'].strftime('%Y-%m-%d %H:%M'), incidencia['estado'], incidencia['descripcion']])
        else:
            writer.writerow([avance['id'], avance['fecha'].strftime('%Y-%m-%d'), avance['ubicacion'], avance['trabajo'], avance['estado'], avance['encargado_nombre'], "N/A", "N/A", "N/A", "N/A"])
            
    csv_content = output.getvalue()
    output.seek(0)
    csv_file = InputFile(csv_content.encode('utf-8'), filename=f"informe_avances_{datetime.now().strftime('%Y%m%d_%H%M')}.csv")

    try:
        await context.bot.send_document(chat_id=query.from_user.id, document=csv_file, caption="✅ Aquí tienes tu informe de avances en formato CSV.")
    except Exception as e:
        await query.message.reply_text("❌ Ocurrió un error al intentar enviar el archivo.")
    
    return await back_to_main_menu(update, context)

async def show_avances_list_paginated(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Muestra una lista paginada de los avances encontrados con los filtros.
    """
    query = update.callback_query
    await query.answer()
    
    page = context.user_data.get('avances_page', 0)
    avances = context.user_data.get('informe_avances_results', [])
    
    if not avances:
        await query.edit_message_text("✅ No se encontraron avances con esos filtros.", reply_markup=get_main_menu_keyboard())
        return SELECTING_FORMAT

    # Paginación
    start_index = page * ITEMS_PER_PAGE
    end_index = start_index + ITEMS_PER_PAGE
    avances_on_page = avances[start_index:end_index]
    total_pages = (len(avances) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

    keyboard = []
    for avance in avances_on_page:
        button_text = f"ID:{avance['id']} - {avance['trabajo']} ({avance['fecha'].strftime('%d/%m')})"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"view_informe_avance_{avance['id']}")])
        
    # Controles de paginación
    pagination_row = []
    if page > 0:
        pagination_row.append(InlineKeyboardButton("⬅️ Anterior", callback_data="avpag_prev"))
    if page < total_pages - 1:
        pagination_row.append(InlineKeyboardButton("Siguiente ➡️", callback_data="avpag_next"))
    if pagination_row:
        keyboard.append(pagination_row)
        
    keyboard.append([InlineKeyboardButton("⏪ Volver a Filtros", callback_data="back_to_filter_type")])
    
    message_text = f"📖 *Resultados del Informe* \\(Página {page + 1}/{total_pages}\\)\n\nSelecciona un avance para ver sus detalles:"
    
    await query.edit_message_text(text=message_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='MarkdownV2')
    return LISTING_AVANCES


async def prepare_avances_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Buscando registros...")

    filters = context.user_data.get('report_filters', {})
    start_date = context.user_data.get('report_start_date')
    end_date = context.user_data.get('report_end_date')

    avances = db.get_avances_for_report(filters, start_date, end_date)
    
    context.user_data['informe_avances_results'] = avances
    context.user_data['avances_page'] = 0

    return await show_avances_list_paginated(update, context)


async def change_informe_avances_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja los botones de paginación para la lista de informes."""
    query = update.callback_query
    await query.answer()
    direction = query.data.split('_')[1]
    page = context.user_data.get('avances_page', 0)
    context.user_data['avances_page'] = page + 1 if direction == 'next' else page - 1
    return await show_avances_list_paginated(update, context)

async def show_avance_detail_from_informe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Muestra el detalle de un avance seleccionado de la lista de informes."""
    query = update.callback_query
    await query.answer()
    avance_id = int(query.data.split('_')[3])
    
    details = db.get_avance_details(avance_id)
    if not details:
        await query.edit_message_text("❌ Error: No se encontraron los detalles.", reply_markup=get_main_menu_keyboard())
        return LISTING_AVANCES

    details_text = (
        f"*Detalle del Avance \\#{details['id']}*\n\n"
        f"👤 *Encargado:* {escape(details['encargado_name'])}\n"
        f"📍 *Ubicación:* {escape(details['ubicacion'])}\n"
        f"🛠️ *Trabajo:* {escape(details['trabajo'])}\n"
        f"🗓️ *Fecha:* {details['fecha_trabajo'].strftime('%d/%m/%Y')}"
    )
    
    # Enviar foto si existe
    if details.get('foto_path') and os.path.exists(details['foto_path']):
        try:
            with open(details['foto_path'], 'rb') as photo_file:
                await context.bot.send_photo(chat_id=query.from_user.id, photo=InputFile(photo_file))
        except Exception as e:
            await query.message.reply_text(f"No se pudo cargar la foto: {e}")

    keyboard = [[InlineKeyboardButton("⏪ Volver a la lista", callback_data="back_to_informe_list")]]
    await query.edit_message_text(text=details_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='MarkdownV2')
    return VIEWING_AVANCE_DETAIL

# =============================================================================
# SECCIÓN 3: INFORMES DE PERSONAL (MODIFICADO)
# =============================================================================

async def start_personal_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    now = datetime.now()
    await query.edit_message_text(
        "*Informe de Personal*\n\nPor favor, selecciona la *fecha de inicio* del informe:",
        # --- INICIO DE LA MODIFICACIÓN ---
        reply_markup=await create_calendar(now.year, now.month, allow_past_dates=True),
        # --- FIN DE LA MODIFICACIÓN ---
        parse_mode='Markdown'
    )
    return ASKING_PERSONAL_START_DATE

async def process_personal_start_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # La función process_calendar_selection ya se encarga de la navegación
    result = await process_calendar_selection(update, context)
    if isinstance(result, date):
        context.user_data['report_start_date'] = result
        now = datetime.now()
        await update.callback_query.edit_message_text(
            f"Fecha de inicio seleccionada: *{result.strftime('%d/%m/%Y')}*\n\nAhora, selecciona la *fecha de fin*:",
            # --- INICIO DE LA MODIFICACIÓN ---
            reply_markup=await create_calendar(now.year, now.month, allow_past_dates=True),
            # --- FIN DE LA MODIFICACIÓN ---
            parse_mode='Markdown'
        )
        return ASKING_PERSONAL_END_DATE
    return ASKING_PERSONAL_START_DATE

async def process_personal_end_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa la fecha de fin, recupera los datos y llama a la función que pregunta por el formato."""
    # La función process_calendar_selection ya se encarga de la navegación
    result = await process_calendar_selection(update, context)
    if isinstance(result, date):
        start_date = context.user_data['report_start_date']
        end_date = result
        
        if end_date < start_date:
            await update.callback_query.edit_message_text(
                "❌ La fecha de fin no puede ser anterior a la de inicio. Por favor, selecciona de nuevo la *fecha de fin*:",
                reply_markup=await create_calendar(end_date.year, end_date.month, allow_past_dates=True),
                parse_mode='Markdown'
            )
            return ASKING_PERSONAL_END_DATE
        
        await update.callback_query.edit_message_text("Buscando registros...")
        
        registros = db.get_personal_registros_for_report(start_date, end_date)
        
        if not registros:
            await update.callback_query.edit_message_text("No se encontraron registros de personal en el rango de fechas seleccionado.")
            return await back_to_main_menu(update, context)
        
        context.user_data['personal_report_results'] = registros
        
        # Llama a la nueva función para mostrar el menú de formato
        return await ask_personal_report_format(update, context)
        
    return ASKING_PERSONAL_END_DATE

# --- INICIO DE LA CORRECCIÓN ---
# Se crea una función específica para mostrar el menú de formato.
# El botón "Volver" ahora puede apuntar directamente a esta función.
async def ask_personal_report_format(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Muestra el menú para elegir el formato del informe de personal (Lista o CSV)."""
    query = update.callback_query
    await query.answer()
    
    registros = context.user_data.get('personal_report_results', [])
    start_date = context.user_data.get('report_start_date')
    
    if not registros or not start_date:
        await query.edit_message_text("Error: No se encontraron datos para el informe. Por favor, empieza de nuevo.")
        return await back_to_main_menu(update, context)

    end_date = registros[-1]['fecha']

    keyboard = [
        [InlineKeyboardButton("📋 Listar en el chat", callback_data="personal_show_list")],
        [InlineKeyboardButton("📄 Descargar .csv", callback_data="personal_generate_csv")],
        [InlineKeyboardButton("📄 Descargar .pdf", callback_data="personal_generate_pdf")], # BOTÓN AÑADIDO
        [InlineKeyboardButton("⬅️ Menú Principal", callback_data="back_to_main_menu")]
    ]
    await query.edit_message_text(
        f"✅ Se encontraron {len(registros)} registros entre el {start_date.strftime('%d/%m/%Y')} y el {end_date.strftime('%d/%m/%Y')}.\n\n¿Cómo deseas verlos?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SELECTING_PERSONAL_FORMAT
# --- FIN DE LA CORRECCIÓN ---


async def show_personal_list_paginated(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    page = context.user_data.get('personal_page', 0)
    registros = context.user_data.get('personal_report_results', [])
    total_pages = (len(registros) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

    start_index = page * ITEMS_PER_PAGE
    end_index = start_index + ITEMS_PER_PAGE
    registros_on_page = registros[start_index:end_index]

    texto = f"📋 *Informe de Personal* (Página {page + 1}/{total_pages})\n"
    texto += "---"
    for reg in registros_on_page:
        texto += (
            f"\n\n🗓️ *Fecha:* {reg['fecha'].strftime('%d/%m/%Y')}\n"
            f"👷 En Obra: {reg['en_obra']} | Faltas: {reg['faltas']} | ❤️‍🩹 Bajas: {reg['bajas']}\n"
            f"_Registrado por: {escape(reg['registrado_por'])}_"
        )

    pagination_row = []
    if page > 0:
        pagination_row.append(InlineKeyboardButton("⬅️ Anterior", callback_data="personal_pag_prev"))
    if page < total_pages - 1:
        pagination_row.append(InlineKeyboardButton("Siguiente ➡️", callback_data="personal_pag_next"))

    keyboard = []
    if pagination_row:
        keyboard.append(pagination_row)
    
    # Este es el botón "Volver" que ahora funcionará correctamente
    keyboard.append([InlineKeyboardButton("⏪ Volver a selección de formato", callback_data="back_to_personal_format_select")])

    await query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return LISTING_PERSONAL

async def change_personal_list_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    direction = query.data.split('_')[2]
    page = context.user_data.get('personal_page', 0)
    context.user_data['personal_page'] = page + 1 if direction == 'next' else page - 1
    return await show_personal_list_paginated(update, context)

async def generate_personal_csv_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Generando archivo .csv, por favor espera...")
    
    registros = context.user_data.get('personal_report_results', [])
    start_date = context.user_data['report_start_date']
    end_date = registros[-1]['fecha']
    
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', quotechar='"', quoting=csv.QUOTE_ALL)
    writer.writerow(["Fecha", "En Obra", "Faltas", "Bajas", "Registrado Por"])
    for reg in registros:
        writer.writerow([reg['fecha'].strftime('%Y-%m-%d'), reg['en_obra'], reg['faltas'], reg['bajas'], reg['registrado_por']])
    
    output.seek(0)
    csv_file = InputFile(output.getvalue().encode('utf-8'), filename=f"informe_personal_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv")
    await context.bot.send_document(chat_id=update.effective_chat.id, document=csv_file, caption="Aquí tienes tu informe de personal.")
    
    return await back_to_main_menu(update, context)

async def generate_pdf_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("⏳ Procesando tu solicitud de PDF...")

    filters = context.user_data.get('report_filters', {})
    avances = db.get_avances_for_report(filters)

    if not avances:
        texto_filtros = ", ".join([f"'{escape(str(v))}'" for v in filters.values()])
        mensaje_error = f"✅ No se encontraron avances que coincidan con los filtros seleccionados \\({texto_filtros}\\)\\."
        await query.edit_message_text(mensaje_error, reply_markup=get_main_menu_keyboard(), parse_mode='MarkdownV2')
        return await back_to_main_menu(update, context)

    await query.edit_message_text(f"✅ Se encontraron {len(avances)} registros. Generando el archivo PDF...")

    # Preparar datos para la tabla del PDF
    headers = ["Fecha", "Ubicación", "Trabajo", "Estado", "Encargado"]
    column_widths = [25, 80, 60, 30, 45]
    table_data = []
    for avance in avances:
        table_data.append([
            avance['fecha'].strftime('%d/%m/%Y'),
            avance['ubicacion'],
            avance['trabajo'],
            avance['estado'],
            avance['encargado_nombre']
        ])

    # Generar el PDF
    pdf = PDFReport()
    pdf_content = pdf.create_table_report(
        table_data,
        headers,
        column_widths,
        report_title="Informe de Avances de Obra"
    )
    
    pdf_file = InputFile(pdf_content, filename=f"informe_avances_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf")

    try:
        await context.bot.send_document(chat_id=query.from_user.id, document=pdf_file, caption="✅ Aquí tienes tu informe de avances en formato PDF.")
    except Exception as e:
        print(f"[ERROR] Fallo al enviar el PDF: {e}")
        await query.message.reply_text("❌ Ocurrió un error al intentar enviar el archivo PDF.")
    
    return await back_to_main_menu(update, context)

async def generate_personal_pdf_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Generando archivo .pdf, por favor espera...")
    
    registros = context.user_data.get('personal_report_results', [])
    start_date = context.user_data['report_start_date']
    end_date = registros[-1]['fecha']
    
    # Preparar datos para la tabla
    headers = ["Fecha", "En Obra", "Faltas", "Bajas", "Registrado Por"]
    column_widths = [40, 40, 40, 40, 80]
    table_data = []
    for reg in registros:
        table_data.append([
            reg['fecha'].strftime('%d/%m/%Y'),
            reg['en_obra'],
            reg['faltas'],
            reg['bajas'],
            reg['registrado_por']
        ])

    # Generar PDF
    pdf = PDFReport()
    pdf_content = pdf.create_table_report(
        table_data,
        headers,
        column_widths,
        report_title=f"Informe de Personal ({start_date.strftime('%d/%m/%y')} - {end_date.strftime('%d/%m/%y')})"
    )

    pdf_file = InputFile(pdf_content, filename=f"informe_personal_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.pdf")
    await context.bot.send_document(chat_id=update.effective_chat.id, document=pdf_file, caption="Aquí tienes tu informe de personal en formato PDF.")
    
    return await back_to_main_menu(update, context)

def _build_filter_summary_text(context: ContextTypes.DEFAULT_TYPE) -> str:
    """Crea un texto que resume los filtros activos."""
    filters = context.user_data.get('report_filters', {})
    start_date = context.user_data.get('report_start_date')
    end_date = context.user_data.get('report_end_date')
    
    summary_parts = []
    if filters:
        loc_filter = ", ".join([f"'{v}'" for v in filters.values()])
        summary_parts.append(f"📍 Ubicación: `{escape(loc_filter)}`")
    if start_date and end_date:
        date_filter = f"{start_date.strftime('%d/%m/%y')} al {end_date.strftime('%d/%m/%y')}"
        summary_parts.append(f"🗓️ Fechas: `{escape(date_filter)}`")

    if not summary_parts:
        return "*Filtros activos:* Ninguno"
        
    return "*Filtros activos:*\n" + "\n".join(summary_parts)

async def ask_date_filter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Pregunta por la fecha de inicio o salta directamente a la selección de formato."""
    query = update.callback_query
    await query.answer()

    if query.data == 'ask_date_filter_no':
        # El usuario no quiere filtro de fecha, vamos a la selección de formato
        return await ask_report_format(update, context)

    # El usuario quiere añadir filtro de fecha, pedimos la fecha de inicio
    now = datetime.now()
    summary_text = _build_filter_summary_text(context)
    await query.edit_message_text(
        f"{summary_text}\n\nPor favor, selecciona la *fecha de inicio* del informe:",
        reply_markup=await create_calendar(now.year, now.month, allow_past_dates=True),
        parse_mode='Markdown'
    )
    return ASKING_START_DATE

async def process_start_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa la fecha de inicio y pide la fecha de fin."""
    result = await process_calendar_selection(update, context)
    if isinstance(result, date):
        context.user_data['report_start_date'] = result
        now = datetime.now()
        summary_text = _build_filter_summary_text(context)
        await update.callback_query.edit_message_text(
            f"{summary_text}\n\nAhora, selecciona la *fecha de fin*:",
            reply_markup=await create_calendar(now.year, now.month, allow_past_dates=True),
            parse_mode='Markdown'
        )
        return ASKING_END_DATE
    return ASKING_START_DATE # Permanece en el estado si solo navega por el calendario

async def process_end_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa la fecha de fin y pasa a la selección de formato."""
    result = await process_calendar_selection(update, context)
    if isinstance(result, date):
        start_date = context.user_data['report_start_date']
        end_date = result
        
        if end_date < start_date:
            await update.callback_query.edit_message_text(
                "❌ La fecha de fin no puede ser anterior a la de inicio. Por favor, selecciona de nuevo la *fecha de fin*:",
                reply_markup=await create_calendar(end_date.year, end_date.month, allow_past_dates=True),
                parse_mode='Markdown'
            )
            return ASKING_END_DATE
        
        context.user_data['report_end_date'] = end_date
        # Una vez tenemos todas las fechas, vamos a la selección de formato
        return await ask_report_format(update, context)
        
    return ASKING_END_DATE # Permanece en el estado si solo navega

async def ask_report_format(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """NUEVA: Centraliza la pregunta del formato del informe (CSV, PDF, Lista)."""
    query = update.callback_query
    await query.answer()
    
    summary_text = _build_filter_summary_text(context)
    keyboard = [
        [InlineKeyboardButton("📋 Ver como Lista", callback_data="show_list")],
        [InlineKeyboardButton("📄 Generar CSV", callback_data="generate_csv")],
        [InlineKeyboardButton("📄 Generar PDF", callback_data="generate_pdf")],
        [InlineKeyboardButton("⏪ Volver a Filtros", callback_data="back_to_filter_type")]
    ]
    
    await query.edit_message_text(
        text=f"{summary_text}\n\nHas finalizado la selección de filtros\\. ¿Cómo deseas ver los resultados?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='MarkdownV2'
    )
    return SELECTING_FORMAT

# =============================================================================
# CONVERSATION HANDLER
# =============================================================================
def get_informes_conversation_handler():
    """Crea y devuelve el ConversationHandler para todo el flujo de informes."""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(start_informes, pattern='^consultar_informes$')],
        states={
            # Estado 0: Menú principal de informes
            SELECTING_REPORT: [
                CallbackQueryHandler(select_avance_filter_type, pattern='^report_avances$'),
                CallbackQueryHandler(select_incidencia_report_type, pattern='^report_incidencias$'),
                CallbackQueryHandler(start_personal_report, pattern='^report_personal$'),
            ],

            # Estado para el menú de informes de incidencias
            SELECTING_INCIDENCIA_TYPE: [
                CallbackQueryHandler(show_incidencias_list, pattern='^show_incidencias_')
            ],

            # Estados para el flujo de informes de avances
            SELECTING_AVANCE_FILTER_TYPE: [
                CallbackQueryHandler(start_dynamic_ubicacion_filter, pattern='^filter_ubicacion$'),
                CallbackQueryHandler(start_informes, pattern='^back_to_report_menu$'),
            ],
            # MODIFICADO: El estado de selección de ubicación ahora tiene más salidas
            SELECTING_UBICACION: [
                CallbackQueryHandler(process_ubicacion_selection, pattern='^select_ubic_'),
                CallbackQueryHandler(ask_date_filter, pattern='^ask_date_filter_'),
                CallbackQueryHandler(select_avance_filter_type, pattern='^back_to_filter_type$')
            ],
            ASKING_START_DATE: [
                CallbackQueryHandler(process_start_date, pattern='^cal_')
            ],
            ASKING_END_DATE: [
                CallbackQueryHandler(process_end_date, pattern='^cal_')
            ],
            SELECTING_FORMAT: [
                CallbackQueryHandler(prepare_avances_list, pattern='^show_list$'),
                CallbackQueryHandler(generate_csv_report, pattern='^generate_csv$'),
                CallbackQueryHandler(generate_pdf_report, pattern='^generate_pdf$'),
                CallbackQueryHandler(select_avance_filter_type, pattern='^back_to_filter_type$')
            ],
            LISTING_AVANCES: [
                CallbackQueryHandler(change_informe_avances_page, pattern='^avpag_'),
                CallbackQueryHandler(show_avance_detail_from_informe, pattern='^view_informe_avance_'),
                CallbackQueryHandler(select_avance_filter_type, pattern='^back_to_filter_type$')
            ],
            VIEWING_AVANCE_DETAIL: [
                CallbackQueryHandler(show_avances_list_paginated, pattern='^back_to_informe_list$'),
            ],
            
            # Estados para el flujo de informes de personal
            ASKING_PERSONAL_START_DATE: [
                CallbackQueryHandler(process_personal_start_date, pattern='^cal_')
            ],
            ASKING_PERSONAL_END_DATE: [
                CallbackQueryHandler(process_personal_end_date, pattern='^cal_')
            ],
            SELECTING_PERSONAL_FORMAT: [
                CallbackQueryHandler(show_personal_list_paginated, pattern='^personal_show_list$'),
                CallbackQueryHandler(generate_personal_csv_report, pattern='^personal_generate_csv$'),
                CallbackQueryHandler(generate_personal_pdf_report, pattern='^personal_generate_pdf$')
            ],
            LISTING_PERSONAL: [
                CallbackQueryHandler(change_personal_list_page, pattern='^personal_pag_'),
                CallbackQueryHandler(ask_personal_report_format, pattern='^back_to_personal_format_select$'),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_report_creation, pattern='^cancel_conversation$'),
            CallbackQueryHandler(back_to_main_menu, pattern='^back_to_main_menu$'),
            CallbackQueryHandler(start_informes, pattern='^back_to_report_menu$'),
        ],
        map_to_parent={
             ConversationHandler.END: ConversationHandler.END
        },
        allow_reentry=True
    )