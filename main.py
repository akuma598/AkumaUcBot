import os
import json
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils import executor
from flask import Flask
from threading import Thread
from datetime import datetime

TOKEN = os.environ.get("TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

ADMIN_PASSWORD = "14022014"
ADMIN_ID = 8504217011

user_data = {}
orders = []
reviews = []
support_requests = []

UC_PRODUCTS = {
    "uc_60": {"amount": 60, "price": 72, "active": True},
    "uc_120": {"amount": 120, "price": 142, "active": True},
    "uc_180": {"amount": 180, "price": 213, "active": True},
    "uc_240": {"amount": 240, "price": 283, "active": True},
    "uc_325": {"amount": 325, "price": 353, "active": True},
    "uc_385": {"amount": 385, "price": 424, "active": True},
    "uc_445": {"amount": 445, "price": 494, "active": True},
    "uc_660": {"amount": 660, "price": 705, "active": True},
    "uc_720": {"amount": 720, "price": 775, "active": True},
    "uc_985": {"amount": 985, "price": 1057, "active": True},
    "uc_1320": {"amount": 1320, "price": 1409, "active": True},
    "uc_1800": {"amount": 1800, "price": 1760, "active": True},
    "uc_1920": {"amount": 1920, "price": 1901, "active": True},
    "uc_2125": {"amount": 2125, "price": 2112, "active": True},
    "uc_2460": {"amount": 2460, "price": 2464, "active": True},
    "uc_3850": {"amount": 3850, "price": 3479, "active": True},
    "uc_4510": {"amount": 4510, "price": 4183, "active": True},
    "uc_5650": {"amount": 5650, "price": 5238, "active": True},
    "uc_8100": {"amount": 8100, "price": 6957, "active": True},
    "uc_9900": {"amount": 9900, "price": 9790, "active": True},
    "uc_11950": {"amount": 11950, "price": 10434, "active": True},
    "uc_16200": {"amount": 16200, "price": 13912, "active": True},
    "uc_24300": {"amount": 24300, "price": 20867, "active": True},
    "uc_32400": {"amount": 32400, "price": 27822, "active": True},
    "uc_40500": {"amount": 40500, "price": 34777, "active": True},
    "uc_81000": {"amount": 81000, "price": 69552, "active": True}
}

BIG_UC_PRODUCTS = {
    "uc_8100": {"amount": 8100, "price": 6957, "active": True},
    "uc_9900": {"amount": 9900, "price": 9790, "active": True},
    "uc_11950": {"amount": 11950, "price": 10434, "active": True},
    "uc_16200": {"amount": 16200, "price": 13912, "active": True},
    "uc_24300": {"amount": 24300, "price": 20867, "active": True},
    "uc_32400": {"amount": 32400, "price": 27822, "active": True},
    "uc_40500": {"amount": 40500, "price": 34777, "active": True},
    "uc_81000": {"amount": 81000, "price": 69552, "active": True}
}

def is_admin(user_id):
    return str(user_id) == str(ADMIN_ID)

# ===== КАРТИНКА (ВАША) =====
WELCOME_IMAGE = "AgACAgIAAxkBAAEpEj5qAAF14VBLMN24S1ngXPeedYLmlrcAAmEYaxs8bQFIsoUcN-o04FMBAAMCAANtAAM7BA"

def main_menu():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("🛒 КУПИТЬ UC / ПП / PRIME / НАБОРЫ", callback_data="buy_menu"),
        InlineKeyboardButton("⭐ ОТЗЫВЫ", callback_data="show_reviews"),
        InlineKeyboardButton("💬 ТЕХ-ПОДДЕРЖКА", callback_data="support"),
        InlineKeyboardButton("🌐 САЙТ [БЕЗ VPN]", url="https://your-site.com"),
        InlineKeyboardButton("🤝 ОТКРЫТЫ К СОТРУДНИЧЕСТВУ", callback_data="cooperation")
    )
    return keyboard

def buy_menu():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("💰 Купить UC [По айди]", callback_data="buy_uc_by_id"),
        InlineKeyboardButton("🔥 По айди [От 8100 Uc+]", callback_data="buy_uc_big"),
        InlineKeyboardButton("📱 Купить UC [По входу]", callback_data="buy_uc_by_login"),
        InlineKeyboardButton("🎫 ПОПУЛЯРНОСТЬ / БИЛЕТЫ ДОМА", callback_data="popularity"),
        InlineKeyboardButton("🟢 PRIME / PRIME+ / НАБОРЫ", callback_data="prime"),
        InlineKeyboardButton("🟡 APOLLO / X-КОСТЮМЫ", callback_data="apollo"),
        InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_menu")
    )
    return keyboard

def uc_selection_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    items = list(UC_PRODUCTS.items())
    for i in range(0, len(items), 2):
        row = []
        pid1, p1 = items[i]
        row.append(InlineKeyboardButton(f"{p1['amount']} - {p1['price']}₽", callback_data=f"select_uc_{pid1}"))
        if i + 1 < len(items):
            pid2, p2 = items[i + 1]
            row.append(InlineKeyboardButton(f"{p2['amount']} - {p2['price']}₽", callback_data=f"select_uc_{pid2}"))
        keyboard.row(*row)
    keyboard.add(InlineKeyboardButton("🔙 НАЗАД", callback_data="buy_menu"))
    return keyboard

def big_uc_selection_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    items = list(BIG_UC_PRODUCTS.items())
    for i in range(0, len(items), 2):
        row = []
        pid1, p1 = items[i]
        row.append(InlineKeyboardButton(f"{p1['amount']} - {p1['price']}₽", callback_data=f"select_uc_big_{pid1}"))
        if i + 1 < len(items):
            pid2, p2 = items[i + 1]
            row.append(InlineKeyboardButton(f"{p2['amount']} - {p2['price']}₽", callback_data=f"select_uc_big_{pid2}"))
        keyboard.row(*row)
    keyboard.add(InlineKeyboardButton("🔙 НАЗАД", callback_data="buy_menu"))
    return keyboard

def reviews_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=5)
    keyboard.add(
        InlineKeyboardButton("⭐ 1", callback_data="review_1"),
        InlineKeyboardButton("⭐⭐ 2", callback_data="review_2"),
        InlineKeyboardButton("⭐⭐⭐ 3", callback_data="review_3"),
        InlineKeyboardButton("⭐⭐⭐⭐ 4", callback_data="review_4"),
        InlineKeyboardButton("⭐⭐⭐⭐⭐ 5", callback_data="review_5")
    )
    keyboard.add(InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_menu"))
    return keyboard

def support_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(InlineKeyboardButton("✖️ ЗАКРЫТЬ ЧАТ", callback_data="close_support"))
    keyboard.add(InlineKeyboardButton("🔙 ГЛАВНОЕ МЕНЮ", callback_data="back_to_menu"))
    return keyboard

def admin_menu():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("📦 Управление UC", callback_data="admin_uc"),
        InlineKeyboardButton("🛒 Заказы", callback_data="admin_orders"),
        InlineKeyboardButton("⏳ Ожидают оплаты", callback_data="admin_pending"),
        InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
        InlineKeyboardButton("⭐ Отзывы", callback_data="admin_reviews"),
        InlineKeyboardButton("🔙 Выйти", callback_data="admin_exit")
    )
    return keyboard

def admin_uc_menu():
    keyboard = InlineKeyboardMarkup(row_width=1)
    for pid, p in UC_PRODUCTS.items():
        status = "✅" if p["active"] else "❌"
        keyboard.add(InlineKeyboardButton(f"{status} {p['amount']} UC — {p['price']}₽", callback_data=f"admin_edit_uc_{pid}"))
    keyboard.add(InlineKeyboardButton("➕ Добавить UC", callback_data="admin_add_uc"))
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="admin_back"))
    return keyboard

last_message_id = {}
admin_state = {}

async def update_message(chat_id, user_id, text, reply_markup=None, parse_mode=None):
    msg_id = last_message_id.get(user_id)
    try:
        if msg_id:
            await bot.delete_message(chat_id, msg_id)
    except:
        pass
    msg = await bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
    last_message_id[user_id] = msg.message_id

async def update_photo(chat_id, user_id, photo, caption, reply_markup=None):
    msg_id = last_message_id.get(user_id)
    try:
        if msg_id:
            await bot.delete_message(chat_id, msg_id)
    except:
        pass
    msg = await bot.send_photo(chat_id, photo=photo, caption=caption, reply_markup=reply_markup)
    last_message_id[user_id] = msg.message_id

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    user_id = str(message.from_user.id)
    text = (
        "**GADZHIK SERVICE**\n"
        "**ТОВАРЫ**\n"
        "**gadzhik service**\n\n"
        "Добро пожаловать, мы работаем 24/7\n\n"
        "Здесь вы можете быстро и удобно пополнить баланс и купить товары, и подписки для популярных игр.\n\n"
        "---"
    )
    await update_photo(message.chat.id, user_id, WELCOME_IMAGE, text, main_menu())

@dp.message_handler(commands=["admin"])
async def admin_login(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    pwd = message.get_args()
    if pwd == ADMIN_PASSWORD:
        await update_message(message.chat.id, str(message.from_user.id), "🔧 **Админ-панель**", admin_menu(), "Markdown")
    else:
        await message.answer("❌ Неверный пароль")

async def ask_pubg_id(chat_id, user_id, uc_amount, uc_price, is_big=False):
    user_data[user_id] = {"uc_amount": uc_amount, "uc_price": uc_price, "is_big": is_big}
    text = "🔹 **Введите ваш Pubg ID начиная с 5.**\n\n(пример: 51867875896)"
    await update_message(chat_id, user_id, text, None, "Markdown")

@dp.callback_query_handler(lambda c: True)
async def handle(callback: types.CallbackQuery):
    data = callback.data
    user_id = str(callback.from_user.id)
    chat_id = callback.message.chat.id
    await bot.answer_callback_query(callback.id)

    if data == "back_to_menu":
        text = (
            "**GADZHIK SERVICE**\n"
            "**ТОВАРЫ**\n"
            "**gadzhik service**\n\n"
            "Добро пожаловать, мы работаем 24/7\n\n"
            "Здесь вы можете быстро и удобно пополнить баланс и купить товары, и подписки для популярных игр.\n\n"
            "---"
        )
        await update_photo(chat_id, user_id, WELCOME_IMAGE, text, main_menu())
    
    elif data == "buy_menu":
        await update_message(chat_id, user_id, "🛍️ **ВЫБЕРИТЕ ТИП ПОКУПКИ:**", buy_menu(), "Markdown")
    
    elif data == "buy_uc_by_id":
        await update_message(chat_id, user_id, "💰 **ВЫБЕРИТЕ КОЛИЧЕСТВО UC:**", uc_selection_keyboard(), "Markdown")
    
    elif data == "buy_uc_big":
        await update_message(chat_id, user_id, "🔥 **ВЫБЕРИТЕ КОЛИЧЕСТВО UC (ОТ 8100):**", big_uc_selection_keyboard(), "Markdown")
    
    elif data.startswith("select_uc_"):
        pid = data.replace("select_uc_", "")
        p = UC_PRODUCTS.get(pid)
        if p and p.get("active", True):
            await ask_pubg_id(chat_id, user_id, p["amount"], p["price"], is_big=False)
    
    elif data.startswith("select_uc_big_"):
        pid = data.replace("select_uc_big_", "")
        p = BIG_UC_PRODUCTS.get(pid)
        if p and p.get("active", True):
            await ask_pubg_id(chat_id, user_id, p["amount"], p["price"], is_big=True)
    
    elif data == "buy_uc_by_login":
        await update_message(chat_id, user_id, "🚧 **РАЗДЕЛ В РАЗРАБОТКЕ**\n\nПокупка по входу скоро появится.", buy_menu(), "Markdown")
    
    elif data == "popularity":
        await update_message(chat_id, user_id, "🎫 **ПОПУЛЯРНОСТЬ / БИЛЕТЫ ДОМА**\n\nСкоро будет доступно!", buy_menu(), "Markdown")
    
    elif data == "prime":
        await update_message(chat_id, user_id, "🟢 **PRIME / PRIME+ / НАБОРЫ**\n\nСкоро будет доступно!", buy_menu(), "Markdown")
    
    elif data == "apollo":
        await update_message(chat_id, user_id, "🟡 **APOLLO / X-КОСТЮМЫ**\n\nСкоро будет доступно!", buy_menu(), "Markdown")
    
    elif data == "cooperation":
        await update_message(chat_id, user_id, "🤝 **СОТРУДНИЧЕСТВО**\n\nПо вопросам сотрудничества: @aakumma", buy_menu(), "Markdown")

    elif data == "show_reviews":
        if not reviews:
            await update_message(chat_id, user_id, "⭐ **ОТЗЫВЫ**\n\nПока нет отзывов. Будьте первым!", reviews_keyboard(), "Markdown")
        else:
            text = "⭐ **ОТЗЫВЫ НАШИХ КЛИЕНТОВ:**\n\n"
            for r in reviews[-10:]:
                stars = "⭐" * r["rating"]
                text += f"{stars} {r['rating']}/5\n{r['text']}\n— {r['user_name']}\n📅 {r['date']}\n\n"
            keyboard = InlineKeyboardMarkup(row_width=1)
            keyboard.add(InlineKeyboardButton("📝 ОСТАВИТЬ ОТЗЫВ", callback_data="leave_review"))
            keyboard.add(InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_menu"))
            await update_message(chat_id, user_id, text, keyboard, "Markdown")
    
    elif data in ["review_1", "review_2", "review_3", "review_4", "review_5"]:
        rating = int(data.replace("review_", ""))
        admin_state[user_id] = f"wait_review_text_{rating}"
        await update_message(chat_id, user_id, f"⭐ Вы выбрали {rating} звёзд.\n\nНапишите текст отзыва:", None)
    
    elif data == "leave_review":
        await update_message(chat_id, user_id, "⭐ **ОЦЕНИТЕ НАШ СЕРВИС:**\n\nНажмите на количество звёзд:", reviews_keyboard(), "Markdown")

    elif data == "support":
        support_requests[user_id] = True
        await update_message(chat_id, user_id, "💬 **ЧАТ ТЕХ-ПОДДЕРЖКИ**\n\nНапишите ваше сообщение. Администратор ответит вам в ближайшее время.", support_keyboard(), "Markdown")
    
    elif data == "close_support":
        support_requests.pop(user_id, None)
        await update_message(chat_id, user_id, "🔚 Чат поддержки закрыт.", main_menu())

    elif data == "admin_uc" and is_admin(user_id):
        await update_message(chat_id, user_id, "📦 **Управление товарами UC:**", admin_uc_menu(), "Markdown")
    
    elif data.startswith("admin_edit_uc_") and is_admin(user_id):
        pid = data.replace("admin_edit_uc_", "")
        p = UC_PRODUCTS.get(pid)
        if p:
            kb = InlineKeyboardMarkup(row_width=2)
            kb.add(InlineKeyboardButton("🔄 Вкл/Выкл", callback_data=f"admin_toggle_uc_{pid}"))
            kb.add(InlineKeyboardButton(f"💰 {p['price']}₽", callback_data=f"admin_price_uc_{pid}"))
            kb.add(InlineKeyboardButton("❌ Удалить", callback_data=f"admin_delete_uc_{pid}"))
            kb.add(InlineKeyboardButton("🔙 Назад", callback_data="admin_uc"))
            status = "✅ Активен" if p["active"] else "❌ Неактивен"
            await update_message(chat_id, user_id, f"📦 **{p['amount']} UC**\n{status}\n💰 {p['price']}₽", kb, "Markdown")
    
    elif data.startswith("admin_toggle_uc_") and is_admin(user_id):
        pid = data.replace("admin_toggle_uc_", "")
        if pid in UC_PRODUCTS:
            UC_PRODUCTS[pid]["active"] = not UC_PRODUCTS[pid]["active"]
            await update_message(chat_id, user_id, f"✅ Товар {'активирован' if UC_PRODUCTS[pid]['active'] else 'деактивирован'}", admin_uc_menu(), "Markdown")
    
    elif data.startswith("admin_price_uc_") and is_admin(user_id):
        pid = data.replace("admin_price_uc_", "")
        admin_state[user_id] = f"wait_price_{pid}"
        await update_message(chat_id, user_id, f"💰 Введите новую цену для {UC_PRODUCTS[pid]['amount']} UC:", None)
    
    elif data.startswith("admin_delete_uc_") and is_admin(user_id):
        pid = data.replace("admin_delete_uc_", "")
        if pid in UC_PRODUCTS:
            del UC_PRODUCTS[pid]
            await update_message(chat_id, user_id, "✅ Товар удалён", admin_uc_menu(), "Markdown")
    
    elif data == "admin_add_uc" and is_admin(user_id):
        admin_state[user_id] = "wait_uc_product"
        await update_message(chat_id, user_id, "➕ **Добавление товара UC**\n\nФормат: `количество|цена`\n\nПример: `5000|4300`", None, "Markdown")
    
    elif data == "admin_orders" and is_admin(user_id):
        if not orders:
            await update_message(chat_id, user_id, "📭 Заказов пока нет", admin_menu(), "Markdown")
        else:
            text = "📋 **СПИСОК ЗАКАЗОВ**\n\n"
            for o in orders[-10:]:
                emoji = "🆕" if o["status"] == "pending" else "💰" if o["status"] == "paid" else "✅"
                text += f"{emoji} #{o['id']} | {o['user_name']} | {o['total']}₽ | {o['status']}\n"
            await update_message(chat_id, user_id, text, admin_menu(), "Markdown")
    
    elif data == "admin_pending" and is_admin(user_id):
        paid_orders = [o for o in orders if o["status"] == "paid"]
        if not paid_orders:
            await update_message(chat_id, user_id, "⏳ Нет заказов, ожидающих выдачи", admin_menu(), "Markdown")
        else:
            text = "⏳ **ЗАКАЗЫ, ОЖИДАЮЩИЕ ВЫДАЧИ**\n\n"
            for o in paid_orders:
                text += f"#{o['id']} | {o['user_name']} | {o['total']}₽\n"
            await update_message(chat_id, user_id, text, admin_menu(), "Markdown")
    
    elif data == "admin_stats" and is_admin(user_id):
        total_orders = len(orders)
        completed = len([o for o in orders if o["status"] == "completed"])
        paid = len([o for o in orders if o["status"] == "paid"])
        revenue = sum(o["total"] for o in orders if o["status"] in ["paid", "completed"])
        text = (f"📊 **СТАТИСТИКА ПРОДАЖ**\n\n"
                f"📦 Всего заказов: {total_orders}\n"
                f"✅ Выполнено: {completed}\n"
                f"⏳ Оплачено: {paid}\n"
                f"💰 Выручка: {revenue}₽\n"
                f"⭐ Отзывов: {len(reviews)}")
        await update_message(chat_id, user_id, text, admin_menu(), "Markdown")
    
    elif data == "admin_reviews" and is_admin(user_id):
        if not reviews:
            await update_message(chat_id, user_id, "⭐ Отзывов пока нет", admin_menu(), "Markdown")
        else:
            text = "⭐ **УПРАВЛЕНИЕ ОТЗЫВАМИ**\n\n"
            for r in reviews[-10:]:
                stars = "⭐" * r["rating"]
                text += f"{stars} {r['rating']}/5\n{r['text']}\n— {r['user_name']}\n\n"
            kb = InlineKeyboardMarkup(row_width=1)
            kb.add(InlineKeyboardButton("🗑 Удалить последний", callback_data="admin_delete_last_review"))
            kb.add(InlineKeyboardButton("🔙 Назад", callback_data="admin_back"))
            await update_message(chat_id, user_id, text, kb, "Markdown")
    
    elif data == "admin_delete_last_review" and is_admin(user_id):
        if reviews:
            deleted = reviews.pop()
            await update_message(chat_id, user_id, f"✅ Удалён отзыв от {deleted['user_name']}", admin_menu(), "Markdown")
        else:
            await update_message(chat_id, user_id, "❌ Нет отзывов", admin_menu(), "Markdown")
    
    elif data == "admin_back" and is_admin(user_id):
        await update_message(chat_id, user_id, "🔧 Админ-панель", admin_menu(), "Markdown")
    
    elif data == "admin_exit" and is_admin(user_id):
        text = (
            "**GADZHIK SERVICE**\n"
            "**ТОВАРЫ**\n"
            "**gadzhik service**\n\n"
            "Добро пожаловать, мы работаем 24/7\n\n"
            "Здесь вы можете быстро и удобно пополнить баланс и купить товары, и подписки для популярных игр.\n\n"
            "---"
        )
        await update_photo(chat_id, user_id, WELCOME_IMAGE, text, main_menu())

@dp.callback_query_handler(lambda c: c.data.startswith("pay_order_"))
async def pay_order(callback: types.CallbackQuery):
    order_id = int(callback.data.replace("pay_order_", ""))
    user_id = str(callback.from_user.id)
    chat_id = callback.message.chat.id
    await bot.answer_callback_query(callback.id)
    
    order = next((o for o in orders if o["id"] == order_id), None)
    if order and order["status"] == "pending":
        order["status"] = "paid"
        await update_message(chat_id, user_id, f"✅ **СПАСИБО ЗА ЗАКАЗ!**\n\nВаш заказ #{order_id} принят.\n\nUC будет начислен после проверки оплаты.", main_menu(), "Markdown")
        await bot.send_message(ADMIN_ID, f"💰 **ЗАКАЗ #{order_id} ОПЛАЧЕН!**\n👤 {order['user_name']}\n🆔 Pubg ID: {order['pubg_id']}\n💰 {order['uc_amount']} UC = {order['total']}₽", parse_mode="Markdown")

@dp.message_handler()
async def handle_text(message: types.Message):
    user_id = str(message.from_user.id)
    text = message.text.strip()
    
    if user_id in admin_state and admin_state[user_id].startswith("wait_review_text_"):
        rating = int(admin_state[user_id].replace("wait_review_text_", ""))
        user_name = message.from_user.first_name or "Пользователь"
        reviews.append({
            "rating": rating, "text": text, "user_name": user_name,
            "user_id": user_id, "date": str(datetime.now())
        })
        del admin_state[user_id]
        await update_message(message.chat.id, user_id, f"⭐ **Спасибо за отзыв!**\nВаша оценка: {rating}★", main_menu(), "Markdown")
        await bot.send_message(ADMIN_ID, f"⭐ **НОВЫЙ ОТЗЫВ!**\nОт: {user_name}\nОценка: {rating}★\nТекст: {text}", parse_mode="Markdown")
        return
    
    if user_id in support_requests:
        await bot.send_message(ADMIN_ID, f"💬 **Сообщение от пользователя**\nID: {user_id}\nИмя: {message.from_user.first_name}\n\n{text}", parse_mode="Markdown")
        await message.answer("✅ Сообщение отправлено администратору!")
        return
    
    if user_id in user_data and user_data[user_id].get("uc_amount"):
        pubg_id = text
        if pubg_id.isdigit() and len(pubg_id) >= 10:
            uc_amount = user_data[user_id]["uc_amount"]
            uc_price = user_data[user_id]["uc_price"]
            user_name = message.from_user.first_name or "Игрок"
            order_id = len(orders) + 1
            
            text_order = (
                f"✅ **ПРОВЕРЬТЕ ВАШ ЗАКАЗ**\n\n"
                f"🔹 **Номер заказа:** #{order_id}\n"
                f"🔹 **ID Pubg ID:** {pubg_id}\n"
                f"🔹 **Ваш Никнейм:** {user_name}\n"
                f"🔹 **Покупка:** {uc_amount} UC\n"
                f"🔹 **Сумма к оплате:** {uc_price}₽\n\n"
                f"💳 **РЕКВИЗИТЫ ДЛЯ ОПЛАТЫ:**\n"
                f"Карта: **** **** **** 1234\n\n"
                f"📌 **Перед оплатой отключите VPN**\n"
                f"🆔 Номер заказа: `{order_id}`"
            )
            
            keyboard = InlineKeyboardMarkup(row_width=1)
            keyboard.add(InlineKeyboardButton("💳 ОПЛАТИТЬ", callback_data=f"pay_order_{order_id}"))
            keyboard.add(InlineKeyboardButton("🔙 НАЗАД", callback_data="buy_menu"))
            
            orders.append({
                "id": order_id, "user_id": user_id, "user_name": user_name,
                "pubg_id": pubg_id, "uc_amount": uc_amount, "total": uc_price,
                "status": "pending", "date": str(datetime.now())
            })
            
            await update_message(message.chat.id, user_id, text_order, keyboard, "Markdown")
            await bot.send_message(ADMIN_ID, f"🆕 **НОВЫЙ ЗАКАЗ #{order_id}!**\n👤 {user_name}\n🆔 Pubg ID: {pubg_id}\n💰 {uc_amount} UC = {uc_price}₽", parse_mode="Markdown")
            del user_data[user_id]
        else:
            await update_message(message.chat.id, user_id, "❌ **НЕВЕРНЫЙ ID!**\n\nВведите корректный Pubg ID (начинается с 5, минимум 10 цифр).", None, "Markdown")
        return
    
    if is_admin(message.from_user.id):
        if user_id in admin_state and admin_state[user_id].startswith("wait_price_"):
            pid = admin_state[user_id].replace("wait_price_", "")
            try:
                new_price = int(text)
                if pid in UC_PRODUCTS:
                    UC_PRODUCTS[pid]["price"] = new_price
                    await message.answer(f"✅ Цена изменена на {new_price}₽ для {UC_PRODUCTS[pid]['amount']} UC")
                else:
                    await message.answer("❌ Товар не найден")
            except:
                await message.answer("❌ Введите число!")
            del admin_state[user_id]
            await message.answer("📦 Управление товарами:", reply_markup=admin_uc_menu())
            return
        
        if user_id in admin_state and admin_state[user_id] == "wait_uc_product":
            parts = text.split("|")
            if len(parts) == 2:
                amount, price = parts[0].strip(), parts[1].strip()
                try:
                    amount_int = int(amount)
                    price_int = int(price)
                    pid = f"uc_{amount_int}"
                    UC_PRODUCTS[pid] = {"amount": amount_int, "price": price_int, "active": True}
                    await message.answer(f"✅ Товар {amount_int} UC добавлен! Цена: {price_int}₽")
                except:
                    await message.answer("❌ Количество и цена должны быть числами!")
            else:
                await message.answer("❌ Неверный формат! Используйте: `количество|цена`")
            del admin_state[user_id]
            await message.answer("📦 Управление товарами:", reply_markup=admin_uc_menu())
            return

@dp.message_handler(commands=["ping"])
async def ping(m: types.Message):
    await m.answer("🏓 Bot is alive!")

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

if __name__ == "__main__":
    keep_alive()
    executor.start_polling(dp, skip_updates=True)
