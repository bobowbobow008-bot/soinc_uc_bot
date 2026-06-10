import os
import telebot
import random
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ========== KONFIGURATSIYA ==========
BOT_TOKEN = "8837237819:AAFnUp607i0r3X1u1IEFVo_KpfT65AbX2hg"
CHANNEL_USERNAME = "@razee_sell"  # Kanal username
PROMO_CODE_MOSBET = "ABDULAZIZ22"
PROMO_CODE_MELBET = "VLEVIL"
LINK_MOSBET = "https://pg5i0mmb.com/LUDU"
LINK_MELBET = "https://clck.ru/3U5H67"

# Apple Fortune KFlar
KF_LIST = [1.92, 2.41, 4.02, 6.71, 27.97, 69.93, 349.68]

bot = telebot.TeleBot(BOT_TOKEN)

# ========== OBUNA TEKSHIRISH ==========
def is_subscribed(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return status in ['member', 'administrator', 'creator']
    except:
        return False

# ========== /start ==========
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📢 Kanalga obuna bo'lish", url=f"https://t.me/{CHANNEL_USERNAME[1:]}"))
        bot.reply_to(message, "❌ Iltimos, avval kanalga obuna bo'ling!\nObuna bo'lgach /start bosing.", reply_markup=markup)
        return
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🍎 SIGNAL OLISH", callback_data="get_signal"))
    bot.reply_to(message, "✅ Xush kelibsiz!\nApple Fortune uchun random signal olish uchun tugmani bosing.", reply_markup=markup)

# ========== SIGNAL OLISH ==========
@bot.callback_query_handler(func=lambda call: call.data == "get_signal")
def ask_promo_and_links(call):
    text = f"""🎯 Apple Fortune SIGNAL olish uchun:

━━━━━━━━━━━━━━━━━━━━━━━━━━━
📢 PROMO KODLAR:
━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Mosbet promo kodi: `{PROMO_CODE_MOSBET}`
• Melbet promo kodi: `{PROMO_CODE_MELBET}`
━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔗 Ro'yxatdan o'tish linklari:
• Mosbet: {LINK_MOSBET}
• Melbet: {LINK_MELBET}

⚠️ ESLATMA:
Promo kodni kiritish va link orqali ro'yxatdan o'tish MAJBURIY!

👇 Signal olish uchun tugmani bosing"""
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🎲 SIGNALNI KO'RSAT", callback_data="show_signal"))
    markup.add(InlineKeyboardButton("📋 Promo kodlarni nusxalash", callback_data="copy_promo"))
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=text,
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data == "copy_promo")
def copy_promo(call):
    bot.answer_callback_query(call.id, f"Mosbet: {PROMO_CODE_MOSBET}\nMelbet: {PROMO_CODE_MELBET}", show_alert=True)

# ========== RANDOM SIGNAL ==========
@bot.callback_query_handler(func=lambda call: call.data == "show_signal")
def send_random_signal(call):
    kf = random.choice(KF_LIST)
    
    if kf <= 2.5:
        rang = "🟢"
        izoh = "Past koeffitsiyent, yuqori ehtimol"
    elif kf <= 10:
        rang = "🟡"
        izoh = "O'rtacha koeffitsiyent"
    elif kf <= 70:
        rang = "🟠"
        izoh = "Yuqori koeffitsiyent, o'rtacha ehtimol"
    else:
        rang = "🔴"
        izoh = "Juda yuqori koeffitsiyent, past ehtimol"
    
    signal_text = f"""🍎 APPLE FORTUNE SIGNAL

{rang} KOEFFITSIYENT: {kf}

📊 {izoh}

⚠️ Eslatma: Bu TASODIFIY signaldir. 
100% yutish kafolatlanmagan.

✅ Omad tilaymiz!"""
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔄 YANA SIGNAL", callback_data="get_signal"))
    markup.add(InlineKeyboardButton("🏠 BOSH MENU", callback_data="main_menu"))
    
    bot.send_message(call.message.chat.id, signal_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "main_menu")
def main_menu(call):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🍎 SIGNAL OLISH", callback_data="get_signal"))
    bot.send_message(call.message.chat.id, "🏠 Bosh menyu:", reply_markup=markup)

# ========== ISHGA TUSHIRISH ==========
if __name__ == "__main__":
    print("Bot ishga tushdi...")
    bot.infinity_polling()
