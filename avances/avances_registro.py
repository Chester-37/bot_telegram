# avances/avances_registro.py
# Sistema de registro optimizado de avances (para Encargados)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    ContextTypes, ConversationHandler, CallbackQueryHandler,
    MessageHandler, filters
)
from datetime import datetime, date
import os
import db_adapter as db_manager
from bot_navigation import end_and_return_to_menu
from calendar_helper import create_calendar, process_calendar_selection
from .avances_keyboards import *
from .avances_utils import *
from reporter import send_report, format_user

# Estados de conversación para registro
(
    REGISTRO_MENU, SELECCIONANDO_UBICACION, SELECCIONANDO_TIPO_TRABAJO,
    ESCRIBIENDO_TRABAJO, ESCRIBIENDO_TIPO_CUSTOM, SELECCIONANDO_FECHA,
    PROCESANDO_FOTO, ESCRIBIENDO_OBSERVACIONES, ESCRIBIENDO_INCIDENCIA,
    CONFIRMANDO_AVANCE, MOSTRANDO_OPCIONES
) = range(11)

async def start_avances_registro(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menú principal de registro para encargados."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    user_role = db_manager.get_user_role(user.id)
    
    if not can_user_create_avances(user_role):
        await query.edit_message_text(
            "❌ *Acceso Denegado*\n\nNo tienes permisos para registrar avances\\.",
            reply_markup=get_nav_keyboard(),
            parse_mode='MarkdownV2'
        )
        return ConversationHandler.END
    
    text = (
        "📋 *Registro de Avances*\n\n"
        f"¡Hola {escape(user.first_name)}\\!\n\n"
        "Desde aquí puedes:\n"
        "• Registrar nuevos avances de trabajo\n"
        "• Ver tus avances anteriores\n"
        "• Consultar avances del equipo\n\n"
        "¿Qué deseas hacer?"
    )
    
    await query.edit_message_text(
        text,
        reply_markup=build_registro_keyboard(),
        parse_mode='MarkdownV2'
    )
    return REGISTRO_MENU

async def start_nuevo_avance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el registro de un nuevo avance."""
    query = update.callback_query
    await query.answer()
    
    # Limpiar datos previos
    context.user_data['current_avance'] = {
        'ubicacion': {},
        'nivel_actual': 'Edificio',
        'jerarquia_completada': []
    }
    
    # Obtener jerarquía de ubicaciones
    jerarquia = db_manager.get_jerarquia_ubicaciones()
    
    if not jerarquia.get('Edificio'):
        await query.edit_message_text(
            "❌ *Error de Configuración*\n\n"
            "No hay edificios configurados\\. Contacta a un técnico\\.",
            reply_markup=get_nav_keyboard(),
            parse_mode='MarkdownV2'
        )
        return ConversationHandler.END
    
    context.user_data['jerarquia_disponible'] = jerarquia
    
    text = (
        "🏢 *Nuevo Avance \\- Paso 1*\n\n"
        "Selecciona la ubicación donde realizaste el trabajo:\n\n"
        "*Paso 1/6:* Edificio"
    )
    
    keyboard = build_ubicacion_keyboard(
        jerarquia['Edificio'], 
        'Edificio', 
        'ubic_'
    )
    
    await query.edit_message_text(
        text,
        reply_markup=keyboard,
        parse_mode='MarkdownV2'
    )
    return SELECCIONANDO_UBICACION

async def process_ubicacion_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa la selección de ubicación jerárquica."""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith('ubic_'):
        # Procesar selección de ubicación
        parts = query.data.split('_')
        nivel = parts[1]
        ubicacion_id = int(parts[2])
        
        # Obtener el nombre de la ubicación
        jerarquia = context.user_data['jerarquia_disponible']
        ubicaciones_nivel = jerarquia.get(nivel, [])
        ubicacion_seleccionada = next((u for u in ubicaciones_nivel if u['id'] == ubicacion_id), None)
        
        if not ubicacion_seleccionada:
            await query.edit_message_text(
                "❌ Error al procesar selección\\.",
                reply_markup=get_nav_keyboard(),
                parse_mode='MarkdownV2'
            )
            return ConversationHandler.END
        
        # Guardar selección
        context.user_data['current_avance']['ubicacion'][nivel.lower()] = ubicacion_seleccionada['nombre']
        context.user_data['current_avance']['jerarquia_completada'].append(nivel)
        
        # Determinar siguiente nivel
        siguiente_nivel = get_jerarquia_nivel_siguiente(nivel)
        
        if siguiente_nivel and jerarquia.get(siguiente_nivel):
            # Continuar con siguiente nivel
            context.user_data['current_avance']['nivel_actual'] = siguiente_nivel
            
            ubicacion_actual = build_ubicacion_string(context.user_data['current_avance']['ubicacion'])
            paso_num = len(context.user_data['current_avance']['jerarquia_completada']) + 1
            
            text = (
                f"{get_nivel_emoji(siguiente_nivel)} *Nuevo Avance \\- Paso {paso_num}*\n\n"
                f"📍 *Ubicación actual:* {escape(ubicacion_actual)}\n\n"
                f"Selecciona {siguiente_nivel.lower()}:"
            )
            
            keyboard = build_ubicacion_keyboard(
                jerarquia[siguiente_nivel],
                siguiente_nivel,
                'ubic_'
            )
            
            await query.edit_message_text(
                text,
                reply_markup=keyboard,
                parse_mode='MarkdownV2'
            )
            return SELECCIONANDO_UBICACION
        else:
            # Pasar a selección de tipo de trabajo
            return await show_tipos_trabajo(update, context)
    
    elif query.data.startswith('registro_nivel_'):
        # Registrar en el nivel actual
        return await show_tipos_trabajo(update, context)
    
    elif query.data == 'avance_back':
        # Volver al nivel anterior
        jerarquia_completada = context.user_data['current_avance']['jerarquia_completada']
        
        if jerarquia_completada:
            # Remover último nivel
            ultimo_nivel = jerarquia_completada.pop()
            nivel_key = ultimo_nivel.lower()
            
            if nivel_key in context.user_data['current_avance']['ubicacion']:
                del context.user_data['current_avance']['ubicacion'][nivel_key]
            
            if jerarquia_completada:
                # Volver al nivel anterior
                nivel_anterior = jerarquia_completada[-1]
                context.user_data['current_avance']['nivel_actual'] = nivel_anterior
                return await process_ubicacion_back(update, context, nivel_anterior)
            else:
                # Volver al primer nivel
                return await start_nuevo_avance(update, context)
        else:
            # Volver al menú de registro
            return await start_avances_registro(update, context)
    
    return SELECCIONANDO_UBICACION

async def process_ubicacion_back(update: Update, context: ContextTypes.DEFAULT_TYPE, nivel: str) -> int:
    """Procesa el regreso a un nivel anterior en la jerarquía."""
    query = update.callback_query
    
    jerarquia = context.user_data['jerarquia_disponible']
    ubicacion_actual = build_ubicacion_string(context.user_data['current_avance']['ubicacion'])
    paso_num = len(context.user_data['current_avance']['jerarquia_completada']) + 1
    
    text = (
        f"{get_nivel_emoji(nivel)} *Nuevo Avance \\- Paso {paso_num}*\n\n"
        f"📍 *Ubicación actual:* {escape(ubicacion_actual)}\n\n"
        f"Selecciona {nivel.lower()}:"
    )
    
    keyboard = build_ubicacion_keyboard(
        jerarquia[nivel],
        nivel,
        'ubic_'
    )
    
    await query.edit_message_text(
        text,
        reply_markup=keyboard,
        parse_mode='MarkdownV2'
    )
    return SELECCIONANDO_UBICACION

async def show_tipos_trabajo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Muestra los tipos de trabajo disponibles."""
    query = update.callback_query if hasattr(update, 'callback_query') and update.callback_query else None
    
    tipos_trabajo = db_manager.get_tipos_trabajo_activos()
    ubicacion_actual = build_ubicacion_string(context.user_data['current_avance']['ubicacion'])
    
    text = (
        "🔧 *Nuevo Avance \\- Paso 3*\n\n"
        f"📍 *Ubicación:* {escape(ubicacion_actual)}\n\n"
        "Selecciona el tipo de trabajo realizado:"
    )
    
    keyboard = build_tipos_trabajo_keyboard(tipos_trabajo, 'tipo_')
    
    if query:
        await query.edit_message_text(
            text,
            reply_markup=keyboard,
            parse_mode='MarkdownV2'
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=keyboard,
            parse_mode='MarkdownV2'
        )
    
    return SELECCIONANDO_TIPO_TRABAJO

async def process_tipo_trabajo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa la selección del tipo de trabajo."""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith('tipo_'):
        if query.data == 'tipo_custom':
            # Solicitar tipo personalizado
            await query.edit_message_text(
                "✏️ *Tipo de Trabajo Personalizado*\n\n"
                "Escribe el tipo de trabajo que realizaste:\n\n"
                "_Ejemplo: Instalación de ventanas, Reparación de tubería, etc\\._",
                reply_markup=get_cancel_keyboard(),
                parse_mode='MarkdownV2'
            )
            return ESCRIBIENDO_TIPO_CUSTOM
        else:
            # Tipo predefinido seleccionado
            tipo_id = int(query.data.replace('tipo_', ''))
            tipos = db_manager.get_tipos_trabajo_activos()
            tipo_seleccionado = next((t for t in tipos if t['id'] == tipo_id), None)
            
            if tipo_seleccionado:
                context.user_data['current_avance']['tipo_trabajo_id'] = tipo_id
                context.user_data['current_avance']['tipo_trabajo'] = tipo_seleccionado['nombre']
                context.user_data['current_avance']['tipo_trabajo_emoji'] = tipo_seleccionado['emoji']
                
                return await ask_trabajo_description(update, context)
    
    elif query.data == 'avance_back':
        # Volver a selección de ubicación
        return await start_nuevo_avance(update, context)
    
    return SELECCIONANDO_TIPO_TRABAJO

async def process_tipo_custom(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa tipo de trabajo personalizado."""
    tipo_custom = clean_text_input(update.message.text)
    
    is_valid, message = validate_work_description(tipo_custom)
    if not is_valid:
        await update.message.reply_text(
            f"❌ {message}\n\nIntenta de nuevo:",
            reply_markup=get_cancel_keyboard(),
            parse_mode='MarkdownV2'
        )
        return ESCRIBIENDO_TIPO_CUSTOM
    
    context.user_data['current_avance']['tipo_trabajo'] = tipo_custom
    context.user_data['current_avance']['tipo_trabajo_emoji'] = '📝'
    
    return await ask_trabajo_description(update, context)

async def ask_trabajo_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Solicita la descripción detallada del trabajo."""
    tipo_info = ""
    if context.user_data['current_avance'].get('tipo_trabajo_emoji'):
        emoji = context.user_data['current_avance']['tipo_trabajo_emoji']
        tipo = context.user_data['current_avance']['tipo_trabajo']
        tipo_info = f"🔧 *Tipo:* {emoji} {escape(tipo)}\n"
    
    ubicacion = build_ubicacion_string(context.user_data['current_avance']['ubicacion'])
    
    text = (
        "📝 *Nuevo Avance \\- Paso 4*\n\n"
        f"📍 *Ubicación:* {escape(ubicacion)}\n"
        f"{tipo_info}\n"
        "Describe específicamente el trabajo realizado:\n\n"
        "_Ejemplo: Instalación de 3 luminarias LED en techo, "
        "Reparación de fuga en tubería principal, etc\\._"
    )
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            reply_markup=get_cancel_keyboard(),
            parse_mode='MarkdownV2'
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=get_cancel_keyboard(),
            parse_mode='MarkdownV2'
        )
    
    return ESCRIBIENDO_TRABAJO

async def process_trabajo_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa la descripción del trabajo."""
    trabajo = clean_text_input(update.message.text)
    
    is_valid, message = validate_work_description(trabajo)
    if not is_valid:
        await update.message.reply_text(
            f"❌ {message}\n\nIntenta de nuevo:",
            reply_markup=get_cancel_keyboard(),
            parse_mode='MarkdownV2'
        )
        return ESCRIBIENDO_TRABAJO
    
    context.user_data['current_avance']['trabajo'] = trabajo
    
    return await ask_fecha_trabajo(update, context)

async def ask_fecha_trabajo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Solicita la fecha del trabajo mediante calendario."""
    ubicacion = build_ubicacion_string(context.user_data['current_avance']['ubicacion'])
    tipo_info = ""
    if context.user_data['current_avance'].get('tipo_trabajo_emoji'):
        emoji = context.user_data['current_avance']['tipo_trabajo_emoji']
        tipo = context.user_data['current_avance']['tipo_trabajo']
        tipo_info = f"🔧 *Tipo:* {emoji} {escape(tipo)}\n"
    
    text = (
        "📅 *Nuevo Avance \\- Paso 5*\n\n"
        f"📍 *Ubicación:* {escape(ubicacion)}\n"
        f"{tipo_info}"
        f"📝 *Trabajo:* {escape(context.user_data['current_avance']['trabajo'])}\n\n"
        "Selecciona la fecha en que se realizó el trabajo:"
    )
    
    now = datetime.now()
    calendar_markup = await create_calendar(now.year, now.month, allow_past_dates=True)
    
    await update.message.reply_text(
        text,
        reply_markup=calendar_markup,
        parse_mode='MarkdownV2'
    )
    
    return SELECCIONANDO_FECHA

async def process_fecha_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa la selección de fecha del calendario."""
    result = await process_calendar_selection(update, context)
    
    if isinstance(result, date):
        context.user_data['current_avance']['fecha_trabajo'] = result
        return await show_opciones_adicionales(update, context)
    elif result is True:
        # Navegación del calendario, mantener estado
        return SELECCIONANDO_FECHA
    else:
        # Ignorar o error
        return SELECCIONANDO_FECHA

async def show_opciones_adicionales(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Muestra opciones adicionales (foto, incidencia, observaciones)."""
    avance_data = context.user_data['current_avance']
    
    summary = format_avance_summary(avance_data)
    
    text = (
        f"{summary}\n"
        "🎯 *Opciones Adicionales*\n\n"
        "¿Quieres añadir algo más a este avance?"
    )
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            reply_markup=build_options_keyboard(),
            parse_mode='MarkdownV2'
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=build_options_keyboard(),
            parse_mode='MarkdownV2'
        )
    
    return MOSTRANDO_OPCIONES

async def process_opciones_adicionales(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa las opciones adicionales seleccionadas."""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'avance_add_photo':
        await query.edit_message_text(
            "📸 *Añadir Foto*\n\n"
            "Envía la foto relacionada con este avance:\n\n"
            "_La foto se guardará y estará disponible en los informes\\._",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⏭️ Omitir foto", callback_data="avance_skip_photo")],
                [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_conversation")]
            ]),
            parse_mode='MarkdownV2'
        )
        return PROCESANDO_FOTO
    
    elif query.data == 'avance_add_observaciones':
        await query.edit_message_text(
            "📝 *Añadir Observaciones*\n\n"
            "Escribe observaciones adicionales sobre este trabajo:\n\n"
            "_Ejemplo: Se necesita material adicional, trabajo pendiente de revisión, etc\\._",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⏭️ Sin observaciones", callback_data="avance_skip_observaciones")],
                [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_conversation")]
            ]),
            parse_mode='MarkdownV2'
        )
        return ESCRIBIENDO_OBSERVACIONES
    
    elif query.data == 'avance_add_incidencia':
        await query.edit_message_text(
            "⚠️ *Reportar Incidencia*\n\n"
            "Describe la incidencia encontrada durante el trabajo:\n\n"
            "_Las incidencias serán notificadas a los técnicos para su resolución\\._",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⏭️ Sin incidencia", callback_data="avance_skip_incidencia")],
                [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_conversation")]
            ]),
            parse_mode='MarkdownV2'
        )
        return ESCRIBIENDO_INCIDENCIA
    
    elif query.data == 'avance_continue':
        return await confirm_avance(update, context)
    
    return MOSTRANDO_OPCIONES

async def process_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa la foto subida."""
    if update.message and update.message.photo:
        try:
            # Obtener la foto de mayor calidad
            photo = update.message.photo[-1]
            
            # Crear directorio si no existe
            photo_dir = "data/fotos_avances"
            os.makedirs(photo_dir, exist_ok=True)
            
            # Generar nombre único para la foto
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            user_id = update.effective_user.id
            photo_filename = f"avance_{user_id}_{timestamp}.jpg"
            photo_path = os.path.join(photo_dir, photo_filename)
            
            # Descargar foto
            file = await context.bot.get_file(photo.file_id)
            await file.download_to_drive(photo_path)
            
            context.user_data['current_avance']['foto_path'] = photo_path
            context.user_data['current_avance']['tiene_foto'] = True
            
            await update.message.reply_text(
                "✅ *Foto guardada exitosamente*",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Continuar", callback_data="avance_continue")]
                ]),
                parse_mode='MarkdownV2'
            )
            
        except Exception as e:
            await update.message.reply_text(
                f"❌ Error al guardar la foto: {str(e)}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⏭️ Continuar sin foto", callback_data="avance_continue")]
                ]),
                parse_mode='MarkdownV2'
            )
    else:
        await update.message.reply_text(
            "❌ Por favor envía una foto válida\\.",
            parse_mode='MarkdownV2'
        )
        return PROCESANDO_FOTO
    
    return await show_opciones_adicionales(update, context)

async def process_observaciones(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa las observaciones añadidas."""
    observaciones = clean_text_input(update.message.text)
    
    is_valid, message = validate_observations(observaciones)
    if not is_valid:
        await update.message.reply_text(
            f"❌ {message}\n\nIntenta de nuevo:",
            parse_mode='MarkdownV2'
        )
        return ESCRIBIENDO_OBSERVACIONES
    
    context.user_data['current_avance']['observaciones'] = observaciones
    
    await update.message.reply_text(
        "✅ *Observaciones guardadas*",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Continuar", callback_data="avance_continue")]
        ]),
        parse_mode='MarkdownV2'
    )
    
    return await show_opciones_adicionales(update, context)

async def process_incidencia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa la descripción de incidencia."""
    incidencia = clean_text_input(update.message.text)
    
    is_valid, message = validate_work_description(incidencia)
    if not is_valid:
        await update.message.reply_text(
            f"❌ {message}\n\nIntenta de nuevo:",
            parse_mode='MarkdownV2'
        )
        return ESCRIBIENDO_INCIDENCIA
    
    context.user_data['current_avance']['incidencia_desc'] = incidencia
    context.user_data['current_avance']['tiene_incidencia'] = True
    
    await update.message.reply_text(
        "⚠️ *Incidencia registrada*\n\n"
        "La incidencia será notificada a los técnicos\\.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Continuar", callback_data="avance_continue")]
        ]),
        parse_mode='MarkdownV2'
    )
    
    return await show_opciones_adicionales(update, context)

async def confirm_avance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Muestra confirmación final del avance."""
    avance_data = context.user_data['current_avance']
    summary = format_avance_summary(avance_data)
    
    text = f"{summary}\n¿Confirmas el registro de este avance?"
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            reply_markup=build_confirmation_keyboard(),
            parse_mode='MarkdownV2'
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=build_confirmation_keyboard(),
            parse_mode='MarkdownV2'
        )
    
    return CONFIRMANDO_AVANCE

async def save_avance_final(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda el avance final en la base de datos."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    avance_data = context.user_data['current_avance']
    
    try:
        # Construir ubicación completa
        ubicacion_str = build_ubicacion_string(avance_data['ubicacion'])
        
        # Determinar estado
        estado = 'Con Incidencia' if avance_data.get('tiene_incidencia') else 'Finalizado'
        
        # Crear avance en BD
        avance_id = db_manager.create_avance(
            encargado_id=user.id,
            ubicacion_completa=ubicacion_str,
            trabajo=avance_data['trabajo'],
            foto_path=avance_data.get('foto_path'),
            estado=estado,
            fecha_trabajo=avance_data['fecha_trabajo'],
            tipo_trabajo_id=avance_data.get('tipo_trabajo_id'),
            observaciones=avance_data.get('observaciones')
        )
        
        if not avance_id:
            raise Exception("Error al crear avance en base de datos")
        
        # Crear incidencia si existe
        incidencia_id = None
        if avance_data.get('tiene_incidencia'):
            incidencia_id = db_manager.create_incidencia(
                avance_id=avance_id,
                descripcion=avance_data['incidencia_desc'],
                reporta_id=user.id
            )
        
        # Enviar reporte
        await send_avance_report(update, context, avance_id, avance_data, incidencia_id)
        
        # Mensaje de éxito
        success_text = (
            "✅ *Avance Registrado Exitosamente*\n\n"
            f"📋 *ID:* `{avance_id}`\n"
            f"📍 *Ubicación:* {escape(ubicacion_str)}\n"
            f"📝 *Trabajo:* {escape(avance_data['trabajo'])}\n"
        )
        
        if incidencia_id:
            success_text += f"\n⚠️ *Incidencia reportada* \\(ID: `{incidencia_id}`\\)"
        
        await query.edit_message_text(
            success_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Registrar otro avance", callback_data="nuevo_avance")],
                [InlineKeyboardButton("📋 Ver mis avances", callback_data="mis_avances")],
                [InlineKeyboardButton("🏠 Menú Principal", callback_data="back_to_main_menu")]
            ]),
            parse_mode='MarkdownV2'
        )
        
        # Limpiar datos
        context.user_data.pop('current_avance', None)
        context.user_data.pop('jerarquia_disponible', None)
        
        return REGISTRO_MENU
        
    except Exception as e:
        await query.edit_message_text(
            f"❌ *Error al guardar avance*\n\n{escape(str(e))}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Intentar de nuevo", callback_data="avance_confirm")],
                [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_conversation")]
            ]),
            parse_mode='MarkdownV2'
        )
        return CONFIRMANDO_AVANCE

async def send_avance_report(update: Update, context: ContextTypes.DEFAULT_TYPE, avance_id: int, avance_data: dict, incidencia_id: int = None):
    """Envía reporte del avance registrado."""
    user = update.effective_user
    ubicacion_str = build_ubicacion_string(avance_data['ubicacion'])
    fecha_formateada = format_date(avance_data['fecha_trabajo'])
    
    if incidencia_id:
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
    else:
        report_text = (
            f"✅ *Reporte: Nuevo Avance Completado*\n\n"
            f"*ID Avance:* `{avance_id}`\n"
            f"*Encargado:* {format_user(user)}\n"
            f"*Ubicación:* {escape(ubicacion_str)}\n"
            f"*Trabajo:* {escape(avance_data['trabajo'])}\n"
            f"*Fecha Trabajo:* {escape(fecha_formateada)}"
        )
        
        if avance_data.get('observaciones'):
            report_text += f"\n\n*Observaciones:*\n_{escape(avance_data['observaciones'])}_"
    
    await send_report(context, report_text)

# Función para obtener el handler completo
def get_avances_registro_handler():
    """Devuelve el ConversationHandler para registro de avances."""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(start_avances_registro, pattern="^registro_avances$")],
        states={
            REGISTRO_MENU: [
                CallbackQueryHandler(start_nuevo_avance, pattern="^nuevo_avance$"),
                CallbackQueryHandler(lambda u, c: end_and_return_to_menu(u, c), pattern="^back_to_main_menu$")
            ],
            SELECCIONANDO_UBICACION: [
                CallbackQueryHandler(process_ubicacion_selection, pattern="^ubic_"),
                CallbackQueryHandler(process_ubicacion_selection, pattern="^registro_nivel_"),
                CallbackQueryHandler(process_ubicacion_selection, pattern="^avance_back$")
            ],
            SELECCIONANDO_TIPO_TRABAJO: [
                CallbackQueryHandler(process_tipo_trabajo, pattern="^tipo_"),
                CallbackQueryHandler(process_tipo_trabajo, pattern="^avance_back$")
            ],
            ESCRIBIENDO_TIPO_CUSTOM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_tipo_custom)
            ],
            ESCRIBIENDO_TRABAJO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_trabajo_description)
            ],
            SELECCIONANDO_FECHA: [
                CallbackQueryHandler(process_fecha_selection, pattern="^cal_")
            ],
            MOSTRANDO_OPCIONES: [
                CallbackQueryHandler(process_opciones_adicionales, pattern="^avance_add_"),
                CallbackQueryHandler(process_opciones_adicionales, pattern="^avance_continue$"),
                CallbackQueryHandler(process_opciones_adicionales, pattern="^avance_skip_")
            ],
            PROCESANDO_FOTO: [
                MessageHandler(filters.PHOTO, process_photo),
                CallbackQueryHandler(show_opciones_adicionales, pattern="^avance_skip_photo$")
            ],
            ESCRIBIENDO_OBSERVACIONES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_observaciones),
                CallbackQueryHandler(show_opciones_adicionales, pattern="^avance_skip_observaciones$")
            ],
            ESCRIBIENDO_INCIDENCIA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_incidencia),
                CallbackQueryHandler(show_opciones_adicionales, pattern="^avance_skip_incidencia$")
            ],
            CONFIRMANDO_AVANCE: [
                CallbackQueryHandler(save_avance_final, pattern="^avance_confirm$"),
                CallbackQueryHandler(show_opciones_adicionales, pattern="^avance_edit$")
            ]
        },
        fallbacks=[
            CallbackQueryHandler(lambda u, c: end_and_return_to_menu(u, c), pattern="^cancel_conversation$"),
            CallbackQueryHandler(lambda u, c: end_and_return_to_menu(u, c), pattern="^back_to_main_menu$")
        ],
        name="avances_registro",
        persistent=False
    )
