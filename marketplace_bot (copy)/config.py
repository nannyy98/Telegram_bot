from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
DB_PATH = os.getenv("DB_PATH", "database.db")
EXCEL_PATH = os.getenv("EXCEL_PATH", "data/products.xlsx")
IMAGE_FOLDER = os.getenv("IMAGE_FOLDER", "data/images")
LANGUAGES = ['ru', 'uz']
