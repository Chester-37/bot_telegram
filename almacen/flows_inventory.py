from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
import db_manager as db
from reporter import escape, format_user, send_report
from almacen.keyboards import (
    get_nav_keyboard,
    get_category_keyboard,
    get_empty_category_keyboard,
    get_item_detail_keyboard,
    get_pagination_keyboard,
    get_confirm_delete_keyboard,
)
from bot_navigation import end_and_return_to_menu
import psycopg2

SELECT_CATEGORY = 5
LIST_ITEMS = 6
VIEW_ITEM_DETAIL = 7
AWAIT_NEW_QUANTITY = 8
AWAIT_NEW_NAME = 9
CONFIRM_DELETE = 10

ITEMS_PER_PAGE = 5

async def start_view_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text(
        "*Ver/Gestionar Inventario*\n\nSelecciona una categoría para ver sus artículos:",
        reply_markup=get_category_keyboard(),
        parse_mode="Markdown",
    )
    return SELECT_CATEGORY

async def list_items_by_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data.startswith("view_cat_"):
        category = query.data.split("_")[2]
        context.user_data["view_category"] = category
        context.user_data["view_page"] = 0
    elif query.data == "back_to_list":
        category = context.user_data["view_category"]
    else:
        category = context.user_data["view_category"]
        page_action = query.data.split("_")[2]
        if page_action == "next":
            context.user_data["view_page"] += 1
        elif page_action == "prev":
            context.user_data["view_page"] -= 1

    page = context.user_data["view_page"]
    items, total_pages = db.get_almacen_items_paginated(
        category, page, ITEMS_PER_PAGE
    )

    if not items and page == 0:
        await query.edit_message_text(
            f"No hay artículos en la categoría '{category}'.",
            reply_markup=get_empty_category_keyboard()
        )
        return SELECT_CATEGORY

    keyboard = []
    for item in items:
        label = f"{item['nombre']} ({item['cantidad']} uds.)"
        keyboard.append(
            [InlineKeyboardButton(label, callback_data=f"view_item_{item['id']}")]
        )

    pagination_markup = get_pagination_keyboard(page, total_pages)
    if pagination_markup:
        keyboard.append(pagination_markup.inline_keyboard[0])

    keyboard.append(
        [InlineKeyboardButton("⬅️ Volver a Categorías", callback_data="back_to_view_start")]
    )

    await query.edit_message_text(
        f"*{escape(category)}s* \\(Página {page + 1}/{total_pages}\\)\n\nSelecciona un artículo para ver detalles y modificarlo:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="MarkdownV2",
    )
    return LIST_ITEMS

async def show_item_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()
        message_sender = query
    else:
        message_sender = update.message

    if query and query.data.startswith("view_item_"):
        item_id = int(query.data.split("_")[2])
        context.user_data["selected_item_id"] = item_id
    elif query and query.data.startswith("del_confirm_no_"):
        item_id = int(query.data.split("_")[3])
    else:
        item_id = context.user_data["selected_item_id"]

    item = db.get_almacen_item_details(item_id)
    if not item:
        await message_sender.edit_message_text(
            "❌ Error: El artículo ya no existe.",
            reply_markup=get_empty_category_keyboard(),
        )
        return LIST_ITEMS

    texto = (
        f"📋 *Detalle de: {escape(item['nombre'])}*\n\n"
        f"🔢 *Cantidad en stock:* {item['cantidad']}\n"
        f"🏷️ *Tipo:* {escape(item['tipo'])}\n"
        f"📝 *Descripción:* {escape(item.get('descripcion') or 'N/A')}"
    )
    keyboard = get_item_detail_keyboard(item_id)

    if query:
        await message_sender.edit_message_text(
            texto, reply_markup=keyboard, parse_mode="MarkdownV2"
        )
    else:
        await message_sender.reply_text(
            texto, reply_markup=keyboard, parse_mode="MarkdownV2"
        )

    return VIEW_ITEM_DETAIL

async def prompt_for_new_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    item_id = int(query.data.split("_")[3])
    item = db.get_almacen_item_details(item_id)
    await query.edit_message_text(
        f"Introduce la *nueva cantidad total* para *{escape(item['nombre'])}*\\.\n"
        f"La cantidad actual es {item['cantidad']}\\.",
        reply_markup=get_nav_keyboard(),
        parse_mode="MarkdownV2",
    )
    return AWAIT_NEW_QUANTITY

async def process_new_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        new_quantity = int(update.message.text)
        if new_quantity < 0:
            raise ValueError("La cantidad no puede ser negativa.")

        item_id = context.user_data["selected_item_id"]
        old_item = db.get_almacen_item_details(item_id)
        db.update_almacen_item_quantity(item_id, new_quantity)

        user_info = format_user(update.effective_user)
        report_text = (
            f"📦 *Actualización de Stock*\n\n"
            f"👤 *Usuario:* {user_info}\n"
            f"📝 *Artículo:* {escape(old_item['nombre'])}\n"
            f"🔢 *Cantidad Anterior:* {old_item['cantidad']}\n"
            f"✅ *Nueva Cantidad:* {new_quantity}"
        )
        await send_report(context, report_text)
        await update.message.reply_text("✅ Cantidad actualizada con éxito\\.")

        return await show_item_detail(update, context)

    except ValueError:
        await update.message.reply_text(
            "❌ Por favor, introduce un número entero no negativo.",
            reply_markup=get_nav_keyboard(),
        )
        return AWAIT_NEW_QUANTITY

async def prompt_for_new_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    item_id = int(query.data.split("_")[3])
    item = db.get_almacen_item_details(item_id)
    await query.edit_message_text(
        f"Introduce el *nuevo nombre* para *{escape(item['nombre'])}*\\.",
        reply_markup=get_nav_keyboard(),
        parse_mode="MarkdownV2",
    )
    return AWAIT_NEW_NAME

async def process_new_name_and_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_name = update.message.text
    item_id = context.user_data["selected_item_id"]

    old_item = db.get_almacen_item_details(item_id)
    success = db.update_almacen_item_details(item_id, new_name, old_item.get('descripcion'))

    if not success:
        await update.message.reply_text(
            f"❌ Error: El nombre '{escape(new_name)}' ya está en uso\\. La operación ha sido cancelada\\.",
            parse_mode="MarkdownV2"
        )
    else:
        user_info = format_user(update.effective_user)
        report_text = (
            f"📦 *Modificación de Artículo*\n\n"
            f"👤 *Usuario:* {user_info}\n"
            f"📝 *Artículo Original:* {escape(old_item['nombre'])}\n"
            f"✨ *Nuevo Nombre:* {escape(new_name)}"
        )
        await send_report(context, report_text)
        await update.message.reply_text("✅ Nombre actualizado con éxito\\.")

    return await show_item_detail(update, context)

async def confirm_delete_item(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    item_id = int(query.data.split("_")[3])
    item = db.get_almacen_item_details(item_id)
    texto = (
        f"⚠️ *¡ATENCIÓN\\!* ⚠️\n\n"
        f"¿Estás seguro de que quieres eliminar permanentemente el artículo *{escape(item['nombre'])}*\\?\n\n"
        f"Esta acción no se puede deshacer\\."
    )
    keyboard = get_confirm_delete_keyboard(item_id)
    await query.edit_message_text(
        texto, reply_markup=keyboard, parse_mode="MarkdownV2"
    )
    return CONFIRM_DELETE

async def delete_item(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    item_id = int(query.data.split("_")[3])
    item = db.get_almacen_item_details(item_id)

    try:
        db.delete_almacen_item(item_id)

        user_info = format_user(update.effective_user)
        report_text = (
            f"🗑️ *Artículo Eliminado del Stock*\n\n"
            f"👤 *Usuario:* {user_info}\n"
            f"📝 *Artículo:* {escape(item['nombre'])}"
        )
        await send_report(context, report_text)
        await query.edit_message_text(
            f"✅ El artículo *{escape(item['nombre'])}* ha sido eliminado\\.",
            parse_mode="MarkdownV2",
        )
        return await list_items_by_category(update, context)

    except psycopg2.IntegrityError:
        await query.edit_message_text(
            f"❌ *No se puede eliminar el artículo*\n\n"
            f"El artículo *{escape(item['nombre'])}* está siendo utilizado en pedidos o incidencias y no puede ser borrado para mantener la integridad de los datos\\.",
            reply_markup=get_item_detail_keyboard(item_id),
            parse_mode="MarkdownV2",
        )
        return VIEW_ITEM_DETAIL
    except Exception as e:
        await query.edit_message_text(f"Ocurrió un error inesperado: {e}")
        return await end_and_return_to_menu(update, context)

async def view_full_inventory(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Buscando en el inventario...")
    inventory = db.get_full_inventory()
    if not inventory:
        await query.edit_message_text(
            "El inventario está vacío.", reply_markup=get_nav_keyboard()
        )
        return ConversationHandler.END
    message_text = "📦 *Inventario Completo*\n"
    grouped_inventory = {}
    for item in inventory:
        grouped_inventory.setdefault(item["tipo"], []).append(item)
    for tipo, items in sorted(grouped_inventory.items()):
        message_text += f"\n*{escape(tipo)}s:*\n"
        message_text += f"{escape('--------------------')}\n"
        for item in items:
            message_text += (
                f"\\- {escape(item['nombre'])}: *{item['cantidad']}* uds\\.\n"
            )
    await query.edit_message_text(
        message_text, parse_mode="MarkdownV2", reply_markup=get_nav_keyboard()
    )
    return ConversationHandler.END

async def listar_material_en_obra(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Consultando material entregado a obra...")
    material_en_obra = db.get_material_en_obra()
    if not material_en_obra:
        await query.edit_message_text(
            "🏗️ No hay registros de material entregado a obra.",
            reply_markup=get_nav_keyboard(),
        )
        return
    message_text = "🏗️ *Material Registrado en Obra*\n\n"
    for item in material_en_obra:
        message_text += f"\\- {escape(item['nombre'])}: *{item['cantidad']}* uds\\. \\(total entregado\\)\n"
    await query.edit_message_text(
        message_text, parse_mode="MarkdownV2", reply_markup=get_nav_keyboard()
    )
    return ConversationHandler.END
