import telebot
from telebot import types
import json
from github_helper import get_stats, save_stats

# ---- Sozlamalar ----
BOT_TOKEN = "8881803852:AAFJ6Uuk1uUFdUsfH3elrpP177aOsLR32Ok"
WEBAPP_URL = "https://abdulhodiyamirdin-777.github.io/Dokon/dokon-yakuniy.html"
ADMIN_CHAT_ID = 8881459774

bot = telebot.TeleBot(BOT_TOKEN)


@bot.message_handler(commands=["start"])
def start_handler(message):
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
        order = json.loads(message.web_app_data.data)
    except Exception:
        bot.send_message(message.chat.id, "Xatolik yuz berdi, qaytadan urinib ko'ring.")
        return

    lines = ["🆕 <b>Yangi buyurtma</b>\n"]
    for item in order.get("items", []):
        lines.append(f"• {item['name']} × {item['qty']} = {item['price'] * item['qty']:,} so'm")

    total = order.get("total", 0)
    lines.append(f"\n💰 <b>Jami:</b> {total:,} so'm")
    lines.append(f"\n👤 <b>Mijoz:</b> {order.get('name')}")
    lines.append(f"📞 <b>Telefon:</b> {order.get('phone')}")
    lines.append(f"📍 <b>Manzil:</b> {order.get('address')}")

    order_text = "\n".join(lines)

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


print("Savdo boti ishga tushdi...")
bot.infinity_polling()
