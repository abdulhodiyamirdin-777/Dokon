import telebot
from telebot import types
import json
import os
import base64
import requests
from datetime import datetime
from github_helper import get_stats, save_stats

# ---- Sozlamalar ----
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
WEBAPP_URL = "https://abdulhodiyamirdin-777.github.io/Dokon/dokon-yakuniy.html"
ADMIN_CHAT_ID = 8881459774

GITHUB_REPO = "abdulhodiyamirdin-777/Dokon"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
CASHBACK_RATE = 0.01  # 1%

bot = telebot.TeleBot(BOT_TOKEN)


# ==============================================================
# users.json bilan ishlash (keshbek + referal ma'lumotlari)
# Bu funksiyalar github_helper.py'ga bog'liq emas - mustaqil ishlaydi
# ==============================================================

def _users_api_url():
    return f"https://api.github.com/repos/{GITHUB_REPO}/contents/users.json"


def get_users():
    try:
        r = requests.get(_users_api_url(), headers={"Authorization": f"token {GITHUB_TOKEN}"})
        r.raise_for_status()
        content = base64.b64decode(r.json()["content"]).decode("utf-8")
        return json.loads(content)
    except Exception as e:
        print("users.json o'qilmadi:", e)
        return {}


def save_users(users, commit_message):
    try:
        r = requests.get(_users_api_url(), headers={"Authorization": f"token {GITHUB_TOKEN}"})
        sha = r.json().get("sha") if r.status_code == 200 else None
        payload = {
            "message": commit_message,
            "content": base64.b64encode(
                json.dumps(users, ensure_ascii=False, indent=2).encode("utf-8")
            ).decode("utf-8"),
        }
        if sha:
            payload["sha"] = sha
        requests.put(_users_api_url(), headers={"Authorization": f"token {GITHUB_TOKEN}"}, json=payload)
    except Exception as e:
        print("users.json yozilmadi:", e)


def ensure_user(users, user_id):
    user_id = str(user_id)
    if user_id not in users:
        users[user_id] = {
            "cashback_balance": 0,
            "referred_by": None,
            "referral_count": 0,
            "orders": [],
        }
    return users[user_id]


def register_referral(new_user_id, referrer_id):
    new_user_id, referrer_id = str(new_user_id), str(referrer_id)
    if new_user_id == referrer_id:
        return
    users = get_users()
    me = ensure_user(users, new_user_id)
    if me["referred_by"] is not None:
        return  # allaqachon ro'yxatdan o'tgan, qayta yozilmaydi
    me["referred_by"] = referrer_id
    ensure_user(users, referrer_id)["referral_count"] += 1
    save_users(users, f"Referal: {referrer_id} <- {new_user_id}")


def _orders_api_url():
    return f"https://api.github.com/repos/{GITHUB_REPO}/contents/orders.json"


def get_orders():
    try:
        r = requests.get(_orders_api_url(), headers={"Authorization": f"token {GITHUB_TOKEN}"})
        r.raise_for_status()
        content = base64.b64decode(r.json()["content"]).decode("utf-8")
        return json.loads(content)
    except Exception as e:
        print("orders.json o'qilmadi:", e)
        return {}


def save_orders(orders, commit_message):
    try:
        r = requests.get(_orders_api_url(), headers={"Authorization": f"token {GITHUB_TOKEN}"})
        sha = r.json().get("sha") if r.status_code == 200 else None
        payload = {
            "message": commit_message,
            "content": base64.b64encode(
                json.dumps(orders, ensure_ascii=False, indent=2).encode("utf-8")
            ).decode("utf-8"),
        }
        if sha:
            payload["sha"] = sha
        requests.put(_orders_api_url(), headers={"Authorization": f"token {GITHUB_TOKEN}"}, json=payload)
    except Exception as e:
        print("orders.json yozilmadi:", e)


def record_order(user_id, order):
    """Admin panelda ko'rinishi uchun har bir buyurtmani alohida saqlaydi."""
    orders = get_orders()
    next_id = max([int(k) for k in orders.keys()], default=10000) + 1
    orders[str(next_id)] = {
        "customer": order.get("name", ""),
        "phone": order.get("phone", ""),
        "address": order.get("address", ""),
        "items": order.get("items", []),
        "total": order.get("total", 0),
        "status": "Yangi",
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "user_id": str(user_id),
    }
    save_orders(orders, f"Yangi buyurtma #{next_id}")
    return next_id


def process_order_cashback(user_id, order):
    user_id = str(user_id)
    total = order.get("total", 0)
    items = order.get("items", [])

    users = get_users()
    me = ensure_user(users, user_id)

    earned = round(total * CASHBACK_RATE)
    me["cashback_balance"] += earned
    me["orders"].append({
        "date": datetime.now().strftime("%d.%m.%Y"),
        "items": [{"name": i["name"], "qty": i["qty"]} for i in items],
        "total": total,
        "cashback_earned": earned,
    })

    if me["referred_by"]:
        ensure_user(users, me["referred_by"])["cashback_balance"] += round(total * CASHBACK_RATE)

    save_users(users, f"Buyurtma: {user_id} (+{earned} keshbek)")


# ==============================================================
# reviews.json bilan ishlash (mahsulot sharhlari)
# ==============================================================

def _reviews_api_url():
    return f"https://api.github.com/repos/{GITHUB_REPO}/contents/reviews.json"


def get_reviews():
    try:
        r = requests.get(_reviews_api_url(), headers={"Authorization": f"token {GITHUB_TOKEN}"})
        r.raise_for_status()
        content = base64.b64decode(r.json()["content"]).decode("utf-8")
        return json.loads(content)
    except Exception as e:
        print("reviews.json o'qilmadi:", e)
        return {}


def save_reviews(reviews, commit_message):
    try:
        r = requests.get(_reviews_api_url(), headers={"Authorization": f"token {GITHUB_TOKEN}"})
        sha = r.json().get("sha") if r.status_code == 200 else None
        payload = {
            "message": commit_message,
            "content": base64.b64encode(
                json.dumps(reviews, ensure_ascii=False, indent=2).encode("utf-8")
            ).decode("utf-8"),
        }
        if sha:
            payload["sha"] = sha
        requests.put(_reviews_api_url(), headers={"Authorization": f"token {GITHUB_TOKEN}"}, json=payload)
    except Exception as e:
        print("reviews.json yozilmadi:", e)


def process_review(user_id, data):
    product_id = str(data.get("product_id"))
    rating = int(data.get("rating", 0))
    comment = data.get("comment", "")

    reviews = get_reviews()
    if product_id not in reviews:
        reviews[product_id] = []
    reviews[product_id].append({
        "user_id": str(user_id),
        "rating": rating,
        "comment": comment,
        "date": datetime.now().strftime("%d.%m.%Y"),
    })
    save_reviews(reviews, f"Sharh: mahsulot {product_id}, {rating} yulduz")


# ==============================================================
# Bot handlerlar
# ==============================================================

@bot.message_handler(commands=["start"])
def start_handler(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) > 1 and parts[1].startswith("ref"):
        try:
            register_referral(message.from_user.id, parts[1][3:])
        except Exception as e:
            print("Referal yozilmadi:", e)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton(
        text="🛍️ Do'konni ochish",
        web_app=types.WebAppInfo(url=WEBAPP_URL)
    ))
    bot.send_message(
        message.chat.id,
        "Assalomu alaykum! Do'konimizga xush kelibsiz.\n"
        "Mahsulotlarni ko'rish uchun pastdagi tugmani bosing 👇",
        reply_markup=markup,
    )


@bot.message_handler(content_types=["web_app_data"])
def web_app_data_handler(message):
    try:
        data = json.loads(message.web_app_data.data)
    except Exception:
        bot.send_message(message.chat.id, "Xatolik yuz berdi, qaytadan urinib ko'ring.")
        return

    if data.get("type") == "review":
        try:
            process_review(message.from_user.id, data)
            bot.send_message(message.chat.id, "✅ Sharhingiz uchun rahmat!")
        except Exception as e:
            print("Sharh saqlanmadi:", e)
            bot.send_message(message.chat.id, "Xatolik yuz berdi, qaytadan urinib ko'ring.")
        return

    order = data

    lines = ["🆕 <b>Yangi buyurtma</b>\n"]
    for item in order.get("items", []):
        lines.append(f"• {item['name']} × {item['qty']} = {item['price'] * item['qty']:,} so'm")

    total = order.get("total", 0)
    lines.append(f"\n💰 <b>Jami:</b> {total:,} so'm")
    lines.append(f"\n👤 <b>Mijoz:</b> {order.get('name')}")
    lines.append(f"📞 <b>Telefon:</b> {order.get('phone')}")
    lines.append(f"📍 <b>Manzil:</b> {order.get('address')}")

    order_text = "\n".join(lines)

    try:
        order_id = record_order(message.from_user.id, order)
        order_text = f"🆕 <b>Yangi buyurtma #{order_id}</b>\n" + order_text.split("\n", 1)[1]
    except Exception as e:
        print("Buyurtma saqlanmadi:", e)

    bot.send_message(ADMIN_CHAT_ID, order_text, parse_mode="HTML")
    bot.send_message(
        message.chat.id,
        "✅ Buyurtmangiz qabul qilindi!\nTez orada operatorimiz siz bilan bog'lanadi."
    )

    # Statistikani yangilash (GitHub orqali)
    try:
        stats = get_stats()
        stats["orders"] = stats.get("orders", 0) + 1
        stats["revenue"] = stats.get("revenue", 0) + total
        save_stats(stats, "Yangi buyurtma statistikasi")
    except Exception as e:
        print("Statistika yangilanmadi:", e)

    # Keshbek + referal
    try:
        process_order_cashback(message.from_user.id, order)
    except Exception as e:
        print("Keshbek yangilanmadi:", e)


print("Savdo boti ishga tushdi...")
bot.infinity_polling()
