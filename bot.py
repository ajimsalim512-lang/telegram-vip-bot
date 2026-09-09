import os
import time
import random
import string
import datetime
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import requests
import telebot
from telebot import types


# ============================================================
# CONFIGURATION
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

CHANNEL_USERNAME = os.getenv(
    "CHANNEL_USERNAME",
    "@novaengine01"
)

CHANNEL_LINK = os.getenv(
    "CHANNEL_LINK",
    "https://t.me/novaengine01"
)

FIREBASE_URL = os.getenv(
    "FIREBASE_URL",
    "https://aimai-817ef-default-rtdb.asia-southeast1.firebasedatabase.app"
).rstrip("/")

FIREBASE_AUTH = os.getenv("FIREBASE_AUTH")

APP_DOWNLOAD_LINK = "https://t.me/memonxgaming/1060"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable missing!")

if not FIREBASE_AUTH:
    raise RuntimeError("FIREBASE_AUTH environment variable missing!")


# ============================================================
# BOT / HTTP SESSION
# ============================================================

bot = telebot.TeleBot(
    BOT_TOKEN,
    parse_mode="HTML"
)

session = requests.Session()

# Local lock prevents simultaneous point operations
# inside the same Render instance.
db_lock = threading.Lock()


# ============================================================
# TIME
# ============================================================

def current_time():
    return datetime.datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


# ============================================================
# FIREBASE HELPERS
# ============================================================

def firebase_url(path):
    return (
        f"{FIREBASE_URL}/{path}.json"
        f"?auth={FIREBASE_AUTH}"
    )


def firebase_get(path):

    try:

        response = session.get(
            firebase_url(path),
            timeout=10
        )

        if response.status_code != 200:

            print(
                "Firebase GET error:",
                response.status_code,
                response.text[:300]
            )

            return None

        return response.json()

    except Exception as e:

        print(
            "Firebase GET exception:",
            e
        )

        return None


def firebase_put(path, data):

    try:

        response = session.put(
            firebase_url(path),
            json=data,
            timeout=10
        )

        if response.status_code != 200:

            print(
                "Firebase PUT error:",
                response.status_code,
                response.text[:300]
            )

            return False

        return True

    except Exception as e:

        print(
            "Firebase PUT exception:",
            e
        )

        return False


def firebase_patch(path, data):

    try:

        response = session.patch(
            firebase_url(path),
            json=data,
            timeout=10
        )

        if response.status_code != 200:

            print(
                "Firebase PATCH error:",
                response.status_code,
                response.text[:300]
            )

            return False

        return True

    except Exception as e:

        print(
            "Firebase PATCH exception:",
            e
        )

        return False


def firebase_delete(path):

    try:

        response = session.delete(
            firebase_url(path),
            timeout=10
        )

        return response.status_code == 200

    except Exception as e:

        print(
            "Firebase DELETE exception:",
            e
        )

        return False


# ============================================================
# USER FUNCTIONS
# ============================================================

def get_user(user_id):

    return firebase_get(
        f"bot_users/{user_id}"
    )


def create_user(
    user_id,
    referrer_id=None
):

    data = {
        "points": 0,
        "referrer_id": referrer_id,
        "is_verified": False,
        "created_at": current_time(),
        "verified_at": None
    }

    return firebase_put(
        f"bot_users/{user_id}",
        data
    )


def attach_referrer(
    user_id,
    referrer_id
):

    user = get_user(user_id)

    if not user:
        return False

    # Referral cannot be changed after verification
    if user.get("is_verified", False):
        return True

    # Existing referral cannot be overwritten
    if user.get("referrer_id"):
        return True

    if str(user_id) == str(referrer_id):
        return True

    return firebase_patch(
        f"bot_users/{user_id}",
        {
            "referrer_id": referrer_id
        }
    )


# ============================================================
# CHANNEL MEMBERSHIP CHECK
# ============================================================

def check_joined(user_id):

    try:

        member = bot.get_chat_member(
            CHANNEL_USERNAME,
            user_id
        )

        print(
            f"CHANNEL CHECK: "
            f"user={user_id}, "
            f"status={member.status}"
        )

        if member.status in [
            "creator",
            "administrator",
            "member"
        ]:
            return True

        if member.status == "restricted":

            return bool(
                getattr(
                    member,
                    "is_member",
                    False
                )
            )

        return False

    except Exception as e:

        print(
            "Channel membership error:",
            e
        )

        # API error = NOT verified
        return False


# ============================================================
# VERIFY USER + REFERRAL REWARD
# ============================================================

def verify_user(user_id):

    with db_lock:

        user = get_user(user_id)

        if not user:
            return False, None

        # Already verified
        if user.get(
            "is_verified",
            False
        ):

            return True, None

        referrer_id = user.get(
            "referrer_id"
        )

        verification_time = current_time()

        # ----------------------------------------------------
        # Mark user verified
        # ----------------------------------------------------

        verified = firebase_patch(
            f"bot_users/{user_id}",
            {
                "is_verified": True,
                "verified_at": verification_time
            }
        )

        if not verified:

            print(
                "Could not mark user verified"
            )

            return False, None

        rewarded_referrer = None

        # ----------------------------------------------------
        # Referral reward
        # ----------------------------------------------------

        if (
            referrer_id
            and str(referrer_id) != str(user_id)
        ):

            # One referred user can reward only once
            reward_path = (
                f"referral_rewards/{user_id}"
            )

            reward_exists = firebase_get(
                reward_path
            )

            if not reward_exists:

                referrer = get_user(
                    referrer_id
                )

                if referrer:

                    old_points = int(
                        referrer.get(
                            "points",
                            0
                        ) or 0
                    )

                    new_points = (
                        old_points + 1
                    )

                    # Add +1 point
                    point_updated = firebase_patch(
                        f"bot_users/{referrer_id}",
                        {
                            "points": new_points
                        }
                    )

                    if point_updated:

                        reward_saved = firebase_put(
                            reward_path,
                            {
                                "referrer_id":
                                    referrer_id,
                                "rewarded_at":
                                    verification_time
                            }
                        )

                        if reward_saved:

                            rewarded_referrer = (
                                referrer_id
                            )

                            print(
                                "================================"
                            )

                            print(
                                "REFERRAL REWARD SUCCESS"
                            )

                            print(
                                f"Referrer: {referrer_id}"
                            )

                            print(
                                f"Old points: {old_points}"
                            )

                            print(
                                f"New points: {new_points}"
                            )

                            print(
                                "================================"
                            )

        return True, rewarded_referrer


# ============================================================
# DASHBOARD
# ============================================================

def get_verified_referrals(user_id):

    all_users = firebase_get(
        "bot_users"
    )

    count = 0

    if isinstance(
        all_users,
        dict
    ):

        for uid, data in all_users.items():

            if not isinstance(
                data,
                dict
            ):
                continue

            if str(
                data.get(
                    "referrer_id"
                )
            ) == str(user_id):

                if data.get(
                    "is_verified",
                    False
                ):

                    count += 1

    return count


def send_dashboard(
    chat_id,
    user_id
):

    user = get_user(user_id)

    if not user:

        create_user(user_id)

        user = get_user(user_id)

    if not user:

        bot.send_message(
            chat_id,
            "⚠️ Database error. Please try again."
        )

        return

    points = int(
        user.get(
            "points",
            0
        ) or 0
    )

    verified_referrals = (
        get_verified_referrals(
            user_id
        )
    )

    try:

        bot_info = bot.get_me()

        referral_link = (
            f"https://t.me/"
            f"{bot_info.username}"
            f"?start={user_id}"
        )

    except Exception:

        referral_link = (
            f"https://t.me/Free_Aim_Ai_Bot"
            f"?start={user_id}"
        )

    text = (
        "🏆 <b>Aapka Rewards Dashboard</b>\n\n"

        f"⭐ Total Points: <b>{points}</b>\n"

        f"👥 Verified Referrals: "
        f"<b>{verified_referrals}</b>\n\n"

        "👇🏻 <b>Aapki Referral Link:</b>\n"
        f"<code>{referral_link}</code>\n\n"

        "📢 Is link ko doston ke saath share karein.\n"

        "Har dost ke link se join karke "
        "channel verify karne par "
        "<b>+1 Point</b> milega."
    )

    bot.send_message(
        chat_id,
        text,
        reply_markup=get_main_keyboard()
    )


# ============================================================
# MAIN KEYBOARD
# ============================================================

def get_main_keyboard():

    keyboard = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    keyboard.row(
        types.KeyboardButton(
            "🎁 Generate Key"
        ),
        types.KeyboardButton(
            "🔗 My Link"
        )
    )

    keyboard.row(
        types.KeyboardButton(
            "👥 Referrals"
        ),
        types.KeyboardButton(
            "🔑 My Keys"
        )
    )

    keyboard.row(
        types.KeyboardButton(
            "🔄 Refresh"
        ),
        types.KeyboardButton(
            "ℹ️ How it works"
        )
    )

    return keyboard


# ============================================================
# JOIN / VERIFY MESSAGE
# ============================================================

def send_join_message(chat_id):

    keyboard = types.InlineKeyboardMarkup()

    keyboard.add(
        types.InlineKeyboardButton(
            "📢 Join Channel",
            url=CHANNEL_LINK
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "✅ Verify / Check",
            callback_data="check_join"
        )
    )

    bot.send_message(
        chat_id,

        "⚠️ <b>Channel Verification Required</b>\n\n"

        "Bot use karne ke liye pehle "
        "official channel join karein.\n\n"

        "1️⃣ <b>Join Channel</b> par click karein\n"
        "2️⃣ Channel join karein\n"
        "3️⃣ Wapas aakar "
        "<b>Verify / Check</b> dabayein\n\n"

        "❗ Channel join aur verification "
        "ke bina referral point nahi milega.",

        reply_markup=keyboard
    )


# ============================================================
# START COMMAND
# ============================================================

@bot.message_handler(
    commands=["start"]
)
def start_command(message):

    user_id = message.from_user.id

    parts = (
        message.text or ""
    ).split()

    referrer_id = None

    # --------------------------------------------------------
    # Read referral ID
    # --------------------------------------------------------

    if len(parts) > 1:

        argument = parts[1].strip()

        if argument.isdigit():

            possible_referrer = int(
                argument
            )

            # Self referral blocked
            if possible_referrer != user_id:

                referrer_id = (
                    possible_referrer
                )

    # --------------------------------------------------------
    # Get/create user
    # --------------------------------------------------------

    user = get_user(user_id)

    if not user:

        create_user(
            user_id,
            referrer_id
        )

    else:

        # Existing unverified user
        # gets referral only if none exists.
        if (
            not user.get(
                "is_verified",
                False
            )
            and not user.get(
                "referrer_id"
            )
            and referrer_id
        ):

            attach_referrer(
                user_id,
                referrer_id
            )

    # --------------------------------------------------------
    # Get latest user
    # --------------------------------------------------------

    user = get_user(user_id)

    if not user:

        bot.send_message(
            message.chat.id,
            "⚠️ Database error. Please try again."
        )

        return

    # --------------------------------------------------------
    # Already verified
    # --------------------------------------------------------

    if user.get(
        "is_verified",
        False
    ):

        send_dashboard(
            message.chat.id,
            user_id
        )

        return

    # --------------------------------------------------------
    # Not verified
    # --------------------------------------------------------

    send_join_message(
        message.chat.id
    )


# ============================================================
# VERIFY CALLBACK
# ============================================================

@bot.callback_query_handler(
    func=lambda call:
        call.data == "check_join"
)
def verify_callback(call):

    user_id = call.from_user.id

    # --------------------------------------------------------
    # Check Telegram channel membership
    # --------------------------------------------------------

    if not check_joined(user_id):

        bot.answer_callback_query(
            call.id,
            "❌ Pehle channel join karein!",
            show_alert=True
        )

        return

    # --------------------------------------------------------
    # Verify user and reward referrer
    # --------------------------------------------------------

    success, referrer_id = (
        verify_user(
            user_id
        )
    )

    if not success:

        bot.answer_callback_query(
            call.id,
            "⚠️ Verification error. Dobara try karein.",
            show_alert=True
        )

        return

    # --------------------------------------------------------
    # Notify referrer
    # --------------------------------------------------------

    if referrer_id:

        try:

            referrer_user = get_user(
                referrer_id
            )

            points = int(
                referrer_user.get(
                    "points",
                    0
                )
                if referrer_user
                else 0
            )

            bot.send_message(
                referrer_id,

                "🎉 <b>Badhai ho!</b>\n\n"

                "Aapki referral link se "
                "ek naya user channel join "
                "aur verify hua.\n\n"

                "⭐ Aapko <b>+1 Point</b> mila.\n"

                f"💰 Total Points: <b>{points}</b>"
            )

        except Exception as e:

            print(
                "Notification error:",
                e
            )

    # --------------------------------------------------------
    # Remove old join message
    # --------------------------------------------------------

    try:

        bot.delete_message(
            call.message.chat.id,
            call.message.message_id
        )

    except Exception:

        pass

    bot.answer_callback_query(
        call.id,
        "✅ Verification successful!"
    )

    send_dashboard(
        call.message.chat.id,
        user_id
    )


# ============================================================
# MENU HANDLER
# ============================================================

@bot.message_handler(
    func=lambda message: True
)
def menu_handler(message):

    user_id = message.from_user.id

    text = (
        message.text or ""
    ).strip()

    # ========================================================
    # GENERATE KEY
    # ========================================================

    if "Generate Key" in text:

        user = get_user(
            user_id
        )

        if not user:

            create_user(
                user_id
            )

            user = get_user(
                user_id
            )

        # Must be verified
        if not user.get(
            "is_verified",
            False
        ):

            send_join_message(
                message.chat.id
            )

            return

        points = int(
            user.get(
                "points",
                0
            ) or 0
        )

        # Minimum 3 points
        if points < 3:

            try:

                bot_info = bot.get_me()

                referral_link = (
                    f"https://t.me/"
                    f"{bot_info.username}"
                    f"?start={user_id}"
                )

            except:

                referral_link = (
                    f"https://t.me/"
                    f"Free_Aim_Ai_Bot"
                    f"?start={user_id}"
                )

            bot.send_message(
                message.chat.id,

                "❌ <b>Points kam hain!</b>\n\n"

                f"⭐ Aapke Points: "
                f"<b>{points}</b>\n"

                "🎯 Required: "
                "<b>3 Points</b>\n\n"

                "👇🏻 <b>Referral Link:</b>\n"
                f"<code>{referral_link}</code>\n\n"

                "💡 Har verified referral par "
                "<b>+1 Point</b> mi
