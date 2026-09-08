import telebot
from telebot import types
import sqlite3
import random
import string
import requests
import datetime
import os
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- CONFIGURATION ---
API_TOKEN = '8803139822:AAFNCLWVAnTGD3g3jg7aNDATiTSRiMAqGMo'
CHANNEL_USERNAME = '@novaengine01'
CHANNEL_LINK = 'https://t.me/novaengine01'

# Aapke Injector App ka Firebase
FIREBASE_URL = 'https://aimai-817ef-default-rtdb.asia-southeast1.firebasedatabase.app'
FIREBASE_AUTH = 'V677nUiq24iMv58OcV02CXyE7iHFqFbke4VVPdmL'

# Aapki APK file ka path
APK_FILE_NAME = 'app.apk'

bot = telebot.TeleBot(API_TOKEN)
session = requests.Session()

# --- DATABASE SETUP ---
conn = sqlite3.connect('referral_bot.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    points INTEGER DEFAULT 0,
    referrer_id INTEGER DEFAULT NULL,
    is_verified INTEGER DEFAULT 0
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS user_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    key_value TEXT,
    plan_days INTEGER,
    created_at TEXT
)''')
conn.commit()

chars = string.ascii_uppercase + string.digits
def generate_random_key():
    return "DP-" + ''.join(random.choices(chars, k=6))

def save_key_to_firebase(key_name, days):
    payload = {
        "user": key_name,
        "days": str(days),
        "status": "active",
        "devices": "1",
        "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    url = f"{FIREBASE_URL}/user/{key_name}.json?auth={FIREBASE_AUTH}"
    try:
        res = session.put(url, json=payload, timeout=5)
        return res.status_code == 200
    except Exception as e:
        print("Firebase Error:", e)
        return False

def check_joined(user_id):
    try:
        member = bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ['creator', 'administrator', 'member']
    except Exception:
        return True

def get_main_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(types.KeyboardButton("🎁 Generate Key"), types.KeyboardButton("🔗 My Link"))
    kb.row(types.KeyboardButton("👥 Referrals"), types.KeyboardButton("🔑 My Keys"))
    kb.row(types.KeyboardButton("🔄 Refresh"), types.KeyboardButton("ℹ️ How it works"))
    return kb

def send_dashboard(chat_id, user_id):
    try:
        bot_info = bot.get_me()
        cursor.execute("SELECT points FROM users WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        points = res[0] if res else 0

        cursor.execute("SELECT COUNT(*) FROM users WHERE referrer_id = ? AND is_verified = 1", (user_id,))
        total_refs = cursor.fetchone()[0]

        ref_link = f"https://t.me/{bot_info.username}?start={user_id}"

        text = (
            f"🏆 <b>Aapka Rewards Dashboard</b>\n\n"
            f"⭐ Total Points: <b>{points}</b>\n"
            f"👥 Verified Referrals: <b>{total_refs}</b>\n\n"
            f"👇🏻 <b>Aapki Referral Link (Tap karke Copy karein):</b>\n"
            f"<code>{ref_link}</code>\n\n"
            f"📢 Is link ko doston ke sath share karein. Har ek dost ke join aur verify hone par <b>+1 Point</b> milega."
        )
        bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=get_main_keyboard())
    except Exception as e:
        print("Dashboard error:", e)

# --- START COMMAND ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id
    parts = message.text.split()
    args = parts[1] if len(parts) > 1 else ""

    cursor.execute("SELECT is_verified, referrer_id FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()

    if not user:
        ref_by = int(args) if args.isdigit() and int(args) != user_id else None
        cursor.execute("INSERT INTO users (user_id, referrer_id) VALUES (?, ?)", (user_id, ref_by))
        conn.commit()
        is_verified = 0
    else:
        is_verified = user[0]

    if not is_verified:
        if not check_joined(user_id):
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK))
            kb.add(types.InlineKeyboardButton("✅ Verify / Check", callback_data="check_join"))
            bot.reply_to(message, f"⚠️ Bot use karne ke liye pehle official channel join karein:\n{CHANNEL_LINK}", reply_markup=kb)
            return

        cursor.execute("UPDATE users SET is_verified = 1 WHERE user_id = ?", (user_id,))
        ref_by = user[1] if user else None
        if ref_by:
            cursor.execute("UPDATE users SET points = points + 1 WHERE user_id = ?", (ref_by,))
            try:
                bot.send_message(ref_by, "🎉 Badhai ho! Ek naye dost ne aapki link se join kiya. Aapko +1 point mila.")
            except:
                pass
        conn.commit()

    send_dashboard(message.chat.id, user_id)

# --- VERIFY CALLBACK ---
@bot.callback_query_handler(func=lambda call: call.data == 'check_join')
def verify_callback(call):
    user_id = call.from_user.id
    if check_joined(user_id):
        cursor.execute("SELECT is_verified, referrer_id FROM users WHERE user_id = ?", (user_id,))
        u_data = cursor.fetchone()
        if u_data and u_data[0] == 0:
            cursor.execute("UPDATE users SET is_verified = 1 WHERE user_id = ?", (user_id,))
            if u_data[1]:
                cursor.execute("UPDATE users SET points = points + 1 WHERE user_id = ?", (u_data[1],))
                try:
                    bot.send_message(u_data[1], "🎉 Badhai ho! Ek naye dost ne aapki link se join kiya. Aapko +1 point mila.")
                except:
                    pass
            conn.commit()
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        send_dashboard(call.message.chat.id, user_id)
    else:
        bot.answer_callback_query(call.id, "❌ Aapne abhi tak channel join nahi kiya! Pehle join karein.", show_alert=True)

# --- BUTTON HANDLERS ---
@bot.message_handler(func=lambda m: True)
def handle_menu_buttons(message):
    user_id = message.from_user.id
    txt = (message.text or "").strip()

    # 1. GENERATE KEY BUTTON
    if "Generate Key" in txt:
        cursor.execute("SELECT points FROM users WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        user_points = res[0] if res else 0

        if user_points < 3:
            bot_info = bot.get_me()
            ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
            
            warning_msg = (
                f"❌ <b>Aapke paas key generate karne ke liye poore points nahi hain!</b>\n\n"
                f"⭐ Aapke Total Points: <b>{user_points}</b>\n"
                f"🎯 Minimum Chahiye: <b>3 Points</b> (1 Day VIP Key ke liye)\n\n"
                f"👇🏻 <b>Aapki Referral Link (Tap karke Copy karein):</b>\n"
                f"<code>{ref_link}</code>\n\n"
                f"💡 <i>Is link ko doston ko share karein. Jaise hi 3 points ho jayenge, aap key generate kar sakenge.</i>"
            )
            bot.send_message(message.chat.id, warning_msg, parse_mode="HTML")
            return

        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(
            types.InlineKeyboardButton("1 Day (3 pts)", callback_data="claim_1"),
            types.InlineKeyboardButton("3 Days (6 pts)", callback_data="claim_3"),
            types.InlineKeyboardButton("7 Days (10 pts)", callback_data="claim_7"),
            types.InlineKeyboardButton("30 Days (25 pts)", callback_data="claim_30")
        )
        bot.send_message(message.chat.id, f"⭐ Aapke Paas: <b>{user_points} Points</b>\nNeeche se apna validity plan select karein:", parse_mode="HTML", reply_markup=kb)
        return

    # 2. HOW IT WORKS
    if "How it works" in txt:
        bot_info = bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start={user_id}"

        guide_text = (
            "📖 <b>Bot Kaise Kaam Karta Hai? (Aasan Guide)</b>\n\n"
            "<b>1️⃣ Points Kaise Kamayein?</b>\n"
            "• Apni referral link apne doston ko share karein.\n"
            "• Jab aapka dost channel join karega, aapko <b>+1 Point</b> milega.\n\n"
            "<b>2️⃣ VIP Key Points:</b>\n"
            "• 1 Day Key = <b>3 Points</b>\n"
            "• 3 Days Key = <b>6 Points</b>\n"
            "• 7 Days Key = <b>10 Points</b>\n"
            "• 30 Days Key = <b>25 Points</b>\n\n"
            "<b>3️⃣ App Me Login Kaise Karein?</b>\n"
            "• Key generate hone par bot aapko APK file aur Key dega.\n"
            "• App open karein, <b>Username</b> me wahi Key dalein aur <b>Password</b> me bhi wahi Key dalein!\n\n"
            "👇🏻 <b>Aapki Referral Link (Tap karke Copy karein):</b>\n"
            f"<code>{ref_link}</code>"
        )
        bot.send_message(message.chat.id, guide_text, parse_mode="HTML")
        return

    # 3. MY KEYS BUTTON
    if "My Keys" in txt:
        cursor.execute("SELECT COUNT(*) FROM users WHERE referrer_id = ? AND is_verified = 1", (user_id,))
        total_refs = cursor.fetchone()[0]

        cursor.execute("SELECT key_value, plan_days, created_at FROM user_keys WHERE user_id = ? ORDER BY id DESC LIMIT 10", (user_id,))
        rows = cursor.fetchall()

        if not rows:
            bot.send_message(
                message.chat.id, 
                f"📊 <b>Aapke Total Referrals:</b> {total_refs}\n\n"
                f"❌ Aapne abhi tak koi key generate nahi ki hai.\n"
                f"Points collect karne ke baad <b>🎁 Generate Key</b> par tap karein.", 
                parse_mode="HTML"
            )
            return

        keys_list = ""
        for idx, r in enumerate(rows, 1):
            keys_list += f"{idx}. Key: <code>{r[0]}</code>\n   Plan: <b>{r[1]} Days</b> | Date: {r[2]}\n\n"

        msg = (
            f"🔑 <b>Aapki Generated Keys:</b>\n"
            f"👥 <b>Total Verified Referrals:</b> {total_refs}\n\n"
            f"{keys_list}"
            f"⚠️ <i>Login note: App me <b>Username</b> aur <b>Password</b> dono jagah ye Key hi daalni hai.</i>"
        )
        bot.send_message(message.chat.id, msg, parse_mode="HTML")
        return

    # 4. REFRESH / MY LINK / REFERRALS
    if any(k in txt for k in ["Refresh", "My Link", "Referrals"]):
        send_dashboard(message.chat.id, user_id)
        return

# --- KEY CLAIM & DIRECT APK FILE SEND ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('claim_'))
def process_claim(call):
    days = int(call.data.split('_')[1])
    costs = {1: 3, 3: 6, 7: 10, 30: 25}
    req_points = costs.get(days, 3)
    user_id = call.from_user.id

    cursor.execute("SELECT points FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    points = res[0] if res else 0

    if points < req_points:
        bot.answer_callback_query(call.id, f"❌ Points kam hain! Chahiye: {req_points} Points (Aapke paas hain: {points})", show_alert=True)
        return

    new_key = generate_random_key()
    saved = save_key_to_firebase(new_key, days)

    if not saved:
        bot.answer_callback_query(call.id, "⚠️ Database connection error, dobara try karein!", show_alert=True)
        return

    cursor.execute("UPDATE users SET points = points - ? WHERE user_id = ?", (req_points, user_id))
    now_str = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
    cursor.execute("INSERT INTO user_keys (user_id, key_value, plan_days, created_at) VALUES (?, ?, ?, ?)", (user_id, new_key, days, now_str))
    conn.commit()

    reply_text = (
        f"🎉 <b>VIP Key Successfully Generate Ho Gayi!</b>\n\n"
        f"📅 Validity: <b>{days} Days</b>\n\n"
        f"👇🏻 <b>Aapki Key (Tap karke Copy karein):</b>\n"
        f"<code>{new_key}</code>\n\n"
        f"📝 <b>App Login Instruction:</b>\n"
        f"• <b>Username:</b> <code>{new_key}</code>\n"
        f"• <b>Password:</b> <code>{new_key}</code>\n\n"
        f"<i>(Dono jagah yahi same key paste karke Login karein)</i>\n\n"
        f"📦 <i>Neeche aapki App APK file bheji ja rahi hai...</i>"
    )
    bot.send_message(call.message.chat.id, reply_text, parse_mode="HTML")
    bot.answer_callback_query(call.id)

    if os.path.exists(APK_FILE_NAME):
        try:
            with open(APK_FILE_NAME, 'rb') as apk:
                bot.send_document(
                    call.message.chat.id, 
                    apk, 
                    caption=f"📲 <b>Carrom VIP Injector App</b>\n🔑 Key: <code>{new_key}</code>", 
                    parse_mode="HTML"
                )
        except Exception as e:
            print("File sending error:", e)
    else:
        bot.send_message(call.message.chat.id, f"📥 App Download karein: {CHANNEL_LINK}")

# --- RENDER WEB SERVER (DUMMY PORT FOR 24/7 HOSTING) ---
class SimpleServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Running 24/7!")

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleServer)
    server.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()

print("⚡ Bot 24/7 chalne ke liye ready hai...")
bot.remove_webhook()

while True:
    try:
        bot.polling(none_stop=True, timeout=60, long_polling_timeout=30)
    except requests.exceptions.ReadTimeout:
        time.sleep(2)
    except Exception as e:
        time.sleep(3)
      
