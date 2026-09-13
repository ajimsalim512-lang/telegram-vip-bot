
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

BOT_TOKEN = os.getenv("BOT_TOKEN", "8803139822:AAHu7GVRxXkozRuM7nhWKnPKAsS3iOhlEbY")
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
NINJA_APK_FILE_ID = os.getenv("NINJA_APK_FILE_ID", "")
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
    try:
        port = int(os.getenv("PORT", "10000"))
        app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
    except Exception as e:
        logger.error("Flask server error: %s", e)

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
    try:
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
    except Exception as e:
        logger.error("create_user_if_missing error: %s", e)
        return None

def check_joined(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, int(user_id))
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        logger.error("Membership check error: %s", e)
        return False

def reward_referrer_once(referred_id):
    try:
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
                "🎉 New Referral Joined!\n\nAapki link se ek naye user ne channel join kar liya hai!\n⭐ Aapko +1 Point mil gaya hai! 🚀"
            )
        except Exception:
            pass
        return True
    except Exception as e:
        logger.error("reward_referrer_once error: %s", e)
        return False

def generate_unique_key():
    for _ in range(100):
        key = f"DP-{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}"
        if firebase_get(f"keys/{key}") is None:
            return key
    return None

@bot.message_handler(content_types=['video', 'document'])
def handle_media_upload(message):
    try:
        if message.video:
            file_id = message.video.file_id
            bot.reply_to(message, f"🎥 Video File ID:\n<code>{file_id}</code>", parse_mode="HTML")
        elif message.document:
            file_id = message.document.file_id
            bot.reply_to(message, f"📁 Document/APK File ID:\n<code>{file_id}</code>", parse_mode="HTML")
    except Exception as e:
        logger.error("Media upload error: %s", e)
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

def send_welcome_intro(user_id, extra_msg=""):
    try:
        user = get_user(user_id)
        if not user:
            return

        features_text = (
            "🤖 BOT FEATURES & OPTIONS MENU 🚀\n\n"
            "🎁 Free Aim AI: Points earn karke free keys generate karein (1 Refer = 1 Point).\n"
            "💳 Purchase Aim AI: Direct paid key ke liye owner se contact karein.\n"
            "💎 Purchase Aim AI Panel: Unlimited keys aur panel selling business ke liye (Only ₹400).\n"
            "🥷 Ninja 8BP: 10 refers complete karke free APK file unlock karein.\n"
            "🔗 My Link: Apni personal referral link copy karein.\n"
            "👥 Referrals: Apne total referrals aur points check karein.\n"
            "🔑 My Keys: Aapki saari generated keys yahan dikhengi.\n"
            "🛡️ Trust Proof: Customer proofs aur successful deals channel.\n\n"
            "👇 Apna option select karne ke liye niche buttons ka use karein:"
        )

        caption = (f"{extra_msg}\n\n" if extra_msg else "") + features_text

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
    except Exception as e:
        logger.error("send_welcome_intro error: %s", e)

@bot.message_handler(commands=["start"])
def start_command(message):
    try:
        user_id = message.from_user.id
        args = message.text.split()
        referrer_id = args[1] if len(args) > 1 and args[1].isdigit() else None

        create_user_if_missing(message.from_user, referrer_id)

        if not check_joined(user_id):
            bot.send_message(
                user_id,
                f"👋 Welcome {message.from_user.first_name}!\n\n"
                "⚠️ Bot aur refer system use karne ke liye pehle hamara Telegram Channel join karna compulsory hai, warna yeh work nahi karega!\n\n"
                "👇 Channel join karne ke baad Verify Joining dabao.",
                reply_markup=join_keyboard()
            )
            return

        reward_referrer_once(user_id)
        send_welcome_intro(user_id, "🎉 Verification Successful!")
    except Exception as e:
        logger.error("start_command error: %s", e)

@bot.callback_query_handler(func=lambda call: call.data == "verify")
def verify_callback(call):
    try:
        user_id = call.from_user.id
        bot.answer_callback_query(call.id)

        if not check_joined(user_id):
            bot.send_message(
                user_id,
                "❌ Verification Failed\n\nAapne abhi tak channel join nahi kiya hai! Pehle channel join karein warna kuch work nahi karega.",
                reply_markup=join_keyboard()
            )
            return

        reward_referrer_once(user_id)
        bot.send_message(user_id, "✅ Verification Successful!")
        send_welcome_intro(user_id, "🎉 Aapka bot ready hai!")
    except Exception as e:
        logger.error("verify_callback error: %s", e)

@bot.message_handler(func=lambda message: True)
def handle_text_buttons(message):
    try:
        user_id = message.from_user.id
        text = (message.text or "").strip()
        create_user_if_missing(message.from_user)

        if text == SECRET_ADMIN_COMMAND:
            firebase_patch(f"users/{user_id}", {"unlimited_access": True})
            bot.send_message(user_id, "👑 Secret Admin Access Activated!", reply_markup=main_keyboard())
            return

        if not check_joined(user_id):
            bot.send_message(
                user_id,
                "⚠️ Access Denied!\n\nBot ko use karne ya refer system chalane ke liye pehle official Telegram Channel join karna compulsory hai!",
                reply_markup=join_keyboard()
            )
            return

        if "Free Aim AI" in text:
            bot.send_message(
                user_id,
                "🎁 Free Aim AI Key Generator\n\n"
                "• 5 Points ➡️ 1 Day Key\n"
                "• 8 Points ➡️ 7 Days Key\n"
                "• 15 Points ➡️ 15 Days Key\n"
                "• 100 Points ➡️ Lifetime + Free Panel\n\n"
                "👇 Apna plan select karein:",
                reply_markup=free_plans_keyboard()
            )
        elif "Purchase Aim AI" in text:
            bot.send_message(
                user_id,
                "💳 Purchase Aim AI\n\n"
                "Direct paid key kharadne ke liye owner se contact karein:\n"
                f"• Telegram: {OWNER_CONTACT}\n"
                f"• WhatsApp: {WHATSAPP_NUMBER}",
                reply_markup=main_keyboard()
            )
        elif "Purchase Aim AI Panel" in text:
            bot.send_message(
                user_id,
                "💎 AIM AI PANEL - KING OF ALL EDITORS 👑\n\n"
                "🔥 Limited Time Special Offer: Only at ₹400! 🔥\n\n"
                "Kyun khareedein yeh panel? Fayde hi fayde:\n"
                "✅ Unlimited Key Generation: Bina kisi limit ke jitni marzi utni keys khud generate karein!\n"
                "✅ Start Your Own Business: Khud ka panel bech kar mota munafa kamayein!\n"
                "✅ 100% Branded Panel: Panel par naam aapka hoga!\n"
                "✅ One time investment: Bar-bar paise dene ki jhanjhat khatam!\n\n"
                "❌ Free version available nahi hai, isliye time waste mat karein! ❌\n\n"
                "💬 Purchase karne ke liye contact karein:\n"
                f"• Telegram: {OWNER_CONTACT}\n"
                f"• WhatsApp: {WHATSAPP_NUMBER}",
                reply_markup=main_keyboard()
            )
        elif "Ninja 8BP" in text:
            user = get_user(user_id)
            ninja_count = user.get("ninja_ref_count", 0) if user else 0
            if ninja_count >= 10:
                if NINJA_APK_FILE_ID:
                    try:
                        bot.send_document(
                            user_id,
                            NINJA_APK_FILE_ID,
                            caption="🥷 Ninja 8BP - Free APK File\n\nAapne 10 refers successfully complete kar liye hain! Yeh rahi aapki APK file 👇"
                        )
                        return
                    except Exception:
                        pass
                bot.send_message(
                    user_id,
                    f"🥷 Ninja 8BP - Free APK Unlocked!\n\nAapne 10 refers complete kar liye hain! Download Link:\n{NINJA_APK_LINK}",
                    reply_markup=main_keyboard()
                )
            else:
                bot.send_message(
                    user_id,
                    f"🥷 Ninja 8BP - Free APK Offer\n\nTotal 10 refers complete karne par aapko sirf APK file free me milegi (Channel join compulsory hai)!\n\n👥 Aapke current refers: {ninja_count}/10\n\n💡 Apni referral link se doston ko invite karein!",
                    reply_markup=main_keyboard()
                )
        elif "My Link" in text:
            link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
            bot.send_message(
                user_id,
                f"🔗 Aapki Personal Referral Link\n\n<code>{link}</code>\n\n👥 Is link ko doston ke sath share karein!\nHar ek verified referral par (jo channel join karega) aapko milega +1 Point ⭐",
                parse_mode="HTML",
                reply_markup=main_keyboard()
            )
        elif "Referrals" in text:
            user = get_user(user_id)
            points = int(user.get("points", 0)) if user else 0
            referrals = int(user.get("referrals", 0)) if user else 0
            bot.send_message(
                user_id,
                f"👥 Aapke Referrals Status\n\n👤 Total Referrals: {referrals}\n⭐ Total Points: {points}",
                reply_markup=main_keyboard()
            )
        elif "My Keys" in text:
            user = get_user(user_id)
            keys = user.get("keys", {}) if user else {}
            if not keys:
                bot.send_message(user_id, "📭 Abhi tak aapne koi key generate nahi ki hai.", reply_markup=main_keyboard())
                return
            text_msg = "🔐 Aapki Generated Keys\n\n"
            for k, info in list(keys.items())[::-1][:20]:
                text_msg += f"🔑 <code>{k}</code>\n⏳ {info.get('days', '?')} Days\n📅 {info.get('created_at', '-')}\n\n"
            bot.send_message(user_id, text_msg, parse_mode="HTML", reply_markup=main_keyboard())
        elif "Trust Proof" in text:
            bot.send_message(
                user_id,
                "🛡️ Trust Proof Channel\n\n"
                f"Customer proofs aur successful deals yahan check karein:\n👉 {PROOF_CHANNEL_LINK}",
                reply_markup=main_keyboard()
            )
        elif "Refresh" in text:
            send_welcome_intro(user_id)
        elif "How it works" in text:
            bot.send_message(
                user_id,
                "📖 How It Works (Aasan Bhasha Me)\n\n"
                "1️⃣ Bot start karne ke liye official Telegram channel join karna compulsory hai.\n"
                "2️⃣ Apni Referral Link doston ke sath share karke points earn karein (1 Refer = 1 Point).\n"
                f"3️⃣ Free Aim AI ke liye points use karein, ya phir direct paid purchase ke liye {OWNER_CONTACT} par contact karein!",
                reply_markup=main_keyboard()
            )
    except Exception as e:
        logger.error("handle_text_buttons error: %s", e)

@bot.callback_query_handler(func=lambda call: call.data.startswith("freegen:"))
def freegen_callback(call):
    try:
        user_id = call.from_user.id
        data = call.data
        bot.answer_callback_query(call.id)

        plan_id = data.split(":", 1)[1]
        if not check_joined(user_id):
            bot.send_message(
                user_id,
                "❌ Access Denied\n\nPehle official channel join karein warna key generate nahi hogi!",
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
                f"❌ Insufficient Points\n\n⭐ Your Points: {points}\nRequired: {plan['points']}\n\n💡 Aur points ke liye apni referral link share karein!",
                reply_markup=main_keyboard()
            )
            return

        key = generate_unique_key()
        if not key:
            bot.send_message(user_id, "❌ Key generation failed. Dobara koshish karein.", reply_markup=main_keyboard())
            return

        new_points = points - plan["points"]
        
        time.sleep(0.5)
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

        success_msg = (
            f"🎉 KEY GENERATED SUCCESSFULLY!\n\n"
            f"Username: <code>{key}</code>\n"
            f"Password: <code>{key}</code>\n"
            f"Key: <code>{key}</code>\n\n"
            f"⏳ Validity: {plan['name']}\n"
            f"📱 App Download Link:\n{APP_DOWNLOAD_LINK}"
        )
        bot.send_message(user_id, success_msg, parse_mode="HTML", reply_markup=main_keyboard())
    except Exception as e:
        logger.error("freegen_callback error: %s", e)

def load_bot_username():
    try:
        global BOT_USERNAME
        me = bot.get_me()
        if me and me.username:
            BOT_USERNAME = me.username
    except Exception as e:
        logger.error("Could not load bot username: %s", e)

def start_bot():
    while True:
        try:
            bot.remove_webhook()
            bot.infinity_polling(timeout=30, long_polling_timeout=30, skip_pending=True)
        except Exception as e:
            logger.error("Polling crashed: %s", e)
            time.sleep(5)

if __name__ == "__main__":
    try:
        threading.Thread(target=run_web_server, daemon=True).start()
        time.sleep(2)
        load_bot_username()
        start_bot()
    except Exception as e:
        logger.error("Main execution error: %s", e)
    
