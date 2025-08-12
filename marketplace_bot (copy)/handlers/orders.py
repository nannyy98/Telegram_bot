# handlers/orders.py
from aiogram import Router
from aiogram.types import CallbackQuery
import sqlite3
from config import DB_PATH, ADMIN_ID

router = Router()

@router.callback_query(lambda c: c.data == "checkout")
async def checkout_callback(call: CallbackQuery):
    user_id = call.from_user.id
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT p.id, p.name_ru, p.price, c.quantity
        FROM cart c JOIN products p ON c.product_id = p.id
        WHERE c.user_id = ?
    ''', (user_id,))
    rows = c.fetchall()
    if not rows:
        await call.answer("Корзина пуста", show_alert=True)
        conn.close()
        return

    details = []
    total = 0
    for pid, name, price, qty in rows:
        details.append(f"{name} x{qty} — {price}$")
        total += price * qty

    details_text = "\n".join(details)
    c.execute("INSERT INTO orders (user_id, details, payment_method, delivery_method, comment) VALUES (?, ?, ?, ?, ?)",
              (user_id, details_text, "Не указан", "Не указан", ""))
    order_id = c.lastrowid
    c.execute("DELETE FROM cart WHERE user_id=?", (user_id,))

    conn.commit()
    conn.close()

    await call.message.answer(f"Заказ #{order_id} оформлен. Итого: {total}$")
    await call.message.bot.send_message(ADMIN_ID, f"Новый заказ #{order_id} от {call.from_user.full_name} (id={user_id})\n{details_text}\nИтого: {total}$")
