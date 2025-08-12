from aiogram import Router
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
import sqlite3
from config import LANGUAGES

router = Router()

@router.message(lambda msg: msg.text.lower() in LANGUAGES)
async def set_language(message: Message):
    user_id = message.from_user.id
    lang = message.text.lower()

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, language) VALUES (?, ?)", (user_id, lang))
    c.execute("UPDATE users SET language = ? WHERE user_id = ?", (lang, user_id))
    conn.commit()
    conn.close()

    # Меню на двух языках
    if lang == 'ru':
        text = "✅ Язык установлен! Выберите действие:"
        kb = ReplyKeyboardMarkup(
            resize_keyboard=True,
            keyboard=[
                [KeyboardButton(text="📦 /Каталог"), KeyboardButton(text="⭐️ Избранные")],
                [KeyboardButton(text="🕘 Заказы"), KeyboardButton(text="💬 Отзыв")],
                [KeyboardButton(text="☎️ Связаться")]
            ]
        )
    else:
        text = "✅ Til tanlandi! Quyidagilardan birini tanlang:"
        kb = ReplyKeyboardMarkup(
            resize_keyboard=True,
            keyboard=[
                [KeyboardButton(text="📦 /Katalog"), KeyboardButton(text="⭐️ Saralanganlar")],
                [KeyboardButton(text="🕘 Buyurtmalar"), KeyboardButton(text="💬 Fikr bildirish")],
                [KeyboardButton(text="☎️ Operator bilan bog‘lanish")]
            ]
        )

    await message.answer(text, reply_markup=kb)
