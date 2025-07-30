# calendar_helper.py
import calendar
from datetime import datetime, date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

async def create_calendar(year: int, month: int, allow_past_dates: bool = False) -> InlineKeyboardMarkup:
    """
    Crea un teclado de calendario inline para un mes y año específicos.
    
    :param allow_past_dates: Si es True, permite seleccionar fechas pasadas.
    """
    calendar.setfirstweekday(calendar.MONDAY)
    
    header_text = f"{calendar.month_name[month]} {year}"
    
    # --- INICIO DE LA MODIFICACIÓN ---
    # Se añade el flag 'allow_past_dates' a los callbacks de navegación
    past_flag = "1" if allow_past_dates else "0"
    prev_month_data = f"cal_prev_{year}_{month}_{past_flag}"
    next_month_data = f"cal_next_{year}_{month}_{past_flag}"
    # --- FIN DE LA MODIFICACIÓN ---
    
    keyboard = [
        [
            InlineKeyboardButton("<<", callback_data=prev_month_data),
            InlineKeyboardButton(header_text, callback_data="cal_ignore"),
            InlineKeyboardButton(">>", callback_data=next_month_data)
        ]
    ]

    days_of_week = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sa", "Do"]
    keyboard.append([InlineKeyboardButton(day, callback_data="cal_ignore") for day in days_of_week])

    month_calendar = calendar.monthcalendar(year, month)
    for week in month_calendar:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(" ", callback_data="cal_ignore"))
            else:
                # --- INICIO DE LA MODIFICACIÓN ---
                # La condición ahora depende del nuevo flag
                if allow_past_dates or date(year, month, day) >= date.today():
                    row.append(InlineKeyboardButton(str(day), callback_data=f"cal_day_{year}_{month}_{day}"))
                else:
                    # Este comportamiento se mantiene para cuando no se permiten fechas pasadas
                    row.append(InlineKeyboardButton("·", callback_data="cal_ignore"))
                # --- FIN DE LA MODIFICACIÓN ---
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("❌ Cancelar Solicitud", callback_data="cancel_conversation")])
    
    return InlineKeyboardMarkup(keyboard)

async def process_calendar_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> date | bool:
    """
    Procesa la selección del calendario.
    Devuelve la fecha seleccionada (date), True si se navega, o False si se ignora.
    """
    query = update.callback_query
    await query.answer()
    
    data_parts = query.data.split('_')
    action = data_parts[1]

    if action == "day":
        _, _, year, month, day = data_parts
        selected_date = date(int(year), int(month), int(day))
        return selected_date

    elif action == "prev" or action == "next":
        # --- INICIO DE LA MODIFICACIÓN ---
        # Ahora leemos el flag del callback
        _, _, year, month, past_flag = data_parts
        allow_past_dates = bool(int(past_flag))
        # --- FIN DE LA MODIFICACIÓN ---
        
        current_date = date(int(year), int(month), 1)
        
        if action == "prev":
            if current_date.month == 1:
                new_date = current_date.replace(year=current_date.year - 1, month=12)
            else:
                new_date = current_date.replace(month=current_date.month - 1)
        else: # action == "next"
            if current_date.month == 12:
                new_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                new_date = current_date.replace(month=current_date.month + 1)

        # Obtenemos el texto del mensaje original para no perderlo
        original_text = query.message.text

        await query.edit_message_text(
            text=original_text,
            # Pasamos el flag al regenerar el calendario
            reply_markup=await create_calendar(new_date.year, new_date.month, allow_past_dates=allow_past_dates)
        )
        return True
        
    return False