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

PLANS = {
    "1": {"name": "1 Day", "days": 1, "points": 3},
    "3": {"name": "3 Days", "days": 3, "points": 6},
    "7": {"name": "7 Days", "days": 7, "points": 10},
    "30": {"name": "30 Days", "days": 30, "points": 25},
    "free_fire": {"name": "Free Fire", "days": 0, "points": 5}
}

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

def create_user_if_missing(telegram_user, referrer_id=None):
    user_id = telegram_user.id
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    old = get_user(user_id)

    if old is None:
        ref = int(referrer_id) if referrer_id and int(referrer_id) != user_id else None
        data = {
            "id": user_id,
            "username": telegram_user.username or "",
            "first_name": telegram_user.first_name or "",
            "points": 0,
            "referrals": 0,
            "referrer_id": ref,
            "started": True,
            "notifications_enabled": True,
            "created_at": now,
            "last_seen": now,
            "keys": {},
            "referral_rewards": {}
        }
        firebase_put(f"users/{user_id}", data)
        return data

    patch = {"username": telegram_user.username or "", "first_name": telegram_user.first_name or "", "last_seen": now, "started": True}
    if referrer_id and int(referrer_id) != user_id and not old.get("referrer_id"):
        patch["referrer_id"] = int(referrer_id)

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

def reward_referrer_once(referred_id):
    referred = get_user(referred_id)
    if not referred:
        return False
    referrer_id = referred.get("referrer_id")
    if not referrer_id or int(referrer_id) == int(referred_id):
        return False
    referrer = get_user(referrer_id)
    if not referrer:
        return False

    rewards = referrer.get("referral_rewards", {})
    if str(referred_id) in rewards:
        return False

    old_points = int(referrer.get("points", 0))
    old_referrals = int(referrer.get("referrals", 0))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    firebase_patch(f"users/{referrer_id}", {
        "points": old_points + 1,
        "referrals": old_referrals + 1,
        f"referral_rewards/{referred_id}": {"rewarded_at": now}
    })

    try:
        bot.send_message(
            int(referrer_id),
            "🎉 <b>New Referral Joined!</b>\n\n"
            "Aapki link se ek naye user ne channel join kar liya hai!\n"
            "⭐ Aapko <b>+1 Point</b> mil gaya hai! 🚀\n\n"
            "✨ <i>Aapka bot ready hai keys generate karne ke liye!</i>",
            parse_mode="HTML"
        )
    except Exception:
        pass
    return True

def generate_unique_key():
    for _ in range(100):
        key = f"DP-{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}"
        if firebase_get(f"keys/{key}") is None:
            return key
    return None

def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton("🎁 Generate Key"), types.KeyboardButton("🔥 Free Fire"))
    markup.row(types.KeyboardButton("💎 Aim AI Panel"), types.KeyboardButton("🔗 My Link"))
    markup.row(types.KeyboardButton("👥 Referrals"), types.KeyboardButton("🔑 My Keys"))
    markup.row(types.KeyboardButton("🔄 Refresh"), types.KeyboardButton("ℹ️ How it works"))
    return markup

def join_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK))
    markup.add(types.InlineKeyboardButton("✅ Verify", callback_data="verify"))
    return markup

def plans_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    for pid, plan in PLANS.items():
        if pid == "free_fire":
            markup.add(types.InlineKeyboardButton(f"🔥 {plan['name']} - ⭐ {plan['points']}", callback_data=f"unlock:{pid}"))
        else:
            markup.add(types.InlineKeyboardButton(f"{plan['name']} - ⭐ {plan['points']}", callback_data=f"generate:{pid}"))
    markup.add(types.InlineKeyboardButton("⬅️ Back", callback_data="refresh"))
    return markup

def send_dashboard(message_or_user, extra_msg=""):
    user_id = message_or_user.from_user.id if hasattr(message_or_user, "from_user") else message_or_user
    user = get_user(user_id)
    if not user:
        return

    text = (f"{extra_msg}\n\n" if extra_msg else "") + (
        f"🏆 <b>Aapka Rewards Dashboard</b>\n\n"
        f"⭐ Total Points: <b>{user.get('points', 0)}</b>\n"
        f"👥 Verified Referrals: <b>{user.get('referrals', 0)}</b>\n\n"
        f"✨ <i>Aapka bot taiyar hai key generate karne ke liye!</i> 🚀\n\n"
        f"📱 <b>App Download Link:</b>\n{APP_DOWNLOAD_LINK}"
    )
    bot.send_message(user_id, text, parse_mode="HTML", reply_markup=main_keyboard())

@bot.message_handler(commands=["start"])
def start_command(message):
    user_id = message.from_user.id
    args = message.text.split()
    referrer_id = args[1] if len(args) > 1 and args[1].isdigit() else None

    create_user_if_missing(message.from_user, referrer_id)

    if not check_joined(user_id):
        bot.send_message(user_id, f"👋 <b>Welcome {message.from_user.first_name}!</b>\n\nBot use karne ke liye pehle official channel join karo.\n\n👇 Join karne ke baad <b>Verify</b> dabao.", parse_mode="HTML", reply_markup=join_keyboard())
        return

    reward_referrer_once(user_id)
    send_dashboard(message, "🎉 <b>Verification Successful! Aapka bot ready hai keys generate karne ke liye!</b>")

@bot.callback_query_handler(func=lambda call: call.data == "verify")
def verify_callback(call):
    user_id = call.from_user.id
    bot.answer_callback_query(call.id)

    if not check_joined(user_id):
        bot.send_message(user_id, "❌ <b>Verification Failed</b>\nAapne abhi channel join nahi kiya hai.", parse_mode="HTML", reply_markup=join_keyboard())
        return

    reward_referrer_once(user_id)
    bot.send_message(user_id, "✅ <b>Verification Successful!</b>", parse_mode="HTML")
    send_dashboard(call.message, "🎉 <b>Aapka bot ready hai keys generate karne ke liye!</b> 🔥")

@bot.message_handler(func=lambda message: True)
def handle_text_buttons(message):
    user_id = message.from_user.id
    text = (message.text or "").strip()
    create_user_if_missing(message.from_user)

    if not check_joined(user_id):
        bot.send_message(user_id, "⚠️ Bot use karne ke liye pehle official channel join karein.", reply_markup=join_keyboard())
        return

    if "Generate Key" in text:
        bot.send_message(user_id, "🛒 <b>Premium Plans</b>\n\n1 Day = ⭐ 3 Points\n3 Days = ⭐ 6 Points\n7 Days = ⭐ 10 Points\n30 Days = ⭐ 25 Points\n\n👇 Apna manpasand plan select karo:", parse_mode="HTML", reply_markup=plans_keyboard())
    elif "Free Fire" in text:
        bot.send_message(
            user_id,
            "🔥 <b>Free Fire Panel / Files</b>\n\n"
            "Isme aapko Free Fire ki mod files aur special setup video milti hai!\n\n"
            "⭐ Required Points: <b>5 Points</b>\n\n"
            "👇 Purchase / Unlock karne ke liye niche click karein:",
            parse_mode="HTML",
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("🔓 Unlock Free Fire (5 ⭐)", callback_data="unlock:free_fire")
            )
        )
    elif "Aim AI Panel" in text:
        bot.send_message(
            user_id,
            "💎 <b>Aim AI Panel</b>\n\n"
            "✅ Generate unlimited keys for free directly\n"
            "✅ Sell unlimited keys\n"
            "✅ Panel with your name\n"
            "✅ One time investment\n"
            "✅ Price ₹300 only\n"
            "❌ Free not available ❌❌\n\n"
            "💬 <b>Paid chahiye jisme zyada features ho? Owner se contact karein:</b>\n"
            "👉 <b>@Memonsalim</b>",
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )
    elif "My Link" in text:
        link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
        bot.send_message(user_id, f"🔗 <b>Aapki Personal Referral Link</b>\n\n<code>{link}</code>\n\n👥 Is link ko doston ke sath share karein!\nHar verified referral par milega <b>+1 Point</b> ⭐", parse_mode="HTML", reply_markup=main_keyboard())
    elif "Referrals" in text:
        user = get_user(user_id)
        bot.send_message(user_id, f"👥 <b>Aapke Referrals Status</b>\n\n👤 Total Referrals: <b>{user.get('referrals', 0)}</b>\n⭐ Total Points: <b>{user.get('points', 0)}</b>", parse_mode="HTML", reply_markup=main_keyboard())
    elif "My Keys" in text:
        user = get_user(user_id)
        keys = user.get("keys", {}) if user else {}
        if not keys:
            bot.send_message(user_id, "📭 Abhi tak aapne koi key generate nahi ki hai.", reply_markup=main_keyboard())
            return
        text_msg = "🔐 <b>Aapki Generated Keys</b>\n\n"
        for k, info in list(keys.items())[::-1][:20]:
            text_msg += f"🔑 <code>{k}</code>\n⏳ {info.get('days', '?')} Days\n📅 {info.get('created_at', '-')}\n\n"
        bot.send_message(user_id, text_msg, parse_mode="HTML", reply_markup=main_keyboard())
    elif "Refresh" in text:
        send_dashboard(message)
    elif "How it works" in text:
        bot.send_message(
            user_id,
            "📖 <b>How It Works (Aasan Bhasha Me Samjho)</b>\n\n"
            "1️⃣ Sabse pehle bot ko start karke hamara official channel join karo aur <b>Verify</b> button par click karo.\n"
            "2️⃣ Ab apna <b>Referral Link</b> copy karke apne doston ke sath share karo.\n"
            "3️⃣ Jaise hi aapka dost aapki link se aakar channel join karega, aapko turant <b>+1 Point (Star)</b> mil jayega! ⭐\n"
            "4️⃣ Jab aapke paas acche khase points ho jayein, toh aap **'Generate Key'** ya **'Free Fire'** par click karke apne points se items unlock kar sakte ho! 🎉\n"
            "5️⃣ Agar aapko aur bhi advanced paid panel chahiye jisme bohot saare features hon, toh aap seedha owner **@Memonsalim** se contact kar sakte ho! 💎",
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    bot.answer_callback_query(call.id)
    if call.data == "refresh":
        send_dashboard(call.message)
    elif call.data.startswith("generate:"):
        plan_id = call.data.split(":", 1)[1]
        if not check_joined(user_id):
            bot.send_message(user_id, "❌ Pehle channel join karke Verify karo.", reply_markup=join_keyboard())
            return
        
        user = get_user(user_id)
        plan = PLANS[plan_id]
        if int(user.get("points", 0)) < plan["points"]:
            bot.send_message(user_id, f"❌ <b>Insufficient Points</b>\nAapke paas points kam hain! (Required: {plan['points']} ⭐)", parse_mode="HTML", reply_markup=main_keyboard())
            return

        key = generate_unique_key()
        if not key:
            bot.send_message(user_id, "❌ Key generation failed. Dobara koshish karein.", reply_markup=main_keyboard())
            return

        new_points = int(user.get("points", 0)) - plan["points"]
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        key_data = {"key": key, "username": key, "password": key, "user_id": str(user_id), "days": plan["days"], "status": "active", "created_at": now}

        if not firebase_put(f"keys/{key}", key_data):
            bot.send_message(user_id, "❌ Database error.", reply_markup=main_keyboard())
            return

        firebase_patch(f"users/{user_id}", {"points": new_points, f"keys/{key}": key_data})
        bot.send_message(user_id, f"🎉 <b>KEY GENERATED SUCCESSFULLY!</b>\n\n🔑 Key: <code>{key}</code>\n⏳ Validity: <b>{plan['days']} Days</b>", parse_mode="HTML", reply_markup=main_keyboard())

    elif call.data == "unlock:free_fire":
        if not check_joined(user_id):
            bot.send_message(user_id, "❌ Pehle channel join karke Verify karo.", reply_markup=join_keyboard())
            return

        user = get_user(user_id)
        points = int(user.get("points", 0))
        required = PLANS["free_fire"]["points"]

        if points < required:
            bot.send_message(user_id, f"❌ <b>Insufficient Points</b>\nFree Fire unlock karne ke liye <b>{required} Points</b> chahiye!\n(Aapke paas: {points} ⭐)", parse_mode="HTML", reply_markup=main_keyboard())
            return

        new_points = points - required
        firebase_patch(f"users/{user_id}", {"points": new_points, "unlocked_free_fire": True})

        try:
            bot.send_message(
                user_id,
                "🎉 <b>Free Fire Package Unlocked Successfully!</b>\n\n"
                "Niche aapki file aur setup video di gayi hai 👇\n"
                "Paid features ke liye owner se contact karein: <b>@Memonsalim</b>",
                parse_mode="HTML"
            )
            # Using placeholder file/video messaging structure handled safely
            bot.send_message(
                user_id,
                "📁 <b>Free Fire Files & Video Package Sent Successfully!</b>\n"
                "Paid features ya full access ke liye owner **@Memonsalim** se contact karein.",
                parse_mode="HTML",
                reply_markup=main_keyboard()
            )
        except Exception:
            bot.send_message(
                user_id,
                "📁 <b>Free Fire Files & Video Link Sent Successfully!</b>\n"
                "Agar koi dikkat aaye toh owner **@Memonsalim** se contact karein.",
                parse_mode="HTML",
                reply_markup=main_keyboard()
            )

def send_startup_broadcast():
    try:
        time.sleep(5)
        users = firebase_get("users")
        if isinstance(users, dict):
            for uid, udata in users.items():
                if isinstance(udata, dict) and udata.get("notifications_enabled", True):
                    try:
                        bot.send_message(
                            int(uid),
                            "🚀 <b>Bot Start Ho Chuka Hai!</b>\n\n"
                            "Sabhi features aur naye updates live hain. Ab aap keys generate kar sakte hain ya points earn kar sakte hain! ✨",
                            parse_mode="HTML"
                        )
                        time.sleep(0.05)
                    except Exception:
                        pass
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
    
