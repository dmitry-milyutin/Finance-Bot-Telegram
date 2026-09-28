from telebot import types

def kb_from_list(
    values: list[str],
    callback_prefix: str,
    tx_id: int,
    cols: int = 2,
    extra_buttons: list[tuple[str, str]] | None = None,
) -> types.InlineKeyboardMarkup:
    """
    Универсальная функция: принимает список значений и собирает inline-клавиатуру.
    callback_data: "{prefix}|{tx_id}|{index}"
    """
    kb = types.InlineKeyboardMarkup(row_width=cols)
    buttons = []

    for i, v in enumerate(values):
        buttons.append(types.InlineKeyboardButton(text=v, callback_data=f"{callback_prefix}|{tx_id}|{i}"))

    if extra_buttons:
        for text, data in extra_buttons:
            buttons.append(types.InlineKeyboardButton(text=text, callback_data=data))

    kb.add(*buttons)
    return kb

def kb_yes_no_type(tx_id: int) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("✅ Доход", callback_data=f"type|{tx_id}|income"),
        types.InlineKeyboardButton("➖ Расход", callback_data=f"type|{tx_id}|expense"),
    )
    kb.add(types.InlineKeyboardButton("✖️ Отмена", callback_data=f"cancel|{tx_id}|0"))
    return kb