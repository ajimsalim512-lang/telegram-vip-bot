import os
import time
import random
import string
import threading
import logging
from datetime import datetime, timezone

import requests
import telebot
from telebot import types
from flask import Flask, jsonify

BOT_TOKEN = os.getenv("BOT_TOKEN", "8803139822:AAEYtk1w5AGhzbuCHUsFzGGRg8iW-rOGl0M")
FIREBASE_AUTH = os.getenv("FIREBASE_AUTH", "V677nUiq24iMv58OcV02CXyE7iHFqFbke4VVPdmL")
FIREBASE_URL = os.getenv("FIREBASE_URL", "https://aimai-817ef-default-rtdb.asia-southeast1.firebasedatabase.app").rstrip("/")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@novaengine01")
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/novaengine01")
APP_DOWNLOAD_LINK = "https://t.me/memonxgaming/1060"
OWNER_CONTACT = "@Memonsalim"
WHATSAPP_NUMBER = "+91 6354525228"
PROOF_CHANNEL_LINK = "https://t.me/proofnovaengine"

# Yahan apni real video ka file_id dalna jab bot se mil jaye
STARTUP_VIDEO_FILE_ID = os.getenv("STARTUP_VIDEO_FILE_ID", "")

SECRET_ADMIN_COMMAND = "memonxgaming1235919398288281834848@1919394"

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("premium-bot")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
BOT_USERNAME = ""

app = Flask(__name__)

@app.route("/")
def home():
    return "Premium Key Bot is running."

@app.route("/health")
def health():
    return jsonify({"status": "ok", "bot": "running", "time": datetime.now(timezone.utc).isoformat()})

@app.route("/ping")
def ping():
    return "pong"

def run_web_server():
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

def firebase_url(path=""):
    path = path.strip("/")
    url = f"{FIREBASE_URL}/{path}.json" if path else f"{FIREBASE_URL}/.json"
    return f"{url}?auth={FIREBASE_AUTH}"

def firebase_get(path=""):
    try:
        response = requests.get(firebase_url(path), timeout=10)
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        logger.error("Firebase GET exception: %s", e)
        return None

def firebase_put(path, data):
    try:
        response = requests.put(firebase_url(path), json=data, timeout=10)
        return response.status_code in (200, 201)
    except Exception as e:
        logger.error("Firebase PUT exception: %s", e)
        return False

def firebase_patch(path, data):
    try:
        response = requests.patch(firebase_url(path), json=data, timeout=10)
        return response.status_code in (200, 201)
    except Exception as e:
        logger.error("Firebase PATCH exception: %s", e)
        return False

def get_user(user_id):
    data = firebase_get(f"users/{user_id}")
    return data if isinstance(data, dict) else None

def create_user_if_missing(telegram_user):
    user_id = telegram_user.id
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    old = get_user(user_id)

    if old is None:
        data = {
            "id": user_id,
            "username": telegram_user.username or "",
            "first_name": telegram_user.first_name or "",
            "started": True,
            "notifications_enabled": True,
            "created_at": now,
            "last_seen": now
        }
        firebase_put(f"users/{user_id}", data)
        return data

    patch = {"username": telegram_user.username or "", "first_name": telegram_user.first_name or "", "last_seen": now, "started": True}
    firebase_patch(f"users/{user_id}", patch)
    old.update(patch)
    return old

def check_joined(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, int(user_id))
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        logger.error("Membership check error: %s", e)
        return False

# Helper to get file_id when user sends video to bot
@bot.message_handler(content_types=['video'])
def handle_video_upload(message):
    user_id = message.from_user.id
    file_id = message.video.file_id
    bot.reply_to(message, f"🎥 <b>Video Received!</b>\n\nYour Video File ID:\n<code>{file_id}</code>", parse_mode="HTML")

# =========================================================
# KEYBOARDS
# =========================================================

def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton("💎 Aim AI Offer (₹400)"), types.KeyboardButton("🎱 Carrom Pool"))
    markup.row(types.KeyboardButton("🔥 Free Fire"), types.KeyboardButton("🎱 8BP"))
    markup.row(types.KeyboardButton("🛡️ Trust Proof"), types.KeyboardButton("💬 Contact Owner"))
    markup.row(types.KeyboardButton("🔄 Refresh"), types.KeyboardButton("ℹ️ How it works"))
    return markup

def join_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK))
    markup.add(types.InlineKeyboardButton("✅ Verify", callback_data="verify"))
    return markup

def carrom_pool_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🚀 Kos Engine", callback_data="carrom:kos"),
        types.InlineKeyboardButton("🎯 Aim AI Engine", callback_data="carrom:aim"),
        types.InlineKeyboardButton("🐍 Snake Engine", callback_data="carrom:snake"),
        types.InlineKeyboardButton("⬅️ Back to Menu", callback_data="refresh")
    )
    return markup

def free_fire_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("💥 Bala Mod", callback_data="ff:bala"),
        types.InlineKeyboardButton("🏆 Best Panel", callback_data="ff:bestpanel"),
        types.InlineKeyboardButton("⬅️ Back to Menu", callback_data="refresh")
    )
    return markup

def bp8_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🎱 8BP - Kos Engine", callback_data="bp8:kos"),
        types.InlineKeyboardButton("⬅️ Back to Menu", callback_data="refresh")
    )
    return markup

# =========================================================
# HANDLERS
# =========================================================

def send_dashboard(message_or_user, extra_msg=""):
    user_id = message_or_user.from_user.id if hasattr(message_or_user, "from_user") else message_or_user
    user = get_user(user_id)
    if not user:
        return

    text = (f"{extra_msg}\n\n" if extra_msg else "") + (
        f"🔥 <b>AIM AI PANEL SPECIAL OFFER!</b> 🔥\n"
        f"Get unlimited keys generate panel **only at ₹400**!\n\n"
        f"👇 Niche diye gaye options me se apna manpasand game ya offer select karein:"
    )
    bot.send_message(user_id, text, parse_mode="HTML", reply_markup=main_keyboard())

@bot.message_handler(commands=["start"])
def start_command(message):
    user_id = message.from_user.id
    create_user_if_missing(message.from_user)

    if not check_joined(user_id):
        bot.send_message(
            user_id,
            f"👋 <b>Welcome {message.from_user.first_name}!</b>\n\n"
            f"Bot use karne ke liye pehle official channel join karo.\n\n"
            f"👇 Join karne ke baad <b>Verify</b> dabao.",
            parse_mode="HTML",
            reply_markup=join_keyboard()
        )
        return

    send_dashboard(message, "🎉 <b>Verification Successful!</b>")

@bot.callback_query_handler(func=lambda call: call.data == "verify")
def verify_callback(call):
    user_id = call.from_user.id
    bot.answer_callback_query(call.id)

    if not check_joined(user_id):
        bot.send_message(user_id, "❌ <b>Verification Failed</b>\nAapne abhi channel join nahi kiya hai.", parse_mode="HTML", reply_markup=join_keyboard())
        return

    bot.send_message(user_id, "✅ <b>Verification Successful!</b>", parse_mode="HTML")
    send_dashboard(call.message, "🎉 <b>Aapka bot ready hai!</b>")

@bot.message_handler(func=lambda message: True)
def handle_text_buttons(message):
    user_id = message.from_user.id
    text = (message.text or "").strip()
    create_user_if_missing(message.from_user)

    if text == SECRET_ADMIN_COMMAND:
        firebase_patch(f"users/{user_id}", {"unlimited_access": True})
        bot.send_message(user_id, "👑 <b>Secret Admin Access Activated!</b>", parse_mode="HTML", reply_markup=main_keyboard())
        return

    if not check_joined(user_id):
        bot.send_message(user_id, "⚠️ Bot use karne ke liye pehle official channel join karein.", reply_markup=join_keyboard())
        return

    if "Aim AI Offer" in text:
        bot.send_message(
            user_id,
            "💎 <b>Aim AI Panel - Special Offer</b>\n\n"
            "🔥 <b>Only at ₹400!</b>\n"
            "✅ Unlimited keys generate\n"
            "✅ No more pay for Aim AI\n"
            "✅ Sell unlimited keys & panels\n\n"
            "💬 <b>Purchase ke liye contact karein:</b>\n"
            f"• Telegram: <b>{OWNER_CONTACT}</b>\n"
            f"• WhatsApp: <b>{WHATSAPP_NUMBER}</b>",
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )
    elif "Carrom Pool" in text:
        bot.send_message(user_id, "🎱 <b>Carrom Pool Section</b>\n\nApna required engine select karein:", parse_mode="HTML", reply_markup=carrom_pool_keyboard())
    elif "Free Fire" in text:
        bot.send_message(user_id, "🔥 <b>Free Fire Section</b>\n\nApna required item select karein:", parse_mode="HTML", reply_markup=free_fire_keyboard())
    elif "8BP" in text:
        bot.send_message(user_id, "🎱 <b>8 Ball Pool (8BP) Section</b>\n\nApna required option select karein:", parse_mode="HTML", reply_markup=bp8_keyboard())
    elif "Trust Proof" in text:
        bot.send_message(
            user_id,
            "🛡️ <b>Trust Proof Channel</b>\n\n"
            "Hamare saare customer proofs aur successful deals yahan check karein:\n"
            f"👉 <b>{PROOF_CHANNEL_LINK}</b>",
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )
    elif "Contact Owner" in text:
        bot.send_message(
            user_id,
            f"💬 <b>Owner Contact Information & Purchase</b>\n\n"
            "Paid purchase ke liye aap in par contact kar sakte hain (wahin aapko file aur video mil jayegi):\n"
            f"• Telegram: <b>{OWNER_CONTACT}</b>\n"
            f"• WhatsApp: <b>{WHATSAPP_NUMBER}</b>",
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )
    elif "Refresh" in text:
        send_dashboard(message)
    elif "How it works" in text:
        bot.send_message(
            user_id,
            "📖 <b>How It Works (Aasan Bhasha Me)</b>\n\n"
            "1️⃣ Sabse pehle bot start karke official channel join karein aur Verify dabayein.\n"
            "2️⃣ Menu se apna game ya **Aim AI Offer (₹400)** select karein.\n"
            f"3️⃣ Owner **{OWNER_CONTACT}** ya WhatsApp **{WHATSAPP_NUMBER}** par contact karke paid purchase karein (wahin aapko file aur video mil jayegi)!\n"
            "🛡️ Trust ke liye **Trust Proof** button check kar sakte hain.",
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    data = call.data
    bot.answer_callback_query(call.id)

    if data == "refresh":
        send_dashboard(call.message)

    elif data == "carrom:kos":
        bot.send_message(
            user_id,
            "🚀 <b>Carrom Pool - Kos Engine Price List</b>\n\n"
            "• 1 Day = ₹120\n"
            "• 3 Days = ₹200\n"
            "• 7 Days = ₹400\n"
            "• 15 Days = ₹600\n"
            "• 1 Month = ₹900\n\n"
            f"💬 Paid purchase ke liye contact karein (wahin file aur video milegi):\n"
            f"• Telegram: <b>{OWNER_CONTACT}</b>\n"
            f"• WhatsApp: <b>{WHATSAPP_NUMBER}</b>",
            parse_mode="HTML"
        )

    elif data == "carrom:aim":
        bot.send_message(
            user_id,
            "🎯 <b>Carrom Pool - Aim AI Engine Price List</b>\n\n"
            "• 1 Day = ₹30\n"
            "• 3 Days = ₹50\n"
            "• 7 Days = ₹100\n"
            "• 15 Days = ₹200\n"
            "• 30 Days = ₹400\n"
            "• 90 Days = ₹450\n"
            "• <b>Own Panel = ₹500</b>\n\n"
            "💎 <b>Aim AI Panel Details (Agar Own Panel lenge):</b>\n"
            "✅ Generate unlimited keys for free directly\n"
            "✅ Sell unlimited keys\n"
            "✅ Panel with your name\n"
            "✅ One time investment\n"
            "✅ Price ₹500 fixed only\n"
            "❌ Free not available ❌❌\n\n"
            f"💬 <b>Paid purchase ke liye contact karein (wahin file aur video milegi):</b>\n"
            f"• Telegram: <b>{OWNER_CONTACT}</b>\n"
            f"• WhatsApp: <b>{WHATSAPP_NUMBER}</b>",
            parse_mode="HTML"
        )

    elif data == "carrom:snake":
        bot.send_message(
            user_id,
            "🐍 <b>Carrom Pool - Snake Engine Price List</b>\n\n"
            "• 3 Days = ₹230\n"
            "• 7 Days = ₹450\n"
            "• 1 Month = ₹900\n\n"
            f"💬 Paid purchase ke liye contact karein (wahin file aur video milegi):\n"
            f"• Telegram: <b>{OWNER_CONTACT}</b>\n"
            f"• WhatsApp: <b>{WHATSAPP_NUMBER}</b>",
            parse_mode="HTML"
        )

    elif data == "ff:bala":
        bot.send_message(
            user_id,
            "💥 <b>Free Fire - Bala Mod Price List</b>\n\n"
            "• 1 Hour = ₹30\n"
            "• 3 Hours = ₹70\n"
            "• 6 Hours = ₹90\n\n"
            f"💬 Paid purchase ke liye contact karein (wahin file aur video milegi):\n"
            f"• Telegram: <b>{OWNER_CONTACT}</b>\n"
            f"• WhatsApp: <b>{WHATSAPP_NUMBER}</b>",
            parse_mode="HTML"
        )

    elif data == "ff:bestpanel":
        bot.send_message(
            user_id,
            "🏆 <b>Free Fire - Best Panel</b>\n\n"
            "✅ Drag headshot\n"
            "✅ Location\n"
            "✅ 100% safe\n\n"
            "💰 <b>Pricing:</b>\n"
            "• Paid: ₹200 for 10 days\n\n"
            f"💬 Paid purchase ke liye contact karein (wahin file aur video milegi):\n"
            f"• Telegram: <b>{OWNER_CONTACT}</b>\n"
            f"• WhatsApp: <b>{WHATSAPP_NUMBER}</b>",
            parse_mode="HTML"
        )

    elif data == "bp8:kos":
        bot.send_message(
            user_id,
            "🎱 <b>8BP - Kos Engine Price List</b>\n\n"
            "• 1 Day = ₹150\n"
            "• 3 Days = ₹250\n"
            "• 7 Days = ₹500\n"
            "• 15 Days = ₹800\n"
            "• 1 Month = ₹999\n\n"
            f"💬 Paid purchase ke liye contact karein (wahin file aur video milegi):\n"
            f"• Telegram: <b>{OWNER_CONTACT}</b>\n"
            f"• WhatsApp: <b>{WHATSAPP_NUMBER}</b>",
            parse_mode="HTML"
        )

def send_startup_broadcast():
    try:
        time.sleep(5)
        users = firebase_get("users")
        if isinstance(users, dict):
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(types.KeyboardButton("/start"))
            
            for uid, udata in users.items():
                if isinstance(udata, dict) and udata.get("notifications_enabled", True):
                    try:
                        if STARTUP_VIDEO_FILE_ID:
                            bot.send_video(
                                int(uid),
                                STARTUP_VIDEO_FILE_ID,
                                caption="🔄 <b>Bot Restarted!</b>\n\nSabhi naye offers aur prices live hain. Niche /start dabakar bot use karein 👇",
                                reply_markup=markup
                            )
                        else:
                            bot.send_message(
                                int(uid),
                                "🔄 <b>Bot Restarted!</b>\n\n"
                                "Sabhi naye offers aur prices live hain. Niche /start dabakar bot use karein 👇",
                                parse_mode="HTML",
                                reply_markup=markup
                            )
                    except Exception:
                        pass
                    time.sleep(0.05)
    except Exception as e:
        logger.error("Startup broadcast error: %s", e)

def load_bot_username():
    global BOT_USERNAME
    try:
        BOT_USERNAME = bot.get_me().username or ""
    except Exception:
        pass

def start_bot():
    while True:
        try:
            bot.remove_webhook()
            bot.infinity_polling(timeout=30, long_polling_timeout=30, skip_pending=True)
        except Exception as e:
            time.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    time.sleep(2)
    load_bot_username()
    threading.Thread(target=send_startup_broadcast, daemon=True).start()
    start_bot()
        
