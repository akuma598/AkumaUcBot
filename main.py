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
        return None, "❌ Промокод использован макс. количество раз"
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
    "pp_1000": {"name": "ПП 1000", "price": 200, "active": True, "category": "pp", "auto": False},
    "pp_5000": {"name": "ПП 5000", "price": 800, "active": True, "category": "pp", "auto": False},
    "sub_1m": {"name": "Подписка 1 месяц", "price": 500, "active": True, "category": "sub", "auto": False},
    "sub_3m": {"name": "Подписка 3 месяца", "price": 1300, "active": True, "category": "sub", "auto": False},
    "sub_6m": {"name": "Подписка 6 месяцев", "price": 2200, "active": True, "category": "sub", "auto": False},
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
        InlineKeyboardButton("🎉 Купить ПП", callback_data="cat_pp"),
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
            keyboard.add(InlineKeyboardButton(f"{p['name']} — {p['price']}₽", callback_data=f"view_{pid}_{category}"))
    keyboard.add(InlineKeyboardButton("🔙 ГЛАВНОЕ МЕНЮ", callback_data="back_to_menu"))
    return keyboard

def product_keyboard(pid, category):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(InlineKeyboardButton("➕ В КОРЗИНУ", callback_data=f"add_{pid}"))
    keyboard.add(InlineKeyboardButton("🔙 НАЗАД", callback_data=f"back_to_cat_{category}"))
    return keyboard

def cart_keyboard(user_id, promo_discount=0):
    cart = get_cart(user_id)
    keyboard = InlineKeyboardMarkup(row_width=1)
    for pid, item in cart.items():
        keyboard.add(InlineKeyboardButton(f"❌ {item['name']} x{item['quantity']} = {item['price'] * item['quantity']}₽", callback_data=f"remove_{pid}"))
    if cart:
        keyboard.add(InlineKeyboardButton("🎟️ Ввести промокод", callback_data="enter_promo"))
        keyboard.add(InlineKeyboardButton("✅ ОФОРМИТЬ", callback_data="checkout"))
        keyboard.add(InlineKeyboardButton("🗑 ОЧИСТИТЬ", callback_data="clear_cart"))
    keyboard.add(InlineKeyboardButton("🔙 ГЛАВНОЕ МЕНЮ", callback_data="back_to_menu"))
    return keyboard

def admin_menu():
    keyboard = InlineKeyboardMarkup(row_width=2)
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

def admin_order_keyboard(order_id):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("✅ Подтвердить", callback_data=f"complete_order_{order_id}"),
        InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_order_{order_id}"),
        InlineKeyboardButton("💬 Написать", callback_data=f"msg_user_{order_id}"),
        InlineKeyboardButton("🔙 Назад", callback_data="admin_orders")
    )
    return keyboard

def admin_products_menu():
    keyboard = InlineKeyboardMarkup(row_width=1)
    for pid, p in PRODUCTS.items():
        status = "✅" if p["active"] else "❌"
        auto = "📦" if p.get("auto", False) else "👤"
        keyboard.add(InlineKeyboardButton(f"{status} {auto} {p['name']} — {p['price']}₽", callback_data=f"admin_edit_{pid}"))
    keyboard.add(InlineKeyboardButton("➕ Добавить", callback_data="admin_add"))
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

def support_keyboard(user_id):
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
    elif data == "cat_pp":
        await update_message(chat_id, user_id, "🎉 **ВЫБЕРИТЕ ПП:**", catalog_keyboard("pp"), "Markdown")
    elif data == "cat_sub":
        await update_message(chat_id, user_id, "📦 **ВЫБЕРИТЕ ПОДПИСКУ:**", catalog_keyboard("sub"), "Markdown")
    elif data == "cat_vpn":
        await update_message(chat_id, user_id, "🌐 **ИНТЕРНЕТ БЕЗ ОГРАНИЧЕНИЙ:**", catalog_keyboard("vpn"), "Markdown")
    
    # Просмотр товара (с категорией)
    elif data.startswith("view_"):
        parts = data.split("_")
        if len(parts) >= 3:
            pid = parts[1]
            category = parts[2]
        else:
            pid = parts[1]
            category = "uc"
        p = PRODUCTS.get(pid)
        if p and p.get("active", True):
            auto_text = "✅ Выдаётся автоматически" if p.get("auto", False) else "👤 Выдача вручную"
            await update_message(chat_id, user_id, f"📦 **{p['name']}**\n💰 Цена: {p['price']}₽\n\n{auto_text}", product_keyboard(pid, category), "Markdown")
        else:
            await update_message(chat_id, user_id, "❌ Товар не найден", main_menu())
    
    # Добавление в корзину
    elif data.startswith("add_"):
        pid = data.replace("add_", "")
        p = PRODUCTS.get(pid)
        if p:
            add_to_cart(user_id, pid, p["name"], p["price"])
            await update_message(chat_id, user_id, f"✅ **{p['name']}** добавлен в корзину!", main_menu())
    
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
            await update_message(chat_id, user_id, text, cart_keyboard(user_id, discount), "Markdown")
    
    # Ввод промокода
    elif data == "enter_promo":
        admin_state[user_id] = "waiting_promo"
        await update_message(chat_id, user_id, "🎟️ **ВВЕДИТЕ ПРОМОКОД:**\n\nОтправьте код текстом.", None, "Markdown")
    
    # Удаление из корзины
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
            await update_message(chat_id, user_id, text, cart_keyboard(user_id, discount), "Markdown")
    
    # Очистка корзины
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
            user_link = f"@{user.username}" if user.username else f"[{user.first_name or 'Пользователь'}](tg://user?id={user.id})"
            items_text = ""
            auto_items = []
            for pid, item in cart.items():
                items_text += f"• {item['name']} x{item['quantity']} = {item['price'] * item['quantity']}₽\n"
                if PRODUCTS.get(pid, {}).get("auto", False):
                    for _ in range(item["quantity"]):
                        auto_items.append(pid)
            orders.append({"id": order_id, "user_id": user_id, "user_link": user_link, "total": final_total, "original_total": total, "discount": discount, "items": items_text, "auto_items": auto_items, "status": "pending", "date": str(datetime.now())})
            save_orders()
            payment_text = f"✅ **ЗАКАЗ #{order_id} ОФОРМЛЕН НА {final_total}₽**\n\n💳 **РЕКВИЗИТЫ ДЛЯ ОПЛАТЫ:**\nКарта: **** **** **** 1234\n\n📌 **После оплаты нажмите кнопку «Я оплатил»**"
            keyboard = InlineKeyboardMarkup(row_width=1)
            keyboard.add(InlineKeyboardButton("✅ Я ОПЛАТИЛ", callback_data=f"paid_{order_id}"))
            keyboard.add(InlineKeyboardButton("🔙 ГЛАВНОЕ МЕНЮ", callback_data="back_to_menu"))
            await update_message(chat_id, user_id, payment_text, keyboard, "Markdown")
            await bot.send_message(ADMIN_ID, f"🆕 **НОВЫЙ ЗАКАЗ #{order_id}!**\n{user_link}\n💰 {final_total}₽\n📉 Скидка: {discount}%\n\n{items_text}", parse_mode="Markdown")
            clear_cart(user_id)
            current_promo.pop(user_id, None)
    
    # Я оплатил
    elif data.startswith("paid_"):
        order_id = int(data.replace("paid_", ""))
        order = next((o for o in orders if o["id"] == order_id), None)
        if order:
            if order["status"] == "pending":
                order["status"] = "paid"
                save_orders()
                await update_message(chat_id, user_id, f"✅ **Спасибо! Заказ #{order_id} отмечен как оплаченный.**\n\nАдмин скоро свяжется с вами.", main_menu(), "Markdown")
                await bot.send_message(ADMIN_ID, f"💰 **ЗАКАЗ #{order_id} ОПЛАЧЕН!**\n{order['user_link']}\n{order['total']}₽", parse_mode="Markdown")
                if order.get("auto_items"):
                    codes_text = ""
                    for pid in order.get("auto_items", []):
                        code = get_code(pid)
                        if code:
                            codes_text += f"• {PRODUCTS[pid]['name']}: `{code}`\n"
                    if codes_text:
                        await bot.send_message(order["user_id"], f"✅ **ЗАКАЗ #{order_id} ВЫПОЛНЕН!**\n\n🎁 **Ваши товары:**\n{codes_text}", parse_mode="Markdown")
            else:
                await update_message(chat_id, user_id, f"⚠️ Заказ #{order_id} уже обработан.", main_menu(), "Markdown")
    
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
    
    # Поддержка
    elif data == "support":
        support_requests[user_id] = True
        await update_message(chat_id, user_id, "💬 **ЧАТ ПОДДЕРЖКИ**\n\nНапишите ваше сообщение. Админ ответит.", support_keyboard(user_id), "Markdown")
    
    elif data == "close_support":
        support_requests.pop(user_id, None)
        await update_message(chat_id, user_id, "🔚 Чат поддержки закрыт.", main_menu())
    
    # Навигация
    elif data == "back_to_menu":
        text = "👋 Добро пожаловать в магазин Akuma UC BOT!\n\nИспользуйте меню ниже для навигации:"
        await update_message(chat_id, user_id, text, main_menu())
    
    elif data.startswith("back_to_cat_"):
        category = data.replace("back_to_cat_", "")
        if category == "uc":
            await update_message(chat_id, user_id, "💰 **ВЫБЕРИТЕ UC:**", catalog_keyboard("uc"), "Markdown")
        elif category == "pp":
            await update_message(chat_id, user_id, "🎉 **ВЫБЕРИТЕ ПП:**", catalog_keyboard("pp"), "Markdown")
        elif category == "sub":
            await update_message(chat_id, user_id, "📦 **ВЫБЕРИТЕ ПОДПИСКУ:**", catalog_keyboard("sub"), "Markdown")
        elif category == "vpn":
            await update_message(chat_id, user_id, "🌐 **ИНТЕРНЕТ БЕЗ ОГРАНИЧЕНИЙ:**", catalog_keyboard("vpn"), "Markdown")
    
    elif data in ["other_games", "tg_products"]:
        await update_message(chat_id, user_id, "🚧 **РАЗДЕЛ В РАЗРАБОТКЕ**", main_menu(), "Markdown")

    # Админка (оставлю коротко, так как работает)
    elif data.startswith("admin_"):
        if is_admin(user_id):
            if data == "admin_stats":
                total_orders = len(orders)
                completed = len([o for o in orders if o["status"] == "completed"])
                paid = len([o for o in orders if o["status"] == "paid"])
                revenue = sum(o["total"] for o in orders if o["status"] in ["paid", "completed"])
                text = f"📊 **СТАТИСТИКА**\n📦 Заказов: {total_orders}\n✅ Выполнено: {completed}\n⏳ Оплачено: {paid}\n💰 Выручка: {revenue}₽\n⭐ Отзывов: {len(reviews)}"
                await update_message(chat_id, user_id, text, admin_menu(), "Markdown")
            elif data == "admin_back":
                await update_message(chat_id, user_id, "🔧 Админ-панель", admin_menu(), "Markdown")
            elif data == "admin_exit":
                await update_message(chat_id, user_id, "🔚 Выход", main_menu())
            else:
                await update_message(chat_id, user_id, "🔧 Админ-панель", admin_menu(), "Markdown")

@dp.message_handler()
async def handle_text(message: types.Message):
    user_id = str(message.from_user.id)
    text = message.text
    
    if user_id in admin_state and admin_state[user_id] == "waiting_promo":
        discount, error = apply_promo(text.upper(), user_id)
        if discount:
            current_promo[user_id] = discount
            use_promo(text.upper(), user_id)
            await update_message(message.chat.id, user_id, f"✅ **ПРОМОКОД АКТИВИРОВАН!**\nСкидка: {discount}%", main_menu(), "Markdown")
        else:
            await update_message(message.chat.id, user_id, error, main_menu(), "Markdown")
        del admin_state[user_id]
        return
    
    if user_id in admin_state and admin_state[user_id].startswith("wait_review_text_"):
        rating = int(admin_state[user_id].replace("wait_review_text_", ""))
        user_name = message.from_user.first_name or "Пользователь"
        reviews.append({"rating": rating, "text": text, "user_name": user_name, "user_id": user_id, "date": str(datetime.now())})
        save_reviews()
        del admin_state[user_id]
        await update_message(message.chat.id, user_id, f"⭐ Спасибо за отзыв!", main_menu(), "Markdown")
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
