"""
Модуль расширенной аналитики для телеграм-бота
"""

from datetime import datetime, timedelta
from utils import format_price, format_date
import json

class AnalyticsManager:
    def __init__(self, db):
        self.db = db
    
    def get_sales_report(self, start_date=None, end_date=None, period='day'):
        """Отчет по продажам за период"""
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        # Основная статистика продаж
        try:
            sales_data = self.db.execute_query('''
                SELECT 
                    COUNT(*) as orders_count,
                    SUM(total_amount) as revenue,
                    AVG(total_amount) as avg_order_value,
                    COUNT(DISTINCT user_id) as unique_customers
                FROM orders 
                WHERE DATE(created_at) BETWEEN ? AND ?
                AND status != 'cancelled'
            ''', (start_date, end_date))
            
            # Топ товары за период
            top_products = self.db.execute_query('''
                SELECT 
                    p.name,
                    SUM(oi.quantity) as units_sold,
                    SUM(oi.quantity * oi.price) as revenue
                FROM order_items oi
                JOIN products p ON oi.product_id = p.id
                JOIN orders o ON oi.order_id = o.id
                WHERE DATE(o.created_at) BETWEEN ? AND ?
                AND o.status != 'cancelled'
                GROUP BY p.id, p.name
                ORDER BY revenue DESC
                LIMIT 10
            ''', (start_date, end_date))
            
            return {
                'period': f"{start_date} - {end_date}",
                'sales_data': sales_data,
                'top_products': top_products
            }
        except Exception as e:
            print(f"Ошибка получения отчета по продажам: {e}")
            return {
                'period': f"{start_date} - {end_date}",
                'sales_data': [],
                'top_products': []
            }
    
    def schedule_analytics_reports(self):
        """Планирование автоматических отчетов"""
        import threading
        import time
        
        def daily_report():
            while True:
                try:
                    now = datetime.now()
                    if now.hour == 9 and now.minute == 0:
                        self.send_daily_analytics_to_admins()
                        time.sleep(60)  # Ждем минуту чтобы не отправить дважды
                    time.sleep(30)  # Проверяем каждые 30 секунд
                except Exception as e:
                    print(f"Ошибка ежедневного отчета: {e}")
                    time.sleep(300)
        
        # Запускаем в фоновом потоке
        threading.Thread(target=daily_report, daemon=True).start()
    
    def send_daily_analytics_to_admins(self):
        """Отправка ежедневной аналитики админам"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            report = self.get_sales_report(today, today, 'day')
            
            if report['sales_data']:
                report_text = self.format_sales_report(report)
                
                # Отправляем всем админам
                admins = self.db.execute_query('SELECT telegram_id FROM users WHERE is_admin = 1')
                for admin in admins:
                    try:
                        if hasattr(self, 'bot'):
                            self.bot.send_message(admin[0], report_text)
                    except Exception as e:
                        print(f"Ошибка отправки аналитики админу {admin[0]}: {e}")
        except Exception as e:
            print(f"Ошибка отправки ежедневной аналитики: {e}")
    
    def format_sales_report(self, report):
        """Форматирование отчета по продажам"""
        if not report or not report['sales_data']:
            return "📊 Нет данных для отчета"
        
        data = report['sales_data'][0]
        text = f"📊 <b>Отчет по продажам</b>\n"
        text += f"📅 Период: {report['period']}\n\n"
        text += f"📦 Заказов: {data[0]}\n"
        text += f"💰 Выручка: {format_price(data[1] or 0)}\n"
        text += f"💳 Средний чек: {format_price(data[2] or 0)}\n"
        text += f"👥 Уникальных клиентов: {data[3]}\n\n"
        
        # Топ товары
        if report['top_products']:
            text += f"🏆 <b>Топ товары:</b>\n"
            for i, product in enumerate(report['top_products'][:5], 1):
                text += f"{i}. {product[0]} - {product[1]} шт. ({format_price(product[2])})\n"
        
        return text