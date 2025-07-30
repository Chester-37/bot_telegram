from reporter import escape

def resumen_articulo(item: dict) -> str:
    """
    Devuelve un resumen formateado de un artículo para confirmación.
    """
    return (
        f"📋 *Resumen del Artículo*\n\n"
        f"▪️ *Nombre:* {escape(item['nombre'])}\n"
        f"🔢 *Cantidad a añadir:* {item['cantidad']}\n"
        f"🏷️ *Tipo:* {escape(item['tipo'])}\n\n"
        "¿Son correctos estos datos?"
    )

def detalle_articulo(item: dict) -> str:
    """
    Devuelve el detalle formateado de un artículo.
    """
    return (
        f"📋 *Detalle de: {escape(item['nombre'])}*\n\n"
        f"🔢 *Cantidad en stock:* {item['cantidad']}\n"
        f"🏷️ *Tipo:* {escape(item['tipo'])}\n"
        f"📝 *Descripción:* {escape(item.get('descripcion') or 'N/A')}"
    )

def inventario_completo(grouped_inventory: dict) -> str:
    """
    Devuelve el texto formateado del inventario completo agrupado por tipo.
    """
    message_text = "📦 *Inventario Completo*\n"
    for tipo, items in sorted(grouped_inventory.items()):
        message_text += f"\n*{escape(tipo)}s:*\n"
        message_text += f"{escape('--------------------')}\n"
        for item in items:
            message_text += (
                f"\\- {escape(item['nombre'])}: *{item['cantidad']}* uds\\.\n"
            )
    return message_text

def material_en_obra(material_list: list) -> str:
    """
    Devuelve el texto formateado del material entregado en obra.
    """
    message_text = "🏗️ *Material Registrado en Obra*\n\n"
    for item in material_list:
        message_text += f"\\- {escape(item['nombre'])}: *{item['cantidad']}* uds\\. \\(total entregado\\)\n"
    return message_text

def mensaje_error_generico() -> str:
    """
    Mensaje de error genérico para mostrar al usuario.
    """
    return "❌ Ocurrió un error inesperado. Por favor, inténtalo de nuevo más tarde."
