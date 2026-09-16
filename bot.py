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


# ============================================================
# CONFIGURATION
# ============================================================

BOT_TOKEN = "8803139822:AAGOzEAyDvgqmq0Gh42Zz0bsvZ-29oEKy5o"
FIREBASE_AUTH = "V677nUiq24iMv58OcV02CXyE7iHFqFbke4VVPdmL"
FIREBASE_URL = "https://aimai-817ef-default-rtdb.asia-southeast1.firebasedatabase.app".rstrip("/")

CHANNEL_1_USERNAME = "@novaengine01"
CHANNEL_1_LINK = "https://t.me/novaengine01"

CHANNEL_2_USERNAME = "@Memonxgamingff"
CHANNEL_2_LINK = "https://t.me/Memonxgamingff"

OWNER_CONTACT = "@Memonsalim"
WHATSAPP_NUMBER = "+91 6354525228"

FREE_KEY_BOT = "@Arsenal_xex_freekeybot"
TRUST_PROOF_LINK = "https://t.me/proofnovaengine"

FREE_FIRE_MEDIAFIRE = "https://www.mediafire.com/file/va2vkas72dfjgjx"
CARROM_FILENAME = "AimAi-2.apk"

SECRET_ADMIN_COMMAND = "memonxgaming1235919398288281834848@1919394"

STARS_REQUIRED = 10

VERIFICATION_EMOJIS = [
    "🍎",
    "🚗",
    "⭐",
    "⚽",
    "🐱"
]

REFRESH_KEY = "refresh_notified_v2"


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger("apk-distribution-bot")


# ============================================================
# TELEGRAM
# ============================================================

bot = telebot.TeleBot(
    BOT_TOKEN,
    parse_mode="HTML",
    threaded=True
)

BOT_USERNAME = ""


# ============================================================
# FLASK / RENDER
# ============================================================

flask_app = Flask(__name__)


@flask_app.route("/")
def home():
    return "Telegram bot is running."


@flask_app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "bot": "running",
        "time": datetime.now(timezone.utc).isoformat()
    })


@flask_app.route("/ping")
def ping():
    return "pong"


def run_web_server():
    try:
        port = int(os.getenv("PORT", "10000"))

        flask_app.run(
            host="0.0.0.0",
            port=port,
            debug=False,
            use_reloader=False
        )

    except Exception as exc:
        logger.exception("Flask error: %s", exc)


# ============================================================
# FIREBASE
# ============================================================

def firebase_url(path=""):
    path = str(path).strip("/")

    if path:
        base = f"{FIREBASE_URL}/{path}.json"
    else:
        base = f"{FIREBASE_URL}/.json"

    separator = "&" if "?" in base else "?"

    return f"{base}{separator}auth={FIREBASE_AUTH}"


def firebase_get(path=""):
    try:
        response = requests.get(
            firebase_url(path),
            timeout=15
        )

        if response.status_code != 200:
            logger.warning(
                "Firebase GET failed: %s",
                response.status_code
            )
            return None

        return response.json()

    except Exception as exc:
        logger.error("Firebase GET error: %s", exc)
        return None


def firebase_put(path, data):
    try:
        response = requests.put(
            firebase_url(path),
            json=data,
            timeout=15
        )

        return response.status_code in (200, 201)

    except Exception as exc:
        logger.error("Firebase PUT error: %s", exc)
        return False


def firebase_patch(path, data):
    try:
        response = requests.patch(
            firebase_url(path),
            json=data,
            timeout=15
        )

        return response.status_code in (200, 201)

    except Exception as exc:
        logger.error("Firebase PATCH error: %s", exc)
        return False


# ============================================================
# USER DATABASE
# ============================================================

def get_user(user_id):
    try:
        data = firebase_get(f"users/{int(user_id)}")

        if isinstance(data, dict):
            return data

    except Exception as exc:
        logger.error("get_user error: %s", exc)

    return None


def create_user(user_obj, referrer_id=None):
    try:
        user_id = int(user_obj.id)
        existing = get_user(user_id)

        now = time.time()

        if existing is not None:
            patch = {
                "username": user_obj.username or "",
                "first_name": user_obj.first_name or "",
                "last_seen": now
            }

            if (
                referrer_id
                and not existing.get("referrer_id")
                and int(referrer_id) != user_id
            ):
                patch["referrer_id"] = int(referrer_id)

            firebase_patch(
                f"users/{user_id}",
                patch
            )

            existing.update(patch)
            return existing

        valid_referrer = None

        try:
            if referrer_id:
                ref = int(referrer_id)

                if ref != user_id:
                    valid_referrer = ref

        except (ValueError, TypeError):
            valid_referrer = None

        data = {
            "id": user_id,
            "username": user_obj.username or "",
            "first_name": user_obj.first_name or "",
            "stars": 0,
            "referrals": 0,
            "referrer_id": valid_referrer,
            "unlimited_access": False,
            "verified": False,
            "verification_step": "emoji",
            "target_emoji": "",
            "created_at": now,
            "created_timestamp": now,
            "last_seen": now,
            "video_sent": False,
            "unlocked_sections": {}
        }

        if firebase_put(
            f"users/{user_id}",
            data
        ):
            return data

    except Exception as exc:
        logger.error("create_user error: %s", exc)

    return None


# ============================================================
# REFERRALS
# ============================================================

def reward_referrer(referred_id):
    try:
        referred = get_user(referred_id)

        if not referred:
            return

        referrer_id = referred.get("referrer_id")

        if not referrer_id:
            return

        referrer_id = int(referrer_id)

        if referrer_id == int(referred_id):
            return

        referrer = get_user(referrer_id)

        if not referrer:
            return

        rewarded = referrer.get("referral_rewards", {})

        if not isinstance(rewarded, dict):
            rewarded = {}

        key = str(referred_id)

        if key in rewarded:
            return

        stars = int(referrer.get("stars", 0))
        referrals = int(referrer.get("referrals", 0))

        update = {
            "stars": stars + 1,
            "referrals": referrals + 1,
            f"referral_rewards/{key}": {
                "rewarded_at": time.time()
            }
        }

        if firebase_patch(
            f"users/{referrer_id}",
            update
        ):
            try:
                bot.send_message(
                    referrer_id,
                    (
                        "🎉 <b>New Referral!</b>\n\n"
                        "Aapko referral ke liye "
                        "<b>+1 ⭐ Star</b> mila hai.\n\n"
                        f"⭐ Total Stars: <b>{stars + 1}</b>"
                    )
                )

            except Exception as exc:
                logger.warning(
                    "Referral notification failed: %s",
                    exc
                )

    except Exception as exc:
        logger.error("reward_referrer error: %s", exc)


# ============================================================
# CHANNEL VERIFICATION
# ============================================================

def is_member(user_id, channel):
    try:
        member = bot.get_chat_member(
            channel,
            int(user_id)
        )

        return member.status in (
            "member",
            "administrator",
            "creator"
        )

    except Exception as exc:
        logger.warning(
            "Channel check failed %s: %s",
            channel,
            exc
        )

        return False


def joined_both_channels(user_id):
    return (
        is_member(user_id, CHANNEL_1_USERNAME)
        and is_member(user_id, CHANNEL_2_USERNAME)
    )


# ============================================================
# KEYBOARDS
# ============================================================

def main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    keyboard.row(
        "🔥 Free Fire",
        "🎱 Carrom Pool"
    )

    keyboard.row(
        "🎱 8 Ball Pool",
        "💳 Paid Hack"
    )

    keyboard.row(
        "🔗 My Link",
        "👥 My Status"
    )

    keyboard.row(
        "🛡️ Trust Proof",
        "🎧 Help & Support"
    )

    keyboard.row(
        "🔄 Refresh",
        "ℹ️ How it works"
    )

    return keyboard


def join_keyboard():
    keyboard = types.InlineKeyboardMarkup()

    keyboard.add(
        types.InlineKeyboardButton(
            "📢 Join Channel 1",
            url=CHANNEL_1_LINK
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "📢 Join Channel 2",
            url=CHANNEL_2_LINK
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "✅ Verify",
            callback_data="verify_channels"
        )
    )

    return keyboard


# ============================================================
# ACCESS CHECK
# ============================================================

def verified_user(user_id):
    user = get_user(user_id)

    if not user:
        return False

    if not user.get("verified", False):
        return False

    return joined_both_channels(user_id)


# ============================================================
# EMOJI VERIFICATION
# ============================================================

def send_emoji_verification(user_id):
    try:
        target = random.choice(
            VERIFICATION_EMOJIS
        )

        firebase_patch(
            f"users/{user_id}",
            {
                "verification_step": "emoji",
                "target_emoji": target
            }
        )

        buttons = [
            types.InlineKeyboardButton(
                emoji,
                callback_data=f"emoji:{emoji}"
            )
            for emoji in VERIFICATION_EMOJIS
        ]

        random.shuffle(buttons)

        keyboard = types.InlineKeyboardMarkup(
            row_width=5
        )

        keyboard.add(*buttons)

        bot.send_message(
            user_id,
            (
                "🤖 <b>Human Verification</b>\n\n"
                f"👇 <b>{target}</b> emoji select karein."
            ),
            reply_markup=keyboard
        )

    except Exception as exc:
        logger.error(
            "send_emoji_verification error: %s",
            exc
        )


# ============================================================
# START
# ============================================================

@bot.message_handler(commands=["start"])
def start_handler(message):
    try:
        user_id = message.from_user.id

        parts = message.text.split()

        referrer_id = None

        if len(parts) > 1:
            candidate = parts[1]

            if candidate.isdigit():
                referrer_id = int(candidate)

        user = create_user(
            message.from_user,
            referrer_id
        )

        if not user:
            bot.send_message(
                user_id,
                "⚠️ Database error. Please try again later."
            )
            return

        if (
            user.get("verified", False)
            and joined_both_channels(user_id)
        ):
            reward_referrer(user_id)

            bot.send_message(
                user_id,
                "🎉 <b>Welcome back!</b>\n\n"
                "Aapka main menu ready hai.",
                reply_markup=main_keyboard()
            )

            return

        send_emoji_verification(user_id)

    except Exception as exc:
        logger.exception(
            "start_handler error: %s",
            exc
        )


# ============================================================
# EMOJI CALLBACK
# ============================================================

@bot.callback_query_handler(
    func=lambda call: call.data.startswith("emoji:")
)
def emoji_callback(call):
    try:
        user_id = call.from_user.id
        selected = call.data.split(":", 1)[1]

        bot.answer_callback_query(call.id)

        user = get_user(user_id)

        if not user:
            return

        target = user.get("target_emoji", "")

        if selected != target:
            bot.answer_callback_query(
                call.id,
                "❌ Wrong emoji!",
                show_alert=True
            )
            return

        firebase_patch(
            f"users/{user_id}",
            {
                "verification_step": "channels",
                "target_emoji": ""
            }
        )

        bot.send_message(
            user_id,
            (
                "✅ <b>Human Verification Passed!</b>\n\n"
                "Ab dono official channels join karein "
                "aur phir <b>Verify</b> dabayein."
            ),
            reply_markup=join_keyboard()
        )

    except Exception as exc:
        logger.error(
            "emoji_callback error: %s",
            exc
        )


# ============================================================
# CHANNEL CALLBACK
# ============================================================

@bot.callback_query_handler(
    func=lambda call: call.data == "verify_channels"
)
def verify_channels_callback(call):
    try:
        user_id = call.from_user.id

        bot.answer_callback_query(call.id)

        if not joined_both_channels(user_id):
            bot.send_message(
                user_id,
                (
                    "❌ <b>Verification Failed</b>\n\n"
                    "Dono channels join karne ke baad "
                    "dobara Verify dabayein."
                ),
                reply_markup=join_keyboard()
            )

            return

        firebase_patch(
            f"users/{user_id}",
            {
                "verified": True,
                "verification_step": "complete"
            }
        )

        reward_referrer(user_id)

        bot.send_message(
            user_id,
            (
                "🎉 <b>Verification Complete!</b>\n\n"
                "Ab aap main menu use kar sakte hain."
            ),
            reply_markup=main_keyboard()
        )

    except Exception as exc:
        logger.error(
            "verify_channels_callback error: %s",
            exc
        )


# ============================================================
# REFERRAL LINK
# ============================================================

def get_bot_username():
    global BOT_USERNAME

    if BOT_USERNAME:
        return BOT_USERNAME

    try:
        info = bot.get_me()
        BOT_USERNAME = info.username or ""

    except Exception as exc:
        logger.error(
            "get_bot_username error: %s",
            exc
        )

    return BOT_USERNAME


# ============================================================
# SECTION UNLOCK
# ============================================================

def unlock_section(user_id, section):
    try:
        user = get_user(user_id)

        if not user:
            return False, "User not found."

        unlimited = bool(
            user.get("unlimited_access", False)
        )

        stars = int(
            user.get("stars", 0)
        )

        unlocked = user.get(
            "unlocked_sections",
            {}
        )

        if not isinstance(unlocked, dict):
            unlocked = {}

        if unlocked.get(section, False):
            return True, "Already unlocked."

        if not unlimited and stars < STARS_REQUIRED:
            return (
                False,
                (
                    "❌ <b>Not enough Stars</b>\n\n"
                    f"⭐ Current: <b>{stars}</b>\n"
                    f"⭐ Required: <b>{STARS_REQUIRED}</b>\n\n"
                    "🔗 My Link se friends invite karein."
                )
            )

        new_stars = (
            stars
            if unlimited
            else stars - STARS_REQUIRED
        )

        update = {
            "stars": new_stars,
            f"unlocked_sections/{section}": True
        }

        if firebase_patch(
            f"users/{user_id}",
            update
        ):
            return True, (
                "🎉 <b>Section Unlocked!</b>\n\n"
                f"⭐ Remaining Stars: <b>{new_stars}</b>"
            )

    except Exception as exc:
        logger.error(
            "unlock_section error: %s",
            exc
        )

    return False, "⚠️ Unlock failed. Please try again."


# ============================================================
# APP DELIVERY
# ============================================================

AUTHORIZED_FILES = {
    "carrom": "AimAi-2.apk",
}


def send_file(user_id, filename, caption):
    try:
        if not os.path.isfile(filename):
            bot.send_message(
                user_id,
                (
                    "⚠️ File server par available nahi hai.\n\n"
                    f"<code>{filename}</code>"
                )
            )
            return False

        with open(
            filename,
            "rb"
        ) as file_object:

            bot.send_document(
                user_id,
                file_object,
                caption=caption
            )

        return True

    except Exception as exc:
        logger.error(
            "send_file error: %s",
            exc
        )

        return False


# ============================================================
# GAME / APP SECTIONS
# ============================================================

def show_section(user_id, section):
    try:
        if not verified_user(user_id):
            bot.send_message(
                user_id,
                "⚠️ Pehle verification complete karein."
            )
            return

        user = get_user(user_id)

        if not user:
            return

        stars = int(
            user.get("stars", 0)
        )

        unlimited = bool(
            user.get("unlimited_access", False)
        )

        unlocked = user.get(
            "unlocked_sections",
            {}
        )

        is_unlocked = (
            unlimited
            or unlocked.get(section, False)
        )

        if not is_unlocked:
            keyboard = types.InlineKeyboardMarkup()

            keyboard.add(
                types.InlineKeyboardButton(
                    f"🔓 Unlock — {STARS_REQUIRED} ⭐",
                    callback_data=f"section_unlock:{section}"
                )
            )

            bot.send_message(
                user_id,
                (
                    f"🔒 <b>{section.title()} Section Locked</b>\n\n"
                    f"⭐ Your Stars: <b>{stars}</b>\n"
                    f"⭐ Required: <b>{STARS_REQUIRED}</b>\n\n"
                    "Unlock karne ke liye button dabayein."
                ),
                reply_markup=keyboard
            )
            return

        if section == "freefire":
            bot.send_message(
                user_id,
                (
                    "🔥 <b>Free Fire Section Unlocked</b>\n\n"
                    f"👉 <a href='{FREE_
