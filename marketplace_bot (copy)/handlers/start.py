from aiogram import Router
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from config import LANGUAGES

router = Router()

@router.message(Command("start"))
async def start_command(message: Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=lang.upper())] for lang in LANGUAGES],
        resize_keyboard=True
    )
    await message.answer("🇷🇺 Выберите язык\n🇺🇿 Tilni tanlang:", reply_markup=kb)
