import asyncio
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web

# ===================== SOZLAMALAR =====================
BOT_TOKEN = "8999661868:AAG5VZzo-_xCH8AjN9EvwNATVdc6WGUlMuM"

# 2 TA KANAL - IKKALASI HAM MAJBURIY
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
            balance INTEGER DEFAULT 0,
            referrer_id INTEGER,
            ref_count INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def add_user(user_id, username, referrer_id=None):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, referrer_id) VALUES (?, ?, ?)",
              (user_id, username, referrer_id))
    conn.commit()
    conn.close()
    if referrer_id:
        update_balance(referrer_id, REFERRAL_BONUS)
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

# ===================== OBUNA TEKSHIRISH =====================
async def check_subscription(user_id):
    """Foydalanuvchi barcha kanallarga obuna bo'lganligini tekshiradi"""
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
    """Obuna tugmalari"""
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
        [KeyboardButton(text="💎 Balans"), KeyboardButton(text="💰 Yechish")],
        [KeyboardButton(text="👥 Referal"), KeyboardButton(text="📋 Qoidalar")],
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
        add_user(user_id, username, referrer_id)
        if referrer_id:
            try:
                await bot.send_message(referrer_id, f"🎉 +{REFERRAL_BONUS} UC!")
            except:
                pass
    
    await message.answer(
        f"✅ <b>Xush kelibsiz, {message.from_user.first_name}!</b>\n\n"
        f"💎 Balans: <b>{get_balance(user_id)} UC</b>\n"
        f"💰 Yechish uchun minimal: <b>{MIN_WITHDRAW} UC</b>\n\n"
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
        add_user(user_id, callback.from_user.username or "", None)
    
    await callback.message.delete()
    await callback.message.answer(
        f"✅ <b>Tabriklaymiz!</b>\n\n"
        f"Siz barcha kanallarga obuna bo'ldingiz!\n"
        f"💎 Balans: <b>{get_balance(user_id)} UC</b>\n\n"
        f"💰 Yechish uchun minimal: <b>{MIN_WITHDRAW} UC</b>",
        parse_mode="HTML",
        reply_markup=get_main_menu()
    )
    await callback.answer("✅ Obuna tasdiqlandi!")

@dp.message(F.text == "💎 Balans")
async def show_balance(message: types.Message):
    user_id = message.from_user.id
    
    if not await check_subscription(user_id):
        await message.answer(
            "⚠️ Iltimos, kanallarga obuna bo'ling!",
            reply_markup=get_subscription_keyboard()
        )
        return
    
    balance = get_balance(user_id)
    ref_count = get_ref_count(user_id)
    
    await message.answer(
        f"💎 <b>Sizning balansingiz</b>\n\n"
        f"💰 Balans: <b>{balance} UC</b>\n"
        f"👥 Referallar soni: <b>{ref_count} ta</b>\n"
        f"🎁 Referaldan daromad: <b>{ref_count * REFERRAL_BONUS} UC</b>\n\n"
        f"📌 Yechish uchun minimal: <b>{MIN_WITHDRAW} UC</b>",
        parse_mode="HTML",
        reply_markup=get_main_menu()
    )

@dp.message(F.text == "💰 Yechish")
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
            f"💰 Sizning balans: <b>{balance} UC</b>\n"
            f"📌 Minimal yechish: <b>{MIN_WITHDRAW} UC</b>\n\n"
            f"💡 Do'stlaringizni taklif qilib, balansingizni oshiring!",
            parse_mode="HTML",
            reply_markup=get_main_menu()
        )
        return
    
    await message.answer(
        f"💰 <b>UC Yechish</b>\n\n"
        f"💎 Balansingiz: <b>{balance} UC</b>\n"
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

@dp.message(F.text == "👥 Referal")
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
        f"💎 Jami daromad: <b>{ref_count * REFERRAL_BONUS} UC</b>\n\n"
        f"🎁 <b>Qanday ishlaydi?</b>\n"
        f"1️⃣ Havolani do'stingizga yuboring\n"
        f"2️⃣ U kanallarga obuna bo'lsin\n"
        f"3️⃣ Siz <b>+{REFERRAL_BONUS} UC</b> olasiz!",
        parse_mode="HTML",
        reply_markup=get_main_menu()
    )

@dp.message(F.text == "📋 Qoidalar")
async def show_rules(message: types.Message):
    await message.answer(
        f"📋 <b>Bot Qoidalari</b>\n\n"
        f"1️⃣ <b>Referal:</b> Har bir taklif uchun +{REFERRAL_BONUS} UC\n"
        f"2️⃣ <b>Yechish:</b> Minimal {MIN_WITHDRAW} UC\n"
        f"3️⃣ <b>Majburiy obuna:</b> 2 ta kanalga obuna bo'lish shart\n"
        f"4️⃣ <b>Aldash:</b> Soxta akkauntlar taqiqlanadi!\n\n"
        f"⚠️ Qoidalarni buzganlar bloklanadi!",
        parse_mode="HTML",
        reply_markup=get_main_menu()
    )

@dp.message(F.text == "📞 Murojat")
async def show_contact(message: types.Message):
    await message.answer(
        "📞 <b>Murojat</b>\n\n"
        "👨‍💼 Admin: @vrxszd\n\n"
        "❓ Savol va muammolar uchun murojaat qiling!",
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
    print("="*50)
    print("🎉 BOT ISHLADI!")
    print("="*50 + "\n")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
