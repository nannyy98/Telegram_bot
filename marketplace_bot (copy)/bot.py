import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import TOKEN
from database import init_db
from utils.excel_loader import load_products_from_excel

from handlers.start import router as start_router
from handlers.language import router as language_router
from handlers.catalog import router as catalog_router
from handlers.cart import router as cart_router
from handlers.orders import router as orders_router
from handlers.feedback import router as feedback_router


API_IPV4 ="149.154.167.220"

async def main():
    logging.basicConfig(level=logging.INFO)

    bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    dp.include_router(start_router)
    dp.include_router(language_router)
    dp.include_router(catalog_router)
    dp.include_router(cart_router)
    dp.include_router(orders_router)
    dp.include_router(feedback_router)

    init_db()
    try:
        load_products_from_excel()
    except Exception as e:
        logging.exception("Ошибка загрузки товаров из Excel: %s", e)

    print("🚀 Бот запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
