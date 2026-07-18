import telebot
from telebot import types
import json
import os
import base64
import requests

# ---- Sozlamalar ----
ADMIN_BOT_TOKEN = os.environ.get("ADMIN_BOT_TOKEN", "")
ADMIN_PANEL_URL = "https://abdulhodiyamirdin-777.github.io/Dokon/admin_panel.html"
OWNER_ID = "8881459774"  # bosh admin

GITHUB_REPO = "abdulhodiyamirdin-777/Dokon"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

bot = telebot.TeleBot(ADMIN_BOT_TOKEN)


# ==============================================================
# GitHub bilan ishlash (mustaqil, boshqa fayllarga bog'liq emas)
# ==============================================================

def _api_url(filename):
    return f"https://api.github.com/repos/{GITHUB_REPO}/contents/{filename}"


def gh_read(filename, default):
    try:
        r = requests.get(_api_url(filename), headers={"Authorization": f"token {GITHUB_TOKEN}"})
        r.raise_for_status()
        content = base64.b64decode(r.json()["content"]).decode("utf-8")
        return json.loads(content)
    except Exception as e:
        print(f"{filename} o'qilmadi:", e)
        return default


def gh_write(filename, data, commit_message):
    try:
        r = requests.get(_api_url(filename), headers={"Authorization": f"token {GITHUB_TOKEN}"})
        sha = r.json().get("sha") if r.status_code == 200 else None
        payload = {
            "message": commit_message,
            "content": base64.b64encode(
                json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
            ).decode("utf-8"),
        }
        if sha:
            payload["sha"] = sha
        requests.put(_api_url(filename), headers={"Authorization": f"token {GITHUB_TOKEN}"}, json=payload)
        return True
    except Exception as e:
        print(f"{filename} yozilmadi:", e)
        return False


# ==============================================================
# Admin tekshiruvi
# ==============================================================

def is_admin(user_id):
    admins = gh_read("admins.json", {})
    return str(user_id) in admins


def ensure_owner_seeded():
    """Birinchi ishga tushganda, agar admins.json bo'sh bo'lsa, bosh adminni qo'shadi."""
    admins = gh_read("admins.json", {})
    if OWNER_ID not in admins:
        admins[OWNER_ID] = {"role": "Bosh admin", "owner": True}
        gh_write("admins.json", admins, "Bosh admin qoshildi")


# ==============================================================
# Handlerlar
# ==============================================================

@bot.message_handler(commands=["start"])
def start_handler(message):
    user_id = str(message.from_user.id)
    ensure_owner_seeded()

    if not is_admin(user_id):
        bot.send_message(message.chat.id, "🔒 Bu bot faqat adminlar uchun.")
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton(
        text="⚙️ Panelni ochish",
        web_app=types.WebAppInfo(url=ADMIN_PANEL_URL)
    ))
    bot.send_message(message.chat.id, "Admin panelga xush kelibsiz 👇", reply_markup=markup)


@bot.message_handler(content_types=["web_app_data"])
def web_app_data_handler(message):
    user_id = str(message.from_user.id)
    if not is_admin(user_id):
        bot.send_message(message.chat.id, "🔒 Sizda ruxsat yo'q.")
        return

    try:
        data = json.loads(message.web_app_data.data)
    except Exception:
        bot.send_message(message.chat.id, "Xatolik yuz berdi.")
        return

    action = data.get("type")
    ok = False

    if action == "edit_price":
        ok = handle_edit_price(data)
    elif action == "toggle_active":
        ok = handle_toggle_active(data)
    elif action == "delete_product":
        ok = handle_delete_product(data)
    elif action == "add_product":
        ok = handle_add_product(data)
    elif action == "order_status":
        ok = handle_order_status(data)
    elif action == "delete_review":
        ok = handle_delete_review(data)
    elif action == "add_admin":
        ok = handle_add_admin(data, user_id)
    elif action == "remove_admin":
        ok = handle_remove_admin(data)

    bot.send_message(message.chat.id, "✅ Bajarildi" if ok else "❌ Xatolik yuz berdi, qaytadan urinib ko'ring.")


# ---- Mahsulotlar ----

def handle_edit_price(data):
    products = gh_read("products.json", [])
    pid = str(data.get("product_id"))
    for p in products:
        if str(p["id"]) == pid:
            p["price"] = data.get("price")
            if p.get("tiers"):
                p["tiers"][0]["price"] = data.get("price")
    return gh_write("products.json", products, f"Narx yangilandi: {pid}")


def handle_toggle_active(data):
    products = gh_read("products.json", [])
    pid = str(data.get("product_id"))
    for p in products:
        if str(p["id"]) == pid:
            p["active"] = data.get("active", True)
    return gh_write("products.json", products, f"Faollik holati: {pid}")


def handle_delete_product(data):
    products = gh_read("products.json", [])
    pid = str(data.get("product_id"))
    products = [p for p in products if str(p["id"]) != pid]
    return gh_write("products.json", products, f"Mahsulot ochirildi: {pid}")


def handle_add_product(data):
    products = gh_read("products.json", [])
    next_id = max([int(p["id"]) for p in products], default=0) + 1
    new_product = {
        "id": next_id,
        "name": data.get("name", ""),
        "price": data.get("price", 0),
        "cat": data.get("cat", ""),
        "image": data.get("image", ""),
        "active": True,
    }
    if data.get("tiers"):
        new_product["tiers"] = data["tiers"]
    products.append(new_product)
    return gh_write("products.json", products, f"Yangi mahsulot: {new_product['name']}")


# ---- Buyurtmalar ----

def handle_order_status(data):
    orders = gh_read("orders.json", {})
    oid = str(data.get("order_id"))
    if oid in orders:
        orders[oid]["status"] = data.get("status", "Yangi")
        return gh_write("orders.json", orders, f"Buyurtma holati: #{oid} -> {data.get('status')}")
    return False


# ---- Sharhlar ----

def handle_delete_review(data):
    reviews = gh_read("reviews.json", {})
    pid = str(data.get("product_id"))
    idx = data.get("index")
    if pid in reviews and idx is not None and 0 <= idx < len(reviews[pid]):
        reviews[pid].pop(idx)
        return gh_write("reviews.json", reviews, f"Sharh ochirildi: mahsulot {pid}")
    return False


# ---- Adminlar ----

def handle_add_admin(data, requester_id):
    admins = gh_read("admins.json", {})
    new_id = str(data.get("admin_id"))
    admins[new_id] = {"role": data.get("role", "Admin"), "owner": False}
    return gh_write("admins.json", admins, f"Yangi admin: {new_id}")


def handle_remove_admin(data):
    admins = gh_read("admins.json", {})
    rid = str(data.get("admin_id"))
    if rid in admins and not admins[rid].get("owner"):
        del admins[rid]
        return gh_write("admins.json", admins, f"Admin ochirildi: {rid}")
    return False


print("Admin bot ishga tushdi...")
bot.infinity_polling()
