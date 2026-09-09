import os
import time
import random
import string
import sqlite3
import datetime
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import requests
import telebot
from telebot import types


# ============================================================
# CONFIGURATION
# ============================================================

API_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@novaengine01")
CHANNEL_LINK = os.getenv(
    "CHANNEL_LINK",
    "https://t.me/novaengine01"
)

# Firebase
FIREBASE_URL = os.getenv(
    "FIREBASE_URL",
    "https://aimai-817ef-default-rtdb.asia-southeast1.firebasedatabase.app"
)

FIREBASE_AUTH = os.getenv("FIREBASE_AUTH")

# APK
APK_FILE_NAME = os.getenv("APK_FILE_NAME", "app.apk")

# Database
DB_FILE = os.getenv("DB_FILE", "referral_bot.db")


if not API_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable missing!")

if not FIREBASE_AUTH:
    print("WARNING: FIREBASE_AUTH environment variable missing!")


bot = telebot.TeleBot(API_TOKEN, parse_mode="HTML")
session = requests.Session()


# ============================================================
# DATABASE
# ============================================================

def get_db():
    db = sqlite3.connect(
        DB_FILE,
        timeout=30,
        check_same_thread=False
    )

    db.execute("PRAGMA busy_timeout = 30000")
    db.execute("PRAGMA journal_mode = WAL")

    return db


def setup_database():
    db = get_db()
    cur = db.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            points INTEGER NOT NULL DEFAULT 0,
            referrer_id INTEGER DEFAULT NULL,
            is_verified INTEGER NOT NULL DEFAULT 0,
            created_at TEXT,
            verified_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            key_value TEXT NOT NULL,
            plan_days INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # Extra table:
    # referral reward ko duplicate hone se rokne ke liye
    cur.execute("""
        CREATE TABLE IF NOT EXISTS referral_rewards (
            referred_user_id INTEGER PRIMARY KEY,
            referrer_id INTEGER NOT NULL,
            rewarded_at TEXT NOT NULL
        )
    """)

    db.commit()
    db.close()


setup_database()


# ============================================================
# KEY GENERATOR
# ============================================================

chars = string.ascii_uppercase + string.digits


def generate_random_key():
    return "DP-" + "".join(
        random.choices(chars, k=6)
    )


# ============================================================
# FIREBASE
# ============================================================

def save_key_to_firebase(key_name, days):

    if not FIREBASE_AUTH:
        print("Firebase auth missing")
        return False

    payload = {
        "user": key_name,
        "days": str(days),
        "status": "active",
        "devices": "1",
        "date": datetime.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    }

    url = (
        f"{FIREBASE_URL}/user/"
        f"{key_name}.json?auth={FIREBASE_AUTH}"
    )

    try:
        response = session.put(
            url,
            json=payload,
            timeout=10
        )

        print(
            "Firebase:",
            response.status_code,
            response.text[:200]
        )

        return response.status_code == 200

    except Exception as e:
        print("Firebase Error:", e)
        return False


# ============================================================
# CHANNEL JOIN CHECK
# ============================================================

def check_joined(user_id):

    try:
        member = bot.get_chat_member(
            CHANNEL_USERNAME,
            user_id
        )

        print(
            f"Join check user={user_id}, "
            f"status={member.status}"
        )

        # Normal member
        if member.status in [
            "creator",
            "administrator",
            "member"
        ]:
            return True

        # Telegram can return restricted users
        if member.status == "restricted":
            return bool(
                getattr(member, "is_member", False)
            )

        # left / kicked / unknown
        return False

    except Exception as e:
        print(
            f"Join check error for {user_id}:",
            e
        )

        # IMPORTANT:
        # API error par user ko verified nahi karna.
        return False


# ============================================================
# USER HELPERS
# ============================================================

def get_user(user_id):

    db = get_db()
    cur = db.cursor()

    cur.execute("""
        SELECT user_id, points, referrer_id,
               is_verified
        FROM users
        WHERE user_id = ?
    """, (user_id,))

    row = cur.fetchone()

    db.close()

    return row


def create_user(user_id, referrer_id=None):

    db = get_db()
    cur = db.cursor()

    now = datetime.datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    cur.execute("""
        INSERT OR IGNORE INTO users
        (
            user_id,
            points,
            referrer_id,
            is_verified,
            created_at
        )
        VALUES (?, 0, ?, 0, ?)
    """, (
        user_id,
        referrer_id,
        now
    ))

    db.commit()
    db.close()


# ============================================================
# REFERRAL REWARD
# ============================================================

def verify_user_and_reward(user_id):

    db = get_db()

    try:
        cur = db.cursor()

        # Transaction start
        cur.execute("BEGIN IMMEDIATE")

        cur.execute("""
            SELECT is_verified, referrer_id
            FROM users
            WHERE user_id = ?
        """, (user_id,))

        user = cur.fetchone()

        if not user:
            db.rollback()
            return False, None

        is_verified = user[0]
        referrer_id = user[1]

        # Already verified:
        # No second point
        if is_verified == 1:
            db.commit()
            return True, None

        now = datetime.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        # User ko verified mark karo
        cur.execute("""
            UPDATE users
            SET is_verified = 1,
                verified_at = ?
            WHERE user_id = ?
              AND is_verified = 0
        """, (
            now,
            user_id
        ))

        if cur.rowcount != 1:
            db.commit()
            return True, None

        rewarded_referrer = None

        # Referral reward
        if referrer_id and referrer_id != user_id:

            # Check whether this referral already rewarded
            cur.execute("""
                SELECT 1
                FROM referral_rewards
                WHERE referred_user_id = ?
            """, (user_id,))

            already_rewarded = cur.fetchone()

            if not already_rewarded:

                # Referrer ko +1 point
                cur.execute("""
                    UPDATE users
                    SET points = COALESCE(points, 0) + 1
                    WHERE user_id = ?
                """, (referrer_id,))

                # Reward record
                cur.execute("""
                    INSERT INTO referral_rewards
                    (
                        referred_user_id,
                        referrer_id,
                        rewarded_at
                    )
                    VALUES (?, ?, ?)
                """, (
                    user_id,
                    referrer_id,
                    now
                ))

                rewarded_referrer = referrer_id

        db.commit()

        return True, rewarded_referrer

    except Exception as e:

        print(
            "Verification transaction error:",
            e
        )

        try:
            db.rollback()
        except:
            pass

        return False, None

    finally:
        db.close()


# ============================================================
# KEYBOARD
# ============================================================

def get_main_keyboard():

    kb = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    kb.row(
        types.KeyboardButton("🎁 Generate Key"),
        types.KeyboardButton("🔗 My Link")
    )

    kb.row(
        types.KeyboardButton("👥 Referrals"),
        types.KeyboardButton("🔑 My Keys")
    )

    kb.row(
        types.KeyboardButton("🔄 Refresh"),
        types.KeyboardButton("ℹ️ How it works")
    )

    return kb


# ============================================================
# DASHBOARD
# ============================================================

def send_dashboard(chat_id, user_id):

    try:

        user = get_user(user_id)

        if not user:
            create_user(user_id)
            user = get_user(user_id)

        points = user[1]

        db = get_db()
        cur = db.cursor()

        cur.execute("""
            SELECT COUNT(*)
            FROM users
            WHERE referrer_id = ?
              AND is_verified = 1
        """, (user_id,))

        total_refs = cur.fetchone()[0]

        db.close()

        bot_info = bot.get_me()

        ref_link = (
            f"https://t.me/"
            f"{bot_info.username}"
            f"?start={user_id}"
        )

        text = (
            "🏆 <b>Aapka Rewards Dashboard</b>\n\n"
            f"⭐ Total Points: <b>{points}</b>\n"
            f"👥 Verified Referrals: <b>{total_refs}</b>\n\n"
            "👇🏻 <b>Aapki Referral Link:</b>\n"
            f"<code>{ref_link}</code>\n\n"
            "📢 Is link ko doston ke saath share karein.\n"
            "Jab dost channel join karke verify karega, "
            "aapko <b>+1 Point</b> milega."
        )

        bot.send_message(
            chat_id,
            text,
            reply_markup=get_main_keyboard()
        )

    except Exception as e:
        print("Dashboard error:", e)


# ============================================================
# JOIN / VERIFY MESSAGE
# ============================================================

def send_join_message(chat_id):

    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "📢 Join Channel",
            url=CHANNEL_LINK
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "✅ Verify / Check",
            callback_data="check_join"
        )
    )

    bot.send_message(
        chat_id,
        "⚠️ <b>Verification Required</b>\n\n"
        "Bot use karne ke liye pehle "
        "hamare official Telegram channel ko join karein.\n\n"
        "1️⃣ Join Channel par click karein\n"
        "2️⃣ Channel join karein\n"
        "3️⃣ Wapas aakar Verify / Check dabayein\n\n"
        "❗ Channel join nahi hoga to referral "
        "point bhi nahi milega.",
        reply_markup=kb
    )


# ============================================================
# /START
# ============================================================

@bot.message_handler(commands=["start"])
def start_cmd(message):

    user_id = message.from_user.id

    parts = message.text.split()

    args = (
        parts[1].strip()
        if len(parts) > 1
        else ""
    )

    # Referral ID
    referrer_id = None

    if args.isdigit():

        possible_referrer = int(args)

        if possible_referrer != user_id:
            referrer_id = possible_referrer

    user = get_user(user_id)

    # New user
    if not user:

        create_user(
            user_id,
            referrer_id
        )

    else:

        # Existing unverified user ke paas
        # referral nahi hai to referral attach kar sakte hain.
        #
        # Verified user ka referral kabhi change nahi hoga.
        if (
            user[3] == 0
            and user[2] is None
            and referrer_id is not None
        ):

            db = get_db()
            cur = db.cursor()

            cur.execute("""
                UPDATE users
                SET referrer_id = ?
                WHERE user_id = ?
                  AND is_verified = 0
                  AND referrer_id IS NULL
            """, (
                referrer_id,
                user_id
            ))

            db.commit()
            db.close()

    # Latest user data
    user = get_user(user_id)

    if not user:
        bot.send_message(
            message.chat.id,
            "⚠️ User database error. Dobara /start karein."
        )
        return

    is_verified = user[3]

    # Already verified
    if is_verified == 1:

        send_dashboard(
            message.chat.id,
            user_id
        )

        return

    # ========================================================
    # IMPORTANT:
    # /start karne par automatically verified nahi karenge.
    # Pehle channel join + Verify button.
    # ========================================================

    send_join_message(
        message.chat.id
    )


# ============================================================
# VERIFY CALLBACK
# ============================================================

@bot.callback_query_handler(
    func=lambda call: call.data == "check_join"
)
def verify_callback(call):

    user_id = call.from_user.id

    # Telegram membership check
    joined = check_joined(user_id)

    if not joined:

        bot.answer_callback_query(
            call.id,
            "❌ Pehle channel join karein!",
            show_alert=True
        )

        return

    # User verified + referral reward
    success, referrer_id = verify_user_and_reward(
        user_id
    )

    if not success:

        bot.answer_callback_query(
            call.id,
            "⚠️ Verification error. Dobara try karein.",
            show_alert=True
        )

        return

    # Referrer ko notification
    if referrer_id:

        try:

            bot.send_message(
                referrer_id,
                "🎉 <b>Badhai ho!</b>\n\n"
                "Aapki referral link se ek naya user "
                "channel join karke verify hua.\n\n"
                "⭐ Aapko <b>+1 Point</b> mila."
            )

        except Exception as e:

            print(
                "Referral notification error:",
                e
            )

    # Old verification message remove
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
# MENU BUTTONS
# ============================================================

@bot.message_handler(func=lambda m: True)
def handle_menu_buttons(message):

    user_id = message.from_user.id

    txt = (
        message.text or ""
    ).strip()

    # --------------------------------------------------------
    # GENERATE KEY
    # --------------------------------------------------------

    if "Generate Key" in txt:

        user = get_user(user_id)

        if not user:

            create_user(user_id)
            user = get_user(user_id)

        # Unverified user ko key nahi milegi
        if user[3] != 1:

            send_join_message(
                message.chat.id
            )

            return

        points = user[1]

        if points < 3:

            bot_info = bot.get_me()

            ref_link = (
                f"https://t.me/"
                f"{bot_info.username}"
                f"?start={user_id}"
            )

            warning = (
                "❌ <b>Aapke paas enough points nahi hain!</b>\n\n"
                f"⭐ Aapke Points: <b>{points}</b>\n"
                "🎯 Required: <b>3 Points</b>\n\n"
                "👇🏻 <b>Aapki Referral Link:</b>\n"
                f"<code>{ref_link}</code>\n\n"
                "💡 Har verified referral par +1 point milega."
            )

            bot.send_message(
                message.chat.id,
                warning
            )

            return

        kb = types.InlineKeyboardMarkup(
            row_width=2
        )

        kb.add(
            types.InlineKeyboardButton(
                "1 Day (3 pts)",
                callback_data="claim_1"
            ),
            types.InlineKeyboardButton(
                "3 Days (6 pts)",
                callback_data="claim_3"
            ),
            types.InlineKeyboardButton(
                "7 Days (10 pts)",
                callback_data="claim_7"
            ),
            types.InlineKeyboardButton(
                "30 Days (25 pts)",
                callback_data="claim_30"
            )
        )

        bot.send_message(
            message.chat.id,
            f"⭐ Aapke paas: <b>{points} Points</b>\n\n"
            "👇 Apna VIP plan select karein:",
            reply_markup=kb
        )

        return

    # --------------------------------------------------------
    # HOW IT WORKS
    # --------------------------------------------------------

    if "How it works" in txt:

        bot_info = bot.get_me()

        ref_link = (
            f"https://t.me/"
            f"{bot_info.username}"
            f"?start={user_id}"
        )

        guide = (
            "📖 <b>Bot Kaise Kaam Karta Hai?</b>\n\n"

            "<b>1️⃣ Referral Points</b>\n"
            "• Apni referral link share karein.\n"
            "• Dost aapki link se bot start kare.\n"
            "• Dost official channel join kare.\n"
            "• Dost Verify / Check dabaye.\n"
            "• Verification successful hone par "
            "aapko <b>+1 Point</b> milega.\n\n"

            "<b>2️⃣ VIP Key Plans</b>\n"
            "• 1 Day = <b>3 Points</b>\n"
            "• 3 Days = <b>6 Points</b>\n"
            "• 7 Days = <b>10 Points</b>\n"
            "• 30 Days = <b>25 Points</b>\n\n"

            "<b>3️⃣ App Login</b>\n"
            "Key generate hone ke baad bot key dega.\n"
            "App me Username aur Password dono jagah "
            "same key use karein.\n\n"

            "👇🏻 <b>Aapki Referral Link:</b>\n"
            f"<code>{ref_link}</code>"
        )

        bot.send_message(
            message.chat.id,
            guide
        )

        return

    # --------------------------------------------------------
    # MY KEYS
    # --------------------------------------------------------

    if "My Keys" in txt:

        user = get_user(user_id)

        if not user:

            create_user(user_id)
            user = get_user(user_id)

        db = get_db()
        cur = db.cursor()

        cur.execute("""
            SELECT COUNT(*)
            FROM users
            WHERE referrer_id = ?
              AND is_verified = 1
        """, (user_id,))

        total_refs = cur.fetchone()[0]

        cur.execute("""
            SELECT key_value,
                   plan_days,
                   created_at
            FROM user_keys
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 10
        """, (user_id,))

        rows = cur.fetchall()

        db.close()

        if not rows:

            bot.send_message(
                message.chat.id,
                f"📊 <b>Verified Referrals:</b> "
                f"{total_refs}\n\n"
                "❌ Abhi tak koi key generate nahi hui."
            )

            return

        keys_text = ""

        for index, row in enumerate(
            rows,
            1
        ):

            keys_text += (
                f"{index}. "
                f"Key: <code>{row[0
