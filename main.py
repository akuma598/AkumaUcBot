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
SUPPORT_CHAT_ID = ADMIN_ID

carts = {}
orders = []
reviews = []
support_requests = {}
codes = {}
promocodes = {}

def load_codes():
    global codes
    if os.path.exists("codes.json"):
        with open("codes.json", "r") as f:
            codes = json.load(f)

def save_codes():
    with open("codes.json", "w") as f:
        json.dump(codes, f)

def add_code(product_id, code):
    if product_id not in codes:
        codes[product_id] = []
    codes[product_id].append(code)
    save_codes()

def get_code(product_id):
    if product_id in codes and codes[product_id]:
        return codes[product_id].pop(0)
    return None

load_codes()

def load_promocodes():
    global promocodes
    if os.path.exists("promocodes.json"):
        with open("promocodes.json", "r") as f:
            promocodes = json.load(f)

def save_promocodes():
    with open("promocodes.json", "w") as f:
        json.dump(promocodes, f)

def apply_promo(code, user_id):
    promo = promocodes.get(code)
    if not promo:
        return None, "❌ Промокод не найден"
    if promo.get("expires") and datetime.now() > datetime.fromisoformat(promo["expires"]):
        return None, "❌ Срок действия истёк"
    if promo.get("max_uses") and promo.get("uses", 0) >= promo["max_uses"]:
        return None, "❌ Промокод использован максимальное количество раз"
    if user_id in promo.get("used_by", []):
        return None, "❌ Вы уже использовали этот промокод"
    return promo["discount"], None

def use_promo(code, user_id):
    promo = promocodes.get(code)
    if promo:
        promo["uses"] = promo.get("uses", 0) + 1
        if "used_by" not in promo:
            promo["used_by"] = []
        promo["used_by"].append(user_id)
        save_promocodes()
        return True
    return False

load_promocodes()

def get_cart(user_id):
    return carts.get(user_id, {})

def save_cart(user_id, cart):
    carts[user_id] = cart

def add_to_cart(user_id, product_id, product_name, price):
    cart = get_cart(user_id)
    if product_id in cart:
        cart[product_id]["quantity"] += 1
    else:
        cart[product_id] = {"name": product_name, "price": price, "quantity": 1}
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

PRODUCTS = {
    "uc_100": {"name": "100 UC", "price": 100, "active": True, "category": "uc", "auto": False},
    "uc_500": {"name": "500 UC", "price": 450, "active": True, "category": "uc", "auto": False},
    "uc_1000": {"name": "1000 UC", "price": 850, "active": True, "category": "uc", "auto": False},
    "vpn": {"name": "VPN 30 дней", "price": 300, "active": True, "category": "vpn", "auto": True}
}

def save_products():
    with open("products.json", "w") as f:
        json.dump(PRODUCTS, f)

def load_products():
    global PRODUCTS
    if os.path.exists("products.json"):
        with open("products.json", "r") as f:
            PRODUCTS = json.load(f)

def save_orders():
    with open("orders.json", "w") as f:
        json.dump(orders, f)

def load_orders():
    global orders
    if os.path.exists("orders.json"):
        with open("orders.json", "r") as f:
            orders = json.load(f)

def save_reviews():
    with open("reviews.json", "w") as f:
        json.dump(reviews, f)

def load_reviews():
    global reviews
    if os.path.exists("reviews.json"):
        with open("reviews.json", "r") as f:
            reviews = json.load(f)

load_products()
load_orders()
load_reviews()

def is_admin(user_id):
    return str(user_id) == str(ADMIN_ID)

def main_menu():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📱 САЙТ", url="https://your-site.com"),
        InlineKeyboardButton("💰 Купить UC", callback_data="cat_uc"),
        InlineKeyboardButton("📦 Подписки", callback_data="cat_sub"),
        InlineKeyboardButton("🎮 ДРУГИЕ ИГРЫ", callback_data="other_games"),
        InlineKeyboardButton("📝 Отзывы", callback_data="show_reviews"),
        InlineKeyboardButton("⭐ ТГ ТОВАРЫ", callback_data="tg_products"),
        InlineKeyboardButton("🔗 МОИ СОЦСЕТИ", url="https://t.me/your_socials"),
        InlineKeyboardButton("🌐 Интернет без ограничений", callback_data="cat_vpn"),
        InlineKeyboardButton("🛒 КОРЗИНА", callback_data="show_cart"),
        InlineKeyboardButton("💬 ПОДДЕРЖКА", callback_data="support"),
        InlineKeyboardButton("🎟️ ПРОМОКОД", callback_data="enter_promo")
    )
    return keyboard

def catalog_keyboard(category):
    keyboard = InlineKeyboardMarkup(row_width=1)
    for pid, p in PRODUCTS.items():
        if p.get("category") == category and p.get("active", True):
            keyboard.add(InlineKeyboardButton(f"{p['name']} — {p['price']}₽", callback_data=f"view_{pid}"))
    keyboard.add(InlineKeyboardButton("🔙 ГЛАВНОЕ МЕНЮ", callback_data="back_to_menu"))
    return keyboard

def product_keyboard(pid):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(InlineKeyboardButton("➕ В КОРЗИНУ", callback_data=f"add_{pid}"))
    keyboard.add(InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_catalog"))
    return keyboard

def cart_keyboard(user_id):
    cart = get_cart(user_id)
    keyboard = InlineKeyboardMarkup(row_width=1)
    for pid, item in cart.items():
        keyboard.add(InlineKeyboardButton(f"❌ {item['name']} x{item['quantity']} = {item['price'] * item['quantity']}₽", callback_data=f"remove_{pid}"))
    if cart:
        keyboard.add(InlineKeyboardButton("✅ ОФОРМИТЬ", callback_data="checkout"))
        keyboard.add(InlineKeyboardButton("🗑 ОЧИСТИТЬ", callback_data="clear_cart"))
    keyboard.add(InlineKeyboardButton("🔙 ГЛАВНОЕ МЕНЮ", callback_data="back_to_menu"))
    return keyboard

def admin_menu():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("📦 Товары", callback_data="admin_products"),
        InlineKeyboardButton("🛒 Заказы", callback_data="admin_orders"),
        InlineKeyboardButton("⏳ Ожидают оплаты", callback_data="admin_pending"),
        InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
        InlineKeyboardButton("💬 Чаты с поддержкой", callback_data="admin_support_chats"),
        InlineKeyboardButton("⭐ Отзывы", callback_data="admin_reviews"),
        InlineKeyboardButton("🎟️ Промокоды", callback_data="admin_promocodes"),
        InlineKeyboardButton("🔑 Коды товаров", callback_data="admin_codes"),
        InlineKeyboardButton("🔙 Выйти", callback_data="admin_exit")
    )
    return keyboard

def admin_products_menu():
    keyboard = InlineKeyboardMarkup(row_width=1)
    for pid, p in PRODUCTS.items():
        status = "✅" if p["active"] else "❌"
        keyboard.add(InlineKeyboardButton(f"{status} {p['name']} — {p['price']}₽", callback_data=f"admin_edit_{pid}"))
    keyboard.add(InlineKeyboardButton("➕ Добавить товар", callback_data="admin_add_product"))
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
current_promo = {}
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
    text = "👋 Добро пожаловать в магазин Akuma UC BOT!\n\nИспользуйте меню ниже для навигации:"
    msg = await bot.send_photo(message.chat.id, photo=IMAGE_ID, caption=text, reply_markup=main_menu())
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

    # Категории
    if data == "cat_uc":
        await update_message(chat_id, user_id, "💰 **ВЫБЕРИТЕ UC:**", catalog_keyboard("uc"), "Markdown")
    elif data == "cat_vpn":
        await update_message(chat_id, user_id, "🌐 **ИНТЕРНЕТ БЕЗ ОГРАНИЧЕНИЙ:**", catalog_keyboard("vpn"), "Markdown")
    elif data == "cat_sub":
        await update_message(chat_id, user_id, "🚧 **РАЗДЕЛ В РАЗРАБОТКЕ**", main_menu(), "Markdown")
    
    # Просмотр товара
    elif data.startswith("view_"):
        pid = data.replace("view_", "")
        p = PRODUCTS.get(pid)
        if p and p.get("active", True):
            auto_text = "✅ Выдаётся автоматически" if p.get("auto", False) else "👤 Выдача вручную"
            await update_message(chat_id, user_id, f"📦 **{p['name']}**\n💰 Цена: {p['price']}₽\n\n{auto_text}", product_keyboard(pid), "Markdown")
        else:
            await update_message(chat_id, user_id, "❌ Товар не найден", main_menu())
    
    # Добавление в корзину
    elif data.startswith("add_"):
        pid = data.replace("add_", "")
        p = PRODUCTS.get(pid)
        if p and p.get("active", True):
            add_to_cart(user_id, pid, p["name"], p["price"])
            await update_message(chat_id, user_id, f"✅ **{p['name']}** добавлен в корзину!", main_menu())
        else:
            await update_message(chat_id, user_id, "❌ Товар не найден", main_menu())
    
    # Назад в каталог
    elif data == "back_to_catalog":
        await update_message(chat_id, user_id, "💰 **ВЫБЕРИТЕ UC:**", catalog_keyboard("uc"), "Markdown")
    
    # Корзина
    elif data == "show_cart":
        cart = get_cart(user_id)
        if not cart:
            await update_message(chat_id, user_id, "🛒 **КОРЗИНА ПУСТА**", main_menu(), "Markdown")
        else:
            total = get_cart_total(cart)
            discount = current_promo.get(user_id, 0)
            final_total = total - int(total * discount / 100)
            text = "🛒 **ВАША КОРЗИНА:**\n\n"
            for item in cart.values():
                text += f"• {item['name']} x{item['quantity']} = {item['price'] * item['quantity']}₽\n"
            text += f"\n💰 **ИТОГО: {total}₽**"
            if discount > 0:
                text += f"\n🎟️ **ПРОМОКОД: -{discount}%**"
                text += f"\n🔄 **К ОПЛАТЕ: {final_total}₽**"
            await update_message(chat_id, user_id, text, cart_keyboard(user_id), "Markdown")
    
    elif data.startswith("remove_"):
        pid = data.replace("remove_", "")
        remove_from_cart(user_id, pid)
        cart = get_cart(user_id)
        if not cart:
            await update_message(chat_id, user_id, "🛒 **КОРЗИНА ПУСТА**", main_menu(), "Markdown")
        else:
            total = get_cart_total(cart)
            discount = current_promo.get(user_id, 0)
            final_total = total - int(total * discount / 100)
            text = "🛒 **ВАША КОРЗИНА:**\n\n"
            for item in cart.values():
                text += f"• {item['name']} x{item['quantity']} = {item['price'] * item['quantity']}₽\n"
            text += f"\n💰 **ИТОГО: {total}₽**"
            if discount > 0:
                text += f"\n🎟️ **ПРОМОКОД: -{discount}%**"
                text += f"\n🔄 **К ОПЛАТЕ: {final_total}₽**"
            await update_message(chat_id, user_id, text, cart_keyboard(user_id), "Markdown")
    
    elif data == "clear_cart":
        clear_cart(user_id)
        current_promo.pop(user_id, None)
        await update_message(chat_id, user_id, "🗑 **КОРЗИНА ОЧИЩЕНА**", main_menu(), "Markdown")
    
    # Оформление заказа
    elif data == "checkout":
        cart = get_cart(user_id)
        if cart:
            total = get_cart_total(cart)
            discount = current_promo.get(user_id, 0)
            final_total = total - int(total * discount / 100)
            user = callback.from_user
            order_id = len(orders) + 1
            user_link = f"@{user.username}" if user.username else user.first_name or "Пользователь"
            items_text = ""
            for pid, item in cart.items():
                items_text += f"• {item['name']} x{item['quantity']} = {item['price'] * item['quantity']}₽\n"
            orders.append({"id": order_id, "user_id": user_id, "user_link": user_link, "total": final_total, "items": items_text, "status": "pending", "date": str(datetime.now())})
            save_orders()
            text = f"✅ **ЗАКАЗ #{order_id} ОФОРМЛЕН НА {final_total}₽**\n\n💳 **РЕКВИЗИТЫ ДЛЯ ОПЛАТЫ:**\nКарта: **** **** **** 1234\n\n📌 **После оплаты нажмите кнопку «Я оплатил»**"
            keyboard = InlineKeyboardMarkup(row_width=1)
            keyboard.add(InlineKeyboardButton("✅ Я ОПЛАТИЛ", callback_data=f"paid_{order_id}"))
            keyboard.add(InlineKeyboardButton("🔙 ГЛАВНОЕ МЕНЮ", callback_data="back_to_menu"))
            await update_message(chat_id, user_id, text, keyboard, "Markdown")
            await bot.send_message(ADMIN_ID, f"🆕 **НОВЫЙ ЗАКАЗ #{order_id}!**\n{user_link}\n💰 {final_total}₽\n\n{items_text}", parse_mode="Markdown")
            clear_cart(user_id)
            current_promo.pop(user_id, None)
    
    elif data.startswith("paid_"):
        order_id = int(data.replace("paid_", ""))
        order = next((o for o in orders if o["id"] == order_id), None)
        if order and order["status"] == "pending":
            order["status"] = "paid"
            save_orders()
            await update_message(chat_id, user_id, f"✅ **Спасибо! Заказ #{order_id} отмечен как оплаченный.**\n\nАдмин скоро свяжется с вами.", main_menu(), "Markdown")
            await bot.send_message(ADMIN_ID, f"💰 **ЗАКАЗ #{order_id} ОПЛАЧЕН!**\n{order['user_link']}\n{order['total']}₽", parse_mode="Markdown")
    
    # Отзывы
    elif data == "show_reviews":
        if not reviews:
            await update_message(chat_id, user_id, "⭐ **ОТЗЫВЫ**\n\nПока нет отзывов. Будьте первым!", reviews_keyboard(), "Markdown")
        else:
            text = "⭐ **ОТЗЫВЫ ПОКУПАТЕЛЕЙ:**\n\n"
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
        await update_message(chat_id, user_id, "⭐ **ОЦЕНИТЕ НАШ МАГАЗИН:**", reviews_keyboard(), "Markdown")
    
    # Промокод от пользователя
    elif data == "enter_promo":
        admin_state[user_id] = "waiting_promo"
        await update_message(chat_id, user_id, "🎟️ **ВВЕДИТЕ ПРОМОКОД:**\n\nОтправьте код текстом.", None, "Markdown")
    
    # Поддержка
    elif data == "support":
        support_requests[user_id] = True
        await update_message(chat_id, user_id, "💬 **ЧАТ ПОДДЕРЖКИ**\n\nНапишите ваше сообщение. Админ ответит.", support_keyboard(), "Markdown")
    
    elif data == "close_support":
        support_requests.pop(user_id, None)
        await update_message(chat_id, user_id, "🔚 Чат поддержки закрыт.", main_menu())
    
    # Главное меню
    elif data == "back_to_menu":
        text = "👋 Добро пожаловать в магазин Akuma UC BOT!\n\nИспользуйте меню ниже для навигации:"
        await update_message(chat_id, user_id, text, main_menu())
    
    elif data in ["other_games", "tg_products"]:
        await update_message(chat_id, user_id, "🚧 **РАЗДЕЛ В РАЗРАБОТКЕ**", main_menu(), "Markdown")

    # ==================== АДМИНКА ====================
    
    # Товары
    elif data == "admin_products" and is_admin(user_id):
        await update_message(chat_id, user_id, "📦 **Управление товарами:**", admin_products_menu(), "Markdown")
    
    elif data.startswith("admin_edit_") and is_admin(user_id):
        pid = data.replace("admin_edit_", "")
        p = PRODUCTS.get(pid)
        if p:
            kb = InlineKeyboardMarkup(row_width=2)
            kb.add(InlineKeyboardButton("🔄 Вкл/Выкл", callback_data=f"admin_toggle_{pid}"))
            kb.add(InlineKeyboardButton(f"💰 {p['price']}₽", callback_data=f"admin_price_{pid}"))
            kb.add(InlineKeyboardButton("❌ Удалить", callback_data=f"admin_delete_{pid}"))
            kb.add(InlineKeyboardButton("🔙 Назад", callback_data="admin_products"))
            status = "✅ Активен" if p["active"] else "❌ Неактивен"
            await update_message(chat_id, user_id, f"📦 **{p['name']}**\n{status}\n💰 {p['price']}₽", kb, "Markdown")
    
    elif data.startswith("admin_toggle_") and is_admin(user_id):
        pid = data.replace("admin_toggle_", "")
        if pid in PRODUCTS:
            PRODUCTS[pid]["active"] = not PRODUCTS[pid]["active"]
            save_products()
            await update_message(chat_id, user_id, f"✅ Товар {'активирован' if PRODUCTS[pid]['active'] else 'деактивирован'}", admin_products_menu(), "Markdown")
    
    elif data.startswith("admin_price_") and is_admin(user_id):
        pid = data.replace("admin_price_", "")
        admin_state[user_id] = f"wait_price_{pid}"
        await update_message(chat_id, user_id, f"💰 Введите новую цену для {PRODUCTS[pid]['name']}:", None)
    
    elif data.startswith("admin_delete_") and is_admin(user_id):
        pid = data.replace("admin_delete_", "")
        if pid in PRODUCTS:
            del PRODUCTS[pid]
            save_products()
            await update_message(chat_id, user_id, "✅ Товар удалён", admin_products_menu(), "Markdown")
    
    elif data == "admin_add_product" and is_admin(user_id):
        admin_state[user_id] = "wait_product"
        await update_message(chat_id, user_id, "➕ **Добавление товара**\n\nФормат: `id|название|цена|категория`\n\nКатегории: uc, vpn, sub\n\nПример: `vpn_pro|VPN PRO|500|vpn`", None, "Markdown")
    
    # Заказы
    elif data == "admin_orders" and is_admin(user_id):
        if not orders:
            await update_message(chat_id, user_id, "📭 Заказов пока нет", admin_menu(), "Markdown")
        else:
            text = "📋 **СПИСОК ЗАКАЗОВ**\n\n"
            for o in orders[-10:]:
                status_emoji = "🆕" if o["status"] == "pending" else "💰" if o["status"] == "paid" else "✅"
                text += f"{status_emoji} #{o['id']} | {o['user_link']} | {o['total']}₽ | {o['status']}\n"
            keyboard = InlineKeyboardMarkup(row_width=1)
            for o in orders[-10:]:
                keyboard.add(InlineKeyboardButton(f"📋 Заказ #{o['id']}", callback_data=f"admin_view_order_{o['id']}"))
            keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="admin_back"))
            await update_message(chat_id, user_id, text, keyboard, "Markdown")
    
    elif data.startswith("admin_view_order_") and is_admin(user_id):
        order_id = int(data.replace("admin_view_order_", ""))
        order = next((o for o in orders if o["id"] == order_id), None)
        if order:
            status_text = {"pending": "🆕 Ожидает оплаты", "paid": "💰 Оплачен", "completed": "✅ Выполнен"}.get(order["status"], order["status"])
            text = f"📋 **ЗАКАЗ #{order['id']}**\n{order['user_link']}\nСтатус: {status_text}\n💰 Сумма: {order['total']}₽\n📅 {order['date']}\n\n**Товары:**\n{order['items']}"
            kb = InlineKeyboardMarkup(row_width=2)
            kb.add(InlineKeyboardButton("✅ Подтвердить", callback_data=f"complete_order_{order_id}"))
            kb.add(InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_order_{order_id}"))
            kb.add(InlineKeyboardButton("🔙 Назад", callback_data="admin_orders"))
            await update_message(chat_id, user_id, text, kb, "Markdown")
    
    elif data.startswith("complete_order_") and is_admin(user_id):
        order_id = int(data.replace("complete_order_", ""))
        order = next((o for o in orders if o["id"] == order_id), None)
        if order:
            order["status"] = "completed"
            save_orders()
            await update_message(chat_id, user_id, f"✅ Заказ #{order_id} выполнен", admin_menu(), "Markdown")
            await bot.send_message(order["user_id"], f"✅ **ЗАКАЗ #{order_id} ВЫПОЛНЕН!**\nСпасибо за покупку!", parse_mode="Markdown")
    
    elif data.startswith("reject_order_") and is_admin(user_id):
        order_id = int(data.replace("reject_order_", ""))
        order = next((o for o in orders if o["id"] == order_id), None)
        if order:
            await bot.send_message(order["user_id"], f"❌ **ЗАКАЗ #{order_id} ОТКЛОНЁН**\nСвяжитесь с @aakumma", parse_mode="Markdown")
            orders.remove(order)
            save_orders()
            await update_message(chat_id, user_id, f"❌ Заказ #{order_id} отклонён", admin_menu(), "Markdown")
    
    # Ожидают оплаты
    elif data == "admin_pending" and is_admin(user_id):
        paid_orders = [o for o in orders if o["status"] == "paid"]
        if not paid_orders:
            await update_message(chat_id, user_id, "⏳ Нет заказов, ожидающих выдачи", admin_menu(), "Markdown")
        else:
            text = "⏳ **ЗАКАЗЫ, ОЖИДАЮЩИЕ ВЫДАЧИ**\n\n"
            for o in paid_orders:
                text += f"#{o['id']} | {o['user_link']} | {o['total']}₽\n"
            await update_message(chat_id, user_id, text, admin_menu(), "Markdown")
    
    # Статистика
    elif data == "admin_stats" and is_admin(user_id):
        total_orders = len(orders)
        completed = len([o for o in orders if o["status"] == "completed"])
        paid = len([o for o in orders if o["status"] == "paid"])
        revenue = sum(o["total"] for o in orders if o["status"] in ["paid", "completed"])
        text = f"📊 **СТАТИСТИКА ПРОДАЖ**\n\n📦 Всего заказов: {total_orders}\n✅ Выполнено: {completed}\n⏳ Оплачено: {paid}\n💰 Выручка: {revenue}₽\n⭐ Отзывов: {len(reviews)}"
        await update_message(chat_id, user_id, text, admin_menu(), "Markdown")
    
    # Чаты поддержки
    elif data == "admin_support_chats" and is_admin(user_id):
        if not support_requests:
            await update_message(chat_id, user_id, "💬 Нет активных чатов поддержки", admin_menu(), "Markdown")
        else:
            text = "💬 **Активные чаты поддержки:**\n\n"
            for uid in support_requests:
                text += f"• {uid}\n"
            await update_message(chat_id, user_id, text, admin_menu(), "Markdown")
    
    # Отзывы админка
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
            save_reviews()
            await update_message(chat_id, user_id, f"✅ Удалён отзыв от {deleted['user_name']}", admin_menu(), "Markdown")
        else:
            await update_message(chat_id, user_id, "❌ Нет отзывов", admin_menu(), "Markdown")
    
    # ========== ПРОМОКОДЫ (РАБОТАЕТ!) ==========
    elif data == "admin_promocodes" and is_admin(user_id):
        if not promocodes:
            text = "🎟️ **ПРОМОКОДЫ**\n\nПока нет промокодов.\n\nНажмите «➕ Добавить промокод» чтобы создать."
        else:
            text = "🎟️ **СПИСОК ПРОМОКОДОВ**\n\n"
            for code, promo in promocodes.items():
                text += f"• `{code}` — скидка {promo['discount']}% (использован: {promo.get('uses', 0)} раз)\n"
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(InlineKeyboardButton("➕ Добавить промокод", callback_data="admin_add_promo"))
        kb.add(InlineKeyboardButton("🗑 Удалить промокод", callback_data="admin_delete_promo"))
        kb.add(InlineKeyboardButton("🔙 Назад", callback_data="admin_back"))
        await update_message(chat_id, user_id, text, kb, "Markdown")
    
    elif data == "admin_add_promo" and is_admin(user_id):
        admin_state[user_id] = "wait_promo"
        await update_message(chat_id, user_id, "🎟️ **СОЗДАНИЕ ПРОМОКОДА**\n\nВведите промокод в формате:\n\n`НАЗВАНИЕ|скидка`\n\n**Примеры:**\n`SUMMER2025|10`\n`WELCOME|15`\n`HAPPY|20`\n\nСкидка указывается в % (число от 1 до 100).", None, "Markdown")
    
    elif data == "admin_delete_promo" and is_admin(user_id):
        if not promocodes:
            await update_message(chat_id, user_id, "❌ Нет промокодов для удаления", admin_menu(), "Markdown")
        else:
            text = "🎟️ **ВЫБЕРИТЕ ПРОМОКОД ДЛЯ УДАЛЕНИЯ**\n\n"
            kb = InlineKeyboardMarkup(row_width=1)
            for code in promocodes.keys():
                kb.add(InlineKeyboardButton(f"🗑 {code}", callback_data=f"admin_delete_promo_code_{code}"))
            kb.add(InlineKeyboardButton("🔙 Назад", callback_data="admin_promocodes"))
            await update_message(chat_id, user_id, text, kb, "Markdown")
    
    elif data.startswith("admin_delete_promo_code_") and is_admin(user_id):
        code = data.replace("admin_delete_promo_code_", "")
        if code in promocodes:
            del promocodes[code]
            save_promocodes()
            await update_message(chat_id, user_id, f"✅ Промокод `{code}` удалён", admin_menu(), "Markdown")
        else:
            await update_message(chat_id, user_id, "❌ Промокод не найден", admin_menu(), "Markdown")
    
    # Коды товаров
    elif data == "admin_codes" and is_admin(user_id):
        text = "🔑 **УПРАВЛЕНИЕ КОДАМИ ТОВАРОВ**\n\n"
        has_auto = False
        for pid, p in PRODUCTS.items():
            if p.get("auto", False):
                has_auto = True
                count = len(codes.get(pid, []))
                text += f"• {p['name']} — {count} кодов\n"
        if not has_auto:
            text += "Нет товаров с автовыдачей.\n\nВключите автовыдачу в настройках товара."
        kb = InlineKeyboardMarkup(row_width=1)
        for pid, p in PRODUCTS.items():
            if p.get("auto", False):
                kb.add(InlineKeyboardButton(f"🔑 Добавить коды для {p['name']}", callback_data=f"admin_add_codes_{pid}"))
        kb.add(InlineKeyboardButton("🔙 Назад", callback_data="admin_back"))
        await update_message(chat_id, user_id, text, kb, "Markdown")
    
    elif data.startswith("admin_add_codes_") and is_admin(user_id):
        pid = data.replace("admin_add_codes_", "")
        admin_state[user_id] = f"wait_codes_{pid}"
        await update_message(chat_id, user_id, f"🔑 **ДОБАВЛЕНИЕ КОДОВ**\n\nВведите коды для товара (каждый с новой строки):\n\nПример:\n`CODE123`\n`CODE456`\n`CODE789`", None, "Markdown")
    
    # Навигация админки
    elif data == "admin_back" and is_admin(user_id):
        await update_message(chat_id, user_id, "🔧 Админ-панель", admin_menu(), "Markdown")
    
    elif data == "admin_exit" and is_admin(user_id):
        await update_message(chat_id, user_id, "🔚 Выход из админ-панели", main_menu())

@dp.message_handler()
async def handle_text(message: types.Message):
    user_id = str(message.from_user.id)
    text = message.text
    
    # Промокод от пользователя
    if user_id in admin_state and admin_state[user_id] == "waiting_promo":
        discount, error = apply_promo(text.upper(), user_id)
        if discount:
            current_promo[user_id] = discount
            await update_message(message.chat.id, user_id, f"✅ **ПРОМОКОД АКТИВИРОВАН!**\nСкидка: {discount}%\n\nПерейдите в корзину для оформления заказа.", main_menu(), "Markdown")
        else:
            await update_message(message.chat.id, user_id, error, main_menu(), "Markdown")
        del admin_state[user_id]
        return
    
    # Отзыв от пользователя
    if user_id in admin_state and admin_state[user_id].startswith("wait_review_text_"):
        rating = int(admin_state[user_id].replace("wait_review_text_", ""))
        user_name = message.from_user.first_name or "Пользователь"
        reviews.append({"rating": rating, "text": text, "user_name": user_name, "user_id": user_id, "date": str(datetime.now())})
        save_reviews()
        del admin_state[user_id]
        await update_message(message.chat.id, user_id, f"⭐ **Спасибо за отзыв!**\nВаша оценка: {rating}★", main_menu(), "Markdown")
        await bot.send_message(ADMIN_ID, f"⭐ **НОВЫЙ ОТЗЫВ!**\nОт: {user_name}\nОценка: {rating}★\nТекст: {text}", parse_mode="Markdown")
        return
    
    # ========== ДЕЙСТВИЯ АДМИНИСТРАТОРА ==========
    if not is_admin(user_id):
        return
    
    # Создание промокода админом
    if user_id in admin_state and admin_state[user_id] == "wait_promo":
        parts = text.split("|")
        if len(parts) == 2:
            code, discount = parts[0].strip().upper(), parts[1].strip()
            try:
                disc = int(discount)
                if 1 <= disc <= 100:
                    promocodes[code] = {"discount": disc, "uses": 0}
                    save_promocodes()
                    await update_message(message.chat.id, user_id, f"✅ **Промокод создан!**\n`{code}` — скидка {disc}%", admin_menu(), "Markdown")
                else:
                    await message.answer("❌ Скидка должна быть от 1 до 100")
            except:
                await message.answer("❌ Скидка должна быть числом!")
        else:
            await message.answer("❌ Неверный формат! Используйте: `КОД|скидка`")
        del admin_state[user_id]
        return
    
    # Изменение цены
    if user_id in admin_state and admin_state[user_id].startswith("wait_price_"):
        pid = admin_state[user_id].replace("wait_price_", "")
        try:
            new_price = int(text)
            if pid in PRODUCTS:
                PRODUCTS[pid]["price"] = new_price
                save_products()
                await message.answer(f"✅ Цена изменена на {new_price}₽")
            else:
                await message.answer("❌ Товар не найден")
        except:
            await message.answer("❌ Введите число!")
        del admin_state[user_id]
        await message.answer("📦 Управление товарами:", reply_markup=admin_products_menu())
        return
    
    # Добавление товара
    if user_id in admin_state and admin_state[user_id] == "wait_product":
        parts = text.split("|")
        if len(parts) >= 4:
            pid, name, price, category = parts[0].strip(), parts[1].strip(), parts[2].strip(), parts[3].strip()
            try:
                PRODUCTS[pid] = {"name": name, "price": int(price), "active": True, "category": category, "auto": False}
                save_products()
                await message.answer(f"✅ Товар `{name}` добавлен в категорию {category}!", parse_mode="Markdown")
            except:
                await message.answer("❌ Цена должна быть числом!")
        else:
            await message.answer("❌ Неверный формат! Используйте: `id|название|цена|категория`")
        del admin_state[user_id]
        await message.answer("📦 Управление товарами:", reply_markup=admin_products_menu())
        return
    
    # Добавление кодов
    if user_id in admin_state and admin_state[user_id].startswith("wait_codes_"):
        pid = admin_state[user_id].replace("wait_codes_", "")
        codes_list = text.strip().split("\n")
        added = 0
        for code in codes_list:
            if code.strip():
                add_code(pid, code.strip())
                added += 1
        await update_message(message.chat.id, user_id, f"✅ Добавлено {added} кодов для товара", admin_menu(), "Markdown")
        del admin_state[user_id]
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
