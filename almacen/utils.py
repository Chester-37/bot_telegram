def validar_cantidad(texto: str) -> int:
    """
    Valida que el texto recibido sea un número entero positivo.
    Devuelve el número si es válido, o lanza ValueError si no lo es.
    """
    cantidad = int(texto)
    if cantidad <= 0:
        raise ValueError("La cantidad debe ser un número positivo.")
    return cantidad

def es_entero_no_negativo(texto: str) -> int:
    """
    Valida que el texto recibido sea un número entero no negativo.
    Devuelve el número si es válido, o lanza ValueError si no lo es.
    """
    cantidad = int(texto)
    if cantidad < 0:
        raise ValueError("La cantidad no puede ser negativa.")
    return cantidad
