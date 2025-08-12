# utils/excel_loader.py
import openpyxl
import os
import sqlite3
from config import EXCEL_PATH, IMAGE_FOLDER, DB_PATH

def load_products_from_excel():
    if not os.path.exists(EXCEL_PATH):
        print("❌ Excel файл не найден:", EXCEL_PATH)
        return

    wb = openpyxl.load_workbook(EXCEL_PATH)
    sheet = wb.active

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # очистим таблицу (опционально)
    c.execute("DELETE FROM products")

    for row_idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
        try:
            name_ru, name_uz, desc_ru, desc_uz, category, price, image_filename = row
        except Exception as e:
            print(f"⚠️ Неправильная строка {row_idx}: {e}")
            continue

        if image_filename:
            image_path = os.path.join(IMAGE_FOLDER, image_filename)
            if not os.path.exists(image_path):
                print(f"⚠️ Изображение не найдено (строка {row_idx}): {image_filename}")
                continue

        try:
            price = float(price) if price is not None else 0.0
        except:
            price = 0.0

        c.execute('''
            INSERT INTO products (name_ru, name_uz, description_ru, description_uz, category, price, image)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (name_ru, name_uz, desc_ru, desc_uz, category, price, image_filename))

    conn.commit()
    conn.close()
    print("✅ Товары успешно загружены в базу.")
