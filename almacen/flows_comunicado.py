from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters
from almacen.keyboards import get_cancel_keyboard
from bot_navigation import end_and_return_to_menu
from reporter import escape, format_user, GROUP_CHAT_ID

AWAITING_COMUNICADO = 11

async def start_comunicado(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text="Por favor, escribe el comunicado que quieres enviar al grupo general.",
        reply_markup=get_cancel_keyboard("cancel_almacen"),
    )
    return AWAITING_COMUNICADO

async def send_comunicado_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_message = update.message.text
    user_info = format_user(update.effective_user)
    comunicado_text = (
        f"📢 *Comunicado de Almacén* 📢\n\n"
        f"{escape(user_message)}\n\n"
        f"Sent by: {user_info}"
    )
    try:
        await context.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=comunicado_text,
            parse_mode="MarkdownV2"
        )
        await update.message.reply_text("✅ Comunicado enviado con éxito al grupo.")
    except Exception as e:
        print(f"Error al enviar comunicado: {e}")
        await update.message.reply_text("❌ Hubo un error al intentar enviar el comunicado.")
    return await end_and_return_to_menu(update, context)

def get_comunicado_handler():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_comunicado, pattern="^almacen_comunicado_start$")
        ],
        states={
            AWAITING_COMUNICADO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, send_comunicado_to_group)
            ]
        },
        fallbacks=[
            CallbackQueryHandler(start_comunicado, pattern="^cancel_almacen$"),
            CallbackQueryHandler(end_and_return_to_menu, pattern="^back_to_main_menu$"),
        ],
        map_to_parent={ConversationHandler.END: ConversationHandler.END},
        allow_reentry=True,
    )
