# almacen/bot_almacen.py

from telegram.ext import (
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from almacen.keyboards import get_nav_keyboard
from almacen.flows_add import (
    start_add_item_flow,
    process_item_type,
    process_item_name,
    process_item_quantity_and_confirm,
    save_item,
    AWAITING_ITEM_TYPE,
    AWAITING_ITEM_NAME,
    AWAITING_ITEM_QUANTITY,
    AWAITING_CONFIRMATION,
)
from almacen.flows_inventory import (
    start_view_flow,
    list_items_by_category,
    show_item_detail,
    prompt_for_new_quantity,
    process_new_quantity,
    prompt_for_new_name,
    process_new_name_and_save,
    confirm_delete_item,
    delete_item,
    view_full_inventory,
    listar_material_en_obra,
    SELECT_CATEGORY,
    LIST_ITEMS,
    VIEW_ITEM_DETAIL,
    AWAIT_NEW_QUANTITY,
    AWAIT_NEW_NAME,
    CONFIRM_DELETE,
)
from almacen.flows_comunicado import (
    start_comunicado,
    send_comunicado_to_group,
    AWAITING_COMUNICADO,
)
from bot_navigation import end_and_return_to_menu
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update

SELECTING_ACTION = 0

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Cancela cualquier operación en curso en el módulo de almacén y retorna al menú principal.
    """
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("Operación de almacén cancelada.", reply_markup=get_nav_keyboard())
    context.user_data.clear()
    return await end_and_return_to_menu(update, context)

async def start_almacen_gestion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Muestra el menú principal de gestión de almacén con las acciones disponibles.
    """
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("➕ Añadir/Actualizar Stock", callback_data="almacen_add_start")],
        [InlineKeyboardButton("📋 Ver/Gestionar Inventario", callback_data="almacen_view_start")],
        [InlineKeyboardButton("📢 Comunicado", callback_data="almacen_comunicado_start")],
        [InlineKeyboardButton("⬅️ Menú Principal", callback_data="back_to_main_menu")],
    ]
    await query.edit_message_text(
        "📦 *Gestión de Almacén*\n\nSelecciona una acción:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )
    return SELECTING_ACTION

def get_almacen_conversation_handler():
    """
    Devuelve el ConversationHandler principal del módulo de almacén, 
    conectando todos los flujos de añadir, consultar, modificar y comunicar.
    """
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_almacen_gestion, pattern="^gestion_almacen$"),
        ],
        states={
            SELECTING_ACTION: [
                CallbackQueryHandler(start_add_item_flow, pattern="^almacen_add_start$"),
                CallbackQueryHandler(start_view_flow, pattern="^almacen_view_start$"),
                CallbackQueryHandler(start_comunicado, pattern="^almacen_comunicado_start$"),
            ],
            AWAITING_ITEM_TYPE: [
                CallbackQueryHandler(process_item_type, pattern="^tipo_")
            ],
            AWAITING_ITEM_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_item_name)
            ],
            AWAITING_ITEM_QUANTITY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_item_quantity_and_confirm)
            ],
            AWAITING_CONFIRMATION: [
                CallbackQueryHandler(save_item, pattern="^save_almacen_item$"),
                CallbackQueryHandler(start_add_item_flow, pattern="^almacen_add_start$"),
            ],
            SELECT_CATEGORY: [
                CallbackQueryHandler(list_items_by_category, pattern="^view_cat_"),
                CallbackQueryHandler(start_almacen_gestion, pattern="^back_to_almacen_menu$"),
                CallbackQueryHandler(start_view_flow, pattern="^back_to_view_start$"),
            ],
            LIST_ITEMS: [
                CallbackQueryHandler(list_items_by_category, pattern="^view_page_"),
                CallbackQueryHandler(show_item_detail, pattern="^view_item_"),
                CallbackQueryHandler(start_view_flow, pattern="^back_to_view_start$"),
            ],
            VIEW_ITEM_DETAIL: [
                CallbackQueryHandler(prompt_for_new_quantity, pattern="^mod_item_qty_"),
                CallbackQueryHandler(prompt_for_new_name, pattern="^mod_item_name_"),
                CallbackQueryHandler(confirm_delete_item, pattern="^mod_item_del_"),
                CallbackQueryHandler(list_items_by_category, pattern="^back_to_list$"),
            ],
            AWAIT_NEW_QUANTITY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_new_quantity)
            ],
            AWAIT_NEW_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_new_name_and_save)
            ],
            CONFIRM_DELETE: [
                CallbackQueryHandler(delete_item, pattern="^del_confirm_yes_"),
                CallbackQueryHandler(show_item_detail, pattern="^del_confirm_no_"),
            ],
            AWAITING_COMUNICADO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, send_comunicado_to_group)
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cancel, pattern="^cancel_almacen$"),
            CallbackQueryHandler(end_and_return_to_menu, pattern="^back_to_main_menu$"),
            CallbackQueryHandler(start_almacen_gestion, pattern="^back_to_almacen_menu$"),
        ],
        map_to_parent={ConversationHandler.END: ConversationHandler.END},
        allow_reentry=True
    )
