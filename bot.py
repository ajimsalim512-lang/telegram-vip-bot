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


# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = os.getenv(
    "BOT_TOKEN",
    "8803139822:AAEYtk1w5AGhzbuCHUsFzGGRg8iW-rOGl0M"
)

FIREBASE_AUTH = os.getenv(
    "FIREBASE_AUTH",
    "V677nUiq24iMv58OcV02CXyE7iHFqFbke4VVPdmL"
)

FIREBASE_URL = os.getenv(
    "FIREBASE_URL",
    "https://aimai-817ef-default-rtdb.asia-southeast1.firebasedatabase.app"
).rstrip("/")

CHANNEL_USERNAME = os.getenv(
    "CHANNEL_USERNAME",
    "@novaengine01"
)

CHANNEL_LINK = os.getenv(
    "CHANNEL_LINK",
    "https://t.me/novaengine01"
)

APP_DOWNLOAD_LINK = (
    "https://t.me/memonxgaming/1060"
)

ADMIN_IDS = {
    int(x.strip())
    for x in os.getenv(
        "ADMIN_IDS", ""
    ).split(",")
    if x.strip().isdigit()
}


# =========================================================
# PLANS
# =========================================================

PLANS = {
    "1": {
        "name": "1 Day",
        "days": 1,
        "points": 3
    },
    "3": {
        "name": "3 Days",
        "days": 3,
        "points": 6
    },
    "7": {
        "name": "7 Days",
        "days": 7,
        "points": 10
    },
    "30": {
        "name": "30 Days",
        "days": 30,
        "points": 25
    }
}


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger("premium-bot")


# =========================================================
# TELEGRAM BOT
# =========================================================

bot = telebot.TeleBot(
    BOT_TOKEN,
    parse_mode="HTML"
)

BOT_USERNAME = ""


# =========================================================
# FLASK (24/7 KEEP ALIVE SERVER FOR RENDER)
# =========================================================

app = Flask(__name__)


@app.route("/")
def home():
    return "Premium Key Bot is running."


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "bot": "running",
        "time": datetime.now(timezone.utc).isoformat()
    })


@app.route("/ping")
def ping():
    return "pong"


def run_web_server():
    port = int(os.getenv("PORT", "10000"))
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
        use_reloader=False
    )


# =========================================================
# FIREBASE HELPERS (FAST & OPTIMIZED)
# =========================================================

def firebase_url(path=""):
    path = path.strip("/")
    if path:
        url = f"{FIREBASE_URL}/{path}.json"
    else:
        url = f"{FIREBASE_URL}/.json"
    return f"{url}?auth={FIREBASE_AUTH}"


def firebase_get(path=""):
    try:
        response = requests.get(firebase_url(path), timeout=10)
        if response.status_code != 200:
            return None
        return response.json()
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


# =========================================================
# USER HELPERS
# =========================================================

def user_path(user_id):
    return f"users/{user_id}"


def get_user(user_id):
    data = firebase_get(user_path(user_id))
    if isinstance(data, dict):
        return data
    return None


def create_user_if_missing(telegram_user, referrer_id=None):
    user_id = telegram_user.id
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    old = get_user(user_id)

    if old is None:
        ref = None
        if referrer_id and int(referrer_id) != user_id:
            ref = int(referrer_id)

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
        firebase_put(user_path(user_id), data)
        return data

    patch = {
        "username": telegram_user.username or "",
        "first_name": telegram_user.first_name or "",
        "last_seen": now,
        "started": True
    }

    if referrer_id and int(referrer_id) != user_id and not old.get("referrer_id"):
        patch["referrer_id"] = int(referrer_id)

    firebase_patch(user_path(user_id), patch)
    old.update(patch)
    return old


# =========================================================
# MEMBERSHIP CHECK
# =========================================================

def check_joined(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, int(user_id))
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        logger.error("Membership check error: %s", e)
        return False


# =========================================================
# REFERRAL REWARD & NOTIFICATION
# =========================================================

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

    firebase_patch(
        user_path(referrer_id),
        {
            "points": old_points + 1,
            "referrals": old_referrals + 1,
            f"referral_rewards/{referred_id}": {
                "rewarded_at": now
            }
        }
    )

    try:
        bot.send_message(
            int(referrer_id),
            "🎉 <b>New Referral Joined!</b>\n\n"
            "Aapki link se ek naye user ne channel join kar liya hai!\n"
            "⭐ Aapko <b>+1 Point</b> mil gaya hai! 🚀",
            parse_mode="HTML"
        )
    except Exception:
        pass

    return True


# =========================================================
# KEY GENERATOR
# =========================================================

def generate_unique_key():
    for _ in range(100):
        chars = string.ascii_uppercase + string.digits
        random_part = "".join(random.choices(chars, k=8))
        key = f"DP-{random_part}"
        if firebase_get(f"keys/{key}") is None:
            return key
    return None


# =========================================================
# CREATE KEY
# =========================================================

def create_key_for_user(user_id, plan_id):
    if plan_id not in PLANS:
        return False, "❌ Invalid plan."

    user = get_user(user_id)
    if not user:
        return False, "❌ User not found."

    plan = PLANS[plan_id]
    required_points = plan["points"]
    days = plan["days"]
    points = int(user.get("points", 0))

    if points < required_points:
        return False, (
            f"❌ <b>Insufficient Points</b>\n\n"
            f"⭐ Your Points: <b>{points}</b>\n"
            f"Required: <b>{required_points}</b>\n\n"
            f"💡 Aur points kamane ke liye apna Referral Link share karein!"
        )

    key = generate_unique_key()
    if not key:
        return False, "❌ Key generate nahi ho saki. Dobara koshish karein."

    new_points = points - required_points
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    key_data = {
        "key": key,
        "username": key,
        "password": key,
        "user_id": str(user_id),
        "days": days,
        "status": "active",
        "devices": 1,
        "created_at": now
    }

    if not firebase_put(f"keys/{key}", key_data):
        return False, "❌ Firebase error."

    firebase_patch(
        user_path(user_id),
        {
            "points": new_points,
            f"keys/{key}": key_data,
            "last_key": key,
            "last_key_at": now
        }
    )
    return True, key_data


# =========================================================
# KEYBOARDS
# =========================================================

def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(
        types.KeyboardButton("🎁 Generate Key"),
        types.KeyboardButton("💎 Aim AI Panel")
    )
    markup.row(
        types.KeyboardButton("🔗 My Link"),
        types.KeyboardButton("👥 Referrals")
    )
    markup.row(
        types.KeyboardButton("🔑 My Keys"),
        types.KeyboardButton("🔄 Refresh")
    )
    markup.row(
        types.KeyboardButton("ℹ️ How it works")
    )
    return markup


def join_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK))
    markup.add(types.InlineKeyboardButton("✅ Verify", callback_data="verify"))
    return markup


def plans_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    for plan_id, plan in PLANS.items():
        markup.add(
            types.InlineKeyboardButton(
                f"{plan['name']} - ⭐ {plan['points']}",
                callback_data=f"generate:{plan_id}"
            )
        )
    markup.add(types.InlineKeyboardButton("⬅️ Back", callback_data="refresh"))
    return markup


# =========================================================
# DASHBOARD
# =========================================================

def send_dashboard(message_or_user, extra_msg=""):
    if hasattr(message_or_user, "from_user"):
        user_obj = message_or_user.from_user
        user_id = user_obj.id
        create_user_if_missing(user_obj)
    else:
        user_id = message_or_user

    user = get_user(user_id)
    if not user:
        bot.send_message(user_id, "❌ User data nahi mila. Pehle /start bhejein.")
        return

    points = int(user.get("points", 0))
    referrals = int(user.get("referrals", 0))

    text = (
        f"{extra_msg}\n\n" if extra_msg else ""
    ) + (
        f"🏆 <b>Aapka Rewards Dashboard</b>\n\n"
        f"⭐ Total Points: <b>{points}</b>\n"
        f"👥 Verified Referrals: <b>{referrals}</b>\n\n"
        f"✨ <i>Aapka bot taiyar hai key generate karne ke liye!</i> 🚀\n\n"
        f"📱 <b>App Download Link:</b>\n{APP_DOWNLOAD_LINK}"
    )

    bot.send_message(
        user_id,
        text,
        parse_mode="HTML",
        reply_markup=main_keyboard()
    )


# =========================================================
# /START COMMAND
# =========================================================

@bot.message_handler(commands=["start"])
def start_command(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or ""

    args = message.text.split()
    referrer_id = None
    if len(args) > 1 and args[1].isdigit():
        referrer_id = args[1]

    create_user_if_missing(message.from_user, referrer_id)

    if not check_joined(user_id):
        bot.send_message(
            user_id,
            f"👋 <b>Welcome {first_name}!</b>\n\n"
            f"Bot use karne ke liye pehle official channel join karo.\n\n"
            f"👇 Join karne ke baad <b>Verify</b> dabao.",
            parse_mode="HTML",
            reply_markup=join_keyboard()
        )
        return

    reward_referrer_once(user_id)
    send_dashboard(message, "🎉 <b>Verification Successful! Aapka bot taiyar hai key generate karne ke liye!</b>")


# =========================================================
# VERIFY CALLBACK
# =========================================================

@bot.callback_query_handler(func=lambda call: call.data == "verify")
def verify_callback(call):
    user_id = call.from_user.id
    bot.answer_callback_query(call.id)

    if not check_joined(user_id):
        bot.send_message(
            user_id,
            "❌ <b>Verification Failed</b>\n\nAapne abhi channel join nahi kiya hai. Pehle join karein!",
            parse_mode="HTML",
            reply_markup=join_keyboard()
        )
        return

    reward_referrer_once(user_id)
    bot.send_message(user_id, "✅ <b>Verification Successful!</b>", parse_mode="HTML")
    send_dashboard(call.message, "🎉 <b>Aapka bot taiyar hai key generate karne ke liye!</b> 🔥")


# =========================================================
# TEXT MESSAGE HANDLERS FOR REPLY KEYBOARD BUTTONS
# =========================================================

@bot.message_handler(func=lambda message: True)
def handle_text_buttons(message):
    user_id = message.from_user.id
    text = (message.text or "").strip()

    create_user_if_missing(message.from_user)

    if not check_joined(user_id):
        bot.send_message(
            user_id,
            "⚠️ Bot use karne ke liye pehle official channel join karein.",
            reply_markup=join_keyboard()
        )
        return

    if "Generate Key" in text:
        bot.send_message(
            user_id,
            "🛒 <b>Premium Plans</b>\n\n"
            "1 Day = ⭐ 3 Points\n"
            "3 Days = ⭐ 6 Points\n"
            "7 Days = ⭐ 10 Points\n"
            "30 Days = ⭐ 25 Points\n\n"
            "👇 Apna manpasand plan select karo:",
            parse_mode="HTML",
            reply_markup=plans_keyboard()
        )
        return

    if "Aim AI Panel" in text:
        bot.send_message(
            user_id,
            "💎 <b>Aim AI Panel</b>\n\n"
            "✅ Generate unlimited keys for free directly\n"
            "✅ Sell unlimited keys\n"
            "✅ Panel with your name\n"
            "✅ One time investment\n"
            "✅ Price ₹300 only\n"
            "❌ Free not available ❌❌\n\n"
            "💬 <b>Buy from here / Contact Owner:</b>\n"
            "👉 <b>@Memonsalim</b>",
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )
        return

    if "My Link" in text:
        link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
        bot.send_message(
            user_id,
            f"🔗 <b>Aapki Personal Referral Link</b>\n\n"
            f"<code>{link}</code>\n\n"
            f"👥 Is link ko doston ke sath share karein!\n"
            f"Har ek verified referral par aapko milega <b>+1 Point</b> ⭐",
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )
        return

    if "Referrals" in text:
        user = get_user(user_id)
        points = int(user.get("points", 0)) if user else 0
        referrals = int(user.get("referrals", 0)) if user else 0
        bot.send_message(
            user_id,
            f"👥 <b>Aapke Referrals Status</b>\n\n"
            f"👤 Total Referrals: <b>{referrals}</b>\n"
            f"⭐ Total Points: <b>{points}</b>",
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )
        return

    if "My Keys" in text:
        user = get_user(user_id)
        keys = user.get("keys", {}) if user else {}
        if not keys:
            bot.send_message(user_id, "📭 Abhi tak aapne koi key generate nahi ki hai.", reply_markup=main_keyboard())
            return

        text_msg = "🔐 <b>Aapki Generated Keys</b>\n\n"
        items = list(keys.items())
        items.reverse()
        for key, info in items[:20]:
            text_msg += f"🔑 <code>{key}</code>\n⏳ {info.get('days', '?')} Days\n📅 {info.get('created_at', '-')}\n\n"

        bot.send_message(user_id, text_msg, parse_mode="HTML", reply_markup=main_keyboard())
        return

    if "Refresh" in text:
        send_dashboard(message)
        return

    if "How it works" in text or "How It Works" in text:
        bot.send_message(
            user_id,
            "📖 <b>How It Works (Kaise Kaam Karta Hai)</b>\n\n"
            "1️⃣ Bot ko start karein.\n"
            "2️⃣ Official channel join karke Verify karein.\n"
            "3️⃣ Apni Referral Link doston ke sath share karein.\n"
            "4️⃣ Har verified referral par <b>+1 Point</b> earn karein.\n"
            "5️⃣ Points se apni <b>Premium Key</b> generate karein! 🎉",
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )
        return


# =========================================================
# INLINE CALLBACK HANDLER FOR PLAN GENERATION
# =========================================================

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    data = call.data
    bot.answer_callback_query(call.id)

    if data == "refresh":
        send_dashboard(call.message)
        return

    if data.startswith("generate:"):
        plan_id = data.split(":", 1)[1]
        if not check_joined(user_id):
            bot.send_message(user_id, "❌ Pehle channel join karke Verify karo.", reply_markup=join_keyboard())
            return

        success, result = create_key_for_user(user_id, plan_id)
        if not success:
            bot.send_message(user_id, str(result), parse_mode="HTML", reply_markup=main_keyboard())
            return

        key_data = result
        bot.send_message(
            user_id,
            f"🎉 <b>KEY GENERATED SUCCESSFULLY!</b>\n\n"
            f"🔑 Key: <code>{key_data['key']}</code>\n"
            f"👤 Username: <code>{key_data['key']}</code>\n"
            f"🔐 Password: <code>{key_data['key']}</code>\n"
            f"⏳ Validity: <b>{key_data['days']} Days</b>\n\n"
            f"📱 <b>App Download Link:</b>\n{APP_DOWNLOAD_LINK}",
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )
        return


# =========================================================
# OTHER COMMANDS (/HELP, /PING)
# =========================================================

@bot.message_handler(commands=["help"])
def help_command(message):
    bot.send_message(message.chat.id, "📖 <b>Help Menu</b>\n\n/start - Bot ko restart karein", parse_mode="HTML", reply_markup=main_keyboard())


@bot.message_handler(commands=["ping"])
def ping_command(message):
    bot.reply_to(message, "🏓 Pong! Bot bilkul mast chal raha hai. 🚀")


# =========================================================
# BOT INFO & POLLING
# =========================================================

def load_bot_username():
    global BOT_USERNAME
    try:
        me = bot.get_me()
        BOT_USERNAME = me.username or ""
        print("Bot Username loaded:", BOT_USERNAME)
    except Exception as e:
        print("Could not get bot info:", e)


def start_bot():
    while True:
        try:
            print("Removing webhooks & starting polling...")
            bot.remove_webhook()
            bot.infinity_polling(timeout=30, long_polling_timeout=30, skip_pending=True)
        except Exception as e:
            print("Polling crashed:", e)
            print("Restarting in 5 seconds...")
            time.sleep(5)


# =========================================================
# MAIN EXECUTION
# ==
