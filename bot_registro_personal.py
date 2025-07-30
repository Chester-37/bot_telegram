# bot_registro_personal.py

from datetime import date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
import db_manager as db
from reporter import GROUP_CHAT_ID, send_report, escape, format_user

# Estados de la conversación
ASKING_EN_OBRA, ASKING_FALTAS, ASKING_BAJAS, CONFIRMING = range(4)

# --- Funciones de Ayuda ---
def get_cancel_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_registro")]])

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la operación de registro."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Registro de personal cancelado.")
    context.user_data.clear()
    return ConversationHandler.END

# --- Flujo de la Conversación ---

async def start_registro_personal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el proceso de registro de personal."""
    query = update.callback_query
    await query.answer()
    
    # Comprobar si ya se ha hecho el registro hoy
    if db.check_personal_registro_today():
        keyboard = [[InlineKeyboardButton("⬅️ Menú Principal", callback_data="back_to_main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "✅ El registro de personal para hoy ya ha sido completado.", 
            reply_markup=reply_markup
        )
        return ConversationHandler.END

    context.user_data['registro_personal'] = {}
    await query.edit_message_text(
        "📝 *Registro Diario de Personal*\n\nPaso 1/3: Por favor, introduce el número de personas que están *en obra*:",
        reply_markup=get_cancel_keyboard(),
        parse_mode='Markdown'
    )
    return ASKING_EN_OBRA

async def get_en_obra(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda el número de personal en obra y pregunta por las faltas."""
    try:
        num_en_obra = int(update.message.text)
        context.user_data['registro_personal']['en_obra'] = num_en_obra
        await update.message.reply_text(
            "Paso 2/3: Introduce el número de *faltas* (personal ausente):",
            reply_markup=get_cancel_keyboard()
        )
        return ASKING_FALTAS
    except ValueError:
        await update.message.reply_text("❌ Por favor, introduce un número válido.", reply_markup=get_cancel_keyboard())
        return ASKING_EN_OBRA

async def get_faltas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda las faltas y pregunta por las bajas."""
    try:
        num_faltas = int(update.message.text)
        context.user_data['registro_personal']['faltas'] = num_faltas
        await update.message.reply_text(
            "Paso 3/3: Introduce el número de personas de *baja*:",
            reply_markup=get_cancel_keyboard()
        )
        return ASKING_BAJAS
    except ValueError:
        await update.message.reply_text("❌ Por favor, introduce un número válido.", reply_markup=get_cancel_keyboard())
        return ASKING_FALTAS

async def get_bajas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda las bajas y muestra la confirmación."""
    try:
        num_bajas = int(update.message.text)
        context.user_data['registro_personal']['bajas'] = num_bajas
        
        # Muestra el resumen para confirmar
        reg = context.user_data['registro_personal']
        texto_resumen = (
            f"📋 *Resumen del Registro para Hoy*\n\n"
            f"👷 *En Obra:* {reg['en_obra']}\n"
            f"❌ *Faltas:* {reg['faltas']}\n"
            f"❤️‍🩹 *Bajas:* {reg['bajas']}\n\n"
            f"¿Son correctos estos datos?"
        )
        keyboard = [
            [InlineKeyboardButton("✅ Sí, Guardar Registro", callback_data="save_registro")],
            [InlineKeyboardButton("❌ No, Empezar de Nuevo", callback_data="restart_registro")]
        ]
        await update.message.reply_text(texto_resumen, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return CONFIRMING
    except ValueError:
        await update.message.reply_text("❌ Por favor, introduce un número válido.", reply_markup=get_cancel_keyboard())
        return ASKING_BAJAS

async def save_registro(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda el registro en la BD y notifica."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    reg_data = context.user_data['registro_personal']
    
    # Guardar en la base de datos
    db.create_personal_registro(
        fecha=date.today(),
        en_obra=reg_data['en_obra'],
        faltas=reg_data['faltas'],
        bajas=reg_data['bajas'],
        user_id=user.id
    )
    
    await query.edit_message_text("✅ ¡Registro de personal guardado con éxito!")
    
    # Notificar al grupo
    report_text = (
        f"📋 *Registro de Personal Diario Completado*\n\n"
        f"👷 *En Obra:* {reg_data['en_obra']}\n"
        f"❌  *Faltas:* {reg_data['faltas']}\n"
        f"❤️‍🩹 *Bajas:* {reg_data['bajas']}\n\n"
        f"_Registrado por: {format_user(user)}_"
    )
    await send_report(context, report_text)
    
    context.user_data.clear()
    return ConversationHandler.END

def get_registro_personal_handler():
    """Crea el ConversationHandler para el registro de personal."""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(start_registro_personal, pattern='^registro_personal_start$')],
        states={
            ASKING_EN_OBRA: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_en_obra)],
            ASKING_FALTAS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_faltas)],
            ASKING_BAJAS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_bajas)],
            CONFIRMING: [
                CallbackQueryHandler(save_registro, pattern='^save_registro$'),
                CallbackQueryHandler(start_registro_personal, pattern='^restart_registro$')
            ],
        },
        fallbacks=[CallbackQueryHandler(cancel, pattern='^cancel_registro$')],
    )