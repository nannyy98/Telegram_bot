from aiogram import Bot, Dispatcher
import asyncio
from config import TOKEN

async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    print("✅ Бот запущен")
    await dp.start_polling(bot)

if name == "main":
    asyncio.run(main())
