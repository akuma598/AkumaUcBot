import os
import logging
import sqlite3
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery
from aiogram.utils import executor

API_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "8504217011"))

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)

conn = sqlite3.connect("shop.db", check_same_thread=False)
cursor = conn.cursor()

# ===== ТАБЛИЦЫ =====
cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    first_name TEXT,
    product_name TEXT,
    product_amount TEXT,
    price_rub INTEGER,
    price_stars INTEGER,
    status TEXT,
    category TEXT,
    created_at TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS banned (
    user_id INTEGER PRIMARY KEY
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS product_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_amount TEXT,
    code TEXT,
    is_used INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS faq (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT,
    answer TEXT
)
""")

# Добавляем стандартные FAQ
cursor.execute("SELECT COUNT(*) FROM faq")
if cursor.fetchone()[0] == 0:
    default_faq = [
        ("❓ Как оплатить заказ?", "Оплата проходит через Telegram Stars. Нажмите «Оплатить Stars» и следуйте инструкциям."),
        ("⏱️ Как быстро приходит товар?", "Для товаров с автовыдачей — мгновенно. Для остальных — в течение 5-15 минут после оплаты."),
        ("🆘 Не пришёл товар. Что делать?", "Напишите в поддержку через кнопку «Поддержка» в главном меню. Укажите номер заказа."),
        ("🔄 Можно вернуть деньги?", "Возврат средств возможен в течение 15 минут после оплаты, если товар не был выдан."),
        ("📞 Как связаться с админом?", "Нажмите кнопку «Поддержка» в главном меню или напишите @aakumma")
    ]
    for q, a in default_faq:
        cursor.execute("INSERT INTO faq (question, answer) VALUES (?, ?)", (q, a))
    conn.commit()

conn.commit()

WELCOME_IMAGE = "AgACAgIAAxkBAAEpEj5qAAF14VBLMN24S1ngXPeedYLmlrcAAmEYaxs8bQFIsoUcN-o04FMBAAMCAANtAAM7BA"

def rub_to_stars(rub):
    return max(1, round(rub / 1.5))

async def is_banned(user_id):
    cursor.execute("SELECT * FROM banned WHERE user_id=?", (user_id,))
    return cursor.fetchone() is not None

# ===== ФУНКЦИИ ДЛЯ АВТОВЫДАЧИ =====
def add_product_code(product_amount, code):
    cursor.execute("INSERT INTO product_codes (product_amount, code) VALUES (?, ?)", (product_amount, code))
    conn.commit()

def get_product_code(product_amount):
    cursor.execute("SELECT id, code FROM product_codes WHERE product_amount=? AND is_used=0 LIMIT 1", (product_amount,))
    result = cursor.fetchone()
    if result:
        cursor.execute("UPDATE product_codes SET is_used=1 WHERE id=?", (result[0],))
        conn.commit()
        return result[1]
    return None

def get_codes_count(product_amount):
    cursor.execute("SELECT COUNT(*) FROM product_codes WHERE product_amount=? AND is_used=0", (product_amount,))
    return cursor.fetchone()[0]

# ===== КЛАВИАТУРЫ =====
def main_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("💰 Купить UC", callback_data="buy_uc"),
        InlineKeyboardButton("📦 Мои заказы", callback_data="my_orders"),
        InlineKeyboardButton("❓ FAQ", callback_data="show_faq"),
        InlineKeyboardButton("⭐ Отзывы", url="https://t.me/your_reviews"),
        InlineKeyboardButton("🔗 Поддержка", url="https://t.me/your_support")
    )
    return kb

def uc_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📦 60 UC — 78₽", callback_data="select_60_78"),
        InlineKeyboardButton("📦 120 UC — 141₽", callback_data="select_120_141"),
        InlineKeyboardButton("📦 180 UC — 204₽", callback_data="select_180_204"),
        InlineKeyboardButton("📦 240 UC — 267₽", callback_data="select_240_267"),
        InlineKeyboardButton("📦 325 UC — 356₽", callback_data="select_325_356"),
        InlineKeyboardButton("📦 385 UC — 419₽", callback_data="select_385_419"),
        InlineKeyboardButton("📦 445 UC — 482₽", callback_data="select_445_482"),
        InlineKeyboardButton("📦 660 UC — 708₽", callback_data="select_660_708"),
        InlineKeyboardButton("📦 720 UC — 771₽", callback_data="select_720_771"),
        InlineKeyboardButton("📦 985 UC — 1049₽", callback_data="select_985_1049"),
        InlineKeyboardButton("📦 1320 UC — 1401₽", callback_data="select_1320_1401"),
        InlineKeyboardButton("📦 1800 UC — 1905₽", callback_data="select_1800_1905"),
        InlineKeyboardButton("⬅️ Назад", callback_data="back")
    )
    return kb

def confirm_keyboard(order_id, product_name, price_rub, price_stars):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ Да, оплатить", callback_data=f"confirm_pay_{order_id}"),
        InlineKeyboardButton("❌ Отмена", callback_data="back")
    )
    return kb

def repeat_order_keyboard(order_id, product_amount):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🔄 Повторить заказ", callback_data=f"repeat_{product_amount}"))
    kb.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_orders"))
    return kb

def admin_menu():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
        InlineKeyboardButton("📦 Все заказы", callback_data="admin_orders"),
        InlineKeyboardButton("✅ Выдать товар", callback_data="admin_give"),
        InlineKeyboardButton("🔑 Коды товаров", callback_data="admin_codes"),
        InlineKeyboardButton("❓ Управление FAQ", callback_data="admin_faq"),
        InlineKeyboardButton("🚫 Бан пользователя", callback_data="admin_ban"),
        InlineKeyboardButton("🔓 Разбан", callback_data="admin_unban"),
        InlineKeyboardButton("🔙 Выйти", callback_data="admin_exit")
    )
    return kb

def admin_codes_menu():
    kb = InlineKeyboardMarkup(row_width=1)
    amounts = ["60", "120", "180", "240", "325", "385", "445", "660", "720", "985", "1320", "1800"]
    for amount in amounts:
        count = get_codes_count(amount)
        kb.add(InlineKeyboardButton(f"📦 {amount} UC — {count} кодов", callback_data=f"admin_codes_{amount}"))
    kb.add(InlineKeyboardButton("🔙 Назад", callback_data="admin_back"))
    return kb

def admin_faq_menu():
    cursor.execute("SELECT id, question FROM faq")
    faq_list = cursor.fetchall()
    kb = InlineKeyboardMarkup(row_width=1)
    for faq in faq_list:
        kb.add(InlineKeyboardButton(f"✏️ {faq[1][:30]}...", callback_data=f"admin_edit_faq_{faq[0]}"))
    kb.add(InlineKeyboardButton("➕ Добавить FAQ", callback_data="admin_add_faq"))
    kb.add(InlineKeyboardButton("🔙 Назад", callback_data="admin_back"))
    return kb

def orders_keyboard(orders_list, page=0):
    kb = InlineKeyboardMarkup(row_width=1)
    start = page * 5
    end = start + 5
    for order in orders_list[start:end]:
        status_emoji = "✅" if order[7] == "✅ Выполнен" else "⏳"
        kb.add(InlineKeyboardButton(
            f"{status_emoji} #{order[0]} | {order[4]} | {order[6]}₽",
            callback_data=f"order_{order[0]}"
        ))
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Назад", callback_data=f"orders_page_{page-1}"))
    if end < len(orders_list):
        nav_buttons.append(InlineKeyboardButton("Вперед ▶️", callback_data=f"orders_page_{page+1}"))
    if nav_buttons:
        kb.row(*nav_buttons)
    
    kb.add(InlineKeyboardButton("🔙 Назад", callback_data="admin_back"))
    return kb

def give_keyboard(order_id):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("✅ Выдать товар", callback_data=f"give_{order_id}"))
    kb.add(InlineKeyboardButton("🔙 Назад", callback_data="admin_back"))
    return kb

# ===== ОБРАБОТЧИКИ =====
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    if await is_banned(message.from_user.id):
        await message.answer("❌ Вы забанены")
        return
    
    text = "👋 **Добро пожаловать в Akuma UC BOT!**\n\n🟢 Мы работаем 24/7\n\nЗдесь вы можете быстро и удобно купить UC.\n\n👇 Используйте меню ниже:"
    
    await message.answer_photo(
        photo=WELCOME_IMAGE,
        caption=text,
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

@dp.message_handler(commands=['admin'])
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Доступ запрещён")
        return
    await message.answer("🔧 **Админ-панель**", reply_markup=admin_menu(), parse_mode="Markdown")

# ===== ПОЛЬЗОВАТЕЛЬСКИЕ КНОПКИ =====
@dp.callback_query_handler(lambda c: c.data == "buy_uc")
async def show_uc(callback: types.CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("❌ Вы забанены", show_alert=True)
        return
    await callback.message.edit_caption(
        caption="💰 **ВЫБЕРИТЕ КОЛИЧЕСТВО UC:**\n\nОплата рублями через Telegram Stars.",
        reply_markup=uc_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "back")
async def back(callback: types.CallbackQuery):
    text = "👋 **Добро пожаловать в Akuma UC BOT!**\n\n🟢 Мы работаем 24/7\n\nЗдесь вы можете быстро и удобно купить UC.\n\n👇 Используйте меню ниже:"
    await callback.message.edit_caption(
        caption=text,
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "show_faq")
async def show_faq(callback: types.CallbackQuery):
    cursor.execute("SELECT question, answer FROM faq")
    faq_list = cursor.fetchall()
    
    text = "❓ **ЧАСТО ЗАДАВАЕМЫЕ ВОПРОСЫ**\n\n"
    for q, a in faq_list:
        text += f"{q}\n{a}\n\n"
    
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🔙 Назад", callback_data="back"))
    
    await callback.message.edit_caption(caption=text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

# ===== КНОПКА "ПОВТОРИТЬ ЗАКАЗ" =====
@dp.callback_query_handler(lambda c: c.data.startswith("repeat_"))
async def repeat_order(callback: types.CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("❌ Вы забанены", show_alert=True)
        return
    
    product_amount = callback.data.split("_")[1]
    
    prices = {
        "60": 78, "120": 141, "180": 204, "240": 267, "325": 356,
        "385": 419, "445": 482, "660": 708, "720": 771, "985": 1049,
        "1320": 1401, "1800": 1905
    }
    price_rub = prices.get(product_amount, 78)
    product_name = f"{product_amount} UC"
    price_stars = rub_to_stars(price_rub)
    
    cursor.execute("""
        INSERT INTO orders (user_id, username, first_name, product_name, product_amount, price_rub, price_stars, status, category, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        callback.from_user.id,
        callback.from_user.username or "Аноним",
        callback.from_user.first_name or "",
        product_name,
        product_amount,
        price_rub,
        price_stars,
        "💳 Ожидание оплаты",
        "UC",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()
    order_id = cursor.lastrowid
    
    text = (
        f"🛒 **ПОДТВЕРЖДЕНИЕ ЗАКАЗА**\n\n"
        f"📦 Товар: {product_name}\n"
        f"💰 Сумма: {price_rub}₽\n"
        f"⭐ Оплата: {price_stars} Telegram Stars\n\n"
        f"Вы уверены, что хотите приобрести этот товар?"
    )
    
    await callback.message.edit_caption(
        caption=text,
        reply_markup=confirm_keyboard(order_id, product_name, price_rub, price_stars),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "back_to_orders")
async def back_to_orders(callback: types.CallbackQuery):
    await callback.message.edit_caption(
        caption="📦 **Вернуться к заказам**",
        reply_markup=admin_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

# ===== СОЗДАНИЕ ЗАКАЗА =====
@dp.callback_query_handler(lambda c: c.data.startswith("select_"))
async def create_order(callback: types.CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("❌ Вы забанены", show_alert=True)
        return
    
    parts = callback.data.split("_")
    product_amount = parts[1]
    price_rub = int(parts[2])
    
    product_name = f"{product_amount} UC"
    price_stars = rub_to_stars(price_rub)
    
    cursor.execute("""
        INSERT INTO orders (user_id, username, first_name, product_name, product_amount, price_rub, price_stars, status, category, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        callback.from_user.id,
        callback.from_user.username or "Аноним",
        callback.from_user.first_name or "",
        product_name,
        product_amount,
        price_rub,
        price_stars,
        "💳 Ожидание оплаты",
        "UC",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()
    order_id = cursor.lastrowid
    
    await bot.send_message(
        ADMIN_ID,
        f"🆕 **НОВЫЙ ЗАКАЗ #{order_id}**\n👤 {callback.from_user.first_name or 'Аноним'} (@{callback.from_user.username or 'нет'})\n📦 {product_name}\n💰 {price_rub}₽",
        parse_mode="Markdown"
    )
    
    text = (
        f"🛒 **ПОДТВЕРЖДЕНИЕ ЗАКАЗА**\n\n"
        f"📦 Товар: {product_name}\n"
        f"💰 Сумма: {price_rub}₽\n"
        f"⭐ Оплата: {price_stars} Telegram Stars\n\n"
        f"Вы уверены, что хотите приобрести этот товар?"
    )
    
    await callback.message.edit_caption(
        caption=text,
        reply_markup=confirm_keyboard(order_id, product_name, price_rub, price_stars),
        parse_mode="Markdown"
    )
    await callback.answer()

# ===== ПОДТВЕРЖДЕНИЕ ОПЛАТЫ =====
@dp.callback_query_handler(lambda c: c.data.startswith("confirm_pay_"))
async def confirm_payment(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[2])
    
    cursor.execute("SELECT product_name, price_stars, product_amount FROM orders WHERE id=?", (order_id,))
    order = cursor.fetchone()
    
    if order:
        await bot.send_invoice(
            chat_id=callback.from_user.id,
            title=f"🛒 Заказ #{order_id}",
            description=order[0],
            payload=f"order_{order_id}",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label=order[0], amount=order[1])],
            start_parameter=f"order_{order_id}"
        )
        await callback.message.delete()
    else:
        await callback.answer("❌ Заказ не найден", show_alert=True)
    await callback.answer()

# ===== ПРОВЕРКА ОПЛАТЫ И АВТОВЫДАЧА =====
@dp.pre_checkout_query_handler(lambda query: True)
async def pre_checkout(pre_checkout_q: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)

@dp.message_handler(content_types=types.ContentType.SUCCESSFUL_PAYMENT)
async def successful_payment(message: types.Message):
    payload = message.successful_payment.invoice_payload
    order_id = int(payload.split("_")[1])
    
    cursor.execute("SELECT product_name, price_rub, price_stars, product_amount FROM orders WHERE id=?", (order_id,))
    order = cursor.fetchone()
    
    if order:
        cursor.execute("UPDATE orders SET status='✅ Оплачен (ожидает выдачи)' WHERE id=?", (order_id,))
        conn.commit()
        
        product_amount = order[3]
        code = get_product_code(product_amount)
        
        if code:
            cursor.execute("UPDATE orders SET status='✅ Выполнен' WHERE id=?", (order_id,))
            conn.commit()
            await message.answer(
                f"✅ **ОПЛАТА ПРОШЛА УСПЕШНО!**\n\n"
                f"📦 Заказ #{order_id}\n"
                f"🎮 Товар: {order[0]}\n"
                f"💰 Сумма: {order[1]}₽\n\n"
                f"🎁 **Код активации:**\n`{code}`\n\n"
                f"Спасибо за покупку!",
                parse_mode="Markdown"
            )
            await bot.send_message(ADMIN_ID, f"💰 **АВТОВЫДАЧА:**\nЗаказ #{order_id}\n📦 {order[0]}\n🔑 Код выдан автоматически")
        else:
            await message.answer(
                f"✅ **ОПЛАТА ПРОШЛА УСПЕШНО!**\n\n"
                f"📦 Заказ #{order_id}\n"
                f"🎮 Товар: {order[0]}\n"
                f"💰 Сумма: {order[1]}₽\n\n"
                f"📌 Товар будет выдан в ближайшее время.",
                parse_mode="Markdown"
            )
            await bot.send_message(
                ADMIN_ID,
                f"💰 **ОПЛАЧЕН ЗАКАЗ #{order_id}**\n👤 {message.from_user.first_name or 'Аноним'} (@{message.from_user.username or 'нет'})\n📦 {order[0]}\n💰 {order[1]}₽\n⭐ {order[2]} Stars",
                parse_mode="Markdown"
            )
    else:
        await message.answer("❌ Заказ не найден")

# ===== МОИ ЗАКАЗЫ =====
@dp.callback_query_handler(lambda c: c.data == "my_orders")
async def my_orders(callback: types.CallbackQuery):
    cursor.execute("SELECT id, product_name, product_amount, price_rub, status, created_at FROM orders WHERE user_id=? ORDER BY id DESC", (callback.from_user.id,))
    orders_list = cursor.fetchall()
    
    if not orders_list:
        await callback.answer("❌ У вас нет заказов", show_alert=True)
        return
    
    kb = InlineKeyboardMarkup(row_width=1)
    for o in orders_list:
        status_emoji = "✅" if o[4] == "✅ Выполнен" else "⏳"
        kb.add(InlineKeyboardButton(
            f"{status_emoji} #{o[0]} | {o[1]} | {o[3]}₽",
            callback_data=f"user_order_{o[0]}"
        ))
    kb.add(InlineKeyboardButton("🔙 Назад", callback_data="back"))
    
    await callback.message.edit_caption(
        caption="📦 **Ваши заказы:**\n\nНажмите на заказ для деталей и повтора.",
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("user_order_"))
async def user_order_detail(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[2])
    
    cursor.execute("SELECT id, product_name, product_amount, price_rub, status, created_at FROM orders WHERE id=?", (order_id,))
    order = cursor.fetchone()
    
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    text = (f"📋 **ЗАКАЗ #{order[0]}**\n"
            f"📦 Товар: {order[1]}\n"
            f"💰 Цена: {order[3]}₽\n"
            f"📅 Дата: {order[5]}\n"
            f"📌 Статус: {order[4]}")
    
    if order[4] == "✅ Выполнен":
        await callback.message.edit_caption(
            caption=text,
            reply_markup=repeat_order_keyboard(order[0], order[2]),
            parse_mode="Markdown"
        )
    else:
        await callback.message.edit_caption(caption=text, parse_mode="Markdown")
    await callback.answer()

# ===== АДМИН ПАНЕЛЬ =====
@dp.callback_query_handler(lambda c: c.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    cursor.execute("SELECT COUNT(*), SUM(price_rub) FROM orders WHERE status='✅ Оплачен (ожидает выдачи)' OR status='✅ Выполнен'")
    completed = cursor.fetchone()
    
    cursor.execute("SELECT COUNT(*), SUM(price_rub) FROM orders")
    total = cursor.fetchone()
    
    text = (f"📊 **СТАТИСТИКА**\n\n"
            f"✅ Выполнено заказов: {completed[0] or 0}\n"
            f"💰 Выручка: {completed[1] or 0}₽\n\n"
            f"📦 Всего заказов: {total[0] or 0}\n"
            f"💸 Общая сумма: {total[1] or 0}₽")
    await callback.message.edit_caption(caption=text, reply_markup=admin_menu(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_orders")
async def admin_orders_list(callback: types.CallbackQuery):
    cursor.execute("SELECT id, product_name, price_rub, status, username, first_name FROM orders ORDER BY id DESC")
    orders_list = cursor.fetchall()
    
    if not orders_list:
        await callback.answer("❌ Нет заказов", show_alert=True)
        return
    
    await callback.message.edit_caption(
        caption="📦 **СПИСОК ЗАКАЗОВ**",
        reply_markup=orders_keyboard(orders_list, 0),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("orders_page_"))
async def orders_page(callback: types.CallbackQuery):
    page = int(callback.data.split("_")[2])
    cursor.execute("SELECT id, product_name, price_rub, status, username, first_name FROM orders ORDER BY id DESC")
    orders_list = cursor.fetchall()
    
    await callback.message.edit_caption(
        caption="📦 **СПИСОК ЗАКАЗОВ**",
        reply_markup=orders_keyboard(orders_list, page),
        parse_mode="Markdown"
    )
    await callback.answer()

# ===== ПРОСМОТР ЗАКАЗА (С ИМЕНЕМ И ПЕРЕХОДОМ В ПРОФИЛЬ) =====
@dp.callback_query_handler(lambda c: c.data.startswith("order_"))
async def view_order(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[1])
    cursor.execute("SELECT id, user_id, username, first_name, product_name, price_rub, status, created_at FROM orders WHERE id=?", (order_id,))
    order = cursor.fetchone()
    
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    user_id = order[1]
    username = order[2]
    first_name = order[3] or "Пользователь"
    
    user_link = f"tg://user?id={user_id}"
    
    if username:
        user_display = f"@{username}"
    else:
        user_display = f"[{first_name}]({user_link})"
    
    text = (f"📋 **ЗАКАЗ #{order[0]}**\n"
            f"👤 Пользователь: {user_display}\n"
            f"🆔 ID: `{user_id}`\n"
            f"📦 Товар: {order[4]}\n"
            f"💰 Цена: {order[5]}₽\n"
            f"📅 Дата: {order[7]}\n"
            f"📌 Статус: {order[6]}")
    
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("✅ Выдать товар", callback_data=f"give_{order[0]}"))
    kb.add(InlineKeyboardButton("💬 Написать", url=user_link))
    kb.add(InlineKeyboardButton("🔙 Назад", callback_data="admin_back"))
    
    await callback.message.edit_caption(caption=text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("give_"))
async def give_item(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[1])
    
    cursor.execute("SELECT user_id, product_name, product_amount FROM orders WHERE id=?", (order_id,))
    order = cursor.fetchone()
    
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    code = get_product_code(order[2])
    
    if code:
        cursor.execute("UPDATE orders SET status='✅ Выполнен' WHERE id=?", (order_id,))
        conn.commit()
        await callback.message.edit_caption(
            caption=f"✅ Товар выдан! Заказ #{order_id} выполнен.\n\n🎁 Код: `{code}`",
            reply_markup=admin_menu(),
            parse_mode="Markdown"
        )
        await bot.send_message(order[0], f"✅ **ВАШ ЗАКАЗ #{order_id} ВЫПОЛНЕН!**\n📦 Товар: {order[1]}\n\n🎁 **Код активации:**\n`{code}`\n\nСпасибо за покупку!", parse_mode="Markdown")
    else:
        cursor.execute("UPDATE orders SET status='✅ Выполнен' WHERE id=?", (order_id,))
        conn.commit()
        await callback.message.edit_caption(
            caption=f"✅ Товар выдан! Заказ #{order_id} выполнен.",
            reply_markup=admin_menu()
        )
        await bot.send_message(order[0], f"✅ **ВАШ ЗАКАЗ #{order_id} ВЫПОЛНЕН!**\n📦 Товар: {order[1]}\n\nСпасибо за покупку!", parse_mode="Markdown")
    
    await callback.answer()
    await bot.send_message(ADMIN_ID, f"✅ Заказ #{order_id} выполнен.")

# ===== АДМИН КОДЫ ТОВАРОВ =====
@dp.callback_query_handler(lambda c: c.data == "admin_codes")
async def admin_codes(callback: types.CallbackQuery):
    await callback.message.edit_caption(
        caption="🔑 **УПРАВЛЕНИЕ КОДАМИ ТОВАРОВ**\n\nВыберите товар для добавления кодов:",
        reply_markup=admin_codes_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("admin_codes_"))
async def admin_add_codes(callback: types.CallbackQuery):
    product_amount = callback.data.split("_")[2]
    admin_state[callback.from_user.id] = f"add_codes_{product_amount}"
    await callback.message.edit_caption(
        caption=f"🔑 **ДОБАВЛЕНИЕ КОДОВ ДЛЯ {product_amount} UC**\n\nВведите коды (каждый с новой строки):\n\nПример:\n`CODE123456`\n`CODE789012`",
        parse_mode="Markdown"
    )
    await callback.answer()

# ===== АДМИН FAQ =====
@dp.callback_query_handler(lambda c: c.data == "admin_faq")
async def admin_faq(callback: types.CallbackQuery):
    await callback.message.edit_caption(
        caption="❓ **УПРАВЛЕНИЕ FAQ**\n\nВыберите вопрос для редактирования:",
        reply_markup=admin_faq_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("admin_edit_faq_"))
async def admin_edit_faq(callback: types.CallbackQuery):
    faq_id = int(callback.data.split("_")[3])
    admin_state[callback.from_user.id] = f"edit_faq_{faq_id}"
    await callback.message.edit_caption(
        caption="✏️ **Введите новый вопрос и ответ**\n\nФормат: `вопрос | ответ`\n\nПример:\n`Как долго ждать товар? | Обычно от 1 до 5 минут.`",
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_add_faq")
async def admin_add_faq(callback: types.CallbackQuery):
    admin_state[callback.from_user.id] = "add_faq"
    await callback.message.edit_caption(
        caption="➕ **ДОБАВЛЕНИЕ FAQ**\n\nВведите вопрос и ответ\n\nФормат: `вопрос | ответ`\n\nПример:\n`Как оплатить? | Оплата через Telegram Stars.`",
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_give")
async def admin_give_menu(callback: types.CallbackQuery):
    await callback.message.edit_caption(
        caption="🔢 **ВЫДАЧА ТОВАРА**\n\nИспользуйте кнопки в заказах.",
        reply_markup=admin_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_ban")
async def admin_ban_menu(callback: types.CallbackQuery):
    await callback.message.edit_caption(
        caption="🚫 **БАН ПОЛЬЗОВАТЕЛЯ**\n\nВведите: `/ban user_id`",
        reply_markup=admin_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_unban")
async def admin_unban_menu(callback: types.CallbackQuery):
    await callback.message.edit_caption(
        caption="🔓 **РАЗБАН**\n\nВведите: `/unban user_id`",
        reply_markup=admin_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_back")
async def admin_back(callback: types.CallbackQuery):
    await callback.message.edit_caption(
        caption="🔧 **Админ-панель**",
        reply_markup=admin_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_exit")
async def admin_exit(callback: types.CallbackQuery):
    text = "👋 **Добро пожаловать в Akuma UC BOT!**\n\n🟢 Мы работаем 24/7\n\nЗдесь вы можете быстро и удобно купить UC.\n\n👇 Используйте меню ниже:"
    await callback.message.edit_caption(
        caption=text,
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

# ===== АДМИН КОМАНДЫ =====
@dp.message_handler(commands=['ban'])
async def ban_command(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("❌ Формат: `/ban user_id`", parse_mode="Markdown")
        return
    
    try:
        user_id = int(parts[1])
        cursor.execute("INSERT OR IGNORE INTO banned VALUES (?)", (user_id,))
        conn.commit()
        await message.answer(f"✅ Пользователь {user_id} забанен")
    except:
        await message.answer("❌ Ошибка!")

@dp.message_handler(commands=['unban'])
async def unban_command(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("❌ Формат: `/unban user_id`", parse_mode="Markdown")
        return
    
    try:
        user_id = int(parts[1])
        cursor.execute("DELETE FROM banned WHERE user_id=?", (user_id,))
        conn.commit()
        await message.answer(f"✅ Пользователь {user_id} разбанен")
    except:
        await message.answer("❌ Ошибка!")

@dp.message_handler(commands=['ping'])
async def ping(message: types.Message):
    await message.answer("🏓 Bot is alive!")

# ===== ХРАНИЛИЩЕ ДЛЯ СОСТОЯНИЙ =====
admin_state = {}

# ===== ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ =====
@dp.message_handler()
async def handle_admin_text(message: types.Message):
    user_id = str(message.from_user.id)
    
    if user_id not in admin_state:
        return
    
    state = admin_state[user_id]
    
    if state.startswith("add_codes_"):
        product_amount = state.split("_")[2]
        codes_list = message.text.strip().split("\n")
        added = 0
        for code in codes_list:
            if code.strip():
                add_product_code(product_amount, code.strip())
                added += 1
        await message.answer(f"✅ Добавлено {added} кодов для {product_amount} UC")
        del admin_state[user_id]
        await message.answer("🔑 Управление кодами:", reply_markup=admin_codes_menu())
        return
    
    if state.startswith("edit_faq_"):
        faq_id = int(state.split("_")[2])
        parts = message.text.split("|")
        if len(parts) == 2:
            question = parts[0].strip()
            answer = parts[1].strip()
            cursor.execute("UPDATE faq SET question=?, answer=? WHERE id=?", (question, answer, faq_id))
            conn.commit()
            await message.answer("✅ FAQ обновлён!")
        else:
            await message.answer("❌ Неверный формат! Используйте: `вопрос | ответ`")
        del admin_state[user_id]
        await message.answer("❓ Управление FAQ:", reply_markup=admin_faq_menu())
        return
    
    if state == "add_faq":
        parts = message.text.split("|")
        if len(parts) == 2:
            question = parts[0].strip()
            answer = parts[1].strip()
            cursor.execute("INSERT INTO faq (question, answer) VALUES (?, ?)", (question, answer))
            conn.commit()
            await message.answer("✅ FAQ добавлен!")
        else:
            await message.answer("❌ Неверный формат! Используйте: `вопрос | ответ`")
        del admin_state[user_id]
        await message.answer("❓ Управление FAQ:", reply_markup=admin_faq_menu())
        return

@dp.message_handler(commands=['ping'])
async def ping(message: types.Message):
    await message.answer("🏓 Bot is alive!")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
