# handlers/cart.py
from aiogram import Router
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
import sqlite3
from config import DB_PATH

router = Router()

@router.callback_query(lambda c: c.data and c.data.startswith("add_"))
async def add_to_cart(call: CallbackQuery):
    user_id = call.from_user.id
    prod_id = int(call.data.split("_",1)[1])
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, quantity FROM cart WHERE user_id=? AND product_id=?",(user_id, prod_id))
    row = c.fetchone()
    if row:
        c.execute("UPDATE cart SET quantity = quantity + 1 WHERE id=?", (row[0],))
    else:
        c.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, 1)", (user_id, prod_id))
    conn.commit()
    conn.close()
    await call.answer("Добавлено в корзину ✅", show_alert=False)

@router.message(Command("cart"))
async def show_cart(message: Message):
    user_id = message.from_user.id
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT p.id, p.name_ru, p.price, c.quantity
        FROM cart c JOIN products p ON c.product_id = p.id
        WHERE c.user_id = ?
    ''', (user_id,))
    rows = c.fetchall()
    conn.close()
    if not rows:
        await message.answer("Ваша корзина пуста.")
        return
    lines = []
    total = 0
    for pid, name, price, qty in rows:
        lines.append(f"{name} x{qty} — {price}$")
        total += price * qty
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Оформить заказ", callback_data="checkout")]])
    await message.answer("\n".join(lines) + f"\n\nИтого: {total}$", reply_markup=kb)
