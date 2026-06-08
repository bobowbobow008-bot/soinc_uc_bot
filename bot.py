import asyncio
import sqlite3
import random
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command  # <-- Command qo'shildi
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web

# ===================== SOZLAMALAR =====================
BOT_TOKEN = "8999661868:AAG5VZzo-_xCH8AjN9EvwNATVdc6WGUlMuM"

CHANNELS = [
    {"id": "@odzif12345", "name": "ODIZV KANALI", "link": "https://t.me/odzif12345", "type": "public"},
    {"id": "@razee_sell", "name": "RAZEE SELL", "link": "https://t.me/razee_sell", "type": "public"},
]

ADMIN_ID = 7928569939
REFERRAL_BONUS = 60
MIN_WITHDRAW = 720

SPIN_REWARDS = {20: 40, 30: 25, 15: 25, 50: 7, 100: 2.5, 200: 0.5}
# ======================================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ===================== DATABASE =====================
def init_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
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

def get_user(user_id):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row

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

def get_total_earned(user_id):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT total_earned FROM users WHERE user_id=?", (user_id,))
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
    rand = random.uniform(0, 100)
    cumulative = 0
    for amount, chance in SPIN_REWARDS.items():
        cumulative += chance
        if rand <= cumulative:
            return amount
    return 20

def get_top_referrers(limit=10):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT user_id, username, full_name, ref_count FROM users WHERE ref_count > 0 ORDER BY ref_count DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_top_earners(limit=10):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT user_id, username, full_name, total_earned FROM users WHERE total_earned > 0 ORDER BY total_earned DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

# ===================== OBUNA TEKSHIRISH =====================
async def check_subscription(user_id):
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(channel["id"], user_id)
            if member.status not in ['member', 'creator', 'administrator']:
                return False
        except:
            return False
    return True

def get_subscription_keyboard():
    buttons = []
    for channel in CHANNELS:
        buttons.append([InlineKeyboardButton(text=f"📢 {channel['name']} ga obuna bo'lish", url=channel["link"])])
    buttons.append([InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_main_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="💰 Balans"), KeyboardButton(text="💸 UC Yechish")],
        [KeyboardButton(text="👥 Referal UC"), KeyboardButton(text="🎡 Baraban")],
        [KeyboardButton(text="🏆 Top Reyting"), KeyboardButton(text="📋 Qoidalar")],
        [KeyboardButton(text="📞 Murojat")]
    ], resize_keyboard=True)

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
    referrer_id = int(args[1]) if len(args) > 1 and args[1].isdigit() and int(args[1]) != user_id else None
    
    if not await check_subscription(user_id):
        await message.answer("⚠️ Botdan foydalanish uchun kanallarga obuna bo'ling!", parse_mode="HTML", reply_markup=get_subscription_keyboard())
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
        f"💸 Yechish: <b>{MIN_WITHDRAW} UC</b> dan\n\n"
        f"🎡 Har kuni baraban aylantiring!\n"
        f"🏆 Top reytingda kimlar yetakchi ekanligini ko'ring!\n\n"
        f"👇 Quyidagi menyudan foydalaning:",
        parse_mode="HTML",
        reply_markup=get_main_menu()
    )

@dp.callback_query(F.data == "check_sub")
async def check_sub_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not await check_subscription(user_id):
        await callback.answer("❌ Kanallarga obuna bo'lmagansiz!", show_alert=True)
        return
    if not get_user(user_id):
        add_user(user_id, callback.from_user.username or "", callback.from_user.full_name, None)
    await callback.message.delete()
    await callback.message.answer(f"✅ Obuna tasdiqlandi!\n💰 Balans: {get_balance(user_id)} UC", parse_mode="HTML", reply_markup=get_main_menu())
    await callback.answer("✅ Obuna tasdiqlandi!")

@dp.message(F.text == "💰 Balans")
async def show_balance(message: types.Message):
    user_id = message.from_user.id
    if not await check_subscription(user_id):
        await message.answer("⚠️ Kanallarga obuna bo'ling!", reply_markup=get_subscription_keyboard())
        return
    await message.answer(
        f"💰 <b>Balansingiz</b>\n\n"
        f"💎 Joriy: <b>{get_balance(user_id)} UC</b>\n"
        f"📈 Jami ishlagan: <b>{get_total_earned(user_id)} UC</b>\n"
        f"👥 Referallar: <b>{get_ref_count(user_id)} ta</b>\n"
        f"🎁 Daromad: <b>{get_ref_count(user_id) * REFERRAL_BONUS} UC</b>",
        parse_mode="HTML", reply_markup=get_main_menu()
    )

@dp.message(F.text == "💸 UC Yechish")
async def withdraw(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if not await check_subscription(user_id):
        await message.answer("⚠️ Kanallarga obuna bo'ling!", reply_markup=get_subscription_keyboard())
        return
    balance = get_balance(user_id)
    if balance < MIN_WITHDRAW:
        await message.answer(f"❌ Yechish uchun {MIN_WITHDRAW} UC kerak!\n💰 Sizda: {balance} UC", reply_markup=get_main_menu())
        return
    await message.answer(f"💰 Balans: {balance} UC\n📝 O'yin ID raqamingizni kiriting:", parse_mode="HTML")
    await state.set_state(WithdrawState.waiting_for_id)

@dp.message(WithdrawState.waiting_for_id)
async def process_withdraw(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    game_id = message.text.strip()
    if not game_id.isdigit():
        await message.answer("❌ Faqat raqam kiriting!")
        return
    balance = get_balance(user_id)
    if balance < MIN_WITHDRAW:
        await message.answer("❌ Balans yetarli emas!", reply_markup=get_main_menu())
        await state.clear()
        return
    update_balance(user_id, -balance)
    await state.clear()
    await message.answer(f"✅ So'rov qabul qilindi!\n🎮 ID: {game_id}\n💎 Summa: {balance} UC\n⏰ 24 soat ichida!", reply_markup=get_main_menu())
    await bot.send_message(ADMIN_ID, f"💸 Yechish!\n👤 {message.from_user.full_name}\n🆔 {user_id}\n🎮 {game_id}\n💎 {balance} UC")

@dp.message(F.text == "👥 Referal UC")
async def show_referral(message: types.Message):
    user_id = message.from_user.id
    if not await check_subscription(user_id):
        await message.answer("⚠️ Kanallarga obuna bo'ling!", reply_markup=get_subscription_keyboard())
        return
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
    await message.answer(
        f"👥 <b>Referal Tizimi</b>\n\n"
        f"🔗 <b>Havolangiz:</b>\n<code>{ref_link}</code>\n\n"
        f"👥 Taklif qilganlar: <b>{get_ref_count(user_id)} ta</b>\n"
        f"💰 Daromad: <b>{get_ref_count(user_id) * REFERRAL_BONUS} UC</b>\n\n"
        f"📌 Har bir do'st uchun <b>+{REFERRAL_BONUS} UC</b>!",
        parse_mode="HTML", reply_markup=get_main_menu()
    )

@dp.message(F.text == "🎡 Baraban")
async def spin_wheel(message: types.Message):
    user_id = message.from_user.id
    
    if not await check_subscription(user_id):
        await message.answer("⚠️ Kanallarga obuna bo'ling!", reply_markup=get_subscription_keyboard())
        return
    
    if not can_spin(user_id):
        last_spin = get_last_spin(user_id)
        if last_spin:
            last_spin_time = datetime.fromisoformat(last_spin)
            next_spin_time = last_spin_time + timedelta(hours=24)
            remaining = next_spin_time - datetime.now()
            hours = remaining.seconds // 3600
            minutes = (remaining.seconds % 3600) // 60
            await message.answer(f"⏰ Baraban {hours} soat {minutes} daqiqadan keyin aylanadi!\n🎡 Har 24 soatda 1 marta!", reply_markup=get_main_menu())
        return
    
    reward = get_spin_reward()
    update_balance(user_id, reward)
    update_total_earned(user_id, reward)
    update_last_spin(user_id)
    
    await message.answer(f"🎉 <b>BARABAN NATIJASI!</b> 🎉\n\n💰 Siz <b>{reward} UC</b> yutdingiz!\n💎 Yangi balans: <b>{get_balance(user_id)} UC</b>\n🎡 Keyingi aylantirish 24 soatdan keyin!", parse_mode="HTML", reply_markup=get_main_menu())

@dp.message(F.text == "🏆 Top Reyting")
async def show_top_rating(message: types.Message):
    user_id = message.from_user.id
    
    if not await check_subscription(user_id):
        await message.answer("⚠️ Kanallarga obuna bo'ling!", reply_markup=get_subscription_keyboard())
        return
    
    top_ref = get_top_referrers(10)
    top_earn = get_top_earners(10)
    
    ref_text = "<b>👥 ENG KO'P TAKLIF QILGANLAR</b>\n\n"
    if top_ref:
        for i, (uid, username, full_name, count) in enumerate(top_ref, 1):
            name = (full_name or username or f"User {uid}")[:20]
            ref_text += f"{i}. {name} – <b>{count}</b> ta\n"
    else:
        ref_text += "Hali hech kim taklif qilmagan\n"
    
    earn_text = "\n\n<b>💰 ENG KO'P UC ISHLAGANLAR</b>\n\n"
    if top_earn:
        for i, (uid, username, full_name, earned) in enumerate(top_earn, 1):
            name = (full_name or username or f"User {uid}")[:20]
            earn_text += f"{i}. {name} – <b>{earned}</b> UC\n"
    else:
        earn_text += "Hali hech kim UC ishlamagan\n"
    
    await message.answer(f"🏆 <b>TOP REYTING</b>\n\n{ref_text}{earn_text}", parse_mode="HTML", reply_markup=get_main_menu())

@dp.message(F.text == "📋 Qoidalar")
async def show_rules(message: types.Message):
    await message.answer(
        f"📋 <b>Bot Qoidalari</b>\n\n"
        f"1️⃣ Referal: +{REFERRAL_BONUS} UC\n"
        f"2️⃣ Yechish: minimal {MIN_WITHDRAW} UC\n"
        f"3️⃣ Baraban: 24 soatda 1 marta\n"
        f"4️⃣ 2 ta kanalga obuna majburiy\n"
        f"5️⃣ Aldash taqiqlanadi!",
        parse_mode="HTML", reply_markup=get_main_menu()
    )

@dp.message(F.text == "📞 Murojat")
async def show_contact(message: types.Message):
    await message.answer("📞 <b>Murojat</b>\n\n👨‍💼 Admin: @vrxszd\n\n❓ Savol va muammolar uchun yozing!", parse_mode="HTML", reply_markup=get_main_menu())

# ===================== ADMIN PROMO =====================
@dp.message(Command("promo"))
async def admin_promo(message: types.Message):
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

# ===================== ASOSIY FUNKSIYA =====================
async def main():
    init_db()
    print("\n" + "="*50)
    print("🤖 BOT ISHGA TUSHMOQDA...")
    print("="*50)
    
    await start_web_server()
    
    me = await bot.get_me()
    print(f"✅ Bot: @{me.username}")
    print(f"\n📢 Majburiy kanallar ({len(CHANNELS)} ta)")
    print(f"💰 Minimal yechish: {MIN_WITHDRAW} UC")
    print(f"🎡 Baraban yutuqlari: {list(SPIN_REWARDS.keys())}")
    print("="*50)
    print("🎉 BOT ISHLADI!")
    print("="*50 + "\n")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
