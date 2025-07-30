# avances/avances_visualization.py
# Sistema de visualización de avances (para Gerentes y consultas)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CallbackQueryHandler,
    MessageHandler, filters
)
from datetime import datetime, date, timedelta
import db_manager as db
from bot_navigation import end_and_return_to_menu
from .avances_keyboards import *
from .avances_utils import *

# Estados de conversación para visualización
(
    VISUALIZATION_MENU, VIEWING_AVANCES, FILTERING_AVANCES,
    SELECTING_DATE_RANGE, VIEWING_REPORTS
) = range(5)

async def start_avances_visualization(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menú principal de visualización para gerentes."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    user_role = db.get_user_role(user.id)
    
    if not can_user_view_all_avances(user_role):
        await query.edit_message_text(
            "❌ *Acceso Denegado*\n\nNo tienes permisos para ver avances\\.",
            reply_markup=get_nav_keyboard(),
            parse_mode='MarkdownV2'
        )
        return ConversationHandler.END
    
    text = (
        "📊 *Visualización de Avances*\n\n"
        f"¡Hola {escape(user.first_name)}\\!\n\n"
        "Consulta avances y genera informes ejecutivos\\.\n\n"
        "¿Qué deseas ver?"
    )
    
    await query.edit_message_text(
        text,
        reply_markup=build_visualization_keyboard(),
        parse_mode='MarkdownV2'
    )
    return VISUALIZATION_MENU

async def show_avances_recent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Muestra avances recientes."""
    query = update.callback_query
    await query.answer()
    
    # Obtener avances de los últimos 7 días
    end_date = date.today()
    start_date = end_date - timedelta(days=7)
    
    avances = db.get_avances_with_filters_extended(
        start_date=start_date,
        end_date=end_date
    )
    
    if not avances:
        await query.edit_message_text(
            "📋 *Avances Recientes \\(7 días\\)*\n\n"
            "No se encontraron avances en los últimos 7 días\\.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🗓️ Cambiar rango de fechas", callback_data="change_date_range")],
                [InlineKeyboardButton("⬅️ Atrás", callback_data="back_to_visualization")]
            ]),
            parse_mode='MarkdownV2'
        )
        return VIEWING_AVANCES
    
    # Estadísticas rápidas
    total_avances = len(avances)
    con_incidencia = len([a for a in avances if a['estado'] == 'Con Incidencia'])
    finalizados = len([a for a in avances if a['estado'] == 'Finalizado'])
    
    text = (
        f"📋 *Avances Recientes \\(últimos 7 días\\)*\n\n"
        f"📊 *Estadísticas:*\n"
        f"• Total: {total_avances} avances\n"
        f"• ✅ Finalizados: {finalizados}\n"
        f"• ⚠️ Con incidencias: {con_incidencia}\n\n"
        f"*Últimos avances:*\n"
    )
    
    # Mostrar últimos 5 avances
    for i, avance in enumerate(avances[:5], 1):
        emoji_estado = "✅" if avance['estado'] == 'Finalizado' else "⚠️"
        emoji_tipo = avance.get('tipo_trabajo_emoji', '🔧')
        
        text += (
            f"{i}\\. {emoji_estado} {emoji_tipo} {escape(avance['trabajo'])}\n"
            f"   📍 {escape(avance['ubicacion'])}\n"
            f"   👤 {escape(avance['encargado_nombre'])} \\- {format_date(avance['fecha'])}\n\n"
        )
    
    if len(avances) > 5:
        text += f"_\\.\\.\\. y {len(avances) - 5} avances más_"
    
    keyboard = [
        [
            InlineKeyboardButton("📋 Ver todos", callback_data="view_all_recent"),
            InlineKeyboardButton("📈 Generar informe", callback_data="generate_report_recent")
        ],
        [
            InlineKeyboardButton("🗓️ Cambiar fechas", callback_data="change_date_range"),
            InlineKeyboardButton("🏗️ Filtrar por ubicación", callback_data="filter_by_location")
        ],
        [
            InlineKeyboardButton("⬅️ Atrás", callback_data="back_to_visualization")
        ]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='MarkdownV2'
    )
    return VIEWING_AVANCES

async def show_avances_by_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Muestra avances filtrados por ubicación."""
    query = update.callback_query
    await query.answer()
    
    # Obtener jerarquía de ubicaciones
    jerarquia = db.get_jerarquia_ubicaciones()
    
    text = (
        "🏗️ *Avances por Ubicación*\n\n"
        "Selecciona el nivel de ubicación para filtrar:"
    )
    
    keyboard = []
    
    # Agregar opciones por nivel
    if jerarquia.get('Edificio'):
        keyboard.append([InlineKeyboardButton("🏢 Por Edificio", callback_data="filter_edificio")])
    
    if jerarquia.get('Zona'):
        keyboard.append([InlineKeyboardButton("📍 Por Zona", callback_data="filter_zona")])
    
    if jerarquia.get('Planta'):
        keyboard.append([InlineKeyboardButton("🏗️ Por Planta", callback_data="filter_planta")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Atrás", callback_data="view_avances_gerente")])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='MarkdownV2'
    )
    return FILTERING_AVANCES

async def show_filter_edificio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Muestra filtro por edificio."""
    query = update.callback_query
    await query.answer()
    
    edificios = db.get_ubicaciones_by_tipo('Edificio')
    
    if not edificios:
        await query.edit_message_text(
            "❌ No hay edificios configurados\\.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Atrás", callback_data="avances_by_location")]
            ]),
            parse_mode='MarkdownV2'
        )
        return FILTERING_AVANCES
    
    keyboard = []
    for edificio in edificios:
        keyboard.append([InlineKeyboardButton(
            f"🏢 {edificio['nombre']}", 
            callback_data=f"filter_apply_edificio_{edificio['id']}"
        )])
    
    keyboard.append([InlineKeyboardButton("⬅️ Atrás", callback_data="avances_by_location")])
    
    await query.edit_message_text(
        "🏢 *Seleccionar Edificio*\n\n"
        "Elige el edificio para ver sus avances:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='MarkdownV2'
    )
    return FILTERING_AVANCES

async def apply_filter_edificio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Aplica filtro por edificio y muestra resultados."""
    query = update.callback_query
    await query.answer()
    
    edificio_id = int(query.data.split('_')[3])
    
    # Obtener nombre del edificio
    edificios = db.get_ubicaciones_by_tipo('Edificio')
    edificio = next((e for e in edificios if e['id'] == edificio_id), None)
    
    if not edificio:
        await query.edit_message_text(
            "❌ Edificio no encontrado\\.",
            reply_markup=get_nav_keyboard(),
            parse_mode='MarkdownV2'
        )
        return ConversationHandler.END
    
    # Filtrar avances por edificio
    filtros = {'edificio': edificio['nombre']}
    avances = db.get_avances_with_filters_extended(filters=filtros)
    
    if not avances:
        await query.edit_message_text(
            f"📋 *Avances en {escape(edificio['nombre'])}*\n\n"
            "No se encontraron avances en este edificio\\.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Cambiar filtro", callback_data="filter_edificio")],
                [InlineKeyboardButton("🏠 Menú Principal", callback_data="back_to_main_menu")]
            ]),
            parse_mode='MarkdownV2'
        )
        return FILTERING_AVANCES
    
    # Estadísticas
    total = len(avances)
    finalizados = len([a for a in avances if a['estado'] == 'Finalizado'])
    con_incidencia = len([a for a in avances if a['estado'] == 'Con Incidencia'])
    
    # Agrupar por tipo de trabajo
    tipos_trabajo = {}
    for avance in avances:
        tipo = avance.get('tipo_trabajo', 'Sin tipo')
        if tipo not in tipos_trabajo:
            tipos_trabajo[tipo] = 0
        tipos_trabajo[tipo] += 1
    
    text = (
        f"📋 *Avances en {escape(edificio['nombre'])}*\n\n"
        f"📊 *Estadísticas:*\n"
        f"• Total: {total} avances\n"
        f"• ✅ Finalizados: {finalizados}\n"
        f"• ⚠️ Con incidencias: {con_incidencia}\n\n"
    )
    
    if tipos_trabajo:
        text += "*Tipos de trabajo:*\n"
        for tipo, count in list(tipos_trabajo.items())[:5]:
            text += f"• {escape(tipo)}: {count}\n"
    
    # Últimos avances
    text += f"\n*Últimos avances:*\n"
    for i, avance in enumerate(avances[:3], 1):
        emoji_estado = "✅" if avance['estado'] == 'Finalizado' else "⚠️"
        text += (
            f"{i}\\. {emoji_estado} {escape(avance['trabajo'])}\n"
            f"   👤 {escape(avance['encargado_nombre'])} \\- {format_date(avance['fecha'])}\n"
        )
    
    keyboard = [
        [
            InlineKeyboardButton("📋 Ver todos", callback_data=f"view_all_edificio_{edificio_id}"),
            InlineKeyboardButton("📈 Generar informe", callback_data=f"report_edificio_{edificio_id}")
        ],
        [
            InlineKeyboardButton("⬅️ Cambiar filtro", callback_data="filter_edificio"),
            InlineKeyboardButton("🏠 Menú Principal", callback_data="back_to_main_menu")
        ]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='MarkdownV2'
    )
    return VIEWING_AVANCES

async def show_avances_by_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Muestra opciones para filtrar por fecha."""
    query = update.callback_query
    await query.answer()
    
    text = (
        "📅 *Avances por Fecha*\n\n"
        "Selecciona el rango de fechas:"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("📅 Hoy", callback_data="date_today"),
            InlineKeyboardButton("📅 Ayer", callback_data="date_yesterday")
        ],
        [
            InlineKeyboardButton("📅 Esta semana", callback_data="date_this_week"),
            InlineKeyboardButton("📅 Semana pasada", callback_data="date_last_week")
        ],
        [
            InlineKeyboardButton("📅 Este mes", callback_data="date_this_month"),
            InlineKeyboardButton("📅 Mes pasado", callback_data="date_last_month")
        ],
        [
            InlineKeyboardButton("📅 Rango personalizado", callback_data="date_custom")
        ],
        [
            InlineKeyboardButton("⬅️ Atrás", callback_data="back_to_visualization")
        ]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='MarkdownV2'
    )
    return SELECTING_DATE_RANGE

async def apply_date_filter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Aplica filtro de fecha seleccionado."""
    query = update.callback_query
    await query.answer()
    
    today = date.today()
    
    if query.data == "date_today":
        start_date = end_date = today
        periodo = "hoy"
    elif query.data == "date_yesterday":
        start_date = end_date = today - timedelta(days=1)
        periodo = "ayer"
    elif query.data == "date_this_week":
        start_date = today - timedelta(days=today.weekday())
        end_date = today
        periodo = "esta semana"
    elif query.data == "date_last_week":
        start_date = today - timedelta(days=today.weekday() + 7)
        end_date = today - timedelta(days=today.weekday() + 1)
        periodo = "la semana pasada"
    elif query.data == "date_this_month":
        start_date = today.replace(day=1)
        end_date = today
        periodo = "este mes"
    elif query.data == "date_last_month":
        first_day_this_month = today.replace(day=1)
        end_date = first_day_this_month - timedelta(days=1)
        start_date = end_date.replace(day=1)
        periodo = "el mes pasado"
    else:
        return SELECTING_DATE_RANGE
    
    # Obtener avances del periodo
    avances = db.get_avances_with_filters_extended(
        start_date=start_date,
        end_date=end_date
    )
    
    context.user_data['filtered_avances'] = avances
    context.user_data['filter_periodo'] = periodo
    
    return await show_filtered_avances_summary(update, context, avances, periodo)

async def show_filtered_avances_summary(update: Update, context: ContextTypes.DEFAULT_TYPE, avances: list, periodo: str) -> int:
    """Muestra resumen de avances filtrados."""
    query = update.callback_query
    
    if not avances:
        await query.edit_message_text(
            f"📋 *Avances de {periodo}*\n\n"
            f"No se encontraron avances en {periodo}\\.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🗓️ Cambiar periodo", callback_data="avances_by_date")],
                [InlineKeyboardButton("⬅️ Atrás", callback_data="back_to_visualization")]
            ]),
            parse_mode='MarkdownV2'
        )
        return VIEWING_AVANCES
    
    # Estadísticas
    total = len(avances)
    finalizados = len([a for a in avances if a['estado'] == 'Finalizado'])
    con_incidencia = len([a for a in avances if a['estado'] == 'Con Incidencia'])
    
    # Top encargados
    encargados = {}
    for avance in avances:
        nombre = avance['encargado_nombre']
        if nombre not in encargados:
            encargados[nombre] = 0
        encargados[nombre] += 1
    
    top_encargados = sorted(encargados.items(), key=lambda x: x[1], reverse=True)[:3]
    
    text = (
        f"📋 *Avances de {periodo}*\n\n"
        f"📊 *Estadísticas:*\n"
        f"• Total: {total} avances\n"
        f"• ✅ Finalizados: {finalizados}\n"
        f"• ⚠️ Con incidencias: {con_incidencia}\n\n"
    )
    
    if top_encargados:
        text += "*Top encargados:*\n"
        for i, (nombre, count) in enumerate(top_encargados, 1):
            text += f"{i}\\. {escape(nombre)}: {count} avances\n"
        text += "\n"
    
    # Mostrar algunos avances
    text += "*Últimos avances:*\n"
    for i, avance in enumerate(avances[:3], 1):
        emoji_estado = "✅" if avance['estado'] == 'Finalizado' else "⚠️"
        emoji_tipo = avance.get('tipo_trabajo_emoji', '🔧')
        
        text += (
            f"{i}\\. {emoji_estado} {emoji_tipo} {escape(avance['trabajo'])}\n"
            f"   📍 {escape(avance['ubicacion'])}\n"
            f"   👤 {escape(avance['encargado_nombre'])}\n\n"
        )
    
    if len(avances) > 3:
        text += f"_\\.\\.\\. y {len(avances) - 3} avances más_"
    
    keyboard = [
        [
            InlineKeyboardButton("📋 Ver detalle completo", callback_data="view_full_filtered"),
            InlineKeyboardButton("📈 Generar informe PDF", callback_data="generate_pdf_filtered")
        ],
        [
            InlineKeyboardButton("🗓️ Cambiar periodo", callback_data="avances_by_date"),
            InlineKeyboardButton("⬅️ Atrás", callback_data="back_to_visualization")
        ]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='MarkdownV2'
    )
    return VIEWING_AVANCES

# Función para obtener el handler completo
def get_avances_visualization_handler():
    """Devuelve el ConversationHandler para visualización de avances."""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(start_avances_visualization, pattern="^visualization_avances$")],
        states={
            VISUALIZATION_MENU: [
                CallbackQueryHandler(show_avances_recent, pattern="^view_avances_gerente$"),
                CallbackQueryHandler(show_avances_by_location, pattern="^avances_by_location$"),
                CallbackQueryHandler(show_avances_by_date, pattern="^avances_by_date$"),
                CallbackQueryHandler(lambda u, c: end_and_return_to_menu(u, c), pattern="^back_to_main_menu$")
            ],
            VIEWING_AVANCES: [
                CallbackQueryHandler(show_avances_by_location, pattern="^filter_by_location$"),
                CallbackQueryHandler(show_avances_by_date, pattern="^change_date_range$"),
                CallbackQueryHandler(start_avances_visualization, pattern="^back_to_visualization$")
            ],
            FILTERING_AVANCES: [
                CallbackQueryHandler(show_filter_edificio, pattern="^filter_edificio$"),
                CallbackQueryHandler(apply_filter_edificio, pattern="^filter_apply_edificio_"),
                CallbackQueryHandler(show_avances_by_location, pattern="^avances_by_location$")
            ],
            SELECTING_DATE_RANGE: [
                CallbackQueryHandler(apply_date_filter, pattern="^date_"),
                CallbackQueryHandler(start_avances_visualization, pattern="^back_to_visualization$")
            ]
        },
        fallbacks=[
            CallbackQueryHandler(lambda u, c: end_and_return_to_menu(u, c), pattern="^cancel_conversation$"),
            CallbackQueryHandler(lambda u, c: end_and_return_to_menu(u, c), pattern="^back_to_main_menu$")
        ],
        name="avances_visualization",
        persistent=False
    )
