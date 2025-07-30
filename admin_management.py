# admin/admin_management.py
# Funciones administrativas exclusivas para el rol Admin

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CallbackQueryHandler,
    MessageHandler, filters
)
import db_adapter as db
from bot_navigation import end_and_return_to_menu

# Estados de conversación
ADMIN_MENU, CONFIRM_RESET, VIEW_STATS = range(3)

async def admin_management_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menú principal de administración (solo para Admin)"""
    user = update.effective_user
    user_role = db.get_user_role(user.id)
    
    if user_role != 'Admin':
        await update.callback_query.answer("❌ Solo administradores pueden acceder")
        return ConversationHandler.END
    
    keyboard = [
        [InlineKeyboardButton("📊 Ver estadísticas de BD", callback_data="admin_stats")],
        [InlineKeyboardButton("💾 Crear backup completo", callback_data="admin_backup")],
        [InlineKeyboardButton("🗑️ Limpiar base de datos", callback_data="admin_reset_confirm")],
        [InlineKeyboardButton("🔙 Volver al menú", callback_data="end_conversation")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message_text = f"""
🔧 **ADMINISTRACIÓN DE BASE DE DATOS**

*Funciones disponibles para administradores:*

📊 **Ver estadísticas** \\- Información general de la BD
💾 **Crear backup** \\- Respaldo completo en JSON
🗑️ **Limpiar datos** \\- Vaciar BD \\(preserva admin\\)

⚠️ *Las operaciones de limpieza son irreversibles*
✅ *Tu usuario Admin siempre se preserva*
"""
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode='MarkdownV2'
        )
    else:
        await update.message.reply_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode='MarkdownV2'
        )
    
    return ADMIN_MENU

async def admin_view_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostrar estadísticas de la base de datos"""
    await update.callback_query.answer("📊 Obteniendo estadísticas...")
    
    stats = db.get_database_statistics()
    
    if not stats['success']:
        error_text = f"❌ Error obteniendo estadísticas: {stats['error']}"
        await update.callback_query.edit_message_text(error_text)
        return ADMIN_MENU
    
    # Construir mensaje de estadísticas
    db_type = stats['database_type']
    tables = stats['tables']
    
    stats_text = f"""
📊 **ESTADÍSTICAS DE BASE DE DATOS**

🗄️ **Tipo:** {db_type}

📋 **Registros por tabla:**
👥 Usuarios: {tables.get('usuarios', 0)}
🔧 Tipos de trabajo: {tables.get('tipos_trabajo', 0)}
📍 Ubicaciones: {tables.get('ubicaciones_config', 0)}
📊 Avances: {tables.get('avances', 0)}
📦 Items almacén: {tables.get('almacen_items', 0)}

📈 **Estadísticas de avances:**
"""
    
    avances_stats = tables.get('avances_stats', {})
    if avances_stats and avances_stats.get('total', 0) > 0:
        stats_text += f"📊 Total avances: {avances_stats['total']}\\n"
        
        # Por tipo de trabajo
        if avances_stats.get('por_tipo'):
            stats_text += "\\n🔧 **Por tipo de trabajo:**\\n"
            for tipo in avances_stats['por_tipo'][:5]:  # Top 5
                if db.USE_SQLITE:
                    emoji = tipo.get('emoji', '📝')
                    nombre = tipo.get('nombre', 'Sin tipo')
                    cantidad = tipo.get('cantidad', 0)
                else:
                    emoji = tipo[1] or '📝'
                    nombre = tipo[0] or 'Sin tipo'
                    cantidad = tipo[2]
                stats_text += f"   {emoji} {nombre}: {cantidad}\\n"
        
        # Por encargado
        if avances_stats.get('por_encargado'):
            stats_text += "\\n👥 **Por encargado:**\\n"
            for enc in avances_stats['por_encargado'][:5]:  # Top 5
                if db.USE_SQLITE:
                    nombre = enc.get('first_name', 'Sin nombre')
                    cantidad = enc.get('cantidad', 0)
                else:
                    nombre = enc[0] or 'Sin nombre'
                    cantidad = enc[1]
                stats_text += f"   👤 {nombre}: {cantidad}\\n"
    else:
        stats_text += "📊 No hay avances registrados\\n"
    
    keyboard = [
        [InlineKeyboardButton("🔄 Actualizar", callback_data="admin_stats")],
        [InlineKeyboardButton("🔙 Volver", callback_data="admin_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        stats_text,
        reply_markup=reply_markup,
        parse_mode='MarkdownV2'
    )
    
    return ADMIN_MENU

async def admin_create_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Crear backup completo de la base de datos"""
    await update.callback_query.answer("💾 Creando backup...")
    
    backup_result = db.backup_database_to_json()
    
    if backup_result['success']:
        backup_text = f"""
✅ **BACKUP CREADO EXITOSAMENTE**

📁 **Archivo:** `{backup_result['backup_path'].split('/')[-1]}`
📊 **Registros respaldados:** {backup_result['total_records']}
📋 **Tablas incluidas:** {backup_result['tables_backed_up']}

💾 El backup se guardó en la carpeta `/data/backups/`

⚠️ *Guarda este archivo en un lugar seguro*
"""
    else:
        backup_text = f"""
❌ **ERROR CREANDO BACKUP**

🚨 **Error:** {backup_result['error']}

💡 *Verifica permisos de escritura y espacio en disco*
"""
    
    keyboard = [
        [InlineKeyboardButton("🔄 Crear otro backup", callback_data="admin_backup")],
        [InlineKeyboardButton("🔙 Volver", callback_data="admin_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        backup_text,
        reply_markup=reply_markup,
        parse_mode='MarkdownV2'
    )
    
    return ADMIN_MENU

async def admin_confirm_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirmar limpieza de base de datos"""
    
    confirm_text = f"""
⚠️ **CONFIRMACIÓN DE LIMPIEZA**

🗑️ **Esta operación eliminará TODOS los datos:**
❌ Todos los avances registrados
❌ Todos los usuarios \\(excepto tu Admin\\)
❌ Configuración personalizada
❌ Registros de almacén

✅ **Se preservará:**
✅ Tu usuario Admin \\(Nico\\)
✅ Tipos de trabajo por defecto
✅ Ubicaciones por defecto

⚠️ **Esta acción NO se puede deshacer**

¿Estás seguro de continuar?
"""
    
    keyboard = [
        [InlineKeyboardButton("🗑️ SÍ, LIMPIAR TODO", callback_data="admin_reset_execute")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="admin_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        confirm_text,
        reply_markup=reply_markup,
        parse_mode='MarkdownV2'
    )
    
    return CONFIRM_RESET

async def admin_execute_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ejecutar limpieza de base de datos"""
    user = update.effective_user
    
    await update.callback_query.answer("🗑️ Limpiando base de datos...")
    
    # Crear backup automático antes de limpiar
    backup_result = db.backup_database_to_json()
    
    # Ejecutar limpieza
    reset_result = db.reset_database_safely(preserve_admin_user_id=user.id)
    
    if reset_result['success']:
        preserved_admin = reset_result['preserved_admin']
        admin_name = preserved_admin['first_name'] if db.USE_SQLITE else preserved_admin[2]
        
        result_text = f"""
✅ **BASE DE DATOS LIMPIADA EXITOSAMENTE**

🗑️ **Eliminados:** {reset_result['total_deleted']} registros
👤 **Admin preservado:** {admin_name}

📋 **Detalles por tabla:**
"""
        
        for table, info in reset_result['deleted_counts'].items():
            if info['deleted'] > 0:
                result_text += f"   🗑️ {table}: {info['deleted']} eliminados\\n"
        
        result_text += f"""
🔄 **Datos reinsertados:**
✅ 8 tipos de trabajo por defecto
✅ 14 ubicaciones por defecto

"""
        
        if backup_result['success']:
            backup_file = backup_result['backup_path'].split('/')[-1]
            result_text += f"💾 **Backup automático:** `{backup_file}`\\n"
        
        result_text += "\\n🎉 **La base de datos está lista para usar**"
        
    else:
        result_text = f"""
❌ **ERROR EN LA LIMPIEZA**

🚨 **Error:** {reset_result['error']}

💾 Los datos permanecen intactos
💡 Verifica conexión a la base de datos
"""
    
    keyboard = [
        [InlineKeyboardButton("📊 Ver estadísticas", callback_data="admin_stats")],
        [InlineKeyboardButton("🔙 Volver al menú", callback_data="admin_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        result_text,
        reply_markup=reply_markup,
        parse_mode='MarkdownV2'
    )
    
    return ADMIN_MENU

# Manejador de callbacks
async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja los callbacks del sistema de administración"""
    query = update.callback_query
    data = query.data
    
    if data == "admin_menu":
        return await admin_management_menu(update, context)
    elif data == "admin_stats":
        return await admin_view_statistics(update, context)
    elif data == "admin_backup":
        return await admin_create_backup(update, context)
    elif data == "admin_reset_confirm":
        return await admin_confirm_reset(update, context)
    elif data == "admin_reset_execute":
        return await admin_execute_reset(update, context)
    elif data == "end_conversation":
        return await end_and_return_to_menu(update, context)
    
    return ADMIN_MENU

# ConversationHandler para administración
admin_management_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(admin_management_menu, pattern="^admin_management$")],
    states={
        ADMIN_MENU: [CallbackQueryHandler(admin_callback_handler)],
        CONFIRM_RESET: [CallbackQueryHandler(admin_callback_handler)],
        VIEW_STATS: [CallbackQueryHandler(admin_callback_handler)]
    },
    fallbacks=[CallbackQueryHandler(end_and_return_to_menu, pattern="^end_conversation$")]
)
