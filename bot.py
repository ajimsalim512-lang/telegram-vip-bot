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
NINJA_APK_LINK = "https://t.me/memonxgaming/1060"
OWNER_CONTACT = "@Memonsalim"
WHATSAPP_NUMBER = "+91 6354525228"
PROOF_CHANNEL_LINK = "https://t.me/proofnovaengine"

INTRO_VIDEO_FILE_ID = os.getenv("INTRO_VIDEO_FILE_ID", "")
SECRET_ADMIN_COMMAND = "memonxgaming1235919398288281834848@1919394"

FREE_PLANS = {
    "1day": {"name": "1 Day Key", "days": 1, "points": 5},
    "7days": {"name": "7 Days Key", "days": 7, "points": 8},
    "15days": {"name": "15 Days Key", "days": 15, "points": 15},
    "lifetime": {"name": "Lifetime + Free Panel", "days": 3650, "points": 100}
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
            "unlimited_access": False,
            "started": True,
            "notifications_enabled": True,
            "intro_sent": False,
            "ninja_ref_count": 0,
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
    ninja_refs = int(referrer.get("ninja_ref_count", 0))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    firebase_patch(f"users/{referrer_id}", {
        "points": old_points + 1,
        "referrals": old_referrals + 1,
        "ninja_ref_count": ninja_refs + 1,
        f"referral_rewards/{referred_id}": {"rewarded_at": now}
    })

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

def generate_unique_key():
    for _ in range(100):
        key = f"DP-{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}"
        if firebase_get(f"keys/{key}") is None:
            return key
    return None

@bot.message_handler(content_types=['video'])
def handle_video_upload(message):
    file_id = message.video.file_id
    bot.reply_to(message, f"🎥 <b>Video File ID Received!</b>\n\nCopy this ID into code:\n<code>{file_id}</code>", parse_mode="HTML")

# =========================================================
# KEYBOARDS
# =========================================================

def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton("🎁 Free Aim AI"), types.KeyboardButton("💳 Purchase Aim AI"))
    markup.row(types.KeyboardButton("💎 Purchase Aim AI Panel"), types.KeyboardButton("🥷 Ninja 8BP"))
    markup.row(types.KeyboardButton("🔗 My Link"), types.KeyboardButton("👥 Referrals"))
    markup.row(types.KeyboardButton("🔑 My Keys"), types.KeyboardButton("🛡️ Trust Proof"))
    markup.row(types.KeyboardButton("🔄 Refresh"), types.KeyboardButton("ℹ️ How it works"))
    return markup

def join_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📢 Join Official Channel", url=CHANNEL_LINK))
    markup.add(types.InlineKeyboardButton("✅ Verify Joining", callback_data="verify"))
    return markup

def free_plans_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    for pid, plan in FREE_PLANS.items():
        markup.add(types.InlineKeyboardButton(f"{plan['name']} - ⭐ {plan['points']}", callback_data=f"freegen:{pid}"))
    markup.add(types.InlineKeyboardButton("⬅️ Back", callback_data="refresh"))
    return markup

# =========================================================
# HANDLERS
# =========================================================

def send_welcome_intro(user_id, extra_msg=""):
    user = get_user(user_id)
    if not user:
        return

    caption = (f"{extra_msg}\n\n" if extra_msg else "") + (
        f"🔥 <b>AIM AI PANEL & FREE AIM AI BOT!</b> 🔥\n"
        f"Free me Aim AI keys lene ke liye friends ko refer karein, ya direct purchase karein.\n\n"
        f"👇 Niche diye gaye options me se apna manpasand feature select karein:"
    )

    if not user.get("intro_sent", False):
        try:
            if INTRO_VIDEO_FILE_ID:
                bot.send_video(user_id, INTRO_VIDEO_FILE_ID, caption=caption, parse_mode="HTML", reply_markup=main_keyboard())
            else:
                bot.send_message(user_id, caption, parse_mode="HTML", reply_markup=main_keyboard())
            firebase_patch(f"users/{user_id}", {"intro_sent": True})
            return
        except Exception:
            pass

    bot.send_message(user_id, caption, parse_mode="HTML", reply_markup=main_keyboard())

@bot.message_handler(commands=["start"])
def start_command(message):
    user_id = message.from_user.id
    args = message.text.split()
    referrer_id = args[1] if len(args) > 1 and args[1].isdigit() else None

    create_user_if_missing(message.from_user, referrer_id)

    if not check_joined(user_id):
        bot.send_message(
            user_id,
            f"👋 <b>Welcome {message.from_user.first_name}!</b>\n\n"
            f"⚠️ Bot aur refer system use karne ke liye pehle hamara <b>Telegram Channel join karna compulsory hai</b>, warna yeh work nahi karega!\n\n"
            f"👇 Channel join karne ke baad <b>Verify Joining</b> dabao.",
            parse_mode="HTML",
            reply_markup=join_keyboard()
        )
        return

    reward_referrer_once(user_id)
    send_welcome_intro(user_id, "🎉 <b>Verification Successful!</b>")

@bot.callback_query_handler(func=lambda call: call.data == "verify")
def verify_callback(call):
    user_id = call.from_user.id
    bot.answer_callback_query(call.id)

    if not check_joined(user_id):
        bot.send_message(
            user_id,
            "❌ <b>Verification Failed</b>\n\nAapne abhi tak channel join nahi kiya hai! Pehle channel join karein warna kuch work nahi karega.",
            parse_mode="HTML",
            reply_markup=join_keyboard()
        )
        return

    reward_referrer_once(user_id)
    bot.send_message(user_id, "✅ <b>Verification Successful!</b>", parse_mode="HTML")
    send_welcome_intro(user_id, "🎉 <b>Aapka bot ready hai!</b>")

@bot.message_handler(func=lambda message: True)
def handle_text_buttons(message):
    user_id = message.from_user.id
    text = (message.text or "").strip()
    create_user_if_missing(message.from_user)

    if text == SECRET_ADMIN_COMMAND:
        firebase_patch(f"users/{user_id}", {"unlimited_access": True})
        bot.send_message(user_id, "👑 <b>Secret Admin Access Activated!</b>", parse_mode="HTML", reply_markup=main_keyboard())
        return

    # Force Channel Join Check for ALL Actions
    if not check_joined(user_id):
        bot.send_message(
            user_id,
            "⚠️ <b>Access Denied!</b>\n\nBot ko use karne ya refer system chalane ke liye pehle official Telegram Channel join karna compulsory hai!",
            parse_mode="HTML",
            reply_markup=join_keyboard()
        )
        return

    if "Free Aim AI" in text:
        bot.send_message(
            user_id,
            "🎁 <b>Free Aim AI Key Generator</b>\n\n"
            "• 5 Points ➡️ 1 Day Key\n"
            "• 8 Points ➡️ 7 Days Key\n"
            "• 15 Points ➡️ 15 Days Key\n"
            "• 100 Points ➡️ Lifetime + Free Panel\n\n"
            "👇 Apna plan select karein:",
            parse_mode="HTML",
            reply_markup=free_plans_keyboard()
        )
    elif "Purchase Aim AI" in text:
        bot.send_message(
            user_id,
            "💳 <b>Purchase Aim AI</b>\n\n"
            "Direct paid key kharadne ke liye owner se contact karein:\n"
            f"• Telegram: <b>{OWNER_CONTACT}</b>\n"
            f"• WhatsApp: <b>{WHATSAPP_NUMBER}</b>",
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )
    elif "Purchase Aim AI Panel" in text:
        bot.send_message(
            user_id,
            "💎 <b>Purchase Aim AI Panel</b>\n\n"
            "✅ Generate unlimited keys directly\n"
            "✅ Sell unlimited keys & panels\n"
            "✅ Panel with your name\n"
            "✅ One time investment\n\n"
            "💬 <b>Purchase ke liye contact karein:</b>\n"
            f"• Telegram: <b>{OWNER_CONTACT}</b>\n"
            f"• WhatsApp: <b>{WHATSAPP_NUMBER}</b>",
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )
    elif "Ninja 8BP" in text:
        user = get_user(user_id)
        ninja_count = user.get("ninja_ref_count", 0) if user else 0
        markup = types.InlineKeyboardMarkup()
        if ninja_count >= 10:
            markup.add(types.InlineKeyboardButton("📥 Download APK File Only", url=NINJA_APK_LINK))
            msg = f"🥷 <b>Ninja 8BP - Free APK Unlocked!</b>\n\nAapne 10 refers successfully complete kar liye hain ({ninja_count}/10). Niche button se sirf APK file download karein 👇"
        else:
            msg = f"🥷 <b>Ninja 8BP - Free APK Offer</b>\n\nTotal 10 refers complete karne par aapko sirf APK file free me milegi (Channel join compulsory hai)!\n\n👥 Aapke current refers: <b>{ninja_count}/10</b>\n\n💡 Apni referral link se doston ko invite karein!"
        
        bot.send_message(user_id, msg, parse_mode="HTML", reply_markup=markup)
    elif "My Link" in text:
        link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
        bot.send_message(
            user_id,
            f"🔗 <b>Aapki Personal Referral Link</b>\n\n"
            f"<code>{link}</code>\n\n"
            f"👥 Is link ko doston ke sath share karein!\n"
            f"Har ek verified referral par (jo channel join karega) aapko milega <b>+1 Point</b> ⭐",
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )
    elif "Referrals" in text:
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
    elif "Trust Proof" in text:
        bot.send_message(
            user_id,
            "🛡️ <b>Trust Proof Channel</b>\n\n"
            "Customer proofs aur successful deals yahan check karein:\n"
            f"👉 <b>{PROOF_CHANNEL_LINK}</b>",
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )
    elif "Refresh" in text:
        send_welcome_intro(user_id)
    elif "How it works" in text:
        bot.send_message(
            user_id,
            "📖 <b>How It Works (Aasan Bhasha Me)</b>\n\n"
            "1️⃣ Bot start karne ke liye official Telegram channel join karna compulsory hai.\n"
            "2️⃣ Apni **Referral Link** doston ke sath share karke points earn karein (1 Refer = 1 Point).\n"
            "3️⃣ Free Aim AI ke liye points use karein, ya phir direct paid purchase ke liye **{OWNER_CONTACT}** par contact karein!",
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    data = call.data
    bot.answer_callback_query(call.id)

    if data == "refresh":
        send_welcome_intro(user_id)

    elif data.startswith("freegen:"):
        plan_id = data.split(":", 1)[1]
        if not check_joined(user_id):
            bot.send_message(
                user_id,
                "❌ <b>Access Denied</b>\n\nPehle official channel join karein warna key generate nahi hogi!",
                parse_mode="HTML",
                reply_markup=join_keyboard()
            )
            return
        
        user = get_user(user_id)
        if not user:
            bot.send_message(user_id, "❌ User data nahi mila.", reply_markup=main_keyboard())
            return

        plan = FREE_PLANS[plan_id]
        points = int(user.get("points", 0))

        if points < plan["points"]:
            bot.send_message(
                user_id,
                f"❌ <b>Insufficient Points</b>\n\n"
                f"⭐ Your Points: <b>{points}</b>\n"
                f"Required: <b>{plan['points']}</b>\n\n"
                f"💡 Aur points ke liye apni referral link share karein!",
                parse_mode="HTML",
                reply_markup=main_keyboard()
            )
            return

        key = generate_unique_key()
        if not key:
            bot.send_message(user_id, "❌ Key generation failed. Dobara koshish karein.", reply_markup=main_keyboard())
            return

        new_points = points - plan["points"]
        
        # UTC timezone sync to fix expiration issues
        now_utc = datetime.now(timezone.utc)
        created_at_str = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")

        key_data = {
            "key": key,
            "username": key,
            "password": key,
            "user_id": str(user_id),
            "days": plan["days"],
            "status": "active",
            "created_at": created_at_str
        }

        if not firebase_put(f"keys/{key}", key_data):
            bot.send_message(user_id, "❌ Database error.", reply_markup=main_keyboard())
            return

        firebase_patch(f"users/{user_id}", {"points": new_points, f"keys/{key}": key_data})

        # Exact requested format
        success_msg = (
            f"🎉 <b>KEY GENERATED SUCCESSFULLY!</b>\n\n"
            f"Username: <code>{key}</code>\n"
            f"Password: <code>{key}</code>\n"
            f"Key: <code>{key}</code>\n\n"
            f"⏳ Validity: <b>{plan['name']}</b>\n"
            f"📱 <b>App Download Link:</b>\n{APP_DOWNLOAD_LINK}"
        )
        bot.send_message(user_id, success_msg, parse_mode="HTML", reply_markup=main_keyboard())

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
    start_bot()
        
