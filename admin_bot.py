import telebot
from telebot import types
from github_helper import get_products, save_products, get_stats

# ---- Sozlamalar ----
ADMIN_BOT_TOKEN = "8305630868:AAGHrpBH6BMFZkjpDhZR0TMUPVBz_JqvamI"
ADMIN_CHAT_ID = 8881459774                       # Faqat shu odam boshqara oladi

bot = telebot.TeleBot(ADMIN_BOT_TOKEN)


def is_admin(message):
    return message.chat.id == ADMIN_CHAT_ID


@bot.message_handler(commands=["start"])
def start_handler(message):
    if not is_admin(message):
        bot.send_message(message.chat.id, "Sizda ruxsat yo'q.")
        return
    bot.send_message(
        message.chat.id,
        "👋 Admin panelga xush kelibsiz!\n\n"
        "Buyruqlar:\n"
        "/royxat — mahsulotlar ro'yxati\n"
        "/narx [ID] [yangi_narx] — narxni o'zgartirish\n"
        "/qoshish [Nomi] | [Narx] | [Kategoriya] | [rasm.jpg] — yangi mahsulot\n"
        "/ochirish [ID] — mahsulotni o'chirish\n"
        "/statistika — buyurtmalar statistikasi"
    )


@bot.message_handler(commands=["royxat"])
def list_handler(message):
    if not is_admin(message):
        return
    products = get_products()
    if not products:
        bot.send_message(message.chat.id, "Mahsulotlar topilmadi.")
        return
    lines = []
    for p in products:
        lines.append(f"#{p['id']} — {p['name']} — {p['price']:,} so'm — {p.get('cat','')}")
    bot.send_message(message.chat.id, "\n".join(lines))


@bot.message_handler(commands=["narx"])
def price_handler(message):
    if not is_admin(message):
        return
    try:
        parts = message.text.split()
        pid = int(parts[1])
        new_price = int(parts[2])
    except (IndexError, ValueError):
        bot.send_message(message.chat.id, "Foydalanish: /narx [ID] [yangi_narx]\nMisol: /narx 1 95000")
        return

    products = get_products()
    found = False
    for p in products:
        if p["id"] == pid:
            p["price"] = new_price
            found = True
            break

    if not found:
        bot.send_message(message.chat.id, f"#{pid} raqamli mahsulot topilmadi.")
        return

    ok = save_products(products, f"Narx yangilandi: #{pid}")
    if ok:
        bot.send_message(message.chat.id, f"✅ #{pid} narxi {new_price:,} so'mga o'zgartirildi.")
    else:
        bot.send_message(message.chat.id, "❌ Xatolik: GitHub'ga yozib bo'lmadi. Tokenni tekshiring.")


@bot.message_handler(commands=["qoshish"])
def add_handler(message):
    if not is_admin(message):
        return
    try:
        text = message.text.split(" ", 1)[1]
        name, price, cat, image = [x.strip() for x in text.split("|")]
        price = int(price)
    except Exception:
        bot.send_message(
            message.chat.id,
            "Foydalanish:\n/qoshish Nomi | Narx | Kategoriya | rasm.jpg\n\n"
            "Misol:\n/qoshish Simsiz sichqoncha | 45000 | Gadjetlar | sichqoncha.jpg"
        )
        return

    products = get_products()
    new_id = max([p["id"] for p in products], default=0) + 1
    products.append({"id": new_id, "name": name, "price": price, "cat": cat, "image": image})

    ok = save_products(products, f"Yangi mahsulot qo'shildi: {name}")
    if ok:
        bot.send_message(message.chat.id, f"✅ '{name}' #{new_id} raqami bilan qo'shildi.")
    else:
        bot.send_message(message.chat.id, "❌ Xatolik yuz berdi.")


@bot.message_handler(commands=["ochirish"])
def delete_handler(message):
    if not is_admin(message):
        return
    try:
        pid = int(message.text.split()[1])
    except (IndexError, ValueError):
        bot.send_message(message.chat.id, "Foydalanish: /ochirish [ID]")
        return

    products = get_products()
    new_products = [p for p in products if p["id"] != pid]

    if len(new_products) == len(products):
        bot.send_message(message.chat.id, f"#{pid} raqamli mahsulot topilmadi.")
        return

    ok = save_products(new_products, f"Mahsulot o'chirildi: #{pid}")
    if ok:
        bot.send_message(message.chat.id, f"✅ #{pid} o'chirildi.")
    else:
        bot.send_message(message.chat.id, "❌ Xatolik yuz berdi.")


@bot.message_handler(commands=["statistika"])
def stats_handler(message):
    if not is_admin(message):
        return
    stats = get_stats()
    bot.send_message(
        message.chat.id,
        f"📊 <b>Statistika</b>\n\n"
        f"🧾 Buyurtmalar soni: {stats.get('orders', 0)}\n"
        f"💰 Umumiy tushum: {stats.get('revenue', 0):,} so'm",
        parse_mode="HTML"
    )


print("Admin bot ishga tushdi...")
bot.infinity_polling()
