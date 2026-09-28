import telebot
from telebot import types

from config import BOT_TOKEN, ALLOWED_USER_ID
from constants import (
    INCOME_CATEGORIES,
    EXPENSE_CATEGORIES,
    TX_TYPE_INCOME,
    TX_TYPE_EXPENSE,
)
from db import init_db, cancel_pending, create_tx, get_tx, set_type, set_category_done, cancel_tx
from keyboards import kb_from_list, kb_yes_no_type
from reports import build_period_report, build_year_months_report, build_balance_report
from utils import parse_amount_to_tyiyn, fmt_money, now_local, dt_to_db_str, period_range

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

def is_allowed(user_id: int) -> bool:
    return (ALLOWED_USER_ID is None) or (user_id == ALLOWED_USER_ID)

@bot.message_handler(commands=["start", "help"])
def cmd_start(m: types.Message):
    print(m.from_user.id)
    if not is_allowed(m.from_user.id):
        return
    text = (
        "Привет! Это личный бот учёта денег.\n\n"
        "Как пользоваться:\n"
        "1) Просто отправь сумму (например: `1500` или `120.50`).\n"
        "2) Выбери: доход/расход.\n"
        "3) Выбери категорию — запись сохранится.\n\n"
        "Отчёты:\n"
        "• /day  — сегодня\n"
        "• /week — текущая неделя\n"
        "• /month — текущий месяц\n"
        "• /balance — текущий баланс\n"
        "• /year — год (по месяцам)\n\n"
        "Дополнительно: /cancel — отменить незавершённую запись."
    )
    bot.send_message(m.chat.id, text)

@bot.message_handler(commands=["balance"])
def cmd_balance(m: types.Message):
    print(1)
    if not is_allowed(m.from_user.id):
        return
    print(2)
    text = build_balance_report(m.from_user.id)
    bot.send_message(m.chat.id, text)
    
@bot.message_handler(commands=["cancel"])
def cmd_cancel(m: types.Message):
    if not is_allowed(m.from_user.id):
        return
    cancel_pending(m.from_user.id)
    bot.send_message(m.chat.id, "Ок, отменил незавершённые записи (если были).")

def send_report(m: types.Message, mode: str):
    title, start, end = period_range(mode)
    if mode == "year":
        text = build_year_months_report(m.from_user.id, title, start, end)
    else:
        text = build_period_report(m.from_user.id, title, start, end)
    bot.send_message(m.chat.id, text)

@bot.message_handler(commands=["day", "week", "month", "year"])
def cmd_reports(m: types.Message):
    if not is_allowed(m.from_user.id):
        return
    mode = m.text.lstrip("/").strip().lower()
    send_report(m, mode)

@bot.message_handler(content_types=["text"])
def on_amount(m: types.Message):
    if not is_allowed(m.from_user.id):
        return

    amount = parse_amount_to_tyiyn(m.text)
    if amount is None:
        # не спамим, просто игнор — это личный бот
        return

    # если есть незавершённое — отменяем (удобнее, чем плодить “подвисшие”)
    cancel_pending(m.from_user.id)

    created_at = dt_to_db_str(now_local())

    # создаём tx “черновик” в БД
    placeholder = bot.send_message(
        m.chat.id,
        f"Сумма: *{fmt_money(amount)}*\n\nЭто доход или расход?",
        reply_markup=types.InlineKeyboardMarkup(),  # временно, ниже заменим
    )
    tx_id = create_tx(
        user_id=m.from_user.id,
        chat_id=m.chat.id,
        message_id=placeholder.message_id,
        amount_tyiyn=amount,
        created_at=created_at,
    )

    bot.edit_message_reply_markup(
        chat_id=m.chat.id,
        message_id=placeholder.message_id,
        reply_markup=kb_yes_no_type(tx_id),
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("type|"))
def cb_type(c: types.CallbackQuery):
    if not is_allowed(c.from_user.id):
        bot.answer_callback_query(c.id, "Нет доступа.")
        return

    _, tx_id_str, t = c.data.split("|", 2)
    tx_id = int(tx_id_str)

    tx = get_tx(tx_id, c.from_user.id)
    if not tx:
        bot.answer_callback_query(c.id, "Запись не найдена.")
        return

    if t not in (TX_TYPE_INCOME, TX_TYPE_EXPENSE):
        bot.answer_callback_query(c.id, "Некорректный тип.")
        return

    set_type(tx_id, c.from_user.id, t)

    cats = INCOME_CATEGORIES if t == TX_TYPE_INCOME else EXPENSE_CATEGORIES
    kb = kb_from_list(
        cats,
        callback_prefix="cat",
        tx_id=tx_id,
        cols=2,
        extra_buttons=[("✖️ Отмена", f"cancel|{tx_id}|0")],
    )

    text = (
        f"Сумма: *{fmt_money(tx['amount_tyiyn'])}*\n"
        f"Тип: *{'Доход' if t == TX_TYPE_INCOME else 'Расход'}*\n\n"
        f"Выбери категорию:"
    )
    bot.edit_message_text(text, chat_id=tx["chat_id"], message_id=tx["message_id"], reply_markup=kb)
    bot.answer_callback_query(c.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("cat|"))
def cb_category(c: types.CallbackQuery):
    if not is_allowed(c.from_user.id):
        bot.answer_callback_query(c.id, "Нет доступа.")
        return

    _, tx_id_str, idx_str = c.data.split("|", 2)
    tx_id = int(tx_id_str)
    idx = int(idx_str)

    tx = get_tx(tx_id, c.from_user.id)
    if not tx:
        bot.answer_callback_query(c.id, "Запись не найдена.")
        return

    if tx.get("tx_type") == TX_TYPE_INCOME:
        cats = INCOME_CATEGORIES
        t_name = "Доход"
    else:
        cats = EXPENSE_CATEGORIES
        t_name = "Расход"

    if idx < 0 or idx >= len(cats):
        bot.answer_callback_query(c.id, "Некорректная категория.")
        return

    category_name = cats[idx]
    # В БД сохраняем именно НАЗВАНИЕ категории
    set_category_done(tx_id, c.from_user.id, category_name)

    text = (
        "✅ *Сохранено!*\n\n"
        f"Сумма: *{fmt_money(tx['amount_tyiyn'])}*\n"
        f"Тип: *{t_name}*\n"
        f"Категория: *{category_name}*\n"
        f"Дата: `{tx['created_at']}`"
    )
    bot.edit_message_text(text, chat_id=tx["chat_id"], message_id=tx["message_id"])
    bot.answer_callback_query(c.id, "Записал ✅")

@bot.callback_query_handler(func=lambda c: c.data.startswith("cancel|"))
def cb_cancel(c: types.CallbackQuery):
    if not is_allowed(c.from_user.id):
        bot.answer_callback_query(c.id, "Нет доступа.")
        return

    _, tx_id_str, _ = c.data.split("|", 2)
    tx_id = int(tx_id_str)
    tx = get_tx(tx_id, c.from_user.id)
    if not tx:
        bot.answer_callback_query(c.id, "Уже отменено/не найдено.")
        return

    cancel_tx(tx_id, c.from_user.id)
    bot.edit_message_text("✖️ Отменено.", chat_id=tx["chat_id"], message_id=tx["message_id"])
    bot.answer_callback_query(c.id, "Отменено")





def main():
    init_db()
    print("Bot started...")
    bot.infinity_polling(skip_pending=True)


if __name__ == "__main__":
    main()