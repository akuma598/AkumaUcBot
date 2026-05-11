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

carts = {}
orders = []
reviews = []
support_requests = {}

# ===== ТОВАРЫ UC (цены +10₽ к каждой) =====
UC_PRODUCTS = {
    "uc_60": {"amount": 60, "price": 82, "active": True},
    "uc_120": {"amount": 120, "price": 152, "active": True},
    "uc_180": {"amount": 180, "price": 223, "active": True},
    "uc_240": {"amount": 240, "price": 293, "active": True},
    "uc_325": {"amount": 325, "price": 363, "active": True},
    "uc_385": {"amount": 385, "price": 434, "active": True},
    "uc_445": {"amount": 445, "price": 504, "active": True},
    "uc_660": {"amount": 660, "price": 715, "active": True},
    "uc_720": {"amount": 720, "price": 785, "active": True},
    "uc_985": {"amount": 985, "price": 1067, "active": True},
    "uc_1320": {"amount": 1320, "price": 1419, "active": True},
    "uc_1800": {"amount": 1800, "price": 1770, "active": True},
    "uc_1920": {"amount": 1920, "price": 1911, "active": True},
    "uc_2125": {"amount": 2125, "price": 2122, "active": True},
    "uc_2460": {"amount": 2460, "price": 2474, "active": True},
    "uc_3850": {"amount": 3850, "price": 3489, "active": True},
    "uc_4510": {"amount": 4510, "price": 4193, "active": True},
    "uc_5650": {"amount": 5650, "price": 5248, "active": True},
    "uc_8100": {"amount": 8100, "price": 6967, "active": True},
    "uc_9900": {"amount": 9900, "price": 9800, "active": True},
    "uc_11950": {"amount": 11950, "price": 10444, "active": True},
    "uc_16200": {"amount": 16200, "price": 13922, "active": True},
    "uc_24300": {"amount": 24300, "price": 20877, "active": True},
    "uc_32400": {"amount": 32400, "price": 27832, "active": True},
    "uc_40500": {"amount": 40500, "price": 34787, "active": True},
    "uc_81000": {"amount": 81000, "price": 69562, "active": True}
}

def get_cart(user_id):
    return carts.get(user_id, {})

def save_cart(user_id, cart):
    carts[user_id] = cart

def add_to_cart(user_id, product_id, amount, price):
    cart = get_cart(user_id)
    if product_id in cart:
        cart[product_id]["quantity"] += 1
    else:
        cart[product_id] = {"name": f"{amount} UC", "amount": amount, "price": price, "quantity": 1}
    save_cart(user_id, cart)

def remove_from_cart(user_id, product_id):
    cart = get_cart(user_id)
    if product_id in cart:
        del cart[product_id]
    save_cart(user_id, cart)

def clear_cart(user_id):
    carts[user_id] = {}

def get_cart_total(cart):
    return sum(item["price"] * item["quantity"] for item in cart.values())

def is_admin(user_id):
    return str(user_id) == str(ADMIN_ID)

# ===== КЛАВИАТУРЫ =====
def main_menu():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🛒 Купить UC", callback_data="cat_uc"),
        InlineKeyboardButton("📝 Отзывы", callback_data="show_reviews"),
        InlineKeyboardButton("🛍️ КОРЗИНА", callback_data="show_cart"),
        InlineKeyboardButton("💬 ПОДДЕРЖКА", callback_data="support"),
        InlineKeyboardButton("🔗 МОИ СОЦСЕТИ", url="https://t.me/your_socials")
    )
    return keyboard

def uc_keyboard():
    """Клавиатура с выбором количества UC (как на скриншоте)"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    # Группируем по 2 кнопки в ряд
    uc_list = list(UC_PRODUCTS.items())
    for i in range(0, len(uc_list), 2):
        row = []
        # Первый товар
        pid1, p1 = uc_list[i]
        row.append(InlineKeyboardButton(
            f"{p1['amount']} — {p1['price']}₽", 
            callback_data=f"add_{pid1}"
        ))
        # Второй товар (если есть)
        if i + 1 < len(uc_list):
            pid2, p2 = uc_list[i + 1]
            row.append(InlineKeyboardButton(
                f"{p2['amount']} — {p2['price']}₽", 
                callback_data=f"add_{pid2}"
            ))
        keyboard.row(*row)
    
    keyboard.add(InlineKeyboardButton("🔙 ГЛАВНОЕ МЕНЮ", callback_data="back_to_menu"))
    return keyboard

def cart_keyboard(user_id):
    cart = get_cart(user_id)
    keyboard = InlineKeyboardMarkup(row_width=1)
    for pid, item in cart.items():
        keyboard.add(InlineKeyboardButton(
            f"❌ {item['name']} x{item['quantity']} = {item['price'] * item['quantity']}₽",
            callback_data=f"remove_{pid}"
        ))
    if cart:
        keyboard.add(InlineKeyboardButton("✅ ОФОРМИТЬ", callback_data="checkout"))
        keyboard.add(InlineKeyboardButton("🗑 ОЧИСТИТЬ", callback_data="clear_cart"))
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
        keyboard.add(InlineKeyboardButton(
            f"{status} {p['amount']} UC — {p['price']}₽",
            callback_data=f"admin_edit_uc_{pid}"
        ))
    keyboard.add(InlineKeyboardButton("➕ Добавить UC", callback_data="admin_add_uc"))
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="admin_back"))
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
    keyboard.add(InlineKeyboardButton("🔙 ГЛАВНОЕ МЕНЮ", callback_data="back_to_menu"))
    return keyboard

def support_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(InlineKeyboardButton("✖️ ЗАКРЫТЬ ЧАТ", callback_data="close_support"))
    keyboard.add(InlineKeyboardButton("🔙 ГЛАВНОЕ МЕНЮ", callback_data="back_to_menu"))
    return keyboard

IMAGE_ID = "AgACAgIAAxkBAAEpEj5qAAF14VBLMN24S1ngXPeedYLmlrcAAmEYaxs8bQFIsoUcN-o04FMBAAMCAANtAAM7BA"

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

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    user_id = str(message.from_user.id)
    text = "👋 **Добро пожаловать в магазин Akuma UC BOT!**\n\n🟢 Мы работаем 24/7\n\nЗдесь вы можете быстро и удобно купить UC для популярных игр.\n\nИспользуйте меню ниже:"
    msg = await bot.send_photo(message.chat.id, photo=IMAGE_ID, caption=text, reply_markup=main_menu(), parse_mode="Markdown")
    last_message_id[user_id] = msg.message_id

@dp.message_handler(commands=["admin"])
async def admin_login(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    pwd = message.get_args()
    if pwd == ADMIN_PASSWORD:
        await update_message(message.chat.id, str(message.from_user.id), "🔧 **Админ-панель**", admin_menu(), "Markdown")
    else:
        await message.answer("❌ Неверный пароль")

@dp.callback_query_handler(lambda c: True)
async def handle(callback: types.CallbackQuery):
    data = callback.data
    user_id = str(callback.from_user.id)
    chat_id = callback.message.chat.id
    await bot.answer_callback_query(callback.id)

    # ===== КАТАЛОГ UC =====
    if data == "cat_uc":
        await update_message(chat_id, user_id, "💰 **ВЫБЕРИТЕ КОЛИЧЕСТВО UC:**\n\nНажмите на нужный пакет:", uc_keyboard(), "Markdown")
    
    # ===== ДОБАВЛЕНИЕ В КОРЗИНУ =====
    elif data.startswith("add_"):
        pid = data.replace("add_", "")
        p = UC_PRODUCTS.get(pid)
        if p and p.get("active", True):
            add_to_cart(user_id, pid, p["amount"], p["price"])
            await update_message(chat_id, user_id, f"✅ **{p['amount']} UC** добавлен в корзину!\n\nТовар можно добавить ещё раз, чтобы увеличить количество.", main_menu(), "Markdown")
        else:
            await update_message(chat_id, user_id, "❌ Товар временно недоступен", main_menu())
    
    # ===== КОРЗИНА =====
    elif data == "show_cart":
        cart = get_cart(user_id)
        if not cart:
            await update_message(chat_id, user_id, "🛒 **КОРЗИНА ПУСТА**\n\nДобавьте товары через меню «Купить UC».", main_menu(), "Markdown")
        else:
            text = "🛒 **ВАША КОРЗИНА:**\n\n"
            for item in cart.values():
                text += f"• {item['name']} x{item['quantity']} = {item['price'] * item['quantity']}₽\n"
            text += f"\n💰 **ИТОГО: {get_cart_total(cart)}₽**"
            await update_message(chat_id, user_id, text, cart_keyboard(user_id), "Markdown")
    
    elif data.startswith("remove_"):
        pid = data.replace("remove_", "")
        remove_from_cart(user_id, pid)
        cart = get_cart(user_id)
        if not cart:
            await update_message(chat_id, user_id, "🛒 **КОРЗИНА ПУСТА**", main_menu(), "Markdown")
        else:
            text = "🛒 **ВАША КОРЗИНА:**\n\n"
            for item in cart.values():
                text += f"• {item['name']} x{item['quantity']} = {item['price'] * item['quantity']}₽\n"
            text += f"\n💰 **ИТОГО: {get_cart_total(cart)}₽**"
            await update_message(chat_id, user_id, text, cart_keyboard(user_id), "Markdown")
    
    elif data == "clear_cart":
        clear_cart(user_id)
        await update_message(chat_id, user_id, "🗑 **КОРЗИНА ОЧИЩЕНА**", main_menu(), "Markdown")
    
    # ===== ОФОРМЛЕНИЕ ЗАКАЗА =====
    elif data == "checkout":
        cart = get_cart(user_id)
        if cart:
            total = get_cart_total(cart)
            user = callback.from_user
            order_id = len(orders) + 1
            user_name = user.first_name or "Пользователь"
            user_link = f"@{user.username}" if user.username else user_name
            items_text = ""
            for item in cart.values():
                items_text += f"• {item['name']} x{item['quantity']} = {item['price'] * item['quantity']}₽\n"
            
            orders.append({
                "id": order_id, 
                "user_id": user_id, 
                "user_link": user_link,
                "user_name": user_name,
                "total": total, 
                "items": items_text, 
                "status": "pending", 
                "date": str(datetime.now())
            })
            
            text = f"✅ **ЗАКАЗ #{order_id} ОФОРМЛЕН НА {total}₽**\n\n"
            text += f"📋 **Детали заказа:**\n{items_text}\n"
            text += f"💳 **РЕКВИЗИТЫ ДЛЯ ОПЛАТЫ:**\n"
            text += f"Карта: **** **** **** 1234\n"
            text += f"Получатель: АКУМА\n\n"
            text += f"📌 **После оплаты нажмите кнопку «Я оплатил»**\n"
            text += f"🆔 Номер заказа: `{order_id}`"
            
            keyboard = InlineKeyboardMarkup(row_width=1)
            keyboard.add(InlineKeyboardButton("✅ Я ОПЛАТИЛ", callback_data=f"paid_{order_id}"))
            keyboard.add(InlineKeyboardButton("🔙 ГЛАВНОЕ МЕНЮ", callback_data="back_to_menu"))
            
            await update_message(chat_id, user_id, text, keyboard, "Markdown")
            
            # Уведомление админу
            admin_text = f"🆕 **НОВЫЙ ЗАКАЗ #{order_id}!**\n"
            admin_text += f"👤 От: {user_link}\n"
            admin_text += f"💰 Сумма: {total}₽\n\n"
            admin_text += f"📦 Товары:\n{items_text}"
            await bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown")
            
            clear_cart(user_id)
    
    elif data.startswith("paid_"):
        order_id = int(data.replace("paid_", ""))
        order = next((o for o in orders if o["id"] == order_id), None)
        if order and order["status"] == "pending":
            order["status"] = "paid"
            await update_message(chat_id, user_id, f"✅ **Спасибо! Заказ #{order_id} отмечен как оплаченный.**\n\nАдмин проверит оплату и выдаст UC в ближайшее время.\n\n📌 Для вопросов: @aakumma", main_menu(), "Markdown")
            await bot.send_message(ADMIN_ID, f"💰 **ЗАКАЗ #{order_id} ОПЛАЧЕН!**\n👤 {order['user_link']}\n💰 {order['total']}₽", parse_mode="Markdown")
    
    # ===== ОТЗЫВЫ =====
    elif data == "show_reviews":
        if not reviews:
            await update_message(chat_id, user_id, "⭐ **ОТЗЫВЫ**\n\nПока нет отзывов. Будьте первым!\n\nОцените нашу работу:", reviews_keyboard(), "Markdown")
        else:
            text = "⭐ **ОТЗЫВЫ НАШИХ КЛИЕНТОВ:**\n\n"
            for r in reviews[-10:]:
                stars = "⭐" * r["rating"]
                text += f"{stars} {r['rating']}/5\n{r['text']}\n— {r['user_name']}\n📅 {r['date']}\n\n"
            keyboard = InlineKeyboardMarkup(row_width=1)
            keyboard.add(InlineKeyboardButton("📝 ОСТАВИТЬ ОТЗЫВ", callback_data="leave_review"))
            keyboard.add(InlineKeyboardButton("🔙 ГЛАВНОЕ МЕНЮ", callback_data="back_to_menu"))
            await update_message(chat_id, user_id, text, keyboard, "Markdown")
    
    elif data in ["review_1", "review_2", "review_3", "review_4", "review_5"]:
        rating = int(data.replace("review_", ""))
        admin_state[user_id] = f"wait_review_text_{rating}"
        await update_message(chat_id, user_id, f"⭐ Вы выбрали {rating} звёзд.\n\nНапишите текст отзыва:", None)
    
    elif data == "leave_review":
        await update_message(chat_id, user_id, "⭐ **ОЦЕНИТЕ НАШ МАГАЗИН:**\n\nНажмите на количество звёзд:", reviews_keyboard(), "Markdown")
    
    # ===== ПОДДЕРЖКА =====
    elif data == "support":
        support_requests[user_id] = True
        await update_message(chat_id, user_id, "💬 **ЧАТ ПОДДЕРЖКИ**\n\nНапишите ваше сообщение. Администратор ответит вам в ближайшее время.\n\nЧтобы закрыть чат, нажмите кнопку ниже.", support_keyboard(), "Markdown")
    
    elif data == "close_support":
        support_requests.pop(user_id, None)
        await update_message(chat_id, user_id, "🔚 Чат поддержки закрыт. Если появятся вопросы — снова нажмите «Поддержка».", main_menu())
    
    # ===== ГЛАВНОЕ МЕНЮ =====
    elif data == "back_to_menu":
        text = "👋 **Добро пожаловать в магазин Akuma UC BOT!**\n\n🟢 Мы работаем 24/7\n\nИспользуйте меню ниже:"
        await update_message(chat_id, user_id, text, main_menu(), "Markdown")
    
    # ==================== АДМИНКА ====================
    elif data == "admin_uc" and is_admin(user_id):
        await update_message(chat_id, user_id, "📦 **Управление товарами UC:**\n\n✅ - активен, ❌ - неактивен", admin_uc_menu(), "Markdown")
    
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
            await update_message(chat_id, user_id, f"📦 **{p['amount']} UC**\n{status}\n💰 Цена: {p['price']}₽", kb, "Markdown")
    
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
        await update_message(chat_id, user_id, "➕ **Добавление товара UC**\n\nФормат: `количество|цена`\n\nПример: `5000|4300`\n\n(цена в рублях)", None, "Markdown")
    
    elif data == "admin_orders" and is_admin(user_id):
        if not orders:
            await update_message(chat_id, user_id, "📭 Заказов пока нет", admin_menu(), "Markdown")
        else:
            text = "📋 **СПИСОК ЗАКАЗОВ**\n\n"
            for o in orders[-10:]:
                emoji = "🆕" if o["status"] == "pending" else "💰" if o["status"] == "paid" else "✅"
                text += f"{emoji} #{o['id']} | {o['user_link']} | {o['total']}₽ | {o['status']}\n"
            await update_message(chat_id, user_id, text, admin_menu(), "Markdown")
    
    elif data == "admin_pending" and is_admin(user_id):
        paid_orders = [o for o in orders if o["status"] == "paid"]
        if not paid_orders:
            await update_message(chat_id, user_id, "⏳ Нет заказов, ожидающих выдачи", admin_menu(), "Markdown")
        else:
            text = "⏳ **ЗАКАЗЫ, ОЖИДАЮЩИЕ ВЫДАЧИ**\n\n"
            for o in paid_orders:
                text += f"#{o['id']} | {o['user_link']} | {o['total']}₽\n"
            await update_message(chat_id, user_id, text, admin_menu(), "Markdown")
    
    elif data == "admin_stats" and is_admin(user_id):
        total_orders = len(orders)
        completed = len([o for o in orders if o["status"] == "completed"])
        paid = len([o for o in orders if o["status"] == "paid"])
        revenue = sum(o["total"] for o in orders if o["status"] in ["paid", "completed"])
        text = f"📊 **СТАТИСТИКА ПРОДАЖ**\n\n"
        text += f"📦 Всего заказов: {total_orders}\n"
        text += f"✅ Выполнено: {completed}\n"
        text += f"⏳ Оплачено, ожидают: {paid}\n"
        text += f"💰 Общая выручка: {revenue}₽\n"
        text += f"⭐ Отзывов оставлено: {len(reviews)}"
        await update_message(chat_id, user_id, text, admin_menu(), "Markdown")
    
    elif data == "admin_reviews" and is_admin(user_id):
        if not reviews:
            await update_message(chat_id, user_id, "⭐ Отзывов пока нет", admin_menu(), "Markdown")
        else:
            text = "⭐ **УПРАВЛЕНИЕ ОТЗЫВАМИ**\n\n"
            for r in reviews[-10:]:
                stars = "⭐" * r["rating"]
                text += f"{stars} {r['rating']}/5\n{r['text']}\n— {r['user_name']}\n📅 {r['date']}\n\n"
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
        await update_message(chat_id, user_id, "🔚 Выход из админ-панели", main_menu())

@dp.message_handler()
async def handle_text(message: types.Message):
    user_id = str(message.from_user.id)
    text = message.text
    
    # Отзыв
    if user_id in admin_state and admin_state[user_id].startswith("wait_review_text_"):
        rating = int(admin_state[user_id].replace("wait_review_text_", ""))
        user_name = message.from_user.first_name or "Пользователь"
        reviews.append({
            "rating": rating, 
            "text": text, 
            "user_name": user_name, 
            "user_id": user_id, 
            "date": str(datetime.now())
        })
        del admin_state[user_id]
        await update_message(message.chat.id, user_id, f"⭐ **Спасибо за отзыв!**\n\nВаша оценка: {rating}★\n\nВаш отзыв опубликован.", main_menu(), "Markdown")
        await bot.send_message(ADMIN_ID, f"⭐ **НОВЫЙ ОТЗЫВ!**\nОт: {user_name}\nОценка: {rating}★\nТекст: {text}", parse_mode="Markdown")
        return
    
    # Поддержка
    if user_id in support_requests:
        await bot.send_message(ADMIN_ID, f"💬 **Сообщение от пользователя**\nID: {user_id}\nИмя: {message.from_user.first_name}\n\n{text}", parse_mode="Markdown")
        await message.answer("✅ Сообщение отправлено администратору! Ожидайте ответа.")
        return
    
    # Админ: изменение цены
    if not is_admin(message.from_user.id):
        return
    
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
    
    # Админ: добавление товара
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

@dp.message_handler(commands=["ping"])
async def ping(m: types.Message):
    await m.answer("🏓 Bot is alive!")

# ===== FLASK KEEP-ALIVE =====
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
