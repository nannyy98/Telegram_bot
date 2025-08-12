# handlers/catalog.py (важные места)
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
import sqlite3
from config import IMAGE_FOLDER, DB_PATH

router = Router()

@router.message(Command("catalog"))
async def show_catalog(message: Message):
    user_id = message.from_user.id
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
    r = c.fetchone()
    lang = r[0] if r else "ru"

    c.execute("SELECT id, name_ru, name_uz, price, image FROM products")
    products = c.fetchall()
    conn.close()

    for prod_id, name_ru, name_uz, price, image in products:
        name = name_ru if lang == 'ru' else name_uz
        img_path = f"{IMAGE_FOLDER}/{image}" if image else None
        caption = f"<b>{name}</b>\n💵 Цена: {price} $"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛍 В корзину", callback_data=f"add_{prod_id}")]
        ])
        if img_path and os.path.exists(img_path):
            await message.answer_photo(photo=FSInputFile(img_path), caption=caption, reply_markup=kb)
        else:
            await message.answer(caption, reply_markup=kb)
