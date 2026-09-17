import os
import time
import random
import threading
import logging
from datetime import datetime, timezone

import requests
import telebot
from telebot import types
from flask import Flask, jsonify

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
REFRESH_NOTIFIED_KEY = "refresh_notified_v23"
VERIFICATION_EMOJIS = ["🍎", "🚗", "⭐", "⚽", "🐱"]
STARS_REQUIRED_PER_APP = 5

GAMES_DATA = {
    "8bp": {
        "title": "🎱 8 Ball Pool Hacks",
        "apps": [
            {"name": "Ninja Crack", "filename": "Ninja-crack.apk", "desc": "Advanced 8BP Ninja Hack"},
            {"name": "AK Loader", "filename": "AKLoader-3.8.2-random-(arm32 a...apk", "desc": "AK Loader Tool for 8BP"}
        ]
    },
    "carrom": {
        "title": "🎱 Carrom Pool Hacks",
        "apps": [
            {"name": "Aim AI Pro", "filename": "AimAi-2.apk", "desc": "Carrom Aim AI Guide & Tool"}
        ]
    },
    "freefire": {
        "title": "🔥 Free Fire Hacks",
        "apps": [
            {"name": "HuuDa Proxy", "filename": "HuuDa Proxy V1.0.apk", "desc": "HuuDa Proxy Mod Panel"},
            {"name": "Krishan X Take Michi", "filename": "KRISHAN X TAKE MICHI_1.0.apk", "desc": "Michi Mod Menu"},
            {"name": "Laugh Mods", "filename": "LAUGH MODS V4_1.0.apk", "desc": "Laugh Mods Panel v4"},
            {"name": "M1NX Proxy", "filename": "M1NX PROXY.apk", "desc": "M1NX FF Proxy Tool"},
            {"name": "RC Beta Proxy", "filename": "RC BETA PROXY V1.apk", "desc": "RC Beta Proxy Panel"},
            {"name": "S3 Hacks Proxy", "filename": "S3 Hacks Proxy_1.8.apk", "desc": "S3 Hacks Proxy v1.8"}
        ]
    }
}

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
    try:
        return jsonify({"status": "ok", "bot": "running", "time": datetime.now(timezone.utc).isoformat()})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/ping")
def ping():
    return "pong"

def run_web_server():
    try:
        port = int(os.getenv("PORT", "10000"))
        app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
    except Exception as e:
        logger.error("Flask server error: " + str(e))

def firebase_url(path=""):
    try:
        path = str(path).strip("/")
        url = FIREBASE_URL + "/" + path + ".json" if path else FIREBASE_URL + "/.json"
        separator = "&" if "?" in url else "?"
        return url + separator + "auth=" + FIREBASE_AUTH
    except Exception:
        return ""

def firebase_get(path=""):
    try:
        response = requests.get(firebase_url(path), timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.error("Firebase GET error: " + str(e))
    return None

def firebase_put(path, data):
    try:
        response = requests.put(firebase_url(path), json=data, timeout=10)
        return response.status_code in (200, 201)
    except Exception as e:
        logger.error("Firebase PUT error: " + str(e))
    return False

def firebase_patch(path, data):
    try:
        response = requests.patch(firebase_url(path), json=data, timeout=10)
        return response.status_code in (200, 201)
    except Exception as e:
        logger.error("Firebase PATCH error: " + str(e))
    return False

def get_user(user_id):
    try:
        data = firebase_get("users/" + str(user_id))
        return data if isinstance(data, dict) else None
    except Exception as e:
        logger.error("get_user error: " + str(e))
    return None

def find_user_by_username(username):
    try:
        username = username.lstrip("@").lower()
        users = firebase_get("users")
        if isinstance(users, dict):
            for uid, udata in users.items():
                if isinstance(udata, dict) and str(udata.get("username", "")).lower() == username:
                    return int(uid), udata
    except Exception as e:
        logger.error("find_user_by_username error: " + str(e))
    return None, None

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
                "created_timestamp": time.time(),
                "video_sent_24h": False,
                "unlocked_apps": {},
                "referral_rewards": {}
            }
            firebase_put("users/" + str(user_id), data)
            return data

        patch = {"username": telegram_user.username or "", "first_name": telegram_user.first_name or "", "last_seen": now, "started": True}
        if referrer_id and int(referrer_id) != user_id and not old.get("referrer_id"):
            patch["referrer_id"] = int(referrer_id)

        firebase_patch("users/" + str(user_id), patch)
        old.update(patch)
        return old
    except Exception as e:
        logger.error("create_user_if_missing error: " + str(e))
    return None

def check_joined_both(user_id):
    try:
        m1 = bot.get_chat_member(CHANNEL_1_USERNAME, int(user_id))
        m2 = bot.get_chat_member(CHANNEL_2_USERNAME, int(user_id))
        ok1 = m1.status in ("member", "administrator", "creator")
        ok2 = m2.status in ("member", "administrator", "creator")
        return ok1 and ok2
    except Exception as e:
        logger.error("check_joined_both error: " + str(e))
    return False

def check_refresh_broadcast(user_id):
    try:
        user = get_user(user_id)
        if user and not user.get(REFRESH_NOTIFIED_KEY, False):
            bot.send_message(
                user_id,
                "🔄 <b>Bot Refresh Update!</b>\n\nAapka bot successfully refresh aur update ho chuka hai! Naye sections, faster speed aur 5-star unlock system ke sath ab aap ise use kar sakte hain 🚀",
                parse_mode="HTML"
            )
            firebase_patch("users/" + str(user_id), {REFRESH_NOTIFIED_KEY: True})
    except Exception as e:
        logger.error("check_refresh_broadcast error: " + str(e))

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

        firebase_patch("users/" + str(referrer_id), {
            "stars": current_stars + 1,
            "referrals": current_refs + 1,
            "referral_rewards/" + str(referred_id): {"rewarded_at": now}
        })

        try:
            bot.send_message(
                int(referrer_id),
                "🎉 <b>New Referral Joined!</b>\n\nAapki link se ek naye user ne join kar liya hai!\n⭐ Aapko <b>+1 Star</b> mil gaya hai! 🚀",
                parse_mode="HTML"
            )
        except Exception:
            pass
    except Exception as e:
        logger.error("reward_referrer_star error: " + str(e))

def send_local_apk(user_id, filename, caption):
    try:
        if os.path.exists(filename):
            with open(filename, "rb") as doc:
                bot.send_document(user_id, doc, caption=caption, parse_mode="HTML")
            return True
        else:
            logger.error("File not found on server: " + filename)
    except Exception as e:
        logger.error("Send local apk error: " + str(e))
    return False

def background_video_worker():
    while True:
        try:
            time.sleep(60)
            users = firebase_get("users")
            if not isinstance(users, dict):
                continue

            current_time = time.time()
            for uid, udata in users.items():
                if not isinstance(udata, dict) or udata.get("video_sent_24h", False):
                    continue
                created_ts = udata.get("created_timestamp", current_time)
                if (current_time - created_ts) >= 86400:
                    video_files = [f for f in os.listdir(".") if f.endswith((".mp4", ".MOV", ".MKV", ".avi"))]
                    if video_files:
                        try:
                            with open(video_files[0], "rb") as vid:
                                bot.send_video(int(uid), vid, caption="🎥 <b>Tutorial / Guide Video</b>\nAapke liye special guide video yahan di gayi hai 👇", parse_mode="HTML")
                            firebase_patch("users/" + str(uid), {"video_sent_24h": True})
                        except Exception:
                            pass
        except Exception as e:
            logger.error("background_video_worker error: " + str(e))

def main_menu_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton("🎱 8 Ball Pool"), types.KeyboardButton("🎱 Carrom Pool"))
    markup.row(types.KeyboardButton("🔥 Free Fire"), types.KeyboardButton("💳 Paid Hack"))
    markup.row(types.KeyboardButton("🔗 My Link"), types.KeyboardButton("👥 My Status"))
    markup.row(types.KeyboardButton("🛡️ Trust Proof"), types.KeyboardButton("🎧 Help & Support"), types.KeyboardButton("🔄 Refresh"), types.KeyboardButton("ℹ️ How it works"))
    return markup

def channels_join_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📢 Join Channel 1 (@novaengine01)", url=CHANNEL_1_LINK))
    markup.add(types.InlineKeyboardButton("📢 Join Channel 2 (@Memonxgamingff)", url=CHANNEL_2_LINK))
    markup.add(types.InlineKeyboardButton("✅ Verify Channels Joined", callback_data="verify_channels"))
    return markup

def get_category_keyboard(cat_key, user_stars, unlocked_dict):
    markup = types.InlineKeyboardMarkup(row_width=1)
    category = GAMES_DATA.get(cat_key, {})
    apps = category.get("apps", [])
    
    for idx, app in enumerate(apps):
        fname = app["filename"]
        is_unlocked = unlocked_dict.get(fname, False)
        if is_unlocked:
            text = "📥 Download " + app['name'] + " (Unlocked ✅)"
            cb = "dl:" + cat_key + ":" + str(idx)
        else:
            text = "🔓 Unlock " + app['name'] + " (Cost: 5 ⭐)"
            cb = "unlock:" + cat_key + ":" + str(idx)
        markup.add(types.InlineKeyboardButton(text, callback_data=cb))
        
    markup.add(types.InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="back_menu"))
    return markup
@bot.message_handler(content_types=['video'])
def handle_video_upload(message):
    try:
        file_id = message.video.file_id
        bot.reply_to(message, "🎥 <b>Tutorial Video Saved Successfully!</b>\nFile ID:\n<code>" + file_id + "</code>", parse_mode="HTML")
    except Exception as e:
        logger.error("Video upload error: " + str(e))

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

        target = random.choice(VERIFICATION_EMOJIS)
        firebase_patch("users/" + str(user_id), {"verification_step": "emoji", "target_emoji": target})

        markup = types.InlineKeyboardMarkup(row_width=5)
        buttons = [types.InlineKeyboardButton(e, callback_data="emoji:" + e) for e in VERIFICATION_EMOJIS]
        random.shuffle(buttons)
        markup.add(*buttons)

        bot.send_message(
            user_id,
            "🤖 <b>Human Verification Required</b>\n\nPlease niche diye gaye emojis me se <b>" + target + "</b> emoji par click karein taaki prove ho sake aap human hain:",
            parse_mode="HTML",
            reply_markup=markup
        )
    except Exception as e:
        logger.error("start_command error: " + str(e))

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
            bot.send_message(user_id, "❌ <b>Wrong Emoji!</b> Sahi emoji select karein: " + target, parse_mode="HTML")
            return

        firebase_patch("users/" + str(user_id), {"verification_step": "channels"})

        bot.send_message(
            user_id,
            "✅ <b>Human Verification Passed!</b>\n\n⚠️ Ab bot ko use karne ke liye hamare <b>dono channels join karna compulsory hai</b>:\n\n1️⃣ <a href='" + CHANNEL_1_LINK + "'>Channel 1 (@novaengine01)</a>\n2️⃣ <a href='" + CHANNEL_2_LINK + "'>Channel 2 (@Memonxgamingff)</a>\n\n👇 Dono join karne ke baad niche button dabayein:",
            parse_mode="HTML",
            reply_markup=channels_join_keyboard(),
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error("emoji_verify_callback error: " + str(e))

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

        firebase_patch("users/" + str(user_id), {"verified": True})
        reward_referrer_star(user_id)

        video_files = [f for f in os.listdir(".") if f.endswith((".mp4", ".MOV", ".MKV", ".avi"))]
        if video_files:
            try:
                with open(video_files[0], "rb") as vid:
                    bot.send_video(user_id, vid, caption="🎥 <b>Welcome Tutorial Video</b>\nAapke liye guide video yahan di gayi hai 👇", parse_mode="HTML")
                firebase_patch("users/" + str(user_id), {"video_sent_24h": True})
            except Exception:
                pass

        bot.send_message(
            user_id,
            "🎉 <b>All Verifications Successful!</b>\n\nAapka account successfully verify ho chuka hai 👇",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard()
        )
    except Exception as e:
        logger.error("verify_channels_callback error: " + str(e))

@bot.callback_query_handler(func=lambda call: call.data == "back_menu")
def back_menu_callback(call):
    try:
        user_id = call.from_user.id
        bot.answer_callback_query(call.id)
        bot.send_message(user_id, "📌 <b>Main Menu:</b>", parse_mode="HTML", reply_markup=main_menu_keyboard())
    except Exception as e:
        logger.error("back_menu_callback error: " + str(e))

@bot.callback_query_handler(func=lambda call: call.data.startswith("unlock:") or call.data.startswith("dl:"))
def app_action_callback(call):
    try:
        user_id = call.from_user.id
        data = call.data
        bot.answer_callback_query(call.id)

        parts = data.split(":")
        action, cat_key, idx_str = parts[0], parts[1], int(parts[2])
        
        user = get_user(user_id)
        if not user:
            return

        is_unlimited = user.get("unlimited_access", False)
        stars = 999999 if is_unlimited else int(user.get("stars", 0))
        
        category = GAMES_DATA.get(cat_key, {})
        apps = category.get("apps", [])
        if idx_str >= len(apps):
            return
            
        app_info = apps[idx_str]
        fname = app_info["filename"]
        unlocked_dict = user.get("unlocked_apps", {})

        if action == "unlock":
            if unlocked_dict.get(fname, False):
                bot.send_message(user_id, "✅ Yeh app pehle se unlocked hai! Niche download button dabayein.")
                return

            if stars < STARS_REQUIRED_PER_APP:
                bot.send_message(
                    user_id,
                    "❌ <b>Insufficient Stars!</b>\n\n⭐ Aapke Stars: <b>" + str(stars) + "</b>\nRequired Stars: <b>5</b> (1 App = 5 Stars)\n\n💡 Aur stars earn karne ke liye apni <b>My Link</b> share karke doston ko invite karein (1 Refer = 1 Star)!",
                    parse_mode="HTML"
                )
                return

            new_stars = stars - STARS_REQUIRED_PER_APP if not is_unlimited else stars
            unlocked_dict[fname] = True

            firebase_patch("users/" + str(user_id), {
                "stars": new_stars,
                "unlocked_apps/" + fname: True
            })

            bot.send_message(
                user_id,
                "🎉 <b>Successfully Unlocked " + app_info['name'] + "!</b>\n\n⭐ Remaining Stars: <b>" + str(new_stars) + "</b>\n\nAb aap iski APK file niche se download kar sakte hain 👇",
                parse_mode="HTML"
            )

            if cat_key == "freefire" and "proxy" in fname.lower():
                sent = send_local_apk(user_id, fname, "📥 <b>" + app_info['name'] + " APK File:</b>")
                if not sent:
                    bot.send_message(user_id, "📥 <b>MediaFire Link:</b>\n👉 " + FREE_FIRE_MEDIAFIRE, parse_mode="HTML", disable_web_page_preview=True)
            elif cat_key == "carrom":
                sent = send_local_apk(user_id, CARROM_FILENAME, "📥 <b>Carrom Aim AI APK File:</b>")
                bot.send_message(user_id, "🔑 <b>Key yahan se generate karein:</b> " + FREE_KEY_BOT, parse_mode="HTML")
            else:
                sent = send_local_apk(user_id, fname, "📥 <b>" + app_info['name'] + " APK File:</b>")
                if not sent:
                    bot.send_message(user_id, "⚠️ File server par nahi mili (`" + fname + "`). GitHub par upload karna na bhulein!")

        elif action == "dl":
            if not unlocked_dict.get(fname, False) and not is_unlimited:
                bot.send_message(user_id, "🔒 Pehle is app ko unlock karne ke liye <b>Unlock</b> button dabayein (Cost: 5 Stars)!", parse_mode="HTML")
                return

            if cat_key == "carrom":
                send_local_apk(user_id, CARROM_FILENAME, "📥 <b>Carrom Aim AI APK File:</b>")
                bot.send_message(user_id, "🔑 <b>Key yahan se generate karein:</b> " + FREE_KEY_BOT, parse_mode="HTML")
            else:
                sent = send_local_apk(user_id, fname, "📥 <b>" + app_info['name'] + " APK File:</b>")
                if not sent:
                    bot.send_message(user_id, "⚠️ File server par nahi mili (`" + fname + "`). GitHub par upload karein.")

        updated_user = get_user(user_id)
        up_stars = 999999 if updated_user.get("unlimited_access", False) else int(updated_user.get("stars", 0))
        up_unlocked = updated_user.get("unlocked_apps", {})
        bot.edit_message_reply_markup(
            chat_id=user_id,
            message_id=call.message.message_id,
            reply_markup=get_category_keyboard(cat_key, up_stars, up_unlocked)
        )
    except Exception as e:
        logger.error("app_action_callback error: " + str(e))

@bot.message_handler(commands=["addstars", "sendstars"])
def add_stars_command(message):
    try:
        user_id = message.from_user.id
        user = get_user(user_id)
        if not user or not user.get("unlimited_access", False):
            bot.reply_to(message, "❌ Aapke pas yeh command use karne ka access nahi hai!")
            return

        parts = message.text.split()
        if len(parts) < 3:
            bot.reply_to(message, "⚠️ Sahi format use karein:\n<code>/addstars @username amount</code> ya <code>/addstars userid amount</code>", parse_mode="HTML")
            return

        target_query = parts[1]
        try:
            amount = int(parts[2])
        except ValueError:
            bot.reply_to(message, "❌ Amount ek number honi chahiye!")
            return

        target_uid = None
        target_data = None

        if target_query.isdigit():
            target_uid = int(target_query)
            target_data = get_user(target_uid)
        else:
            target_uid, target_data = find_user_by_username(target_query)

        if not target_data:
            bot.reply_to(message, "❌ User database me nahi mila!")
            return

        current_stars = int(target_data.get("stars", 0))
        new_stars = current_stars + amount
        firebase_patch("users/" + str(target_uid), {"stars": new_stars})

        bot.reply_to(message, "✅ Successfully user ko <b>" + str(amount) + "</b> stars bhej diye gaye hain!\nNew Total Stars: <b>" + str(new_stars) + "</b>", parse_mode="HTML")
        try:
            bot.send_message(target_uid, "🎁 Admin ki taraf se aapke account me <b>+" + str(amount) + " Stars</b> add kar diye gaye hain! ⭐", parse_mode="HTML")
        except Exception:
            pass
    except Exception as e:
        logger.error("add_stars_command error: " + str(e))

@bot.message_handler(func=lambda message: True)
def handle_menu_actions(message):
    try:
        user_id = message.from_user.id
        text = (message.text or "").strip()
        user = create_user_if_missing(message.from_user)
        check_refresh_broadcast(user_id)

        if text == SECRET_ADMIN_COMMAND:
            firebase_patch("users/" + str(user_id), {"unlimited_access": True, "stars": 999999, "referrals": 999999})
            bot.send_message(user_id, "👑 <b>Admin Unlimited Stars & Access Activated!</b>", parse_mode="HTML", reply_markup=main_menu_keyboard())
            return

        if not user.get("verified", False) or not check_joined_both(user_id):
            bot.send_message(user_id, "⚠️ Pehle verification aur channel join complete karein! Type /start", reply_markup=types.ReplyKeyboardRemove())
            return

        is_unlimited = user.get("unlimited_access", False)
        stars = 999999 if is_unlimited else int(user.get("stars", 0))
        unlocked_dict = user.get("unlocked_apps", {})

        if "8 Ball Pool" in text:
            bot.send_message(
                user_id,
                "🎱 <b>8 Ball Pool Hacks Section</b>\n\n⭐ Aapke Available Stars: <b>" + str(stars) + "</b>\n💡 Har app ko unlock karne ke liye <b>5 Stars</b> lagenge.\n\n👇 Niche diye gaye hacks me se select karein:",
                parse_mode="HTML",
                reply_markup=get_category_keyboard("8bp", stars, unlocked_dict)
            )

        elif "Carrom Pool" in text:
            bot.send_message(
                user_id,
                "🎱 <b>Carrom Pool Hacks Section</b>\n\n⭐ Aapke Available Stars: <b>" + str(stars) + "</b>\n💡 Aim AI tool ko unlock karne ke liye <b>5 Stars</b> lagenge.\n\n🔑 Key yahan se generate kar sakte hain: <b>" + FREE_KEY_BOT + "</b>\n\n👇 Niche click karke unlock/download karein:",
                parse_mode="HTML",
                reply_markup=get_category_keyboard("carrom", stars, unlocked_dict)
            )

        elif "Free Fire" in text:
            bot.send_message(
                user_id,
                "🔥 <b>Free Fire Hacks & Mod Menu Section</b>\n\n⭐ Aapke Available Stars: <b>" + str(stars) + "</b>\n💡 Har ek Free Fire app ko unlock karne ke liye <b>5 Stars</b> lagenge.\n\n👇 Niche apne manpasand mod/proxy ko select karein:",
                parse_mode="HTML",
                reply_markup=get_category_keyboard("freefire", stars, unlocked_dict)
            )

        elif "Paid Hack" in text:
            bot.send_message(
                user_id,
                "💳 <b>PAID HACK DIRECT PURCHASE</b> 👑\n\nAap direct paid hack kharidne ke liye owner se direct contact kar sakte hain:\n• Telegram Owner: <b>" + OWNER_CONTACT + "</b>\n• WhatsApp: " + WHATSAPP_NUMBER,
                parse_mode="HTML",
                reply_markup=main_menu_keyboard()
            )

        elif "My Link" in text:
            link = "https://t.me/" + BOT_USERNAME + "?start=" + str(user_id)
            bot.send_message(
                user_id,
                "🔗 <b>Aapki Personal Referral Link:</b>\n\n<code>" + link + "</code>\n\n👥 Is link ko doston ke sath share karein!\nHar ek naye user ke join karne par aapko milega <b>+1 Star</b> ⭐",
                parse_mode="HTML",
                reply_markup=main_menu_keyboard()
            )

        elif "My Status" in text:
            current_stars = 999999 if user.get("unlimited_access", False) else int(user.get("stars", 0))
            refs = user.get("referrals", 0)
            bot.send_message(
                user_id,
                "👥 <b>Aapka Status & Referrals</b>\n\n👤 Total Referrals: <b>" + str(refs) + "</b>\n⭐ Total Available Stars: <b>" + str(current_stars) + "</b>\n\n💡 <i>Har ek app ko unlock karne ke liye sirf 5 Stars lagte hain. Doston ko invite karke stars earn karein!</i>",
                parse_mode="HTML",
                reply_markup=main_menu_keyboard()
            )

        elif "Trust Proof" in text:
            bot.send_message(
                user_id,
                "🛡️ <b>Trust Proof Channel</b>\n\nCustomer proofs aur successful deals yahan check karein:\n👉 " + TRUST_PROOF_LINK,
                parse_mode="HTML",
                reply_markup=main_menu_keyboard(),
                disable_web_page_preview=True
            )

        elif "Help & Support" in text:
            bot.send_message(
                user_id,
                "🎧 <b>Help & Support Center</b>\n\nAapko koi bhi problem aa rahi ho ya key/APK me issue ho, toh aap seedha owner se contact kar sakte hain:\n\n👉 <b>Telegram Support:</b> " + OWNER_CONTACT + "\n👉 <b>WhatsApp Support:</b> " + WHATSAPP_NUMBER,
                parse_mode="HTML",
                reply_markup=main_menu_keyboard()
            )

        elif "How it works" in text:
            bot.send_message(
                user_id,
                "📖 <b>How It Works (Aasan Bhasha Me)</b>\n\n1️⃣ Sabse pehle bot start karke Human Verification (Emoji select) aur hamare <b>dono Telegram channels join karna compulsory hai</b>.\n2️⃣ Verification ke baad aapko Main Menu dikhega jisme <b>8 Ball Pool, Carrom Pool, aur Free Fire</b> ke alag-alag hacking sections milenge.\n3️⃣ Kisi bhi app ko unlock karne ke liye <b>5 Stars</b> ki zarurat hoti hai (1 App = 5 Stars).\n4️⃣ Stars earn karne ke liye <b>My Link</b> par click karke apni referral link doston ko share karein (Har ek refer par +1 Star milta hai).\n5️⃣ Jaise hi aapke pas 5 ya usse zyada stars ho jayein, aap <b>Unlock</b> button dabakar app ki APK file turant download kar sakte hain! 🚀",
                parse_mode="HTML",
                reply_markup=main_menu_keyboard()
            )

        elif "Refresh" in text:
            current_stars = 999999 if user.get("unlimited_access", False) else int(user.get("stars", 0))
            refs = user.get("referrals", 0)
            bot.send_message(
                user_id,
                "🔄 <b>Bot Refreshed Successfully!</b>\n\n👥 Total Referrals: <b>" + str(refs) + "</b>\n⭐ Available Stars: <b>" + str(current_stars) + "</b>\n\nAapka menu updated aur active hai. Sabhi features fully functional hain!",
                parse_mode="HTML",
                reply_markup=main_menu_keyboard()
            )
    except Exception as e:
        logger.error("handle_menu_actions error: " + str(e))

def load_bot_username():
    try:
        global BOT_USERNAME
        me = bot.get_me()
        if me and me.username:
            BOT_USERNAME = me.username
    except Exception as e:
        logger.error("Could not load bot username: " + str(e))

def start_bot():
    while True:
        try:
            bot.remove_webhook()
            bot.infinity_polling(timeout=30, long_polling_timeout=30, skip_pending=True)
        except Exception as e:
            logger.error("Polling crashed: " + str(e))
            time.sleep(5)

if __name__ == "__main__":
    try:
        threading.Thread(target=run_web_server, daemon=True).start()
        threading.Thread(target=background_video_worker, daemon=True).start()
        time.sleep(2)
        load_bot_username()
        start_bot()
    except Exception as e:
        logger.error("Main execution error: " + str(e))
        
