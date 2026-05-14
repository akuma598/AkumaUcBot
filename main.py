import os
import logging
import sqlite3
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
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
        ("❓ Как оплатить заказ?", "Оплата происходит переводом на карту. После оплаты нажмите «Я оплатил» в боте."),
        ("⏱️ Как быстро приходит товар?", "Обычно в течение 5-15 минут после подтверждения оплаты."),
        ("🆘 Не пришёл товар. Что делать?", "Напишите в поддержку через кнопку «Поддержка» в главном меню. Укажите номер заказа."),
        ("🔄 Можно вернуть деньги?", "Возврат средств возможен в течение 15 минут после оплаты, если товар не был выдан."),
        ("📞 Как связаться с админом?", "Нажмите кнопку «Поддержка» в главном меню или напишите @aakumma")
    ]
    for q, a in default_faq:
        cursor.execute("INSERT INTO faq (question, answer) VALUES (?, ?)", (q, a))
    conn.commit()

conn.commit()

WELCOME_IMAGE = "AgACAgIAAxkBAAEpEj5qAAF14VBLMN24S1ngXPeedYLmlrcAAmEYaxs8bQFIsoUcN-o04FMBAAMCAANtAAM7BA"

# ===== КЛАВИАТУРЫ =====
def main_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("💰 Купить UC", callback_data="buy_uc"),
        InlineKeyboardButton("🎉 Купить ПП", callback_data="buy_pp"),
        InlineKeyboardButton("📦 Подписки Prime", callback_data="buy_prime"),
        InlineKeyboardButton("👗 X-костюмы", callback_data="buy_costumes"),
        InlineKeyboardButton("📦 Мои заказы", callback_data="my_orders"),
        InlineKeyboardButton("❓ FAQ", callback_data="show_faq"),
        InlineKeyboardButton("⭐ Отзывы", url="https://t.me/your_reviews"),
        InlineKeyboardButton("🔗 Поддержка", url="https://t.me/your_support")
    )
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
        status_emoji = "✅" if order[6] == "✅ Выполнен" else "⏳"
        kb.add(InlineKeyboardButton(
            f"{status_emoji} #{order[0]} | {order[1]} | {order[3]}₽",
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

def user_orders_keyboard(orders_list):
    kb = InlineKeyboardMarkup(row_width=1)
    for o in orders_list:
        status_emoji = "✅" if o[4] == "✅ Выполнен" else "⏳"
        kb.add(InlineKeyboardButton(
            f"{status_emoji} #{o[0]} | {o[1]} | {o[3]}₽",
            callback_data=f"user_order_{o[0]}"
        ))
    kb.add(InlineKeyboardButton("🔙 Назад", callback_data="back"))
    return kb

# ===== ФУНКЦИИ ДЛЯ КОДОВ =====
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

async def is_banned(user_id):
    cursor.execute("SELECT * FROM banned WHERE user_id=?", (user_id,))
    return cursor.fetchone() is not None

# ===== ОБРАБОТЧИКИ =====
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    if await is_banned(message.from_user.id):
        await message.answer("❌ Вы забанены")
        return
    
    text = "👋 **Добро пожаловать в магазин Akuma UC BOT!**\n\n🟢 Мы работаем 24/7\n\n👇 Используйте меню ниже для навигации:"
    
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

# ===== ПОКУПКА ТОВАРОВ =====
@dp.callback_query_handler(lambda c: c.data == "buy_uc")
async def buy_uc(callback: types.CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("❌ Вы забанены", show_alert=True)
        return
    
    await callback.message.answer(
        "💰 **Выберите количество UC:**\n\n"
        "60 UC — 87₽\n"
        "120 UC — 152₽\n"
        "180 UC — 223₽\n"
        "240 UC — 293₽\n"
        "325 UC — 387₽\n"
        "385 UC — 434₽\n"
        "445 UC — 482₽\n"
        "660 UC — 756₽\n"
        "720 UC — 771₽\n"
        "985 UC — 1049₽\n"
        "1320 UC — 1401₽\n"
        "1800 UC — 1891₽\n"
        "3850 UC — 3753₽\n"
        "8100 UC — 7243₽\n"
        "9900 UC — 9790₽\n\n"
        "Напишите номер заказа в формате:\n"
        "`Купить 60 UC` или `Купить 325 UC`",
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "buy_pp")
async def buy_pp(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "🎉 **Популярность (ПП)**\n\n"
        "10 000 ПП — 152₽\n"
        "20 000 ПП — 289₽\n"
        "30 000 ПП — 424₽\n"
        "40 000 ПП — 561₽\n"
        "50 000 ПП — 696₽\n"
        "60 000 ПП — 833₽\n\n"
        "Напишите: `Купить 10000 ПП`",
        parse_mode="Markdown"
    )

@dp.callback_query_handler(lambda c: c.data == "buy_prime")
async def buy_prime(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "📦 **Prime подписки**\n\n"
        "Prime (1 месяц) — 125₽\n"
        "Prime (3 месяца) — 318₽\n"
        "Prime (6 месяцев) — 550₽\n"
        "Prime (12 месяцев) — 1027₽\n\n"
        "Напишите: `Купить Prime 1 месяц`",
        parse_mode="Markdown"
    )

@dp.callback_query_handler(lambda c: c.data == "buy_costumes")
async def buy_costumes(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "👗 **X-костюмы**\n\n"
        "🐦‍⬛ Ворон — 4500₽\n"
        "🔥 Феникс — 4500₽\n\n"
        "Напишите: `Купить Ворон`",
        parse_mode="Markdown"
    )

@dp.callback_query_handler(lambda c: c.data == "my_orders")
async def my_orders(callback: types.CallbackQuery):
    cursor.execute("SELECT id, product_name, price_rub, status, created_at FROM orders WHERE user_id=? ORDER BY id DESC", (callback.from_user.id,))
    orders_list = cursor.fetchall()
    
    if not orders_list:
        await callback.answer("❌ У вас нет заказов", show_alert=True)
        return
    
    text = "📦 **Ваши заказы:**\n\n"
    for o in orders_list:
        text += f"🆔 #{o[0]} | {o[1]} | {o[2]}₽ | {o[3]}\n📅 {o[4]}\n\n"
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "show_faq")
async def show_faq(callback: types.CallbackQuery):
    cursor.execute("SELECT question, answer FROM faq")
    faq_list = cursor.fetchall()
    
    text = "❓ **ЧАСТО ЗАДАВАЕМЫЕ ВОПРОСЫ**\n\n"
    for q, a in faq_list:
        text += f"{q}\n{a}\n\n"
    
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "back")
async def back(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.answer()

# ===== ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ (ЗАКАЗЫ) =====
@dp.message_handler()
async def handle_order(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "нет"
    first_name = message.from_user.first_name or "Пользователь"
    text = message.text.lower()
    
    # Парсим заказ
    if text.startswith("купить"):
        parts = text.split()
        if len(parts) >= 2:
            product_name = " ".join(parts[1:])
            
            # Цены на товары
            prices = {
                "60 uc": 87, "120 uc": 152, "180 uc": 223, "240 uc": 293,
                "325 uc": 387, "385 uc": 434, "445 uc": 482, "660 uc": 756,
                "720 uc": 771, "985 uc": 1049, "1320 uc": 1401, "1800 uc": 1891,
                "3850 uc": 3753, "8100 uc": 7243, "9900 uc": 9790,
                "10000 пп": 152, "20000 пп": 289, "30000 пп": 424,
                "40000 пп": 561, "50000 пп": 696, "60000 пп": 833,
                "prime 1 месяц": 125, "prime 3 месяца": 318,
                "prime 6 месяцев": 550, "prime 12 месяцев": 1027,
                "ворон": 4500, "феникс": 4500
            }
            
            price = None
            for key, val in prices.items():
                if key in product_name:
                    price = val
                    product_name = key
                    break
            
            if price:
                cursor.execute("""
                    INSERT INTO orders (user_id, username, first_name, product_name, price_rub, status, category, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (user_id, username, first_name, product_name, price, "⏳ Ожидает оплаты", "UC", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
                order_id = cursor.lastrowid
                
                # Уведомление админу
                user_link = f"tg://user?id={user_id}"
                admin_text = f"🆕 **НОВЫЙ ЗАКАЗ #{order_id}**\n👤 [{first_name}]({user_link})\n📦 {product_name}\n💰 {price}₽"
                await bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown")
                
                await message.answer(
                    f"✅ **ЗАКАЗ #{order_id} ПРИНЯТ!**\n\n"
                    f"📦 Товар: {product_name}\n"
                    f"💰 Сумма: {price}₽\n\n"
                    f"💳 **Реквизиты для оплаты:**\n"
                    f"Карта: **** **** **** 1234\n\n"
                    f"📌 После оплаты напишите сюда номер заказа: #{order_id}",
                    parse_mode="Markdown"
                )
            else:
                await message.answer("❌ Товар не найден. Напишите `Купить 60 UC`", parse_mode="Markdown")

# ===== АДМИН КОМАНДЫ =====
@dp.message_handler(commands=['give'])
async def give_command(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("❌ Формат: `/give order_id код`", parse_mode="Markdown")
        return
    
    try:
        order_id = int(parts[1])
        code = parts[2]
        
        cursor.execute("UPDATE orders SET status='✅ Выполнен' WHERE id=?", (order_id,))
        conn.commit()
        
        cursor.execute("SELECT user_id FROM orders WHERE id=?", (order_id,))
        user = cursor.fetchone()
        if user:
            await bot.send_message(user[0], f"✅ **ВАШ ЗАКАЗ #{order_id} ВЫПОЛНЕН!**\n\n🎁 Код: `{code}`", parse_mode="Markdown")
        
        await message.answer(f"✅ Заказ #{order_id} выполнен, код отправлен")
    except:
        await message.answer("❌ Ошибка!")

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

@dp.message_handler(commands=['stats'])
async def stats_command(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    cursor.execute("SELECT COUNT(*), SUM(price_rub) FROM orders WHERE status='✅ Выполнен'")
    completed = cursor.fetchone()
    
    cursor.execute("SELECT COUNT(*) FROM orders")
    total = cursor.fetchone()
    
    await message.answer(
        f"📊 **СТАТИСТИКА**\n\n"
        f"✅ Выполнено заказов: {completed[0] or 0}\n"
        f"💰 Выручка: {completed[1] or 0}₽\n\n"
        f"📦 Всего заказов: {total[0] or 0}",
        parse_mode="Markdown"
    )

@dp.message_handler(commands=['orders'])
async def orders_command(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    cursor.execute("SELECT id, product_name, price_rub, status, username, first_name FROM orders ORDER BY id DESC LIMIT 10")
    orders = cursor.fetchall()
    
    if not orders:
        await message.answer("📭 Нет заказов")
        return
    
    text = "📋 **ПОСЛЕДНИЕ ЗАКАЗЫ:**\n\n"
    for o in orders:
        status_emoji = "✅" if o[3] == "✅ Выполнен" else "⏳"
        text += f"{status_emoji} #{o[0]} | {o[1]} | {o[2]}₽ | {o[4] or o[5]}\n"
    
    await message.answer(text, parse_mode="Markdown")

@dp.message_handler(commands=['ping'])
async def ping(message: types.Message):
    await message.answer("🏓 Bot is alive!")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
