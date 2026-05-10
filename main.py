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
    "uc_100": {"name": "100 UC", "price": 100, "active": True, "category": "uc"},
    "uc_500": {"name": "500 UC", "price": 450, "active": True, "category": "uc"},
    "uc_1000": {"name": "1000 UC", "price": 850, "active": True, "category": "uc"},
    "pp_1000": {"name": "ПП 1000", "price": 200, "active": True, "category": "pp"},
    "pp_5000": {"name": "ПП 5000", "price": 800, "active": True, "category": "pp"},
    "sub_1m": {
        "name": "Подписка 1 месяц",
        "price": 500,
        "active": True,
        "category": "sub",
    },
    "sub_3m": {
        "name": "Подписка 3 месяца",
        "price": 1300,
        "active": True,
        "category": "sub",
    },
    "sub_6m": {
        "name": "Подписка 6 месяцев",
        "price": 2200,
        "active": True,
        "category": "sub",
    },
    "vpn": {"name": "VPN 30 дней", "price": 300, "active": True, "category": "vpn"},
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
    )
    return keyboard


def catalog_keyboard(category):
    keyboard = InlineKeyboardMarkup(row_width=1)
    for pid, p in PRODUCTS.items():
        if p.get("category") == category and p.get("active", True):
            keyboard.add(
                InlineKeyboardButton(
                    f"{p['name']} — {p['price']}₽", callback_data=f"view_{pid}"
                )
            )
    keyboard.add(InlineKeyboardButton("🔙 ГЛАВНОЕ МЕНЮ", callback_data="back_to_menu"))
    return keyboard


def product_keyboard(pid):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(InlineKeyboardButton("➕ В КОРЗИНУ", callback_data=f"add_{pid}"))
    keyboard.add(InlineKeyboardButton("🔙 НАЗАД", callback_data="back_to_menu"))
    return keyboard


def cart_keyboard(user_id):
    cart = get_cart(user_id)
    keyboard = InlineKeyboardMarkup(row_width=1)
    for pid, item in cart.items():
        keyboard.add(
            InlineKeyboardButton(
                f"❌ {item['name']} x{item['quantity']} = {item['price'] * item['quantity']}₽",
                callback_data=f"remove_{pid}",
            )
        )
    if cart:
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
        InlineKeyboardButton(
            "💬 Чаты с поддержкой", callback_data="admin_support_chats"
        ),
        InlineKeyboardButton("⭐ Отзывы (управление)", callback_data="admin_reviews"),
        InlineKeyboardButton("🔙 Выйти", callback_data="admin_exit"),
    )
    return keyboard


def admin_order_keyboard(order_id):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton(
            "✅ Подтвердить", callback_data=f"complete_order_{order_id}"
        ),
        InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_order_{order_id}"),
        InlineKeyboardButton("💬 Написать", callback_data=f"msg_user_{order_id}"),
        InlineKeyboardButton("🔙 Назад", callback_data="admin_orders"),
    )
    return keyboard


def admin_products_menu():
    keyboard = InlineKeyboardMarkup(row_width=1)
    for pid, p in PRODUCTS.items():
        status = "✅" if p["active"] else "❌"
        keyboard.add(
            InlineKeyboardButton(
                f"{status} {p['name']} — {p['price']}₽",
                callback_data=f"admin_edit_{pid}",
            )
        )
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
        InlineKeyboardButton("⭐⭐⭐⭐⭐ 5", callback_data="review_5"),
    )
    keyboard.add(InlineKeyboardButton("🔙 ГЛАВНОЕ МЕНЮ", callback_data="back_to_menu"))
    return keyboard


def support_keyboard(user_id):
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(InlineKeyboardButton("✖️ ЗАКРЫТЬ ЧАТ", callback_data="close_support"))
    keyboard.add(InlineKeyboardButton("🔙 ГЛАВНОЕ МЕ"�Ю", callback_data="back_to_menu"))
    return keyboard


IMAGE_ID = "AgACAgIAAxkBAAEpEj5qAAF14VBLMN24S1ngXPeedYLmlrcAAmEYaxs8bQFIsoUcN-o04FMBAAMCAANtAAM7BA"

last_message_id = {}


async def update_message(chat_id, user_id, text, reply_markup=None, parse_mode=None):
    msg_id = last_message_id.get(user_id)
    try:
        if msg_id:
            await bot.edit_message_text(
                text, chat_id, msg_id, reply_markup=reply_markup, parse_mode=parse_mode
            )
        else:
            msg = await bot.send_message(
                chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode
            )
            last_message_id[user_id] = msg.message_id
    except:
        msg = await bot.send_message(
            chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode
        )
        last_message_id[user_id] = msg.message_id


@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    user_id = str(message.from_user.id)
    text = "👋 Добро пожаловать в магазин Akuma UC BOT!\n\nИспользуйте меню ниже для навигации:"
    msg = await bot.send_photo(
        message.chat.id, photo=IMAGE_ID, caption=text, reply_markup=main_menu()
    )
    last_message_id[user_id] = msg.message_id


@dp.message_handler(commands=["admin"])
async def admin_login(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    pwd = message.get_args()
    if pwd == ADMIN_PASSWORD:
        await update_message(
            message.chat.id,
            str(message.from_user.id),
            "🔧 **Админ-панель**",
            admin_menu(),
            "Markdown",
        )
    else:
        await message.answer("❌ Неверный пароль")


@dp.message_handler(lambda message: support_requests.get(str(message.from_user.id)))
async def handle_support_message(message: types.Message):
    user_id = str(message.from_user.id)
    await bot.send_message(
        SUPPORT_CHAT_ID,
        f"💬 **Сообщение от пользователя**\n\n{message.text}\n\n[Ответить](tg://user?id={user_id})",
        parse_mode="Markdown",
    )
    await message.answer("✅ Сообщение отправлено администратору! Ожидайте ответа.")


@dp.message_handler()
async def handle_text(message: types.Message):
    user_id = str(message.from_user.id)
    text = message.text

    # Обработка отзыва (ДОЛЖНА БЫТЬ ПЕРВОЙ!)
    if user_id in admin_state and admin_state[user_id].startswith("wait_review_text_"):
        rating = int(admin_state[user_id].replace("wait_review_text_", ""))
        user_name = (
            message.from_user.first_name or message.from_user.username or "Пользователь"
        )

        new_review = {
            "rating": rating,
            "text": text,
            "user_name": user_name,
            "user_id": user_id,
            "date": str(datetime.now()),
        }
        reviews.append(new_review)
        save_reviews()

        del admin_state[user_id]

        await update_message(
            message.chat.id,
            user_id,
            f"⭐ **Спасибо за отзыв!**\n\nВаша оценка: {rating}★\n\nВаш отзыв опубликован в разделе «Отзывы».",
            main_menu(),
            "Markdown",
        )

        await bot.send_message(
            ADMIN_ID,
            f"⭐ **НОВЫЙ ОТЗЫВ!**\nОт: {user_name}\nОценка: {rating}★\nТекст: {text}",
            parse_mode="Markdown",
        )
        return

    # Обработка ответа админа пользователю из поддержки
    if user_id in admin_state and admin_state[user_id].startswith("admin_msg_"):
        target_user = admin_state[user_id].replace("admin_msg_", "")
        await bot.send_message(
            target_user,
            f"💬 **Ответ администратора:**\n\n{text}",
            parse_mode="Markdown",
        )
        await update_message(
            message.chat.id,
            user_id,
            f"✅ Сообщение отправлено пользователю {target_user}",
            admin_menu(),
            "Markdown",
        )
        del admin_state[user_id]
        return

    # Обработка сообщения админу для заказа
    if user_id in admin_state and admin_state[user_id].startswith("msg_"):
        order_id = int(admin_state[user_id].replace("msg_", ""))
        order = next((o for o in orders if o["id"] == order_id), None)
        if order:
            await bot.send_message(
                order["user_id"],
                f"💬 **Сообщение от администратора:**\n\n{text}",
                parse_mode="Markdown",
            )
            await message.answer(
                f"✅ Сообщение отправлено пользователю заказа #{order_id}"
            )
        else:
            await message.answer("❌ Заказ не найден")
        del admin_state[user_id]
        await update_message(
            message.chat.id, user_id, "🔧 Админ-панель", admin_menu(), "Markdown"
        )
        return

    if not is_admin(user_id):
        return

    if user_id in admin_state:
        state = admin_state[user_id]

        if state == "wait_product":
            parts = text.split("|")
            if len(parts) >= 4:
                pid, name, price, category = (
                    parts[0].strip(),
                    parts[1].strip(),
                    parts[2].strip(),
                    parts[3].strip(),
                )
                try:
                    PRODUCTS[pid] = {
                        "name": name,
                        "price": int(price),
                        "active": True,
                        "category": category,
                    }
                    save_products()
                    await message.answer(
                        f"✅ Товар `{name}` добавлен в категорию {category}!",
                        parse_mode="Markdown",
                    )
                except:
                    await message.answer("❌ Цена должна быть числом!")
            else:
                await message.answer(
                    "❌ Неверный формат! Используйте: `id|название|цена|категория`",
                    parse_mode="Markdown",
                )
            del admin_state[user_id]
            await message.answer(
                "📦 Управление товарами:", reply_markup=admin_products_menu()
            )

        elif state.startswith("wait_price_"):
            pid = state.replace("wait_price_", "")
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
            await message.answer(
                "📦 Управление товарами:", reply_markup=admin_products_menu()
            )


admin_state = {}


@dp.callback_query_handler(lambda c: True)
async def handle(callback: types.CallbackQuery):
    data = callback.data
    user_id = str(callback.from_user.id)
    chat_id = callback.message.chat.id
    await bot.answer_callback_query(callback.id)

    # КАТАЛОГ
    if data == "cat_uc":
        await update_message(
            chat_id, user_id, "💰 **ВЫБЕРИТЕ UC:**", catalog_keyboard("uc"), "Markdown"
        )
    elif data == "cat_pp":
        await update_message(
            chat_id, user_id, "🎉 **ВЫБЕРИТЕ ПП:**", catalog_keyboard("pp"), "Markdown"
        )
    elif data == "cat_sub":
        await update_message(
            chat_id,
            user_id,
            "📦 **ВЫБЕРИТЕ ПОДПИСКУ:**",
            catalog_keyboard("sub"),
            "Markdown",
        )
    elif data == "cat_vpn":
        await update_message(
            chat_id,
            user_id,
            "🌐 **ИНТЕРНЕТ БЕЗ ОГРАНИЧЕНИЙ:**",
            catalog_keyboard("vpn"),
            "Markdown",
        )

    # ПРОСМОТР ТОВАРА
    elif data.startswith("view_"):
        pid = data.replace("view_", "")
        p = PRODUCTS.get(pid)
        if p and p.get("active", True):
            await update_message(
                chat_id,
                user_id,
                f"📦 **{p['name']}**\n💰 Цена: {p['price']}₽",
                product_keyboard(pid),
                "Markdown",
            )
        else:
            await update_message(chat_id, user_id, "❌ Товар не найден", main_menu())

    # ДОБАВЛЕНИЕ В КОРЗИНУ
    elif data.startswith("add_"):
        pid = data.replace("add_", "")
        p = PRODUCTS.get(pid)
        if p:
            add_to_cart(user_id, pid, p["name"], p["price"])
            await update_message(
                chat_id, user_id, f"✅ **{p['name']}** добавлен в корзину!", main_menu()
            )

    # КОРЗИНА
    elif data == "show_cart":
        cart = get_cart(user_id)
        if not cart:
            await update_message(
                chat_id, user_id, "🛒 **КОРЗИНА ПУСТА**", main_menu(), "Markdown"
            )
        else:
            text = "🛒 **ВАША КОРЗИНА:**\n\n"
            for item in cart.values():
                text += f"• {item['name']} x{item['quantity']} = {item['price'] * item['quantity']}₽\n"
            text += f"\n💰 **ИТОГО: {get_cart_total(cart)}₽**"
            await update_message(
                chat_id, user_id, text, cart_keyboard(user_id), "Markdown"
            )

    elif data.startswith("remove_"):
        pid = data.replace("remove_", "")
        remove_from_cart(user_id, pid)
        cart = get_cart(user_id)
        if not cart:
            await update_message(
                chat_id, user_id, "🛒 **КОРЗИНА ПУСТА**", main_menu(), "Markdown"
            )
        else:
            text = "🛒 **ВАША КОРЗИНА:**\n\n"
            for item in cart.values():
                text += f"• {item['name']} x{item['quantity']} = {item['price'] * item['quantity']}₽\n"
            text += f"\n💰 **ИТОГО: {get_cart_total(cart)}₽**"
            await update_message(
                chat_id, user_id, text, cart_keyboard(user_id), "Markdown"
            )

    elif data == "clear_cart":
        clear_cart(user_id)
        await update_message(
            chat_id, user_id, "🗑 **КОРЗИНА ОЧИЩЕНА**", main_menu(), "Markdown"
        )

    # ОФОРМЛЕНИЕ ЗАКАЗА
    elif data == "checkout":
        cart = get_cart(user_id)
        if cart:
            total = get_cart_total(cart)
            user = callback.from_user
            order_id = len(orders) + 1

            user_link = (
                f"@{user.username}"
                if user.username
                else f"[{user.first_name or 'Пользователь'}](tg://user?id={user.id})"
            )

            items_text = ""
            for pid, item in cart.items():
                items_text += f"• {item['name']} x{item['quantity']} = {item['price'] * item['quantity']}₽\n"

            orders.append(
                {
                    "id": order_id,
                    "user_id": user_id,
                    "user_link": user_link,
                    "total": total,
                    "items": items_text,
                    "status": "pending",
                    "date": str(datetime.now()),
                }
            )
            save_orders()

            text = f"✅ **ЗАКАЗ #{order_id} ОФОРМЛЕН НА {total}₽**\n\n💳 Реквизиты: **** **** **** 1234\n\n📌 **После оплаты нажмите кнопку «Я оплатил»**"
            keyboard = InlineKeyboardMarkup(row_width=1)
            keyboard.add(
                InlineKeyboardButton("✅ Я ОПЛАТИЛ", callback_data=f"paid_{order_id}")
            )
            keyboard.add(
                InlineKeyboardButton("🔙 ГЛАВНОЕ МЕНЮ", callback_data="back_to_menu")
            )

            await update_message(chat_id, user_id, text, keyboard, "Markdown")
            await bot.send_message(
                ADMIN_ID,
                f"🆕 **НОВЫЙ ЗАКАЗ #{order_id}!**\n{user_link}\n💰 {total}₽\n\n{items_text}",
                parse_mode="Markdown",
            )
            clear_cart(user_id)

    # Я ОПЛАТИЛ
    elif data.startswith("paid_"):
        order_id = int(data.replace("paid_", ""))
        order = next((o for o in orders if o["id"] == order_id), None)
        if order:
            order["status"] = "paid"
            save_orders()
            await update_message(
                chat_id,
                user_id,
                f"✅ **Спасибо! Заказ #{order_id} отмечен как оплаченный.**\n\nАдмин скоро свяжется с вами.",
                main_menu(),
                "Markdown",
            )
            await bot.send_message(
                ADMIN_ID,
                f"💰 **ЗАКАЗ #{order_id} ОПЛАЧЕН!**\n{order['user_link']}\n{order['total']}₽",
                parse_mode="Markdown",
            )

    # ===== ОТЗЫВЫ (ИСПРАВЛЕННЫЕ) =====
    elif data == "show_reviews":
        if not reviews:
            await update_message(
                chat_id,
                user_id,
                "⭐ **ОТЗЫВЫ**\n\nПока нет отзывов. Будьте первым!\n\nЧтобы оставить отзыв, нажмите на количество звёзд:",
                reviews_keyboard(),
                "Markdown",
            )
        else:
            text = "⭐ **ОТЗЫВЫ ПОКУПАТЕЛЕЙ:**\n\n"
            for r in reviews[-10:]:
                stars = "⭐" * r["rating"]
                text += f"{stars} {r['rating']}/5\n{r['text']}\n— {r['user_name']}\n📅 {r['date']}\n\n"
            keyboard = InlineKeyboardMarkup(row_width=1)
            keyboard.add(
                InlineKeyboardButton("📝 ОСТАВИТЬ ОТЗЫВ", callback_data="leave_review")
            )
            keyboard.add(
                InlineKeyboardButton("🔙 ГЛАВНОЕ МЕНЮ", callback_data="back_to_menu")
            )
            await update_message(chat_id, user_id, text, keyboard, "Markdown")

    elif data == "leave_review":
        await update_message(
            chat_id,
            user_id,
            "⭐ **ОЦЕНИТЕ НАШ МАГАЗИН:**\n\nВыберите количество звёзд:",
            reviews_keyboard(),
            "Markdown",
        )

    elif data in ["review_1", "review_2", "review_3", "review_4", "review_5"]:
        rating = int(data.replace("review_", ""))
        admin_state[user_id] = f"wait_review_text_{rating}"
        await update_message(
            chat_id,
            user_id,
            f"⭐ Вы выбрали {rating} звёзд.\n\nНапишите текст отзыва:",
            None,
        )

    # ПОДДЕРЖКА
    elif data == "support":
        support_requests[user_id] = True
        await update_message(
            chat_id,
            user_id,
            "💬 **ЧАТ ПОДДЕРЖКИ**\n\nНапишите ваше сообщение. Администратор ответит вам как можно скорее.\n\nЧтобы закрыть чат, нажмите кнопку ниже.",
            support_keyboard(user_id),
            "Markdown",
        )

    elif data == "close_support":
        support_requests.pop(user_id, None)
        await update_message(
            chat_id,
            user_id,
            "🔚 Чат поддержки закрыт. Если появятся вопросы — снова нажмите «Поддержка» в меню.",
            main_menu(),
        )

    # ГЛАВНОЕ МЕНЮ
    elif data == "back_to_menu":
        text = "👋 Добро пожаловать в магазин Akuma UC BOT!\n\nИспользуйте меню ниже для навигации:"
        await update_message(chat_id, user_id, text, main_menu())

    elif data in ["other_games", "tg_products"]:
        await update_message(
            chat_id, user_id, "🚧 **РАЗДЕЛ В РАЗРАБОТКЕ**", main_menu(), "Markdown"
        )

    # АДМИНКА
    elif data == "admin_stats" and is_admin(user_id):
        total_orders = len(orders)
        completed_orders = len([o for o in orders if o["status"] == "completed"])
        paid_orders = len([o for o in orders if o["status"] == "paid"])
        total_revenue = sum(
            o["total"] for o in orders if o["status"] in ["paid", "completed"]
        )

        product_sales = {}
        for order in orders:
            for line in order["items"].split("\n"):
                if "x" in line:
                    try:
                        name_part = line.split("x")[0].strip("• ")
                        product_sales[name_part] = product_sales.get(name_part, 0) + 1
                    except:
                        pass

        top_products = sorted(product_sales.items(), key=lambda x: x[1], reverse=True)[
            :5
        ]
        top_text = (
            "\n".join([f"• {name}: {count} шт" for name, count in top_products])
            if top_products
            else "Нет продаж"
        )

        text = f"📊 **СТАТИСТИКА ПРОДАЖ**\n\n"
        text += f"📦 Всего заказов: {total_orders}\n"
        text += f"✅ Выполнено: {completed_orders}\n"
        text += f"⏳ Оплачено, ожидают: {paid_orders}\n"
        text += f"💰 Общая выручка: {total_revenue}₽\n\n"
        text += f"🔥 **Топ товаров:**\n{top_text}\n\n"
        text += f"⭐ Отзывов оставлено: {len(reviews)}"

        keyboard = InlineKeyboardMarkup(row_width=1)
        keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="admin_back"))
        await update_message(chat_id, user_id, text, keyboard, "Markdown")

    elif data == "admin_reviews" and is_admin(user_id):
        if not reviews:
            await update_message(
                chat_id, user_id, "⭐ Отзывов пока нет", admin_menu(), "Markdown"
            )
        else:
            text = "⭐ **УПРАВЛЕНИЕ ОТЗЫВАМИ**\n\n"
            for i, r in enumerate(reviews[-10:]):
                stars = "⭐" * r["rating"]
                text += f"{stars} {r['rating']}/5\n{r['text']}\n— {r['user_name']}\n\n"
            keyboard = InlineKeyboardMarkup(row_width=1)
            keyboard.add(
                InlineKeyboardButton(
                    "🗑 Удалить последний отзыв",
                    callback_data="admin_delete_last_review",
                )
            )
            keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="admin_back"))
            await update_message(chat_id, user_id, text, keyboard, "Markdown")

    elif data == "admin_delete_last_review" and is_admin(user_id):
        if reviews:
            deleted = reviews.pop()
            save_reviews()
            await update_message(
                chat_id,
                user_id,
                f"✅ Удалён отзыв от {deleted['user_name']}",
                admin_menu(),
                "Markdown",
            )
        else:
            await update_message(
                chat_id, user_id, "❌ Отзывов больше нет", admin_menu(), "Markdown"
            )

    elif data == "admin_support_chats" and is_admin(user_id):
        active_chats = list(support_requests.keys())
        if not active_chats:
            await update_message(
                chat_id,
                user_id,
                "💬 Нет активных чатов поддержки",
                admin_menu(),
                "Markdown",
            )
        else:
            text = "💬 **Активные чаты поддержки:**\n\n"
            for uid in active_chats:
                text += f"• {uid}\n"
            keyboard = InlineKeyboardMarkup(row_width=1)
            for uid in active_chats:
                keyboard.add(
                    InlineKeyboardButton(
                        f"💬 Написать пользователю {uid}",
                        callback_data=f"admin_msg_user_{uid}",
                    )
                )
            keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="admin_back"))
            await update_message(chat_id, user_id, text, keyboard, "Markdown")

    elif data.startswith("admin_msg_user_") and is_admin(user_id):
        target_user = data.replace("admin_msg_user_", "")
        admin_state[user_id] = f"admin_msg_{target_user}"
        await update_message(
            chat_id,
            user_id,
            f"💬 Введите сообщение для пользователя {target_user}:",
            None,
        )

    elif data == "admin_products" and is_admin(user_id):
        await update_message(
            chat_id,
            user_id,
            "📦 **Управление товарами:**",
            admin_products_menu(),
            "Markdown",
        )

    elif data == "admin_orders" and is_admin(user_id):
        if not orders:
            await update_message(
                chat_id, user_id, "📭 Заказов пока нет", admin_menu(), "Markdown"
            )
        else:
            text = "📋 **СПИСОК ЗАКАЗОВ**\n\n"
            for order in orders[-10:]:
                status_emoji = (
                    "✅"
                    if order["status"] == "completed"
                    else "⏳"
                    if order["status"] == "paid"
                    else "🆕"
                )
                text += f"{status_emoji} #{order['id']} | {order['user_link']} | {order['total']}₽ | {order['status']}\n"
            keyboard = InlineKeyboardMarkup(row_width=1)
            for order in orders[-10:]:
                keyboard.add(
                    InlineKeyboardButton(
                        f"📋 Заказ #{order['id']}",
                        callback_data=f"admin_view_order_{order['id']}",
                    )
                )
            keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="admin_back"))
            await update_message(chat_id, user_id, text, keyboard, "Markdown")

    elif data == "admin_pending" and is_admin(user_id):
        paid_orders = [o for o in orders if o["status"] == "paid"]
        if not paid_orders:
            await update_message(
                chat_id,
                user_id,
                "⏳ Нет заказов, ожидающих выдачи товара",
                admin_menu(),
                "Markdown",
            )
        else:
            text = "⏳ **ЗАКАЗЫ, ОЖИДАЮЩИЕ ВЫДАЧИ:**\n\n"
            for o in paid_orders[-10:]:
                text += f"🆔 #{o['id']} | {o['user_link']} | {o['total']}₽\n"
            keyboard = InlineKeyboardMarkup(row_width=1)
            for o in paid_orders[-10:]:
                keyboard.add(
                    InlineKeyboardButton(
                        f"📦 Выдать товар для заказа #{o['id']}",
                        callback_data=f"complete_order_{o['id']}",
                    )
                )
            keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="admin_back"))
            await update_message(chat_id, user_id, text, keyboard, "Markdown")

    elif data.startswith("admin_view_order_") and is_admin(user_id):
        order_id = int(data.replace("admin_view_order_", ""))
        order = next((o for o in orders if o["id"] == order_id), None)
        if order:
            status_text = {
                "pending": "🆕 Ожидает оплаты",
                "paid": "💰 Оплачен, ожидает выдачи",
                "completed": "✅ Выполнен",
            }.get(order["status"], order["status"])
            text = f"📋 **ЗАКАЗ #{order['id']}**\n{order['user_link']}\nСтатус: {status_text}\n💰 Сумма: {order['total']}₽\n📅 {order['date']}\n\n**Товары:**\n{order['items']}"
            await update_message(
                chat_id, user_id, text, admin_order_keyboard(order_id), "Markdown"
            )

    elif data.startswith("complete_order_") and is_admin(user_id):
        order_id = int(data.replace("complete_order_", ""))
        order = next((o for o in orders if o["id"] == order_id), None)
        if order:
            order["status"] = "completed"
            save_orders()
            await update_message(
                chat_id,
                user_id,
                f"✅ Заказ #{order_id} отмечен как выполненный!",
                admin_menu(),
                "Markdown",
            )
            await bot.send_message(
                order["user_id"],
                f"✅ **ВАШ ЗАКАЗ #{order_id} ВЫПОЛНЕН!**\n\nЕсли хотите оставить отзыв, нажмите кнопку «Отзывы» в главном меню.",
                parse_mode="Markdown",
            )

    elif data.startswith("reject_order_") and is_admin(user_id):
        order_id = int(data.replace("reject_order_", ""))
        order = next((o for o in orders if o["id"] == order_id), None)
        if order:
            await bot.send_message(
                order["user_id"],
                f"❌ **ЗАКАЗ #{order_id} ОТКЛОНЁН**\n\nПожалуйста, свяжитесь с @aakumma",
                parse_mode="Markdown",
            )
            orders.remove(order)
            save_orders()
            await update_message(
                chat_id,
                user_id,
                f"❌ Заказ #{order_id} отклонён",
                admin_menu(),
                "Markdown",
            )

    elif data.startswith("msg_user_") and is_admin(user_id):
        order_id = int(data.replace("msg_user_", ""))
        admin_state[user_id] = f"msg_{order_id}"
        await update_message(
            chat_id,
            user_id,
            f"💬 Напишите сообщение для пользователя заказа #{order_id}:",
            None,
        )

    elif data == "admin_exit" and is_admin(user_id):
        await update_message(chat_id, user_id, "🔚 Выход из админ-панели", main_menu())

    elif data == "admin_back" and is_admin(user_id):
        await update_message(
            chat_id, user_id, "🔧 **Админ-панель**", admin_menu(), "Markdown"
        )

    elif data.startswith("admin_edit_") and is_admin(user_id):
        pid = data.replace("admin_edit_", "")
        p = PRODUCTS.get(pid)
        if p:
            kb = InlineKeyboardMarkup(row_width=2)
            kb.add(
                InlineKeyboardButton(
                    "🔄 Вкл/Выкл", callback_data=f"admin_toggle_{pid}"
                ),
                InlineKeyboardButton(
                    f"💰 {p['price']}₽", callback_data=f"admin_price_{pid}"
                ),
                InlineKeyboardButton("❌ Удалить", callback_data=f"admin_delete_{pid}"),
                InlineKeyboardButton("🔙 Назад", callback_data="admin_products"),
            )
            status = "✅ Активен" if p["active"] else "❌ Неактивен"
            await update_message(
                chat_id,
                user_id,
                f"📦 **{p['name']}**\n{status}\n💰 {p['price']}₽",
                kb,
                "Markdown",
            )

    elif data.startswith("admin_toggle_") and is_admin(user_id):
        pid = data.replace("admin_toggle_", "")
        if pid in PRODUCTS:
            PRODUCTS[pid]["active"] = not PRODUCTS[pid]["active"]
            save_products()
            await update_message(
                chat_id,
                user_id,
                f"✅ Товар {'активирован' if PRODUCTS[pid]['active'] else 'деактивирован'}",
                admin_products_menu(),
                "Markdown",
            )

    elif data.startswith("admin_price_") and is_admin(user_id):
        pid = data.replace("admin_price_", "")
        admin_state[user_id] = f"wait_price_{pid}"
        await update_message(
            chat_id,
            user_id,
            f"💰 Введите новую цену для {PRODUCTS[pid]['name']} (в рублях):",
            None,
        )

    elif data.startswith("admin_delete_") and is_admin(user_id):
        pid = data.replace("admin_delete_", "")
        if pid in PRODUCTS:
            del PRODUCTS[pid]
            save_products()
            await update_message(
                chat_id, user_id, "✅ Товар удалён", admin_products_menu(), "Markdown"
            )

    elif data == "admin_add" and is_admin(user_id):
        admin_state[user_id] = "wait_product"
        await update_message(
            chat_id,
            user_id,
            "➕ Введите данные нового товара в формате:\n\n`id|название|цена|категория`\n\nКатегории: uc, pp, sub, vpn\n\nПример: `new_1|Новый товар|500|uc`",
            None,
            "Markdown",
        )


@dp.message_handler(commands=["ping"])
async def ping(m: types.Message):
    await m.answer("🏓 Bot is alive!")


app = Flask(__name__)


@app.route("/")
def home():
    return "Bot is alive!"


def run():
    app.run(host="0.0.0.0", port=8080)


def keep_alive():
    Thread(target=run).start()


if __name__ == "__main__":
    keep_alive()
    executor.start_polling(dp, skip_updates=True)
