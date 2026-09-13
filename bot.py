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
# AIM AI + NINJA 8BP TELEGRAM BOT
# PART 1
# ============================================================

# IMPORTANT:
# The credentials originally supplied in chat are exposed.
# Rotate them before production deployment.
#
# Set the rotated values directly below.
#
# Example:
# BOT_TOKEN = "ROTATED_BOT_TOKEN"
# FIREBASE_AUTH = "ROTATED_FIREBASE_AUTH"


BOT_TOKEN = "REPLACE_WITH_ROTATED_BOT_TOKEN"

FIREBASE_AUTH = "REPLACE_WITH_ROTATED_FIREBASE_AUTH"

FIREBASE_DB_URL = (
    "https://aimai-817ef-default-rtdb."
    "asia-southeast1.firebasedatabase.app"
)

OFFICIAL_CHANNEL = "@novaengine01"

OFFICIAL_CHANNEL_LINK = (
    "https://t.me/novaengine01"
)

APP_DOWNLOAD_LINK = (
    "https://t.me/memonxgaming/1060"
)

OWNER_TELEGRAM = "@Memonsalim"

OWNER_WHATSAPP = "+91 6354525228"

TRUST_PROOF_CHANNEL = (
    "https://t.me/proofnovaengine"
)

ADMIN_SECRET = (
    "ROTATE_ADMIN_SECRET_BEFORE_PRODUCTION"
)

NINJA_APK_PATH = "Ninja8BP.apk"

PORT = int(
    os.getenv("PORT", "10000")
)


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(name)s | "
        "%(message)s"
    ),
)

logger = logging.getLogger("AimAI")


# ============================================================
# FLASK SERVER
# ============================================================

web_app = Flask(__name__)


@web_app.route("/")
def web_home():
    try:
        return "Aim AI Bot is running.", 200
    except Exception:
        logger.exception("Home route error")
        return "OK", 200


@web_app.route("/health")
def web_health():
    try:
        return "OK", 200
    except Exception:
        logger.exception("Health route error")
        return "OK", 200


@web_app.route("/ping")
def web_ping():
    try:
        return "pong", 200
    except Exception:
        logger.exception("Ping route error")
        return "pong", 200


def run_web_server():
    try:
        web_app.run(
            host="0.0.0.0",
            port=PORT,
            debug=False,
            use_reloader=False,
        )
    except Exception:
        logger.exception(
            "Flask server stopped."
        )


# ============================================================
# FIREBASE HELPERS
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

    except Exception:
        logger.exception(
            "firebase_url failed"
        )
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

    except Exception:
        logger.exception(
            "Firebase GET failed: %s",
            path,
        )
        return None


def firebase_put(path, data):
    try:
        url = firebase_url(path)

        if not url:
            return None

        response = requests.put(
            url,
            json=data,
            timeout=15,
        )

        response.raise_for_status()

        return response.json()

    except Exception:
        logger.exception(
            "Firebase PUT failed: %s",
            path,
        )
        return None


def firebase_patch(path, data):
    try:
        url = firebase_url(path)

        if not url:
            return None

        response = requests.patch(
            url,
            json=data,
            timeout=15,
        )

        response.raise_for_status()

        return response.json()

    except Exception:
        logger.exception(
            "Firebase PATCH failed: %s",
            path,
        )
        return None


# ============================================================
# USER DATABASE
# ============================================================

def get_user(user_id):
    try:
        return firebase_get(
            "users/" + str(user_id)
        )

    except Exception:
        logger.exception(
            "get_user failed"
        )
        return None


def create_user(tg_user):
    try:
        user_id = tg_user.id

        existing = get_user(
            user_id
        )

        now = datetime.now(
            timezone.utc
        ).isoformat()

        username = (
            tg_user.username
            or ""
        )

        first_name = (
            tg_user.first_name
            or ""
        )

        if existing:
            firebase_patch(
                "users/" + str(user_id),
                {
                    "username": username,
                    "first_name": first_name,
                    "updated_at": now,
                },
            )

            existing["username"] = username
            existing["first_name"] = first_name

            return existing

        data = {
            "telegram_id": user_id,
            "username": username,
            "first_name": first_name,
            "points": 0,
            "referrals": 0,
            "ninja_ref_count": 0,
            "referred_by": None,
            "referral_rewarded": False,
            "created_at": now,
            "updated_at": now,
        }

        firebase_put(
            "users/" + str(user_id),
            data,
        )

        return data

    except Exception:
        logger.exception(
            "create_user failed"
        )
        return None


def update_user(
    user_id,
    data,
):
    try:
        data = dict(data)

        data["updated_at"] = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        return firebase_patch(
            "users/" + str(user_id),
            data,
        )

    except Exception:
        logger.exception(
            "update_user failed"
        )
        return None


# ============================================================
# MEMBERSHIP
# ============================================================

async def check_membership(
    update,
    context,
):
    try:
        user = update.effective_user

        if not user:
            return False

        member = await context.bot.get_chat_member(
            chat_id=OFFICIAL_CHANNEL,
            user_id=user.id,
        )

        allowed = {
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
        }

        return member.status in allowed

    except Exception:
        logger.exception(
            "Membership check failed"
        )
        return False


def join_keyboard():
    try:
        return InlineKeyboardMarkup(
            [
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
        )

    except Exception:
        logger.exception(
            "join_keyboard failed"
        )
        return InlineKeyboardMarkup([])


async def force_join(
    update,
    context,
):
    try:
        if await check_membership(
            update,
            context,
        ):
            return True

        text = (
            "🔒 CHANNEL JOIN REQUIRED\n\n"
            "Bot use karne ke liye pehle "
            "official channel join karein.\n\n"
            "1️⃣ Join Official Channel\n"
            "2️⃣ Channel join karein\n"
            "3️⃣ Verify Joining press karein"
        )

        if update.callback_query:
            query = update.callback_query

            await query.answer()

            try:
                await query.edit_message_text(
                    text,
                    reply_markup=join_keyboard(),
                )
            except Exception:
                await query.message.reply_text(
                    text,
                    reply_markup=join_keyboard(),
                )

        elif update.message:
            await update.message.reply_text(
                text,
                reply_markup=join_keyboard(),
            )

        return False

    except Exception:
        logger.exception(
            "force_join failed"
        )
        return False


# ============================================================
# REPLY KEYBOARD
# ============================================================

def main_keyboard():
    try:
        rows = [
            [
                "🎁 Free Aim AI",
                "💳 Purchase Aim AI",
            ],
            [
                "💎 Purchase Aim AI Panel",
                "🥷 Ninja 8BP",
            ],
            [
                "🔗 My Link",
                "👥 Referrals",
            ],
            [
                "🔑 My Keys",
                "🛡️ Trust Proof",
            ],
            [
                "🔄 Refresh",
                "ℹ️ How it works",
            ],
        ]

        return ReplyKeyboardMarkup(
            rows,
            resize_keyboard=True,
            is_persistent=True,
        )

    except Exception:
        logger.exception(
            "main_keyboard failed"
        )
        return ReplyKeyboardMarkup([])


# ============================================================
# PLAN CONFIG
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


def plan_keyboard():
    try:
        return InlineKeyboardMarkup(
            [
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
                        "♾️ Lifetime — 100 Points",
                        callback_data="plan_lifetime",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🏠 Main Menu",
                        callback_data="home",
                    )
                ],
            ]
        )

    except Exception:
        logger.exception(
            "plan_keyboard failed"
        )
        return InlineKeyboardMarkup([])


# ============================================================
# KEY GENERATION
# ============================================================

def random_value(length):
    try:
        alphabet = (
            string.ascii_letters
            + string.digits
        )

        return "".join(
            secrets.choice(alphabet)
            for _ in range(length)
        )

    except Exception:
        logger.exception(
            "random_value failed"
        )
        raise


def create_key(
    plan_name,
    days,
):
    try:
        now = datetime.now(
            timezone.utc
        )

        if days is None:
            expires_at = None
        else:
            expires_at = (
                now
                + timedelta(days=days)
            ).isoformat()

        return {
            "id": uuid.uuid4().hex,
            "username": random_value(12),
            "password": random_value(18),
            "key": random_value(24),
            "plan": plan_name,
            "created_at": now.isoformat(),
            "expires_at": expires_at,
            "active": True,
        }

    except Exception:
        logger.exception(
            "create_key failed"
        )
        raise


def save_key(
    user_id,
    record,
):
    try:
        result = firebase_put(
            "keys/{}/{}".format(
                user_id,
                record["id"],
            ),
            record,
        )

        return result is not None

    except Exception:
        logger.exception(
            "save_key failed"
        )
        return False


# ============================================================
# END PART 1
# ============================================================
# ============================================================
# AIM AI + NINJA 8BP TELEGRAM BOT
# PART 2
# ============================================================


# ============================================================
# KEY VALIDATION
# ============================================================

def key_is_valid(record):
    try:
        if not record:
            return False

        if record.get("active") is not True:
            return False

        expires_at = record.get(
            "expires_at"
        )

        if not expires_at:
            return True

        expiry = datetime.fromisoformat(
            expires_at.replace(
                "Z",
                "+00:00",
            )
        )

        now = datetime.now(
            timezone.utc
        )

        return now < expiry

    except Exception:
        logger.exception(
            "key_is_valid failed"
        )
        return False


# ============================================================
# SAFE REPLY
# ============================================================

async def safe_reply(
    update,
    text,
):
    try:
        if update.message:
            await update.message.reply_text(
                text,
                reply_markup=main_keyboard(),
            )

        elif update.callback_query:
            await update.callback_query.message.reply_text(
                text,
                reply_markup=main_keyboard(),
            )

    except Exception:
        logger.exception(
            "safe_reply failed"
        )


# ============================================================
# FREE AIM AI
# ============================================================

async def free_aim_ai(
    update,
    context,
):
    try:
        if not await force_join(
            update,
            context,
        ):
            return

        user = get_user(
            update.effective_user.id
        ) or {}

        points = int(
            user.get(
                "points",
                0,
            )
        )

        text = (
            "🎁 FREE AIM AI\n\n"
            "1 verified referral = +1 Point\n\n"
            "AVAILABLE PLANS\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🔑 5 Points  → 1 Day Key\n"
            "🔑 8 Points  → 7 Days Key\n"
            "🔑 15 Points → 15 Days Key\n"
            "♾️ 100 Points → Lifetime + Free Panel\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"💎 Your Points: {points}\n\n"
            "Neeche plan select karein."
        )

        await update.message.reply_text(
            text,
            reply_markup=plan_keyboard(),
        )

    except Exception:
        logger.exception(
            "free_aim_ai failed"
        )

        await safe_reply(
            update,
            "❌ Free Aim AI open nahi ho saka.",
        )


# ============================================================
# GENERATE SELECTED PLAN
# ============================================================

async def generate_plan(
    update,
    context,
):
    try:
        query = update.callback_query

        if not await force_join(
            update,
            context,
        ):
            return

        await query.answer()

        plan_id = query.data.replace(
            "plan_",
            "",
            1,
        )

        if plan_id not in PLANS:
            await query.answer(
                "Invalid plan.",
                show_alert=True,
            )
            return

        plan = PLANS[plan_id]

        user_id = update.effective_user.id

        user = get_user(
            user_id
        ) or {}

        points = int(
            user.get(
                "points",
                0,
            )
        )

        required = int(
            plan["points"]
        )

        if points < required:

            remaining = (
                required - points
            )

            await query.edit_message_text(
                "❌ NOT ENOUGH POINTS\n\n"
                f"Your Points: {points}\n"
                f"Required: {required}\n"
                f"Remaining: {remaining}\n\n"
                "👥 Referrals karke points earn karein."
            )

            return

        record = create_key(
            plan["name"],
            plan["days"],
        )

        saved = save_key(
            user_id,
            record,
        )

        if not saved:
            await query.edit_message_text(
                "❌ Key save nahi ho saki.\n"
                "Please try again.",
            )
            return

        update_user(
            user_id,
            {
                "points": points - required,
            },
        )

        output = (
            "Username: {}\n"
            "Password: {}\n"
            "Key: {}\n"
            "Validity: {}\n"
            "App Download Link: {}"
        ).format(
            record["username"],
            record["password"],
            record["key"],
            plan["name"],
            APP_DOWNLOAD_LINK,
        )

        await query.edit_message_text(
            output,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🏠 Main Menu",
                            callback_data="home",
                        )
                    ]
                ]
            ),
        )

    except Exception:
        logger.exception(
            "generate_plan failed"
        )

        try:
            await update.callback_query.edit_message_text(
                "❌ Key generation failed. Please try again."
            )
        except Exception:
            pass


# ============================================================
# REFERRAL PAGE
# ============================================================

async def referrals_page(
    update,
    context,
):
    try:
        if not await force_join(
            update,
            context,
        ):
            return

        user_id = update.effective_user.id

        user = get_user(
            user_id
        ) or {}

        referrals = int(
            user.get(
                "referrals",
                0,
            )
        )

        points = int(
            user.get(
                "points",
                0,
            )
        )

        ninja_count = int(
            user.get(
                "ninja_ref_count",
                0,
            )
        )

        bot = await context.bot.get_me()

        link = (
            "https://t.me/"
            + bot.username
            + "?start=ref_"
            + str(user_id)
        )

        text = (
            "👥 MY REFERRALS\n\n"
            f"Verified Referrals: {referrals}\n"
            f"Points: {points}\n"
            f"Ninja Progress: {ninja_count}/10\n\n"
            "🎁 FREE AIM AI\n"
            "5 Points → 1 Day\n"
            "8 Points → 7 Days\n"
            "15 Points → 15 Days\n"
            "100 Points → Lifetime + Free Panel\n\n"
            "🔗 YOUR REFERRAL LINK\n"
            f"{link}"
        )

        await update.message.reply_text(
            text,
            reply_markup=main_keyboard(),
        )

    except Exception:
        logger.exception(
            "referrals_page failed"
        )

        await safe_reply(
            update,
            "❌ Referral information load nahi hui.",
        )


# ============================================================
# MY LINK
# ============================================================

async def my_link(
    update,
    context,
):
    try:
        if not await force_join(
            update,
            context,
        ):
            return

        user_id = update.effective_user.id

        bot = await context.bot.get_me()

        link = (
            "https://t.me/"
            + bot.username
            + "?start=ref_"
            + str(user_id)
        )

        await update.message.reply_text(
            "🔗 YOUR REFERRAL LINK\n\n"
            + link
            + "\n\n"
            "Har verified referral = +1 Point.",
            reply_markup=main_keyboard(),
        )

    except Exception:
        logger.exception(
            "my_link failed"
        )

        await safe_reply(
            update,
            "❌ Link generate nahi hua.",
        )


# ============================================================
# MY KEYS
# ============================================================

async def my_keys(
    update,
    context,
):
    try:
        if not await force_join(
            update,
            context,
        ):
            return

        user_id = update.effective_user.id

        data = firebase_get(
            "keys/" + str(user_id)
        )

        if not data:
            await update.message.reply_text(
                "🔑 MY KEYS\n\n"
                "Aapne abhi koi key generate nahi ki.",
                reply_markup=main_keyboard(),
            )
            return

        records = []

        if isinstance(data, dict):
            records = list(
                data.values()
            )

        active_keys = []

        for record in records:

            if key_is_valid(record):
                active_keys.append(
                    record
                )

        if not active_keys:

            await update.message.reply_text(
                "🔑 MY KEYS\n\n"
                "Aapki koi active key nahi hai.",
                reply_markup=main_keyboard(),
            )

            return

        lines = [
            "🔑 MY ACTIVE KEYS",
            "",
        ]

        for number, record in enumerate(
            active_keys,
            1,
        ):

            lines.append(
                "Key #{}".format(number)
            )

            lines.append(
                "Username: "
                + str(
                    record.get(
                        "username",
                        "",
                    )
                )
            )

            lines.append(
                "Password: "
                + str(
                    record.get(
                        "password",
                        "",
                    )
                )
            )

            lines.append(
                "Key: "
                + str(
                    record.get(
                        "key",
                        "",
                    )
                )
            )

            lines.append(
                "Validity: "
                + str(
                    record.get(
                        "plan",
                        "",
                    )
                )
            )

            lines.append("")

        await update.message.reply_text(
            "\n".join(lines),
            reply_markup=main_keyboard(),
        )

    except Exception:
        logger.exception(
            "my_keys failed"
        )

        await safe_reply(
            update,
            "❌ Keys load nahi ho sakin.",
        )


# ============================================================
# NINJA 8BP
# ============================================================

async def ninja_8bp(
    update,
    context,
):
    try:
        if not await force_join(
            update,
            context,
        ):
            return

        user_id = update.effective_user.id

        user = get_user(
            user_id
        ) or {}

        count = int(
            user.get(
                "ninja_ref_count",
                0,
            )
        )

        if count < 10:

            remaining = 10 - count

            await update.message.reply_text(
                "🥷 NINJA 8BP\n\n"
                "APK unlock ke liye "
                "10 verified referrals required hain.\n\n"
                f"Progress: {count}/10\n"
                f"Remaining: {remaining}",
                reply_markup=main_keyboard(),
            )

            return

        if not os.path.isfile(
            NINJA_APK_PATH
        ):

            await update.message.reply_text(
                "❌ Ninja 8BP APK server par nahi mili.\n\n"
                f"Owner: {OWNER_TELEGRAM}",
                reply_markup=main_keyboard(),
            )

            return

        await update.message.reply_text(
            "⏳ 10 referrals verified.\n"
            "Ninja 8BP APK upload ho rahi hai..."
        )

        with open(
            NINJA_APK_PATH,
            "rb",
        ) as apk:

            await context.bot.send_document(
                chat_id=user_id,
                document=apk,
                caption=(
                    "🥷 Ninja 8BP\n\n"
                    "✅ 10 verified referrals completed."
                ),
            )

    except Exception:
        logger.exception(
            "ninja_8bp failed"
        )

        await safe_reply(
            update,
            "❌ Ninja 8BP APK send nahi ho saki.",
        )


# ============================================================
# PURCHASE AIM AI
# ============================================================

async def purchase_aim(
    update,
    context,
):
    try:
        if not await force_join(
            update,
            context,
        ):
            return

        text = (
            "💳 PURCHASE AIM AI\n\n"
            "Aim AI purchase aur activation ke liye "
            "owner se direct contact karein.\n\n"
            "👤 Telegram:\n"
            f"{OWNER_TELEGRAM}\n\n"
            "📱 WhatsApp:\n"
            f"{OWNER_WHATSAPP}\n\n"
            "📥 App:\n"
            f"{APP_DOWNLOAD_LINK}"
        )

        await update.message.reply_text(
            text,
            reply_markup=main_keyboard(),
        )

    except Exception:
        logger.exception(
            "purchase_aim failed"
        )

        await safe_reply(
            update,
            "❌ Purchase page open nahi hui.",
        )


# ============================================================
# PURCHASE AIM AI PANEL
# ============================================================

async def purchase_panel(
    update,
    context,
):
    try:
        if not await force_join(
            update,
            context,
        ):
            return

        text = (
            "💎 AIM AI PANEL\n\n"
            "🔥 ONE-TIME INVESTMENT: ₹400\n\n"
            "Apna khud ka Aim AI key distribution "
            "aur resale business start karein.\n\n"
            "✨ PANEL BENEFITS\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "♾️ Unlimited Key Generation\n"
            "🔑 Key Distribution System\n"
            "💰 Resale Business Opportunity\n"
            "🎨 Custom Branding\n"
            "⚡ Fast Key Management\n"
            "📦 Multiple Key Generation\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "₹400 fixed one-time investment.\n"
            "Monthly subscription nahi.\n\n"
            "📩 Purchase ke liye contact:\n"
            f"Telegram: {OWNER_TELEGRAM}\n"
            f"WhatsApp: {OWNER_WHATSAPP}"
        )

        await update.message.reply_text(
            text,
            reply_markup=main_keyboard(),
        )

    except Exception:
        logger.exception(
            "purchase_panel failed"
        )

        await safe_reply(
            update,
            "❌ Panel page open nahi hui.",
        )


# ============================================================
# TRUST PROOF
# ============================================================

async def trust_proof(
    update,
    context,
):
    try:
        if not await force_join(
            update,
            context,
        ):
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

        await update.message.reply_text(
            "🛡️ TRUST PROOF\n\n"
            "Customer proofs aur feedback "
            "official proof channel par available hain.",
            reply_markup=keyboard,
        )

    except Exception:
        logger.exception(
            "trust_proof failed"
        )

        await safe_reply(
            update,
            "❌ Trust Proof open nahi hua.",
        )


# ============================================================
# HOW IT WORKS
# ============================================================

async def how_it_works(
    update,
    context,
):
    try:
        if not await force_join(
            update,
            context,
        ):
            return

        text = (
            "ℹ️ HOW IT WORKS\n\n"
            "1️⃣ Official channel join karein.\n\n"
            "2️⃣ Apna referral link share karein.\n\n"
            "3️⃣ Har verified referral = +1 Point.\n\n"
            "4️⃣ Points se free Aim AI key generate karein.\n\n"
            "5️⃣ 10 verified referrals par Ninja 8BP APK unlock hota hai.\n\n"
            "🎁 PLANS\n"
            "5 → 1 Day\n"
            "8 → 7 Days\n"
            "15 → 15 Days\n"
            "100 → Lifetime + Free Panel"
        )

        await update.message.reply_text(
            text,
            reply_markup=main_keyboard(),
        )

    except Exception:
        logger.exception(
            "how_it_works failed"
        )

        await safe_reply(
            update,
            "❌ Information load nahi hui.",
        )


# ============================================================
# REFRESH
# ============================================================

async def refresh(
    update,
    context,
):
    try:
        if not await force_join(
            update,
            context,
        ):
            return

        user = get_user(
            update.effective_user.id
        ) or {}

        points = int(
            user.get(
                "points",
                0,
            )
        )

        referrals = int(
            user.get(
                "referrals",
                0,
            )
        )

        ninja = int(
            user.get(
                "ninja_ref_count",
                0,
            )
        )

        await update.message.reply_text(
            "🔄 REFRESHED\n\n"
            f"💎 Points: {points}\n"
            f"👥 Referrals: {referrals}\n"
            f"🥷 Ninja Progress: {ninja}/10",
            reply_markup=main_keyboard(),
        )

    except Exception:
        logger.exception(
            "refresh failed"
        )

        await safe_reply(
            update,
            "❌ Refresh failed.",
        )


# ============================================================
# VERIFY JOINING
# ============================================================

async def verify_joining(
    update,
    context,
):
    try:
        query = update.callback_query

        joined = await check_membership(
            update,
            context,
        )

        if joined:

            await query.answer(
                "✅ Joining verified!",
                show_alert=True,
            )

            await query.message.reply_text(
                "✅ CHANNEL VERIFIED\n\n"
                "Ab bot ke features available hain.",
                reply_markup=main_keyboard(),
            )

        else:

            await query.answer(
                "❌ Pehle official channel join karein.",
                show_alert=True,
            )

    except Exception:
        logger.exception(
            "verify_joining failed"
        )


# ============================================================
# HOME CALLBACK
# ============================================================

async def home_callback(
    update,
    context,
):
    try:
        if not await force_join(
            update,
            context,
        ):
            return

        query = update.callback_query

        await query.answer()

        await
