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

# ===== БАЗА ДАННЫХ =====
conn = sqlite3.connect("shop.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    uc_amount TEXT,
    price TEXT,
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
conn.commit()

# ===== КАРТИНКА ДЛЯ ПРИВЕТСТВИЯ =====
WELCOME_IMAGE = "AgACAgIAAxkBAAEpEj5qAAF14VBLMN24S1ngXPeedYLmlrcAAmEYaxs8bQFIsoUcN-o04FMBAAMCAANtAAM7BA"

async def is_banned(user_id):
    cursor.execute("SELECT * FROM banned WHERE user_id=?", (user_id,))
    return cursor.fetchone() is not None

# ===== ГЛАВНОЕ МЕНЮ (с картинкой) =====
def main_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("💰 Купить UC", callback_data="buy_uc"),
        InlineKeyboardButton("🎮 METRO ROYALE", callback_data="metro_royale"),
        InlineKeyboardButton("📦 Мои заказы", callback_data="my_orders"),
        InlineKeyboardButton("⭐ Отзывы", url="https://t.me/your_reviews"),
        InlineKeyboardButton("🔗 Поддержка", url="https://t.me/your_support")
    )
    return kb

# ===== МЕНЮ UC =====
def uc_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("60 UC — 1$", callback_data="buy_60_1"),
        InlineKeyboardButton("120 UC — 2$", callback_data="buy_120_2"),
        InlineKeyboardButton("180 UC — 3$", callback_data="buy_180_3"),
        InlineKeyboardButton("240 UC — 4$", callback_data="buy_240_4"),
        InlineKeyboardButton("325 UC — 5$", callback_data="buy_325_5"),
        InlineKeyboardButton("385 UC — 6$", callback_data="buy_385_6"),
        InlineKeyboardButton("445 UC — 7$", callback_data="buy_445_7"),
        InlineKeyboardButton("660 UC — 8$", callback_data="buy_660_8"),
        InlineKeyboardButton("720 UC — 9$", callback_data="buy_720_9"),
        InlineKeyboardButton("985 UC — 12$", callback_data="buy_985_12"),
        InlineKeyboardButton("1320 UC — 16$", callback_data="buy_1320_16"),
        InlineKeyboardButton("1800 UC — 20$", callback_data="buy_1800_20"),
        InlineKeyboardButton("1920 UC — 22$", callback_data="buy_1920_22"),
        InlineKeyboardButton("2125 UC — 24$", callback_data="buy_2125_24"),
        InlineKeyboardButton("2460 UC — 28$", callback_data="buy_2460_28"),
        InlineKeyboardButton("3850 UC — 40$", callback_data="buy_3850_40"),
        InlineKeyboardButton("4510 UC — 48$", callback_data="buy_4510_48"),
        InlineKeyboardButton("5650 UC — 60$", callback_data="buy_5650_60"),
        InlineKeyboardButton("8100 UC — 80$", callback_data="buy_8100_80"),
        InlineKeyboardButton("9900 UC — 112$", callback_data="buy_9900_112"),
        InlineKeyboardButton("11950 UC — 120$", callback_data="buy_11950_120"),
        InlineKeyboardButton("16200 UC — 160$", callback_data="buy_16200_160"),
        InlineKeyboardButton("24300 UC — 240$", callback_data="buy_24300_240"),
        InlineKeyboardButton("32400 UC — 320$", callback_data="buy_32400_320"),
        InlineKeyboardButton("40500 UC — 400$", callback_data="buy_40500_400"),
        InlineKeyboardButton("81000 UC — 800$", callback_data="buy_81000_800"),
        InlineKeyboardButton("⬅️ Назад", callback_data="back")
    )
    return kb

# ===== МЕНЮ METRO ROYALE =====
def metro_menu():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("🔫 КАЛАШНИКОВ + 5000 ДЕНЕГ", callback_data="metro_ak47"),
        InlineKeyboardButton("🎯 M416 + 10000 ДЕНЕГ", callback_data="metro_m416"),
        InlineKeyboardButton("💎 ЭЛИТНЫЙ НАБОР", callback_data="metro_elite"),
        InlineKeyboardButton("👑 VIP НАБОР", callback_data="metro_vip"),
        InlineKeyboardButton("⬅️ Назад", callback_data="back")
    )
    return kb

def metro_buy_keyboard(item_name, price):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton(f"💰 Купить за {price}$", callback_data=f"buy_metro_{item_name}_{price}"),
        InlineKeyboardButton("⬅️ Назад", callback_data="metro_royale")
    )
    return kb

# ===== АДМИН МЕНЮ =====
def admin_menu():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
        InlineKeyboardButton("📦 Все заказы", callback_data="admin_orders"),
        InlineKeyboardButton("✅ Выдача товара", callback_data="admin_give"),
        InlineKeyboardButton("🚫 Бан пользователя", callback_data="admin_ban"),
        InlineKeyboardButton("🔓 Разбан пользователя", callback_data="admin_unban"),
        InlineKeyboardButton("🔙 Выйти", callback_data="admin_exit")
    )
    return kb

def orders_keyboard(orders_list, page=0):
    kb = InlineKeyboardMarkup(row_width=1)
    start = page * 5
    end = start + 5
    for order in orders_list[start:end]:
        status_emoji = "✅" if order[4] == "Выполнен" else "⏳"
        kb.add(InlineKeyboardButton(
            f"{status_emoji} #{order[0]} | {order[1]} | {order[3]}$ | {order[5]}",
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
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ Выдать товар", callback_data=f"give_{order_id}"),
        InlineKeyboardButton("🔙 Назад", callback_data="admin_back")
    )
    return kb

# ===== ОБРАБОТЧИКИ =====
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    if await is_banned(message.from_user.id):
        await message.answer("❌ Вы забанены в этом магазине.")
        return
    
    text = "👋 **GADZHIK SERVICE**\n\nДобро пожаловать, мы работаем 24/7\n\nЗдесь вы можете быстро и удобно пополнить баланс и купить товары для популярных игр.\n\n👇 Используйте меню ниже:"
    
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
        caption="💰 **ВЫБЕРИТЕ КОЛИЧЕСТВО UC:**\n\nНажмите на нужный пакет:",
        reply_markup=uc_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "metro_royale")
async def show_metro(callback: types.CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("❌ Вы забанены", show_alert=True)
        return
    await callback.message.edit_caption(
        caption="🎮 **METRO ROYALE**\n\n💰 **ДОНАТ НА ОРУЖИЕ И ДЕНЬГИ**\n\nВыберите товар:",
        reply_markup=metro_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "back")
async def back(callback: types.CallbackQuery):
    text = "👋 **GADZHIK SERVICE**\n\nДобро пожаловать, мы работаем 24/7\n\nЗдесь вы можете быстро и удобно пополнить баланс и купить товары для популярных игр.\n\n👇 Используйте меню ниже:"
    await callback.message.edit_caption(
        caption=text,
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("metro_"))
async def metro_item(callback: types.CallbackQuery):
    items = {
        "metro_ak47": {"name": "🔫 КАЛАШНИКОВ + 5000 ДЕНЕГ", "price": 5},
        "metro_m416": {"name": "🎯 M416 + 10000 ДЕНЕГ", "price": 8},
        "metro_elite": {"name": "💎 ЭЛИТНЫЙ НАБОР", "price": 15},
        "metro_vip": {"name": "👑 VIP НАБОР", "price": 30}
    }
    
    if callback.data in items:
        item = items[callback.data]
        await callback.message.edit_caption(
            caption=f"🎮 **{item['name']}**\n\n💰 Цена: {item['price']}$\n\nНажмите «Купить» для оформления заказа:",
            reply_markup=metro_buy_keyboard(item['name'], item['price']),
            parse_mode="Markdown"
        )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("buy_metro_"))
async def buy_metro(callback: types.CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("❌ Вы забанены", show_alert=True)
        return
    
    parts = callback.data.split("_")
    item_name = "_".join(parts[2:-1])
    price = parts[-1]
    
    cursor.execute("""
        INSERT INTO orders (user_id, username, uc_amount, price, status, category, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        callback.from_user.id,
        callback.from_user.username or "Аноним",
        item_name,
        price,
        "⏳ Ожидание",
        "METRO ROYALE",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()
    order_id = cursor.lastrowid
    
    await callback.message.edit_caption(
        caption=f"✅ **ЗАКАЗ #{order_id} СОЗДАН!**\n\n"
        f"🎮 Товар: {item_name}\n"
        f"💰 Цена: {price}$\n\n"
        f"💳 **РЕКВИЗИТЫ ДЛЯ ОПЛАТЫ:**\n"
        f"Карта: **** **** **** 1234\n\n"
        f"📌 После оплаты напишите @admin с номером заказа",
        reply_markup=None,
        parse_mode="Markdown"
    )
    await callback.answer()
    
    await bot.send_message(ADMIN_ID, f"🆕 **НОВЫЙ ЗАКАЗ #{order_id}**\n👤 @{callback.from_user.username or 'Аноним'}\n🎮 {item_name}\n💰 {price}$")

@dp.callback_query_handler(lambda c: c.data.startswith("buy_"))
async def buy_uc(callback: types.CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("❌ Вы забанены", show_alert=True)
        return
    
    parts = callback.data.split("_")
    amount = parts[1]
    price = parts[2]
    
    cursor.execute("""
        INSERT INTO orders (user_id, username, uc_amount, price, status, category, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        callback.from_user.id,
        callback.from_user.username or "Аноним",
        amount,
        price,
        "⏳ Ожидание",
        "UC",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()
    order_id = cursor.lastrowid
    
    await callback.message.edit_caption(
        caption=f"✅ **ЗАКАЗ #{order_id} СОЗДАН!**\n\n"
        f"📦 UC: {amount}\n"
        f"💰 Цена: {price}$\n\n"
        f"💳 **РЕКВИЗИТЫ ДЛЯ ОПЛАТЫ:**\n"
        f"Карта: **** **** **** 1234\n\n"
        f"📌 После оплаты напишите @admin с номером заказа",
        reply_markup=None,
        parse_mode="Markdown"
    )
    await callback.answer()
    
    await bot.send_message(ADMIN_ID, f"🆕 **НОВЫЙ ЗАКАЗ #{order_id}**\n👤 @{callback.from_user.username or 'Аноним'}\n📦 {amount} UC\n💰 {price}$")

@dp.callback_query_handler(lambda c: c.data == "my_orders")
async def my_orders(callback: types.CallbackQuery):
    cursor.execute("SELECT id, uc_amount, price, status, category, created_at FROM orders WHERE user_id=? ORDER BY id DESC", (callback.from_user.id,))
    orders = cursor.fetchall()
    
    if not orders:
        await callback.answer("❌ У вас нет заказов", show_alert=True)
        return
    
    text = "📦 **Ваши заказы:**\n\n"
    for o in orders:
        text += f"🆔 #{o[0]} | {o[1]} | {o[2]}$ | {o[3]}\n🎮 {o[4]} | 📅 {o[5]}\n\n"
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

# ===== АДМИН КНОПКИ =====
@dp.callback_query_handler(lambda c: c.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    cursor.execute("SELECT COUNT(*), SUM(price) FROM orders WHERE status='Выполнен'")
    completed = cursor.fetchone()
    
    cursor.execute("SELECT COUNT(*), SUM(price) FROM orders")
    total = cursor.fetchone()
    
    script = (
        f"📊 **СТАТИСТИКА**\n\n"
        f"✅ Выполнено заказов: {completed[0] or 0}\n"
        f"💰 Выручка: ${completed[1] or 0}\n\n"
        f"📦 Всего заказов: {total[0] or 0}\n"
        f"💸 Общая сумма: ${total[1] or 0}"
    )
    await callback.message.edit_caption(caption=script, reply_markup=admin_menu(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_orders")
async def admin_orders_list(callback: types.CallbackQuery):
    cursor.execute("SELECT id, uc_amount, price, status, category, username FROM orders ORDER BY id DESC")
    orders = cursor.fetchall()
    
    if not orders:
        await callback.answer("❌ Нет заказов", show_alert=True)
        return
    
    await callback.message.edit_caption(
        caption="📦 **СПИСОК ЗАКАЗОВ**\n\nВыберите заказ для выдачи:",
        reply_markup=orders_keyboard(orders, 0),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("orders_page_"))
async def orders_page(callback: types.CallbackQuery):
    page = int(callback.data.split("_")[2])
    cursor.execute("SELECT id, uc_amount, price, status, category, username FROM orders ORDER BY id DESC")
    orders = cursor.fetchall()
    
    await callback.message.edit_caption(
        caption="📦 **СПИСОК ЗАКАЗОВ**\n\nВыберите заказ для выдачи:",
        reply_markup=orders_keyboard(orders, page),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("order_"))
async def view_order(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[1])
    cursor.execute("SELECT id, user_id, username, uc_amount, price, status, category, created_at FROM orders WHERE id=?", (order_id,))
    order = cursor.fetchone()
    
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    text = (
        f"📋 **ЗАКАЗ #{order[0]}**\n"
        f"👤 Пользователь: @{order[2] or 'Аноним'}\n"
        f"🆔 ID: {order[1]}\n"
        f"🎮 Категория: {order[6]}\n"
        f"📦 Товар: {order[3]}\n"
        f"💰 Цена: {order[4]}$\n"
        f"📅 Дата: {order[7]}\n"
        f"📌 Статус: {order[5]}"
    )
    await callback.message.edit_caption(caption=text, reply_markup=give_keyboard(order_id), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("give_"))
async def give_item(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[1])
    
    cursor.execute("SELECT user_id, uc_amount FROM orders WHERE id=?", (order_id,))
    order = cursor.fetchone()
    
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    cursor.execute("UPDATE orders SET status='✅ Выполнен' WHERE id=?", (order_id,))
    conn.commit()
    
    await callback.message.edit_caption(
        caption=f"✅ Товар выдан! Заказ #{order_id} выполнен.",
        reply_markup=admin_menu()
    )
    await callback.answer()
    
    await bot.send_message(order[0], f"✅ **ВАШ ЗАКАЗ #{order_id} ВЫПОЛНЕН!**\n📦 Товар: {order[1]}\n\nСпасибо за покупку!", parse_mode="Markdown")
    await bot.send_message(ADMIN_ID, f"✅ Заказ #{order_id} выполнен. Товар выдан.")

@dp.callback_query_handler(lambda c: c.data == "admin_give")
async def admin_give_menu(callback: types.CallbackQuery):
    await callback.message.edit_caption(
        caption="🔢 **ВЫДАЧА ТОВАРА**\n\nВведите команду:\n`/give user_id товар`\n\nПример: `/give 123456789 КАЛАШНИКОВ+5000ДЕНЕГ`",
        reply_markup=admin_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_ban")
async def admin_ban_menu(callback: types.CallbackQuery):
    await callback.message.edit_caption(
        caption="🚫 **БАН ПОЛЬЗОВАТЕЛЯ**\n\nВведите команду:\n`/ban user_id`\n\nПример: `/ban 123456789`",
        reply_markup=admin_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_unban")
async def admin_unban_menu(callback: types.CallbackQuery):
    await callback.message.edit_caption(
        caption="🔓 **РАЗБАН ПОЛЬЗОВАТЕЛЯ**\n\nВведите команду:\n`/unban user_id`\n\nПример: `/unban 123456789`",
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
    text = "👋 **GADZHIK SERVICE**\n\nДобро пожаловать, мы работаем 24/7\n\nЗдесь вы можете быстро и удобно пополнить баланс и купить товары для популярных игр.\n\n👇 Используйте меню ниже:"
    await callback.message.edit_caption(
        caption=text,
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

# ===== АДМИН КОМАНДЫ =====
@dp.message_handler(commands=['give'])
async def give_command(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("❌ Формат: `/give user_id товар`", parse_mode="Markdown")
        return
    
    try:
        user_id = int(parts[1])
        item = parts[2]
        
        await bot.send_message(user_id, f"✅ **ВАМ ВЫДАН ТОВАР:**\n📦 {item}\n\nСпасибо что с нами!", parse_mode="Markdown")
        await message.answer(f"✅ Выдан товар пользователю {user_id}")
    except:
        await message.answer("❌ Ошибка! Проверьте ID пользователя.")

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

# ===== ЗАПУСК =====
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
