from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
import db_manager as db
from reporter import escape
from almacen.keyboards import get_cancel_keyboard, get_item_type_keyboard, get_save_or_restart_keyboard
from bot_navigation import end_and_return_to_menu
from almacen.utils import validar_cantidad  # Si usas validaciones

# Estados necesarios (deben coincidir con los definidos en bot_almacen.py)
AWAITING_ITEM_TYPE = 1
AWAITING_ITEM_NAME = 2
AWAITING_ITEM_QUANTITY = 3
AWAITING_CONFIRMATION = 4

async def start_add_item_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["current_item"] = {}
    await query.edit_message_text(
        "Vas a añadir un artículo al inventario.\n\n"
        "Paso 1: Selecciona el tipo de artículo:",
        reply_markup=get_item_type_keyboard(),
    )
    return AWAITING_ITEM_TYPE

async def process_item_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    item_type = query.data.split("_")[1]
    context.user_data["current_item"]["tipo"] = item_type
    await query.edit_message_text(
        f"Tipo seleccionado: *{escape(item_type)}*\\.\n\n"
        "Paso 2: Introduce el *nombre* del artículo \\(ej: 'Martillo percutor'\\)\\.",
        reply_markup=get_cancel_keyboard(),
        parse_mode="MarkdownV2",
    )
    return AWAITING_ITEM_NAME

async def process_item_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    item_name = update.message.text
    context.user_data["current_item"]["nombre"] = item_name
    await update.message.reply_text(
        f"Nombre: *{escape(item_name)}*\\.\n\n"
        "Paso 3: Introduce la *cantidad* a añadir \\(si ya existe, se sumará al stock\\)\\.",
        reply_markup=get_cancel_keyboard(),
        parse_mode="MarkdownV2",
    )
    return AWAITING_ITEM_QUANTITY

async def process_item_quantity_and_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        quantity = int(update.message.text)
        if quantity <= 0:
            raise ValueError("La cantidad debe ser un número positivo.")
        context.user_data["current_item"]["cantidad"] = quantity
        context.user_data["current_item"]["descripcion"] = "Sin descripción"
        item = context.user_data["current_item"]
        texto_resumen = (
            f"📋 *Resumen del Artículo*\n\n"
            f"▪️ *Nombre:* {escape(item['nombre'])}\n"
            f"🔢 *Cantidad a añadir:* {item['cantidad']}\n"
            f"🏷️ *Tipo:* {escape(item['tipo'])}\n\n"
            "¿Son correctos estos datos?"
        )
        await update.message.reply_text(
            texto_resumen,
            reply_markup=get_save_or_restart_keyboard(),
            parse_mode="MarkdownV2",
        )
        return AWAITING_CONFIRMATION
    except ValueError:
        await update.message.reply_text(
            "❌ Por favor, introduce un número válido y positivo para la cantidad.",
            reply_markup=get_cancel_keyboard(),
        )
        return AWAITING_ITEM_QUANTITY

async def save_item(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    item_data = context.user_data["current_item"]
    db.add_or_update_almacen_item(
        item_data["nombre"],
        item_data["cantidad"],
        item_data["descripcion"],
        item_data["tipo"],
    )
    context.user_data.clear()
    await query.edit_message_text("✅ ¡Artículo guardado con éxito!")
    return await end_and_return_to_menu(update, context)
