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
# CONFIGURATION & TOKENS
# =========================================================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8803139822:AAGOzEAyDvgqmq0Gh42Zz0bsvZ-29oEKy5o")
FIREBASE_AUTH = os.getenv("FIREBASE_AUTH", "V677nUiq24iMv58OcV02CXyE7iHFqFbke4VVPdmL")
FIREBASE_URL = os.getenv("FIREBASE_URL", "https://aimai-817ef-default-rtdb.asia-southeast1.firebasedatabase.app").rstrip("/")

CHANNEL_1_USERNAME = "@novaengine01"
CHANNEL_1_LINK = "https://t.me/novaengine01"
CHANNEL_2_USERNAME = "@Memonxgamingff"
CHANNEL_2_LINK = "https://t.me/Memonxgamingff"

OWNER_CONTACT = "@Memonsalim"
WHATSAPP_NUMBER = "+91 6354525228"
FREE_KEY_BOT = "@Arsenal_xex_freekeybot"
TRUST_PROOF_LINK = "https://t.me/proofnovaengine"

FREE_FIRE_MEDIAFIRE = "https://www.mediafire.com/file/va2vkas72dfjgjx"
CARROM_FILENAME = "AimAi v new (1).apk"
EIGHT_BP_FILENAME = "Ninja_Engine_v2.1.1.apk"

SECRET_ADMIN_COMMAND = "memonxgaming1235919398288281834848@1919394"
REFRESH_NOTIFIED_KEY = "refresh_notified_v6"
VERIFICATION_EMOJIS = ["🍎", "🚗", "⭐", "⚽", "🐱"]

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("premium-bot")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
BOT_USERNAME = ""

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running smoothly."

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
                "stars": 0,
                "referrals": 0,
                "referrer_id": ref,
                "unlimited_access": False,
                "verified": False,
                "verification_step": "emoji",
                "target_emoji": "",
                "started": True,
                "created_at": now,
                "last_seen": now,
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

def check_joined_both(user_id):
    try:
        m1 = bot.get_chat_member(CHANNEL_1_USERNAME, int(user_id))
        m2 = bot.get_chat_member(CHANNEL_2_USERNAME, int(user_id))
        ok1 = m1.status in ("member", "administrator", "creator")
        ok2 = m2.status in ("member", "administrator", "creator")
        return ok1 and ok2
    except Exception as e:
        logger.error("Membership check error: %s", e)
        return False

def check_refresh_broadcast(user_id):
    try:
        user = get_user(user_id)
        if user and not user.get(REFRESH_NOTIFIED_KEY, False):
            bot.send_message(
                user_id,
                "🔄 <b>Bot Refresh Update!</b>\n\n"
                "Aapka bot successfully refresh aur update ho chuka hai! Naye features ke sath ab aap ise use kar sakte hain 🚀",
                parse_mode="HTML"
            )
            firebase_patch(f"users/{user_id}", {REFRESH_NOTIFIED_KEY: True})
    except Exception:
        pass

def reward_referrer_star(referred_id):
    try:
        referred = get_user(referred_id)
        if not referred:
            return
        referrer_id = referred.get("referrer_id")
        if not referrer_id or int(referrer_id) == int(referred_id):
            return
        referrer = get_user(referrer_id)
        if not referrer:
            return

        rewards = referrer.get("referral_rewards", {})
        if str(referred_id) in rewards:
            return

        current_stars = int(referrer.get("stars", 0))
        current_refs = int(referrer.get("referrals", 0))
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        firebase_patch(f"users/{referrer_id}", {
            "stars": current_stars + 1,
            "referrals": current_refs + 1,
            f"referral_rewards/{referred_id}": {"rewarded_at": now}
        })

        try:
            bot.send_message(
                int(referrer_id),
                "🎉 <b>New Referral Joined!</b>\n\n"
                "Aapki link se ek naye user ne join kar liya hai!\n"
                "⭐ Aapko <b>+1 Star</b> mil gaya hai! 🚀",
                parse_mode="HTML"
            )
        except Exception:
            pass
    except Exception as e:
        logger.error("reward_referrer_star error: %s", e)

def send_local_apk(user_id, filename, caption):
    try:
        if os.path.exists(filename):
            with open(filename, "rb") as doc:
                bot.send_document(user_id, doc, caption=caption, parse_mode="HTML")
            return True
        else:
            logger.error("File not found on server: %s", filename)
    except Exception as e:
        logger.error("Send local apk error: %s", e)
    return False

# =========================================================
# KEYBOARDS
# =========================================================
def main_menu_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton("🔥 Free Fire"), types.KeyboardButton("🎱 Carrom"))
    markup.row(types.KeyboardButton("🎱 8BP"), types.KeyboardButton("💳 Paid Hack"))
    markup.row(types.KeyboardButton("🔗 My Link"), types.KeyboardButton("👥 My Status"))
    markup.row(types.KeyboardButton("🛡️ Trust Proof"), types.KeyboardButton("🔄 Refresh"))
    return markup

def channels_join_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📢 Join Channel 1 (@novaengine01)", url=CHANNEL_1_LINK))
    markup.add(types.InlineKeyboardButton("📢 Join Channel 2 (@Memonxgamingff)", url=CHANNEL_2_LINK))
    markup.add(types.InlineKeyboardButton("✅ Verify Channels Joined", callback_data="verify_channels"))
    return markup

# =========================================================
# HANDLERS & VERIFICATION
# =========================================================
@bot.message_handler(commands=["start"])
def start_command(message):
    try:
        user_id = message.from_user.id
        args = message.text.split()
        referrer_id = args[1] if len(args) > 1 and args[1].isdigit() else None

        user = create_user_if_missing(message.from_user, referrer_id)
        check_refresh_broadcast(user_id)

        if user.get("verified", False) and check_joined_both(user_id):
            reward_referrer_star(user_id)
            bot.send_message(user_id, "🎉 <b>Welcome back! Aapka menu ready hai:</b>", parse_mode="HTML", reply_markup=main_menu_keyboard())
            return

        # Human Verification: Random Emoji selection
        target = random.choice(VERIFICATION_EMOJIS)
        firebase_patch(f"users/{user_id}", {"verification_step": "emoji", "target_emoji": target})

        markup = types.InlineKeyboardMarkup(row_width=5)
        buttons = [types.InlineKeyboardButton(e, callback_data=f"emoji:{e}") for e in VERIFICATION_EMOJIS]
        random.shuffle(buttons)
        markup.add(*buttons)

        bot.send_message(
            user_id,
            f"🤖 <b>Human Verification Required</b>\n\n"
            f"Please niche diye gaye emojis me se <b>{target}</b> emoji par click karein taaki prove ho sake aap human hain:",
            parse_mode="HTML",
            reply_markup=markup
        )
    except Exception as e:
        logger.error("start_command error: %s", e)

@bot.callback_query_handler(func=lambda call: call.data.startswith("emoji:"))
def emoji_verify_callback(call):
    try:
        user_id = call.from_user.id
        _, clicked = call.data.split(":", 1)
        bot.answer_callback_query(call.id)

        user = get_user(user_id)
        if not user:
            return

        target = user.get("target_emoji", "")
        if clicked != target:
            bot.send_message(user_id, f"❌ <b>Wrong Emoji!</b> Sahi emoji select karein: {target}", parse_mode="HTML")
            return

        firebase_patch(f"users/{user_id}", {"verification_step": "channels"})

        bot.send_message(
            user_id,
            "✅ <b>Human Verification Passed!</b>\n\n"
            "⚠️ Ab bot ko use karne ke liye hamare <b>dono channels join karna compulsory hai</b>:\n\n"
            f"1️⃣ <a href='{CHANNEL_1_LINK}'>Channel 1 (@novaengine01)</a>\n"
            f"2️⃣ <a href='{CHANNEL_2_LINK}'>Channel 2 (@Memonxgamingff)</a>\n\n"
            "👇 Dono join karne ke baad niche button dabayein:",
            parse_mode="HTML",
            reply_markup=channels_join_keyboard(),
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error("emoji_verify_callback error: %s", e)

@bot.callback_query_handler(func=lambda call: call.data == "verify_channels")
def verify_channels_callback(call):
    try:
        user_id = call.from_user.id
        bot.answer_callback_query(call.id)

        if not check_joined_both(user_id):
            bot.send_message(
                user_id,
                "❌ <b>Verification Failed!</b>\n\nAapne abhi tak dono channels join nahi kiye hain! Pehle dono join karein phir verify dabayein.",
                parse_mode="HTML",
                reply_markup=channels_join_keyboard()
            )
            return

        firebase_patch(f"users/{user_id}", {"verified": True})
        reward_referrer_star(user_id)

        bot.send_message(
            user_id,
            "🎉 <b>All Verifications Successful!</b>\n\nAapka account successfully verify ho chuka hai 👇",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard()
        )
    except Exception as e:
        logger.error("verify_channels_callback error: %s", e)

@bot.message_handler(func=lambda message: True)
def handle_menu_actions(message):
    try:
        user_id = message.from_user.id
        text = (message.text or "").strip()
        user = create_user_if_missing(message.from_user)
        check_refresh_broadcast(user_id)

        if text == SECRET_ADMIN_COMMAND:
            firebase_patch(f"users/{user_id}", {"unlimited_access": True, "stars": 999999, "referrals": 999999})
            bot.send_message(user_id, "👑 <b>Admin Unlimited Stars & Access Activated!</b>", parse_mode="HTML", reply_markup=main_menu_keyboard())
            return

        if not user.get("verified", False) or not check_joined_both(user_id):
            bot.send_message(user_id, "⚠️ Pehle verification aur channel join complete karein! Type /start", reply_markup=types.ReplyKeyboardRemove())
            return

        is_unlimited = user.get("unlimited_access", False)
        stars = 999999 if is_unlimited else int(user.get("stars", 0))

        if "Free Fire" in text:
            if stars >= 10:
                bot.send_message(
                    user_id,
                    f"🔥 <b>Free Fire Link Unlocked!</b>\n\n"
                    f"Aapne 10 refers/stars complete kar liye hain! Yeh raha aapka MediaFire link 👇\n"
                    f"👉 {FREE_FIRE_MEDIAFIRE}",
                    parse_mode="HTML",
                    reply_markup=main_menu_keyboard(),
                    disable_web_page_preview=True
                )
            else:
                bot.send_message(
                    user_id,
                    f"🔥 <b>Free Fire Hack Offer</b>\n\n"
                    f"Free link lene ke liye total 10 refers (stars) complete karein!\n"
                    f"⭐ Aapke current stars/refers: <b>{stars}/10</b>\n\n"
                    f"💡 Apni referral link se doston ko invite karein!",
                    parse_mode="HTML",
                    reply_markup=main_menu_keyboard()
                )

        elif "Carrom" in text:
            if stars >= 10:
                sent = send_local_apk(user_id, CARROM_FILENAME, "🎱 <b>Carrom AimAi v new APK File Unlocked!</b>\nAapne 10 refers complete kar liye hain! Yeh rahi aapki APK file 👇")
                bot.send_message(user_id, f"🔑 <b>Key yahan se generate karein:</b> {FREE_KEY_BOT}", parse_mode="HTML")
                if not sent:
                    bot.send_message(
                        user_id,
                        f"🎱 <b>Carrom AimAi v new APK Unlocked!</b>\n\n"
                        f"Aapne 10 refers complete kar liye hain! File name: <code>{CARROM_FILENAME}</code> (Make sure file is uploaded on GitHub)\n\n"
                        f"🔑 Key yahan se generate karein: <b>{FREE_KEY_BOT}</b>",
                        parse_mode="HTML",
                        reply_markup=main_menu_keyboard()
                    )
            else:
                bot.send_message(
                    user_id,
                    f"🎱 <b>Carrom Hack Offer</b>\n\n"
                    f"Free me lene ke liye total 10 refers complete karein!\n"
                    f"⭐ Aapke current stars: <b>{stars}/10</b>\n\n"
                    f"💡 Key yahan se generate karein (refer complete hone ke baad): <b>{FREE_KEY_BOT}</b>",
                    parse_mode="HTML",
                    reply_markup=main_menu_keyboard()
                )

        elif "8BP" in text:
            if stars >= 10:
                sent = send_local_apk(user_id, EIGHT_BP_FILENAME, "🎱 <b>8BP - ninja_Engine_v.1.1 APK File Unlocked!</b>\nAapne 10 refers successfully complete kar liye hain! Yeh rahi aapki APK file 👇")
                if not sent:
                    bot.send_message(
                        user_id,
                        f"🎱 <b>8BP - ninja_Engine_v.1.1 Unlocked!</b>\n\n"
                        f"Aapne 10 refers complete kar liye hain! File name: <code>{EIGHT_BP_FILENAME}</code> (Make sure file is uploaded on GitHub)",
                        parse_mode="HTML",
                        reply_markup=main_menu_keyboard()
                    )
            else:
                bot.send_message(
                    user_id,
                    f"🎱 <b>8BP Hack Offer</b>\n\n"
                    f"Free me lene ke liye total 10 refers complete karein!\n"
                    f"⭐ Aapke current stars: <b>{stars}/10</b>\n\n"
                    f"💡 Apni referral link se doston ko invite karein!",
                    parse_mode="HTML",
                    reply_markup=main_menu_keyboard()
                )

        elif "Paid Hack" in text:
            bot.send_message(
                user_id,
                "💳 <b>PAID HACK DIRECT PURCHASE</b> 👑\n\n"
                "Aap direct paid hack kharidne ke liye owner se direct contact kar sakte hain:\n"
                f"• Telegram Owner: <b>{OWNER_CONTACT}</b>\n"
                f"• WhatsApp: <b>{WHATSAPP_NUMBER}</b>",
                parse_mode="HTML",
                reply_markup=main_menu_keyboard()
            )

        elif "My Link" in text:
            link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
            bot.send_message(
                user_id,
                f"🔗 <b>Aapki Personal Referral Link:</b>\n\n"
                f"<code>{link}</code>\n\n"
                f"👥 Is link ko share karein!\n"
                f"Har ek naye user ke join karne par aapko milega <b>+1 Star</b> ⭐",
                parse_mode="HTML",
                reply_markup=main_menu_keyboard()
            )

        elif "My Status" in text:
            current_stars = 999999 if user.get("unlimited_access", False) else int(user.get("stars", 0))
            refs = user.get("referrals", 0)
            bot.send_message(
                user_id,
                f"👥 <b>Aapka Status & Referrals</b>\n\n"
                f"👤 Total Referrals: <b>{refs}</b>\n"
                f"⭐ Total Stars: <b>{current_stars}</b>\n\n"
                f"🔥 Free Fire Progress: <b>{current_stars}/10</b>\n"
                f"🎱 Carrom Progress: <b>{current_stars}/10</b>\n"
                f"🎱 8BP Progress: <b>{current_stars}/10</b>",
                parse_mode="HTML",
                reply_markup=main_menu_keyboard()
            )

        elif "Trust Proof" in text:
            bot.send_message(
                user_id,
                "🛡️ <b>Trust Proof Channel</b>\n\n"
                f"Customer proofs aur successful deals yahan check karein:\n👉 {TRUST_PROOF_LINK}",
                parse_mode="HTML",
                reply_markup=main_menu_keyboard()
            )

        elif "Refresh" in text:
            bot.send_message(
                user_id,
                "🔄 <b>Bot Refreshed Successfully!</b>\n\nAapka menu updated aur active hai.",
                parse_mode="HTML",
                reply_markup=main_menu_keyboard()
            )
    except Exception as e:
        logger.error("handle_menu_actions error: %s", e)

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
    
