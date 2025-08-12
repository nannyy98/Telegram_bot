import os
from dotenv import load_dotenv

# Загружаем .env
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

if not TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден или пустой в .env")

if not ADMIN_ID:
    raise ValueError("❌ ADMIN_ID не найден или пустой в .env")

ADMIN_ID = int(ADMIN_ID)

DB_PATH = os.getenv("DB_PATH", "database.db")
EXCEL_PATH = os.getenv("EXCEL_PATH", "data/products.xlsx")
IMAGE_FOLDER = os.getenv("IMAGE_FOLDER", "data/images")
LANGUAGES = ['ru', 'uz']
