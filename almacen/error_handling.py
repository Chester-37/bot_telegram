import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger("almacen.error_handling")

async def log_and_notify_error(update: Update, context: ContextTypes.DEFAULT_TYPE, error: Exception, user_message: str = None):
    logger.error("Ocurrió un error: %s", error, exc_info=True)
    if user_message is None:
        user_message = "❌ Ocurrió un error inesperado. Por favor, inténtalo de nuevo más tarde."
    try:
        if update.callback_query:
            await update.callback_query.edit_message_text(user_message)
        elif update.message:
            await update.message.reply_text(user_message)
    except Exception as e:
        logger.error("No se pudo enviar el mensaje de error al usuario: %s", e)

def log_warning(message: str):
    """
    Loguea una advertencia.
    """
    logger.warning(message)

def log_info(message: str):
    """
    Loguea información.
    """
    logger.info(message)
