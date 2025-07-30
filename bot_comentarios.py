from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    CommandHandler
)
import db_manager as db
# ### AÑADIDO ### - Importar la función desde main
from bot_navigation import end_and_return_to_menu
from bot_navigation import start

AWAITING_COMMENT = range(1)

# --- Helpers de Teclado ---
def get_cancel_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_conversation")]])

def get_nav_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Menú Principal", callback_data="back_to_main_menu")]])

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la operación y vuelve directamente al menú principal."""
    query = update.callback_query
    if query:
        await query.answer("Operación cancelada.")
    else:
        await update.message.reply_text("Operación cancelada.")
    
    context.user_data.clear()
    await start(update, context) # Llama a la función que muestra el menú
    return ConversationHandler.END

# --- Flujo de la Conversación (Lógica sin cambios) ---
async def start_add_comment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el proceso para añadir un comentario a una incidencia."""
    query = update.callback_query
    await query.answer()
    
    incidencia_id = int(query.data.split('_')[1])
    context.user_data['comment_incidencia_id'] = incidencia_id
    
    await query.edit_message_text(
        "Por favor, escribe el comentario o actualización que deseas añadir:",
        reply_markup=get_cancel_keyboard()
    )
    return AWAITING_COMMENT

async def save_comment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda el comentario en la base de datos y notifica."""
    comentario_texto = update.message.text
    incidencia_id = context.user_data['comment_incidencia_id']
    usuario_id = update.effective_user.id
    
    db.add_incidencia_comentario(incidencia_id, usuario_id, comentario_texto)
    
    await update.message.reply_text("✅ Comentario añadido con éxito.", reply_markup=get_nav_keyboard())
    
    # Notificar al encargado original del avance
    incidencia_details = db.get_incidencia_details(incidencia_id)
    if incidencia_details and incidencia_details.get('encargado_id') and incidencia_details['encargado_id'] != usuario_id:
        encargado_id = incidencia_details['encargado_id']
        texto_notificacion = (
            f"💬 @{update.effective_user.username} ha añadido una actualización a la incidencia ID {incidencia_id}:\n\n"
            f"'{comentario_texto}'"
        )
        await context.bot.send_message(chat_id=encargado_id, text=texto_notificacion)

    context.user_data.clear()
    return ConversationHandler.END

def get_comentario_conversation_handler():
    # ### MODIFICADO ### - Añadido el fallback para volver al menú
    """Crea el ConversationHandler para añadir comentarios."""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(start_add_comment, pattern='^comentario_')],
        states={
            AWAITING_COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_comment)],
        },
        fallbacks=[
            CallbackQueryHandler(cancel, pattern='^cancel_conversation$'),
            CallbackQueryHandler(end_and_return_to_menu, pattern='^back_to_main_menu$')
        ],
    )