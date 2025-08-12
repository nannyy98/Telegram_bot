# handlers/feedback.py
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
import sqlite3
from config import DB_PATH, ADMIN_ID

router = Router()

@router.message(Command("feedback"))
async def feedback_cmd(message: Message):
    text = message.get_args()
    user_id = message.from_user.id
    if not text:
        await message.answer("Использование: /feedback ваш_отзыв")
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO feedback (user_id, product_id, message) VALUES (?, ?, ?)", (user_id, None, text))
    conn.commit()
    conn.close()
    await message.answer("Спасибо! Ваш отзыв принят.")
    await message.bot.send_message(ADMIN_ID, f"Новый отзыв от {message.from_user.full_name} (id={user_id}):\n{text}")
