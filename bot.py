import os
import uuid
import secrets
import string
import logging
import threading
from datetime import datetime, timezone, timedelta

import requests
from flask import Flask
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)
from telegram.constants import ChatMemberStatus
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)


# ============================================================
# CONFIGURATION
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

FIREBASE_AUTH = os.getenv("FIREBASE_AUTH", "").strip()

FIREBASE_DB_URL = (
    "https://aimai-817ef-default-rtdb.asia-southeast1."
    "firebasedatabase.app"
)

OFFICIAL_CHANNEL = "@novaengine01"
OFFICIAL_CHANNEL_LINK = "https://t.me/novaengine01"

APP_DOWNLOAD_LINK = "https://t.me/memonxgaming/1060"

OWNER_TELEGRAM = "@Memonsalim"
OWNER_WHATSAPP = "+91 6354525228"

TRUST_PROOF_CHANNEL = "https://t.me/proofnovaengine"

ADMIN_SECRET = os.getenv("ADMIN_SECRET", "").strip()

# Screenshot mein jo APK filename hai:
NINJA_APK_PATH = "Ninja_Engine_V2.1.apk"

PORT = int(os.getenv("PORT", "10000"))


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# ============================================================
# FLASK SERVER
# ============================================================

flask_app = Flask(__name__)


@flask_app.route("/")
def home_route():
    try:
        return "Aim AI Telegram Bot is running.", 200
    except Exception as e:
        logger.exception("Home route error: %s", e)
        return "Server error", 500


@flask_app.route("/health")
def health_route():
    try:
        return "OK", 200
    except Exception as e:
        logger.exception("Health route error: %s", e)
        return "ERROR", 500


@flask_app.route("/ping")
def ping_route():
    try:
        return "PONG", 200
    except Exception as e:
        logger.exception("Ping route error: %s", e)
        return "ERROR", 500


def run_flask():
    try:
        flask_app.run(
            host="0.0.0.0",
            port=PORT,
            debug=False,
            use_reloader=False,
        )
    except Exception as e:
        logger.exception("Flask server error: %s", e)


# ============================================================
# TIME HELPERS
# ============================================================

def utc_now():
    try:
        return datetime.now(timezone.utc)
    except Exception as e:
        logger.exception("utc_now error: %s", e)
        return datetime.now(timezone.utc)


def iso_now():
    try:
        return utc_now().isoformat()
    except Exception as e:
        logger.exception("iso_now error: %s", e)
        return datetime.now(timezone.utc).isoformat()


# ============================================================
# FIREBASE REST HELPERS
# ============================================================

def firebase_url(path):
    try:
        clean_path = str(path).strip("/")

        url = (
            FIREBASE_DB_URL.rstrip("/")
            + "/"
            + clean_path
            + ".json"
        )

        if FIREBASE_AUTH:
            url += "?auth=" + FIREBASE_AUTH

        return url

    except Exception as e:
        logger.exception("firebase_url error: %s", e)
        return ""


def firebase_get(path):
    try:
        url = firebase_url(path)

        if not url:
            return None

        response = requests.get(
            url,
            timeout=15,
        )

        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.exception("Firebase GET error [%s]: %s", path, e)
        return None


def firebase_put(path, data):
    try:
        url = firebase_url(path)

        if not url:
            return False

        response = requests.put(
            url,
            json=data,
            timeout=15,
        )

        response.raise_for_status()

        return True

    except Exception as e:
        logger.exception("Firebase PUT error [%s]: %s", path, e)
        return False


def firebase_patch(path, data):
    try:
        url = firebase_url(path)

        if not url:
            return False

        response = requests.patch(
            url,
            json=data,
            timeout=15,
        )

        response.raise_for_status()

        return True

    except Exception as e:
        logger.exception("Firebase PATCH error [%s]: %s", path, e)
        return False


def firebase_delete(path):
    try:
        url = firebase_url(path)

        if not url:
            return False

        response = requests.delete(
            url,
            timeout=15,
        )

        response.raise_for_status()

        return True

    except Exception as e:
        logger.exception("Firebase DELETE error [%s]: %s", path, e)
        return False


# ============================================================
# USER DATABASE
# ============================================================

def get_user(user_id):
    try:
        return firebase_get(f"users/{user_id}")
    except Exception as e:
        logger.exception("get_user error: %s", e)
        return None


def create_user(tg_user):
    try:
        user_id = str(tg_user.id)

        existing = get_user(user_id)

        if existing:
            return existing

        now = iso_now()

        data = {
            "telegram_id": tg_user.id,
            "username": tg_user.username or "",
            "first_name": tg_user.first_name or "",
            "points": 0,
            "referrals": 0,
            "ninja_ref_count": 0,
            "referred_by": None,
            "referral_rewarded": False,
            "created_at": now,
            "updated_at": now,
        }

        firebase_put(
            f"users/{user_id}",
            data,
        )

        return data

    except Exception as e:
        logger.exception("create_user error: %s", e)
        return None


def update_user(user_id, data):
    try:
        update_data = dict(data)
        update_data["updated_at"] = iso_now()

        return firebase_patch(
            f"users/{user_id}",
            update_data,
        )

    except Exception as e:
        logger.exception("update_user error: %s", e)
        return False


# ============================================================
# MEMBERSHIP
# ============================================================

async def check_membership(update, context):
    try:
        user = update.effective_user

        if not user:
            return False

        member = await context.bot.get_chat_member(
            chat_id=OFFICIAL_CHANNEL,
            user_id=user.id,
        )

        allowed_statuses = {
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
        }

        return member.status in allowed_statuses

    except Exception as e:
        logger.exception("Membership check error: %s", e)
        return False


def join_keyboard():
    try:
        buttons = [
            [
                InlineKeyboardButton(
                    "📢 Join Official Channel",
                    url=OFFICIAL_CHANNEL_LINK,
                )
            ],
            [
                InlineKeyboardButton(
                    "✅ Verify Joining",
                    callback_data="verify_join",
                )
            ],
        ]

        return InlineKeyboardMarkup(buttons)

    except Exception as e:
        logger.exception("join_keyboard error: %s", e)
        return InlineKeyboardMarkup([])


async def force_join(update, context):
    try:
        joined = await check_membership(update, context)

        if joined:
            return True

        text = (
            "🔒 <b>Channel Join Required</b>\n\n"
            "Bot use karne se pehle hamare official channel ko "
            "join karna mandatory hai.\n\n"
            "1️⃣ Join Official Channel\n"
            "2️⃣ Verify Joining\n"
        )

        if update.callback_query:
            try:
                await update.callback_query.answer()
            except Exception:
                pass

            await update.callback_query.message.reply_text(
                text,
                reply_markup=join_keyboard(),
                parse_mode="HTML",
            )

        elif update.message:
            await update.message.reply_text(
                text,
                reply_markup=join_keyboard(),
                parse_mode="HTML",
            )

        return False

    except Exception as e:
        logger.exception("force_join error: %s", e)
        return False


# ============================================================
# KEYBOARDS
# ============================================================

def main_keyboard():
    try:
        keyboard = [
            ["🎁 Free Aim AI", "💳 Purchase Aim AI"],
            ["💎 Purchase Aim AI Panel", "🥷 Ninja 8BP"],
            ["🔗 My Link", "👥 Referrals"],
            ["🔑 My Keys", "🛡️ Trust Proof"],
            ["🔄 Refresh", "ℹ️ How it works"],
        ]

        return ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
            is_persistent=True,
        )

    except Exception as e:
        logger.exception("main_keyboard error: %s", e)
        return ReplyKeyboardMarkup([])


def plan_keyboard():
    try:
        keyboard = [
            [
                InlineKeyboardButton(
                    "🔑 1 Day — 5 Points",
                    callback_data="plan_1day",
                )
            ],
            [
                InlineKeyboardButton(
                    "🔑 7 Days — 8 Points",
                    callback_data="plan_7day",
                )
            ],
            [
                InlineKeyboardButton(
                    "🔑 15 Days — 15 Points",
                    callback_data="plan_15day",
                )
            ],
            [
                InlineKeyboardButton(
                    "👑 Lifetime + Panel — 100 Points",
                    callback_data="plan_lifetime",
                )
            ],
        ]

        return InlineKeyboardMarkup(keyboard)

    except Exception as e:
        logger.exception("plan_keyboard error: %s", e)
        return InlineKeyboardMarkup([])


# ============================================================
# PLANS
# ============================================================

PLANS = {
    "1day": {
        "points": 5,
        "days": 1,
        "name": "1 Day",
    },
    "7day": {
        "points": 8,
        "days": 7,
        "name": "7 Days",
    },
    "15day": {
        "points": 15,
        "days": 15,
        "name": "15 Days",
    },
    "lifetime": {
        "points": 100,
        "days": None,
        "name": "Lifetime + Free Panel",
    },
}


# ============================================================
# RANDOM KEY GENERATION
# ============================================================

def random_value(length):
    try:
        alphabet = string.ascii_uppercase + string.digits

        return "".join(
            secrets.choice(alphabet)
            for _ in range(length)
        )

    except Exception as e:
        logger.exception("random_value error: %s", e)
        return uuid.uuid4().hex.upper()


def create_key(plan_name, days):
    try:
        now = utc_now()

        if days is None:
            expires_at = None
        else:
            expires_at = (
                now + timedelta(days=days)
            ).isoformat()

        record = {
            "id": uuid.uuid4().hex,
            "username": random_value(12),
            "password": random_value(18),
            "key": random_value(24),
            "plan": plan_name,
            "created_at": now.isoformat(),
            "expires_at": expires_at,
            "active": True,
        }

        return record

    except Exception as e:
        logger.exception("create_key error: %s", e)
        return None


def save_key(user_id, record):
    try:
        if not record:
            return False

        key_id = record.get("id")

        if not key_id:
            return False

        return firebase_put(
            f"keys/{user_id}/{key_id}",
            record,
        )

    except Exception as e:
        logger.exception("save_key error: %s", e)
        return False# ============================================================
# KEY VALIDATION
# ============================================================

def key_is_valid(record):
    try:
        if not record:
            return False

        if not record.get("active", False):
            return False

        expires_at = record.get("expires_at")

        if expires_at is None:
            return True

        expiry = datetime.fromisoformat(
            str(expires_at).replace("Z", "+00:00")
        )

        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)

        return utc_now() < expiry

    except Exception as e:
        logger.exception("key_is_valid error: %s", e)
        return False


# ============================================================
# SAFE REPLY
# ============================================================

async def safe_reply(update, text, **kwargs):
    try:
        if update.message:
            return await update.message.reply_text(
                text,
                **kwargs,
            )

        if update.callback_query:
            return await update.callback_query.message.reply_text(
                text,
                **kwargs,
            )

        return None

    except Exception as e:
        logger.exception("safe_reply error: %s", e)
        return None


# ============================================================
# WELCOME
# ============================================================

async def send_welcome(update, context):
    try:
        text = (
            "🎯 <b>Welcome to Aim AI</b>\n\n"
            "Premium Aim AI services aur Ninja 8BP access "
            "ke liye neeche menu use karein.\n\n"
            "👥 Referral se Points earn karein.\n"
            "🔑 Points se keys redeem karein."
        )

        await safe_reply(
            update,
            text,
            parse_mode="HTML",
            reply_markup=main_keyboard(),
        )

    except Exception as e:
        logger.exception("send_welcome error: %s", e)


# ============================================================
# FREE AIM AI
# ============================================================

async def free_aim_ai(update, context):
    try:
        if not await force_join(update, context):
            return

        text = (
            "🎁 <b>Free Aim AI</b>\n\n"
            "Referral system se points collect karein.\n\n"
            "🎯 5 Points = 1 Day Key\n"
            "🎯 8 Points = 7 Days Key\n"
            "🎯 15 Points = 15 Days Key\n"
            "👑 100 Points = Lifetime + Free Panel\n\n"
            "👇 Key redeem karne ke liye button use karein."
        )

        await safe_reply(
            update,
            text,
            parse_mode="HTML",
            reply_markup=plan_keyboard(),
        )

    except Exception as e:
        logger.exception("free_aim_ai error: %s", e)


# ============================================================
# GENERATE PLAN KEY
# ============================================================

async def generate_plan(update, context, plan_id):
    try:
        if not await force_join(update, context):
            return

        if plan_id not in PLANS:
            await safe_reply(
                update,
                "❌ Invalid plan.",
            )
            return

        user = update.effective_user

        if not user:
            return

        user_id = str(user.id)

        db_user = get_user(user_id)

        if not db_user:
            db_user = create_user(user)

        if not db_user:
            await safe_reply(
                update,
                "❌ Database error. Please try again.",
            )
            return

        plan = PLANS[plan_id]

        points = int(db_user.get("points", 0))

        required_points = int(
            plan["points"]
        )

        if points < required_points:
            remaining = required_points - points

            await safe_reply(
                update,
                (
                    f"❌ <b>Insufficient Points</b>\n\n"
                    f"Required: {required_points} Points\n"
                    f"Your Points: {points}\n"
                    f"Remaining: {remaining}"
                ),
                parse_mode="HTML",
            )

            return

        record = create_key(
            plan["name"],
            plan["days"],
        )

        if not record:
            await safe_reply(
                update,
                "❌ Key generation failed.",
            )
            return

        saved = save_key(
            user_id,
            record,
        )

        if not saved:
            await safe_reply(
                update,
                "❌ Could not save key. Points were not deducted.",
            )
            return

        new_points = points - required_points

        updated = update_user(
            user_id,
            {
                "points": new_points,
            },
        )

        if not updated:
            logger.warning(
                "Points update failed for user %s",
                user_id,
            )

        message = (
            f"Username: {record['username']}\n"
            f"Password: {record['password']}\n"
            f"Key: {record['key']}\n"
            f"Validity: {record['plan']}\n"
            f"App Download Link: {APP_DOWNLOAD_LINK}"
        )

        await safe_reply(
            update,
            "✅ <b>Key Generated Successfully</b>\n\n"
            + message,
            parse_mode="HTML",
        )

    except Exception as e:
        logger.exception("generate_plan error: %s", e)

        await safe_reply(
            update,
            "❌ Something went wrong. Please try again.",
        )


# ============================================================
# REFERRAL PROCESSING
# ============================================================

async def process_referral(new_user_id, referral_code):
    try:
        if not referral_code:
            return False

        referral_code = str(referral_code).strip()

        if not referral_code.startswith("ref_"):
            return False

        referrer_id = referral_code[4:]

        if not referrer_id.isdigit():
            return False

        if str(referrer_id) == str(new_user_id):
            return False

        new_user = get_user(new_user_id)

        if not new_user:
            return False

        if new_user.get("referral_rewarded", False):
            return False

        referrer = get_user(referrer_id)

        if not referrer:
            return False

        current_points = int(
            referrer.get("points", 0)
        )

        current_referrals = int(
            referrer.get("referrals", 0)
        )

        current_ninja = int(
            referrer.get("ninja_ref_count", 0)
        )

        update_referrer = update_user(
            referrer_id,
            {
                "points": current_points + 1,
                "referrals": current_referrals + 1,
                "ninja_ref_count": current_ninja + 1,
            },
        )

        if not update_referrer:
            return False

        update_user(
            new_user_id,
            {
                "referred_by": str(referrer_id),
                "referral_rewarded": True,
            },
        )

        try:
            await application_instance.bot.send_message(
                chat_id=int(referrer_id),
                text=(
                    "🎉 <b>New Verified Referral!</b>\n\n"
                    "+1 Point added.\n"
                    f"Total Points: {current_points + 1}\n"
                    f"Total Referrals: {current_referrals + 1}"
                ),
                parse_mode="HTML",
            )
        except Exception:
            pass

        return True

    except Exception as e:
        logger.exception("process_referral error: %s", e)
        return False


# ============================================================
# REFERRAL MENU
# ============================================================

async def referrals(update, context):
    try:
        if not await force_join(update, context):
            return

        user = update.effective_user

        if not user:
            return

        db_user = get_user(str(user.id))

        if not db_user:
            db_user = create_user(user)

        points = int(
            db_user.get("points", 0)
        ) if db_user else 0

        referrals_count = int(
            db_user.get("referrals", 0)
        ) if db_user else 0

        ninja_count = int(
            db_user.get("ninja_ref_count", 0)
        ) if db_user else 0

        bot_info = await context.bot.get_me()

        bot_username = bot_info.username

        referral_link = (
            f"https://t.me/{bot_username}"
            f"?start=ref_{user.id}"
        )

        text = (
            "👥 <b>Referral System</b>\n\n"
            f"⭐ Points: {points}\n"
            f"👥 Verified Referrals: {referrals_count}\n"
            f"🥷 Ninja Referrals: {ninja_count}\n\n"
            "🎁 Rewards:\n"
            "• 5 Points → 1 Day Key\n"
            "• 8 Points → 7 Days Key\n"
            "• 15 Points → 15 Days Key\n"
            "• 100 Points → Lifetime + Free Panel\n\n"
            "<b>Your Referral Link:</b>\n"
            f"{referral_link}"
        )

        await safe_reply(
            update,
            text,
            parse_mode="HTML",
        )

    except Exception as e:
        logger.exception("referrals error: %s", e)


# ============================================================
# MY LINK
# ============================================================

async def my_link(update, context):
    try:
        if not await force_join(update, context):
            return

        user = update.effective_user

        if not user:
            return

        bot_info = await context.bot.get_me()

        link = (
            f"https://t.me/{bot_info.username}"
            f"?start=ref_{user.id}"
        )

        await safe_reply(
            update,
            (
                "🔗 <b>Your Referral Link</b>\n\n"
                f"{link}\n\n"
                "Is link ko friends ke saath share karein."
            ),
            parse_mode="HTML",
        )

    except Exception as e:
        logger.exception("my_link error: %s", e)


# ============================================================
# MY KEYS
# ============================================================

async def my_keys(update, context):
    try:
        if not await force_join(update, context):
            return

        user = update.effective_user

        if not user:
            return

        user_id = str(user.id)

        records = firebase_get(
            f"keys/{user_id}"
        )

        if not records:
            await safe_reply(
                update,
                "🔑 <b>My Keys</b>\n\nNo keys found.",
                parse_mode="HTML",
            )
            return

        valid_keys = []

        for _, record in records.items():
            if key_is_valid(record):
                valid_keys.append(record)

        if not valid_keys:
            await safe_reply(
                update,
                "🔑 <b>My Keys</b>\n\nNo active keys found.",
                parse_mode="HTML",
            )
            return

        lines = [
            "🔑 <b>Your Active Keys</b>",
            "",
        ]

        for index, record in enumerate(
            valid_keys,
            start=1,
        ):
            lines.append(
                f"<b>Key #{index}</b>"
            )
            lines.append(
                f"Username: {record.get('username', '')}"
            )
            lines.append(
                f"Password: {record.get('password', '')}"
            )
            lines.append(
                f"Key: {record.get('key', '')}"
            )
            lines.append(
                f"Validity: {record.get('plan', '')}"
            )
            lines.append("")

        await safe_reply(
            update,
            "\n".join(lines),
            parse_mode="HTML",
        )

    except Exception as e:
        logger.exception("my_keys error: %s", e)


# ============================================================
# NINJA 8BP
# ============================================================

async def ninja_8bp(update, context):
    try:
        if not await force_join(update, context):
            return

        user = update.effective_user

        if not user:
            return

        db_user = get_user(str(user.id))

        if not db_user:
            db_user = create_user(user)

        ninja_count = int(
            db_user.get("ninja_ref_count", 0)
        ) if db_user else 0

        required = 10

        if ninja_count < required:
            remaining = required - ninja_count

            await safe_reply(
                update,
                (
                    "🥷 <b>Ninja 8BP</b>\n\n"
                    f"Your verified referrals: {ninja_count}/{required}\n\n"
                    f"❗ {remaining} more referral(s) required.\n\n"
                    "Referral complete hone ke baad Ninja APK "
                    "yahan se milega."
                ),
                parse_mode="HTML",
            )

            return

        if not os.path.isfile(NINJA_APK_PATH):
            await safe_reply(
                update,
                (
                    "❌ Ninja APK server par nahi mili.\n\n"
                    f"Required filename:\n"
                    f"<code>{NINJA_APK_PATH}</code>"
                ),
                parse_mode="HTML",
            )
            return

        await safe_reply(
            update,
            "🥷 <b>Ninja 8BP</b>\n\n"
            "✅ Requirement completed.\n"
            "📦 APK sending..."
            ,
            parse_mode="HTML",
        )

        with open(
            NINJA_APK_PATH,
            "rb",
        ) as apk_file:

            await context.bot.send_document(
                chat_id=user.id,
                document=apk_file,
                filename=NINJA_APK_PATH,
                caption=(
                    "🥷 <b>Ninja 8BP APK</b>\n\n"
                    "✅ Referral requirement completed."
                ),
                parse_mode="HTML",
            )

    except Exception as e:
        logger.exception("ninja_8bp error: %s", e)

        await safe_reply(
            update,
            "❌ APK send karte waqt error aaya.",
        )


# ============================================================
# PURCHASE AIM AI
# ============================================================

async def purchase_aim_ai(update, context):
    try:
        if not await force_join(update, context):
            return

        text = (
            "💳 <b>Purchase Aim AI</b>\n\n"
            "📲 Telegram:\n"
            f"{OWNER_TELEGRAM}\n\n"
            "📱 WhatsApp:\n"
            f"{OWNER_WHATSAPP}\n\n"
            "📦 App Download:\n"
            f"{APP_DOWNLOAD_LINK}"
        )

        await safe_reply(
            update,
            text,
            parse_mode="HTML",
        )

    except Exception as e:
        logger.exception("purchase_aim_ai error: %s", e)


# ============================================================
# PURCHASE PANEL
# ============================================================

async def purchase_panel(update, context):
    try:
        if not await force_join(update, context):
            return

        text = (
            "💎 <b>Aim AI Panel</b>\n\n"
            "💰 Price: <b>₹400 Lifetime</b>\n\n"
            "🔥 Panel Features:\n"
            "• Unlimited key generation\n"
            "• Keys resale business\n"
            "• Custom branding\n"
            "• One-time investment\n"
            "• No monthly subscription\n\n"
            "📲 Telegram:\n"
            f"{OWNER_TELEGRAM}\n\n"
            "📱 WhatsApp:\n"
            f"{OWNER_WHATSAPP}"
        )

        await safe_reply(
            update,
            text,
            parse_mode="HTML",
        )

    except Exception as e:
        logger.exception("purchase_panel error: %s", e)


# ============================================================
# TRUST PROOF
# ============================================================

async def trust_proof(update, context):
    try:
        if not await force_join(update, context):
            return

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🛡️ Open Trust Proof",
                        url=TRUST_PROOF_CHANNEL,
                    )
                ]
            ]
        )

        await safe_reply(
            update,
            (
                "🛡️ <b>Trust Proof</b>\n\n"
                "Previous proofs aur customer-related proof "
                "dekhne ke liye channel open karein."
            ),
            parse_mode="HTML",
            reply_markup=keyboard,
        )

    except Exception as e:
        logger.exception("trust_proof error: %s", e)


# ============================================================
# HOW IT WORKS
# ============================================================

async def how_it_works(update, context):
    try:
        if not await force_join(update, context):
            return

        text = (
            "ℹ️ <b>How It Works</b>\n\n"
            "1️⃣ Official channel join karein.\n"
            "2️⃣ Verify Joining dabayein.\n"
            "3️⃣ Referral link share karein.\n"
            "4️⃣ Har verified referral = +1 Point.\n"
            "5️⃣ Points se key redeem karein.\n\n"
            "🎯 5 → 1 Day\n"
            "🎯 8 → 7 Days\n"
            "🎯 15 → 15 Days\n"
            "👑 100 → Lifetime + Free Panel\n\n"
            "🥷 Ninja 8BP ke liye 10 verified Ninja referrals "
            "required hain."
        )

        await safe_reply(
            update,
            text,
            parse_mode="HTML",
        )

    except Exception as e:
        logger.exception("how_it_works error: %s", e)


# ============================================================
# REFRESH
# ============================================================

async def refresh(update, context):
    try:
        if not await force_join(update, context):
            return

        await safe_reply(
            update,
            "🔄 Menu refreshed.",
            reply_markup=main_keyboard(),
        )

    except Exception as e:
        logger.exception("refresh error: %s", e)


# ============================================================
# VERIFY JOIN CALLBACK
# ============================================================

async def verify_join_callback(update, context):
    try:
        query = update.callback_query

        if not query:
            return

        await query.answer()

        joined = await check_membership(
            update,
            context,
        )

        if not joined:
            await query.message.reply_text(
                "❌ Abhi channel membership verify nahi hui.\n\n"
                "Pehle channel join karein aur phir Verify Joining dabayein.",
                reply_markup=join_keyboard(),
            )
            return

        await query.message.reply_text(
            "✅ <b>Membership Verified!</b>\n\n"
            "Ab bot ke saare features available hain.",
            parse_mode="HTML",
            reply_markup=main_keyboard(),
        )

    except Exception as e:
        logger.exception(
            "verify_join_callback error: %s",
            e,
        )


# ============================================================
# CALLBACK ROUTER
# ============================================================

async def callback_router(update, context):
    try:
        query = update.callback_query

        if not query:
            return

        dat
