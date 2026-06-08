import asyncio
import sqlite3
import random
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web

# ===================== SOZLAMALAR =====================
BOT_TOKEN = "8999661868:AAG5VZzo-_xCH8AjN9EvwNATVdc6WGUlMuM"

# 2 TA KANAL
CHANNELS = [
    {
        "id": "@odzif12345",
        "name": "ODIZV KANALI",
        "link": "https://t.me/odzif12345",
        "type": "public"
    },
    {
        "id": "@razee_sell",
        "name": "RAZEE SELL",
        "link": "https://t.me/razee_sell",
        "type": "public"
    },
]

ADMIN_ID = 7928569939
REFERRAL_BONUS = 60
MIN_WITHDRAW = 720

# Baraban yutuqlari (UC)
SPIN_REWARDS = {
    20: 40,   # 20 UC - 40% ehtimol
    30: 25,   # 30 UC - 25% ehtimol
    15: 25,   # 15 UC - 25% ehtimol
    50: 7,    # 50 UC - 7% ehtimol
    100: 2.5, # 100 UC - 2.5% ehtimol
    200: 0.5, # 200 UC - 0.5% ehtimol
}
# ======================================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ===================== DATABASE =====================
def init_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    # Foydalanuvchilar jadvali
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            balance INTEGER DEFAULT 0,
            total_earned INTEGER DEFAULT 0,
            referrer_id INTEGER,
            ref_count INTEGER DEFAULT 0,
            last_spin TEXT,
            promo_used INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def add_user(user_id, username, full_name, referrer_id=None):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, full_name, referrer_id) VALUES (?, ?, ?, ?)",
              (user_id, username, full_name, referrer_id))
    conn.commit()
    conn.close()
    if referrer_id:
        update_balance(referrer_id, REFERRAL_BONUS)
        update_total_earned(referrer_id, REFERRAL_BONUS)
        update_ref_count(referrer_id)

def get_user(user_id):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row

def update_balance(user_id, amount):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()

def update_total_earned(user_id, amount):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET total_earned = total_earned + ? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()

def get_balance(user_id):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

def update_ref_count(user_id):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET ref_count = ref_count + 1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def get_ref_count(user_id):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT ref_count FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

def get_total_earned(user_id):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT total_earned FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

def get_last_spin(user_id):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT last_spin FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def update_last_spin(user_id):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET last_spin = ? WHERE user_id=?", (datetime.now().isoformat(), user_id))
    conn.commit()
    conn.close()

def can_spin(user_id):
    last_spin = get_last_spin(user_id)
    if not last_spin:
        return True
    last_spin_time = datetime.fromisoformat(last_spin)
    return datetime.now() - last_spin_time >= timedelta(hours=24)

def get_spin_reward():
    """Baraban aylantirish: ehtimollik asosida yutuq tanlaydi"""
    rand = random.uniform(0, 100)
    cumulative = 0
    for amount, chance in SPIN_REWARDS.items():
        cumulative += chance
        if rand <= cumulative:
            return amount
    return 20

def has_used_promo(user_id):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT promo_used FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] == 1 if row else False

def set_promo_used(user_id):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET promo_used = 1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def get_top_referrers(limit=10):
    """Eng ko'p referal taklif qilganlar"""
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("""
        SELECT user_id, username, full_name, ref_count 
        FROM users 
        WHERE ref_count > 0 
        ORDER BY ref_count DESC 
        LIMIT ?
    """, (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_top_earners(limit=10):
    """Eng ko'p UC ishlaganlar"""
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("""
        SELECT user_id, username, full_name, total_earned 
        FROM users 
        WHERE total_earned > 0 
        ORDER BY total_earned DESC 
        LIMIT ?
    """, (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

# ===================== OBUNA TEKSHIRISH =====================
async def check_subscription(user_id):
    for channel in CHANNELS:
        try:
            channel_id = channel["id"]
            channel_name = channel["name"]
            
            if channel_id.startswith("@"):
                member = await bot.get_chat_member(channel_id, user_id)
            else:
                member = await bot.get_chat_member(channel_id, user_id)
            
            if member.status not in ['member', 'creator', 'administrator']:
                print(f"❌ {channel_name} ga obuna emas")
                return False
            else:
                print(f"✅ {channel_name} ga obuna: {member.status}")
                
        except Exception as e:
            print(f"⚠️ {channel_name} tekshirish xatosi: {e}")
            return False
    
    return True

def get_subscription_keyboard():
    buttons = []
    for channel in CHANNELS:
        buttons.append([InlineKeyboardButton(
            text=f"📢 {channel['name']} ga obuna bo'lish",
            url=channel["link"]
        )])
    
    buttons.append([InlineKeyboardButton(
        text="✅ Obunani tekshirish",
        callback_data="check_sub"
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ===================== MENU =====================
def get_main_menu():
    keyboard = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="💰 Balans"), KeyboardButton(text="💸 UC Yechish")],
        [KeyboardButton(text="👥 Referal UC"), KeyboardButton(text="🎡 Baraban")],
        [KeyboardButton(text="🏆 Top Reyting"), KeyboardButton(text="📋 Qoidalar")],
        [KeyboardButton(text="📞 Murojat")]
    ], resize_keyboard=True)
    return keyboard

# ===================== WEB SERVER =====================
async def health_check(request):
    return web.Response(text="Bot is running!", status=200)

async def start_web_server():
    app = web.Application()
    app.router.add_get('/health', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    print("✅ Web server started on port 8080")

# ===================== HANDLERLAR =====================
class WithdrawState(StatesGroup):
    waiting_for_id = State()

@dp.message(CommandStart())
async def start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    full_name = message.from_user.full_name
    
    args = message.text.split()
    referrer_id = None
    if len(args) > 1 and args[1].isdigit():
        referrer_id = int(args[1])
        if referrer_id == user_id:
            referrer_id = None
    
    print(f"📝 Foydalanuvchi: {user_id}")
    
    if not await check_subscription(user_id):
        channels_text = "\n".join([f"• {ch['name']}" for ch in CHANNELS])
        
        await message.answer(
            f"⚠️ <b>Botdan foydalanish uchun kanallarga obuna bo'ling!</b>\n\n"
            f"📢 Kerakli kanallar:\n{channels_text}\n\n"
            f"👇 Obuna bo'lgach, <b>✅ Obunani tekshirish</b> tugmasini bosing.",
            parse_mode="HTML",
            reply_markup=get_subscription_keyboard()
        )
        return
    
    if not get_user(user_id):
        add_user(user_id, username, full_name, referrer_id)
        if referrer_id:
            try:
                await bot.send_message(referrer_id, f"🎉 Referal orqali +{REFERRAL_BONUS} UC qo'shildi!")
            except:
                pass
    
    await message.answer(
        f"✅ <b>Xush kelibsiz, {message.from_user.first_name}!</b>\n\n"
        f"💰 Balans: <b>{get_balance(user_id)} UC</b>\n"
        f"💸 Yechish uchun minimal: <b>{MIN_WITHDRAW} UC</b>\n\n"
        f"🎡 Har kuni baraban aylantirib UC yutib oling!\n"
        f"🏆 Top reytingda kimlar yetakchi ekanligini ko'ring!\n\n"
        f"👇 Quyidagi menyudan foydalaning:",
        parse_mode="HTML",
        reply_markup=get_main_menu()
    )

@dp.callback_query(F.data == "check_sub")
async def check_subscription_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    print(f"🔍 Obuna tekshirilmoqda: {user_id}")
    
    if not await check_subscription(user_id):
        await callback.answer("❌ Siz hali barcha kanallarga obuna bo'lmadingiz!", show_alert=True)
        return
    
    if not get_user(user_id):
        add_user(user_id, callback.from_user.username or "", callback.from_user.full_name, None)
    
    await callback.message.delete()
    await callback.message.answer(
        f"✅ <b>Tabriklaymiz!</b>\n\n"
        f"Siz barcha kanallarga obuna bo'ldingiz!\n"
        f"💰 Balans: <b>{get_balance(user_id)} UC</b>\n\n"
        f"🎡 Baraban aylantirish uchun <b>🎡 Baraban</b> tugmasini bosing!",
        parse_mode="HTML",
        reply_markup=get_main_menu()
    )
    await callback.answer("✅ Obuna tasdiqlandi!")

# ===================== BALANS =====================
@dp.message(F.text == "💰 Balans")
async def show_balance(message: types.Message):
    user_id = message.from_user.id
    
    if not await check_subscription(user_id):
        await message.answer(
            "⚠️ Iltimos, kanallarga obuna bo'ling!",
            reply_markup=get_subscription_keyboard()
        )
        return
    
    balance = get_balance(user_id)
    total_earned = get_total_earned(user_id)
    ref_count = get_ref_count(user_id)
    
    await message.answer(
        f"💰 <b>Sizning balansingiz</b>\n\n"
        f"💎 Joriy balans: <b>{balance} UC</b>\n"
        f"📈 Jami ishlagan: <b>{total_earned} UC</b>\n"
        f"👥 Referallar: <b>{ref_count} ta</b>\n"
        f"🎁 Referaldan daromad: <b>{ref_count * REFERRAL_BONUS} UC</b>\n\n"
        f"💸 Yechish uchun minimal: <b>{MIN_WITHDRAW} UC</b>",
        parse_mode="HTML",
        reply_markup=get_main_menu()
    )

# ===================== YECHISH =====================
@dp.message(F.text == "💸 UC Yechish")
async def withdraw(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    if not await check_subscription(user_id):
        await message.answer(
            "⚠️ Iltimos, kanallarga obuna bo'ling!",
            reply_markup=get_subscription_keyboard()
        )
        return
    
    balance = get_balance(user_id)
    
    if balance < MIN_WITHDRAW:
        await message.answer(
            f"❌ <b>Yechish uchun balans yetarli emas!</b>\n\n"
            f"💰 Balans: <b>{balance} UC</b>\n"
            f"📌 Minimal yechish: <b>{MIN_WITHDRAW} UC</b>\n\n"
            f"💡 Do'stlaringizni taklif qiling yoki baraban aylantiring!",
            parse_mode="HTML",
            reply_markup=get_main_menu()
        )
        return
    
    await message.answer(
        f"💸 <b>UC Yechish</b>\n\n"
        f"💰 Balans: <b>{balance} UC</b>\n"
        f"📌 Yechiladigan miqdor: <b>{balance} UC</b>\n\n"
        f"📝 O'yin ID raqamingizni kiriting:",
        parse_mode="HTML"
    )
    await state.set_state(WithdrawState.waiting_for_id)

@dp.message(WithdrawState.waiting_for_id)
async def process_withdraw(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    game_id = message.text.strip()
    
    if not game_id.isdigit():
        await message.answer("❌ Noto'g'ri ID! Faqat raqam kiriting:")
        return
    
    balance = get_balance(user_id)
    
    if balance < MIN_WITHDRAW:
        await message.answer("❌ Balans yetarli emas!", reply_markup=get_main_menu())
        await state.clear()
        return
    
    update_balance(user_id, -balance)
    await state.clear()
    
    await message.answer(
        f"✅ <b>So'rovingiz qabul qilindi!</b>\n\n"
        f"🎮 O'yin ID: <b>{game_id}</b>\n"
        f"💎 Yechilgan summa: <b>{balance} UC</b>\n\n"
        f"⏰ <b>24 soat ichida</b> hisobingizga o'tkaziladi!\n"
        f"📞 Muammo bo'lsa: @vrxszd",
        parse_mode="HTML",
        reply_markup=get_main_menu()
    )
    
    try:
        await bot.send_message(
            ADMIN_ID,
            f"💸 <b>YANGI YECHISH SO'ROVI</b>\n\n"
            f"👤 Foydalanuvchi: {message.from_user.full_name}\n"
            f"📝 Username: @{message.from_user.username}\n"
            f"🆔 Telegram ID: {user_id}\n"
            f"🎮 O'yin ID: {game_id}\n"
            f"💎 Miqdor: {balance} UC",
            parse_mode="HTML"
        )
    except:
        pass

# ===================== REFERAL UC =====================
@dp.message(F.text == "👥 Referal UC")
async def show_referral(message: types.Message):
    user_id = message.from_user.id
    
    if not await check_subscription(user_id):
        await message.answer(
            "⚠️ Iltimos, kanallarga obuna bo'ling!",
            reply_markup=get_subscription_keyboard()
        )
        return
    
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
    ref_count = get_ref_count(user_id)
    
    await message.answer(
        f"👥 <b>Referal Tizimi</b>\n\n"
        f"🔗 <b>Sizning havolangiz:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        f"📊 <b>Statistika:</b>\n"
        f"👥 Taklif qilganlar: <b>{ref_count} ta</b>\n"
        f"💰 Jami daromad: <b>{ref_count * REFERRAL_BONUS} UC</b>\n\n"
        f"🎁 <b>Qanday ishlaydi?</b>\n"
        f"1️⃣ Havolani do'stingizga yuboring\n"
        f"2️⃣ U kanallarga obuna bo'lsin\n"
        f"3️⃣ Siz <b>+{REFERRAL_BONUS} UC</b> olasiz!\n\n"
        f"📌 Cheklovsiz taklif qilishingiz mumkin!",
        parse_mode="HTML",
        reply_markup=get_main_menu()
    )

# ===================== BARABAN =====================
@dp.message(F.text == "🎡 Baraban")
async def spin_wheel(message: types.Message):
    user_id = message.from_user.id
    
    if not await check_subscription(user_id):
        await message.answer(
            "⚠️ Iltimos, kanallarga obuna bo'ling!",
            reply_markup=get_subscription_keyboard()
        )
        return
    
    if not can_spin(user_id):
        last_spin = get_last_spin(user_id)
        last_spin_time = datetime.fromisoformat(last_spin)
        next_spin_time = last_spin_time + timedelta(hours=24)
        remaining = next_spin_time - datetime.now()
        hours = remaining.seconds // 3600
        minutes = (remaining.seconds % 3600) // 60
        
        await message.answer(
            f"⏰ <b>Baraban hali tayyor emas!</b>\n\n"
            f"Keyingi aylantirish: <b>{hours} soat {minutes} daqiqa</b> qoldi\n\n"
            f"🎡 Har <b>24 soatda 1 marta</b> aylantira olasiz!",
            parse_mode="HTML",
            reply_markup=get_main_menu()
        )
        return
    
    # Baraban aylantirish
    reward = get_spin_reward()
    update_balance(user_id, reward)
    update_total_earned(user_id, reward)
    update_last_spin(user_id)
    
    # Animatsiya effekti
    msg = await message.answer("🎡 <b>Baraban aylanyapti...</b> 🎡\n\n⏳ Iltimos kuting...", parse_mode="HTML")
    await asyncio.sleep(1.5)
    
    # Natijani ko'rsatish
    await msg.edit_text(
        f"🎉 <b>BARABAN NATIJASI!</b> 🎉\n\n"
        f"💰 Siz <b>{reward} UC</b> yutdingiz!\n\n"
        f"💎 Yangi balans: <b>{get_balance(user_id)} UC</b>\n"
        f"📈 Jami ishlagan: <b>{get_total_earned(user_id)} UC</b>\n\n"
        f"🎡 Keyingi aylantirish <b>24 soatdan keyin</b> mumkin!",
        parse_mode="HTML",
        reply_markup=get_main_menu()
    )

# ===================== TOP REYTING =====================
@dp.message(F.text == "🏆 Top Reyting")
async def show_top_rating(message: types.Message):
    user_id = message.from_user.id
    
    if not await check_subscription(user_id):
        await message.answer(
            "⚠️ Iltimos, kanallarga obuna bo'ling!",
            reply_markup=get_subscription_keyboard()
        )
        return
    
    top_referrers = get_top_referrers(10)
    top_earners = get_top_earners(10)
    
    # Top referallar
    referrer_text = "<b>👥 ENG KO'P TAKLIF QILGANLAR</b>\n\n"
    if top_referrers:
        for i, (uid, username, full_name, count) in enumerate(top_referrers, 1):
            name = full_name if full_name else username or f"User {uid}"
            if len(name) > 20:
                name = name[:18] + "..."
            referrer_text += f"{i}. {name} – <b>{count}</b> ta\n"
    else:
        referrer_text += "Hali hech kim taklif qilmagan\n"
    
    # Top ishlaganlar
    earner_text = "\n\n<b>💰 ENG KO'P UC ISHLAGANLAR</b>\n\n"
    if top_earners:
        for i, (uid, username, full_name, earned) in enumerate(top_earners, 1):
            name = full_name if full_name else username or f"User {uid}"
            if len(name) > 20:
                name = name[:18] + "..."
            earner_text += f"{i}. {name} – <b>{earned}</b> UC\n"
    else:
        earner_text += "Hali hech kim UC ishlamagan\n"
    
    await message.answer(
        f"🏆 <b>TOP REYTING</b>\n\n"
        f"{referrer_text}{earner_text}\n\n"
        f"🎡 Baraban aylantirib va do'stlaringizni taklif qilib\n"
        f"🏆 TOP reytingga kiring!",
        parse_mode="HTML",
        reply_markup=get_main_menu()
    )

# ===================== PROMO KOD (FAQAT ADMIN) =====================
@dp.message(Command("promo"))
async def admin_promo(message: types.Message):
    """Faqat admin promo kod berishi mumkin: /promo user_id amount"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Bu buyruq faqat admin uchun!")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.answer("❗ Ishlatish: /promo user_id amount\n\nMisol: /promo 123456789 120")
        return
    
    try:
        target_user = int(args[1])
        amount = int(args[2])
        
        update_balance(target_user, amount)
        update_total_earned(target_user, amount)
        
        await message.answer(f"✅ Foydalanuvchi {target_user} ga {amount} UC berildi!")
        
        try:
            await bot.send_message(target_user, f"🎁 <b>PROMO KOD!</b>\n\nSizga <b>{amount} UC</b> qo'shildi!\n💰 Yangi balans: <b>{get_balance(target_user)} UC</b>", parse_mode="HTML")
        except:
            pass
    except:
        await message.answer("❌ Xato! To'g'ri formatda yozing: /promo user_id amount")

# ===================== QOIDALAR =====================
@dp.message(F.text == "📋 Qoidalar")
async def show_rules(message: types.Message):
    await message.answer(
        f"📋 <b>Bot Qoidalari</b>\n\n"
        f"1️⃣ <b>Referal UC:</b>\n"
        f"   • Har bir taklif uchun <b>+{REFERRAL_BONUS} UC</b>\n"
        f"   • Cheklovsiz taklif qila olasiz\n\n"
        f"2️⃣ <b>Yechish:</b>\n"
        f"   • Minimal yechish: <b>{MIN_WITHDRAW} UC</b>\n"
        f"   • Yechimlar <b>24 soat</b> ichida amalga oshiriladi\n\n"
        f"3️⃣ <b>Baraban:</b>\n"
        f"   • Har <b>24 soatda 1 marta</b> aylantirish mumkin\n"
        f"   • Yutuqlar: 15, 20, 30, 50, 100, 200 UC\n\n"
        f"4️⃣ <b>Top Reyting:</b>\n"
        f"   • Eng ko'p taklif qilganlar\n"
        f"   • Eng ko'p UC ishlaganlar\n\n"
        f"5️⃣ <b>Majburiy obuna:</b>\n"
        f"   • Botdan foydalanish uchun kanallarga obuna bo'ling\n\n"
        f"6️⃣ <b>Ta'qiqlangan harakatlar:</b>\n"
        f"   • Soxta akkauntlar\n"
        f"   • Botni aldash\n"
        f"   • Spam yuborish\n\n"
        f"⚠️ Qoidalarni buzganlar <b>bloklanadi</b>!",
        parse_mode="HTML",
        reply_markup=get_main_menu()
    )

# ===================== MUROJAT =====================
@dp.message(F.text == "📞 Murojat")
async def show_contact(message: types.Message):
    await message.answer(
        "📞 <b>Murojat va Yordam</b>\n\n"
        "👨‍💼 <b>Admin:</b> @vrxszd\n\n"
        "❓ <b>Savollar bo'yicha:</b>\n"
        "• Yechim muammolari\n"
        "• Referal bo'yicha\n"
        "• Baraban va reyting\n"
        "• Umumiy savollar\n\n"
        "📢 <b>Reklama va hamkorlik:</b>\n"
        "👨‍💼 @vrxszd\n\n"
        "⏰ <b>Ish vaqti:</b> 09:00 - 23:00\n"
        "📅 Dushanba - Yakshanba",
        parse_mode="HTML",
        reply_markup=get_main_menu()
    )

# ===================== ASOSIY FUNKSIYA =====================
async def main():
    init_db()
    print("\n" + "="*50)
    print("🤖 BOT ISHGA TUSHMOQDA...")
    print("="*50)
    
    await start_web_server()
    
    me = await bot.get_me()
    print(f"✅ Bot: @{me.username}")
    print(f"\n📢 Majburiy kanallar ({len(CHANNELS)} ta):")
    for ch in CHANNELS:
        print(f"   - {ch['name']}: {ch['link']}")
    print(f"\n💰 Minimal yechish: {MIN_WITHDRAW} UC")
    print(f"🎁 Referal bonus: {REFERRAL_BONUS} UC")
    print(f"🎡 Baraban yutuqlari: {list(SPIN_REWARDS.keys())}")
    print("="*50)
    print("🎉 BOT ISHLADI!")
    print("="*50 + "\n")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
