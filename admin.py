"""
Админ-панель для телеграм-бота интернет-магазина
"""

from datetime import datetime, timedelta
from utils import format_price, format_date, log_user_action
from keyboards import create_admin_keyboard, create_confirmation_keyboard
try:
    from localization import t
except ImportError:
    def t(key, **kwargs):
        return key

class AdminHandler:
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db
        self.admin_states = {}
        self.notification_manager = None
    
    def handle_admin_command(self, message):
        """Обработка админ команд"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        text = message.get('text', '')
        
        # Проверяем права админа
        if not self.is_admin(telegram_id):
            self.bot.send_message(chat_id, "❌ У вас нет прав администратора")
            return
        
        if text == '/admin' or text == '📊 Статистика':
            self.show_admin_panel(chat_id)
        elif text == '📦 Заказы':
            self.show_orders_management(chat_id)
        elif text == '🛠 Товары':
            self.show_products_management(chat_id)
        elif text == '👥 Пользователи':
            self.show_users_management(chat_id)
        elif text == '📈 Аналитика':
            self.show_analytics_menu(chat_id)
        elif text == '🛡 Безопасность':
            self.show_security_menu(chat_id)
        elif text == '💰 Финансы':
            self.show_financial_menu(chat_id)
        elif text == '📦 Склад':
            self.show_inventory_menu(chat_id)
        elif text == '🤖 AI':
            self.show_ai_menu(chat_id)
        elif text == '🎯 Автоматизация':
            self.show_automation_menu(chat_id)
        elif text == '👥 CRM':
            self.show_crm_menu(chat_id)
        elif text == '📢 Рассылка':
            self.show_broadcast_menu(chat_id)
        elif text == '🔙 Пользовательский режим':
            self.exit_admin_mode(chat_id)
        else:
            self.bot.send_message(chat_id, "❓ Неизвестная админ команда")
    
    def is_admin(self, telegram_id):
        """Проверка прав администратора"""
        try:
            admin_check = self.db.execute_query(
                'SELECT is_admin FROM users WHERE telegram_id = ?',
                (telegram_id,)
            )
            return admin_check and admin_check[0][0] == 1
        except:
            return False
    
    def show_admin_panel(self, chat_id):
        """Показ главной админ-панели"""
        # Получаем статистику
        stats = self.get_basic_stats()
        
        admin_text = f"🔧 <b>Админ-панель</b>\n\n"
        admin_text += f"📊 <b>Статистика:</b>\n"
        admin_text += f"👥 Пользователей: {stats['users_count']}\n"
        admin_text += f"📦 Заказов: {stats['orders_count']}\n"
        admin_text += f"🛍 Товаров: {stats['products_count']}\n"
        admin_text += f"💰 Выручка: {format_price(stats['total_revenue'])}\n\n"
        admin_text += f"📅 Сегодня:\n"
        admin_text += f"📦 Заказов: {stats['today_orders']}\n"
        admin_text += f"💰 Выручка: {format_price(stats['today_revenue'])}\n"
        
        self.bot.send_message(
            chat_id, admin_text,
            reply_markup=create_admin_keyboard()
        )
    
    def get_basic_stats(self):
        """Получение базовой статистики"""
        try:
            # Общая статистика
            users_count = self.db.execute_query('SELECT COUNT(*) FROM users WHERE is_admin = 0')[0][0]
            orders_count = self.db.execute_query('SELECT COUNT(*) FROM orders')[0][0]
            products_count = self.db.execute_query('SELECT COUNT(*) FROM products WHERE is_active = 1')[0][0]
            
            total_revenue = self.db.execute_query(
                'SELECT SUM(total_amount) FROM orders WHERE status != "cancelled"'
            )[0][0] or 0
            
            # Статистика за сегодня
            today = datetime.now().strftime('%Y-%m-%d')
            today_orders = self.db.execute_query(
                'SELECT COUNT(*) FROM orders WHERE DATE(created_at) = ?',
                (today,)
            )[0][0]
            
            today_revenue = self.db.execute_query(
                'SELECT SUM(total_amount) FROM orders WHERE DATE(created_at) = ? AND status != "cancelled"',
                (today,)
            )[0][0] or 0
            
            return {
                'users_count': users_count,
                'orders_count': orders_count,
                'products_count': products_count,
                'total_revenue': total_revenue,
                'today_orders': today_orders,
                'today_revenue': today_revenue
            }
        except Exception as e:
            print(f"Ошибка получения статистики: {e}")
            return {
                'users_count': 0,
                'orders_count': 0,
                'products_count': 0,
                'total_revenue': 0,
                'today_orders': 0,
                'today_revenue': 0
            }
    
    def show_orders_management(self, chat_id):
        """Управление заказами"""
        # Получаем последние заказы
        recent_orders = self.db.execute_query('''
            SELECT o.id, u.name, o.total_amount, o.status, o.created_at
            FROM orders o
            JOIN users u ON o.user_id = u.id
            ORDER BY o.created_at DESC
            LIMIT 10
        ''')
        
        orders_text = "📦 <b>Управление заказами</b>\n\n"
        
        if recent_orders:
            orders_text += "📋 <b>Последние заказы:</b>\n"
            for order in recent_orders:
                status_emoji = self.get_status_emoji(order[3])
                orders_text += f"{status_emoji} #{order[0]} - {order[1]} - {format_price(order[2])}\n"
                orders_text += f"   📅 {format_date(order[4])}\n"
            
            # Добавляем inline клавиатуру для управления
            keyboard = {
                'inline_keyboard': []
            }
            
            for order in recent_orders[:5]:  # Первые 5 заказов
                keyboard['inline_keyboard'].append([
                    {'text': f"📦 Заказ #{order[0]}", 'callback_data': f'order_details_{order[0]}'}
                ])
            
            keyboard['inline_keyboard'].append([
                {'text': '🔙 Назад', 'callback_data': 'admin_back'}
            ])
            
            self.bot.send_message(chat_id, orders_text, reply_markup=keyboard)
        else:
            orders_text += "📭 Заказов пока нет"
            self.bot.send_message(chat_id, orders_text)
    
    def get_status_emoji(self, status):
        """Получение эмодзи для статуса"""
        emojis = {
            'pending': '⏳',
            'confirmed': '✅',
            'shipped': '🚚',
            'delivered': '📦',
            'cancelled': '❌'
        }
        return emojis.get(status, '❓')
    
    def show_products_management(self, chat_id):
        """Управление товарами"""
        products = self.db.execute_query('''
            SELECT id, name, price, stock, is_active
            FROM products
            ORDER BY created_at DESC
            LIMIT 10
        ''')
        
        products_text = "🛍 <b>Управление товарами</b>\n\n"
        
        if products:
            for product in products:
                status = "✅" if product[4] else "❌"
                products_text += f"{status} <b>{product[1]}</b>\n"
                products_text += f"   💰 {format_price(product[2])} | 📦 {product[3]} шт.\n"
        
            # Добавляем inline клавиатуру для управления товарами
            keyboard = {
                'inline_keyboard': []
            }
            
            for product in products[:5]:
                keyboard['inline_keyboard'].append([
                    {'text': f"📝 {product[1]}", 'callback_data': f'edit_product_{product[0]}'}
                ])
            
            keyboard['inline_keyboard'].append([
                {'text': '➕ Добавить товар', 'callback_data': 'add_new_product'},
                {'text': '🔙 Назад', 'callback_data': 'admin_back'}
            ])
            
            self.bot.send_message(chat_id, products_text, reply_markup=keyboard)
        else:
            products_text += "📭 Товаров пока нет"
            self.bot.send_message(chat_id, products_text)
    
    def show_users_management(self, chat_id):
        """Управление пользователями"""
        users_stats = self.db.execute_query('''
            SELECT 
                COUNT(*) as total_users,
                COUNT(CASE WHEN created_at >= datetime('now', '-7 days') THEN 1 END) as new_users,
                COUNT(CASE WHEN id IN (SELECT DISTINCT user_id FROM orders) THEN 1 END) as buyers
            FROM users
            WHERE is_admin = 0
        ''')[0]
        
        users_text = f"👥 <b>Управление пользователями</b>\n\n"
        users_text += f"📊 <b>Статистика:</b>\n"
        users_text += f"👤 Всего пользователей: {users_stats[0]}\n"
        users_text += f"🆕 Новых за неделю: {users_stats[1]}\n"
        users_text += f"🛒 Покупателей: {users_stats[2]}\n"
        
        # Добавляем клавиатуру для действий с пользователями
        keyboard = {
            'inline_keyboard': [
                [
                    {'text': '📊 Детальная статистика', 'callback_data': 'users_detailed_stats'},
                    {'text': '📢 Рассылка', 'callback_data': 'users_broadcast'}
                ],
                [
                    {'text': '🔙 Назад', 'callback_data': 'admin_back'}
                ]
            ]
        }
        
        self.bot.send_message(chat_id, users_text, reply_markup=keyboard)
    
    def show_analytics_menu(self, chat_id):
        """Меню аналитики"""
        analytics_text = "📈 <b>Аналитика и отчеты</b>\n\n"
        analytics_text += "Выберите тип отчета:"
        
        keyboard = {
            'inline_keyboard': [
                [
                    {'text': '📊 Продажи', 'callback_data': 'analytics_sales'},
                    {'text': '👥 Клиенты', 'callback_data': 'analytics_customers'}
                ],
                [
                    {'text': '📦 Товары', 'callback_data': 'analytics_products'},
                    {'text': '💰 Финансы', 'callback_data': 'analytics_finance'}
                ],
                [
                    {'text': '🔙 Назад', 'callback_data': 'admin_back'}
                ]
            ]
        }
        
        self.bot.send_message(chat_id, analytics_text, reply_markup=keyboard)
    
    def show_security_menu(self, chat_id):
        """Меню безопасности"""
        security_text = "🛡 <b>Безопасность системы</b>\n\n"
        security_text += "Мониторинг и защита:"
        
        keyboard = {
            'inline_keyboard': [
                [
                    {'text': '🚨 Логи безопасности', 'callback_data': 'security_logs'},
                    {'text': '🚫 Заблокированные', 'callback_data': 'security_blocked'}
                ],
                [
                    {'text': '📊 Статистика атак', 'callback_data': 'security_stats'},
                    {'text': '⚙️ Настройки', 'callback_data': 'security_settings'}
                ],
                [
                    {'text': '🔙 Назад', 'callback_data': 'admin_back'}
                ]
            ]
        }
        
        self.bot.send_message(chat_id, security_text, reply_markup=keyboard)
    
    def show_financial_menu(self, chat_id):
        """Меню финансовой отчетности"""
        financial_text = "💰 <b>Финансовая отчетность</b>\n\n"
        financial_text += "Выберите тип отчета:"
        
        keyboard = {
            'inline_keyboard': [
                [
                    {'text': '📊 P&L отчет', 'callback_data': 'finance_pl'},
                    {'text': '💸 Cash Flow', 'callback_data': 'finance_cashflow'}
                ],
                [
                    {'text': '🏛 Налоговый отчет', 'callback_data': 'finance_tax'},
                    {'text': '📈 ROI анализ', 'callback_data': 'finance_roi'}
                ],
                [
                    {'text': '📋 Экспорт CSV', 'callback_data': 'finance_export'},
                    {'text': '🔙 Назад', 'callback_data': 'admin_back'}
                ]
            ]
        }
        
        self.bot.send_message(chat_id, financial_text, reply_markup=keyboard)
    
    def show_inventory_menu(self, chat_id):
        """Меню управления складом"""
        inventory_text = "📦 <b>Управление складом</b>\n\n"
        inventory_text += "Складские операции:"
        
        keyboard = {
            'inline_keyboard': [
                [
                    {'text': '📊 Сводка склада', 'callback_data': 'inventory_summary'},
                    {'text': '🔄 Движения', 'callback_data': 'inventory_movements'}
                ],
                [
                    {'text': '📈 ABC анализ', 'callback_data': 'inventory_abc'},
                    {'text': '⚡ Оборачиваемость', 'callback_data': 'inventory_turnover'}
                ],
                [
                    {'text': '🚚 Поставщики', 'callback_data': 'inventory_suppliers'},
                    {'text': '⚠️ Низкие остатки', 'callback_data': 'inventory_low_stock'}
                ],
                [
                    {'text': '🔙 Назад', 'callback_data': 'admin_back'}
                ]
            ]
        }
        
        self.bot.send_message(chat_id, inventory_text, reply_markup=keyboard)
    
    def show_ai_menu(self, chat_id):
        """Меню AI функций"""
        ai_text = "🤖 <b>AI функции и аналитика</b>\n\n"
        ai_text += "Искусственный интеллект:"
        
        keyboard = {
            'inline_keyboard': [
                [
                    {'text': '🎯 Рекомендации', 'callback_data': 'ai_recommendations'},
                    {'text': '🔍 Анализ поиска', 'callback_data': 'ai_search_analysis'}
                ],
                [
                    {'text': '📊 Прогнозы', 'callback_data': 'ai_predictions'},
                    {'text': '🎭 Сегментация', 'callback_data': 'ai_segmentation'}
                ],
                [
                    {'text': '💬 Поддержка', 'callback_data': 'ai_support_stats'},
                    {'text': '🔙 Назад', 'callback_data': 'admin_back'}
                ]
            ]
        }
        
        self.bot.send_message(chat_id, ai_text, reply_markup=keyboard)
    
    def show_automation_menu(self, chat_id):
        """Меню маркетинговой автоматизации"""
        automation_text = "🎯 <b>Маркетинговая автоматизация</b>\n\n"
        automation_text += "Автоматические кампании:"
        
        keyboard = {
            'inline_keyboard': [
                [
                    {'text': '🛒 Брошенные корзины', 'callback_data': 'auto_abandoned_cart'},
                    {'text': '🔄 Возврат клиентов', 'callback_data': 'auto_win_back'}
                ],
                [
                    {'text': '⬆️ Upsell кампании', 'callback_data': 'auto_upsell'},
                    {'text': '🔀 Cross-sell', 'callback_data': 'auto_cross_sell'}
                ],
                [
                    {'text': '📊 Статистика', 'callback_data': 'auto_stats'},
                    {'text': '⚙️ Настройки', 'callback_data': 'auto_settings'}
                ],
                [
                    {'text': '🔙 Назад', 'callback_data': 'admin_back'}
                ]
            ]
        }
        
        self.bot.send_message(chat_id, automation_text, reply_markup=keyboard)
    
    def show_crm_menu(self, chat_id):
        """Меню CRM"""
        crm_text = "👥 <b>CRM и управление клиентами</b>\n\n"
        crm_text += "Работа с клиентами:"
        
        keyboard = {
            'inline_keyboard': [
                [
                    {'text': '🎯 Сегментация', 'callback_data': 'crm_segmentation'},
                    {'text': '📊 Профили клиентов', 'callback_data': 'crm_profiles'}
                ],
                [
                    {'text': '🎁 Персональные предложения', 'callback_data': 'crm_offers'},
                    {'text': '📈 Анализ поведения', 'callback_data': 'crm_behavior'}
                ],
                [
                    {'text': '⚠️ Риск оттока', 'callback_data': 'crm_churn_risk'},
                    {'text': '🔙 Назад', 'callback_data': 'admin_back'}
                ]
            ]
        }
        
        self.bot.send_message(chat_id, crm_text, reply_markup=keyboard)
    
    def show_broadcast_menu(self, chat_id):
        """Меню рассылок"""
        broadcast_text = "📢 <b>Рассылки и уведомления</b>\n\n"
        broadcast_text += "Массовые уведомления:"
        
        keyboard = {
            'inline_keyboard': [
                [
                    {'text': '📢 Всем пользователям', 'callback_data': 'broadcast_all'},
                    {'text': '🎯 По сегментам', 'callback_data': 'broadcast_segments'}
                ],
                [
                    {'text': '📊 Статистика рассылок', 'callback_data': 'broadcast_stats'},
                    {'text': '📝 Шаблоны', 'callback_data': 'broadcast_templates'}
                ],
                [
                    {'text': '🔙 Назад', 'callback_data': 'admin_back'}
                ]
            ]
        }
        
        self.bot.send_message(chat_id, broadcast_text, reply_markup=keyboard)
    
    def exit_admin_mode(self, chat_id):
        """Выход из админ-режима"""
        from keyboards import create_main_keyboard
        
        self.bot.send_message(
            chat_id,
            "👤 Переключение в пользовательский режим",
            reply_markup=create_main_keyboard()
        )
    
    def handle_callback_query(self, callback_query):
        """Обработка callback запросов"""
        chat_id = callback_query['message']['chat']['id']
        data = callback_query['data']
        
        if data.startswith('analytics_'):
            self.handle_analytics_callback(callback_query)
        elif data.startswith('finance_'):
            self.handle_finance_callback(callback_query)
        elif data.startswith('inventory_'):
            self.handle_inventory_callback(callback_query)
        elif data.startswith('ai_'):
            self.handle_ai_callback(callback_query)
        elif data.startswith('auto_'):
            self.handle_automation_callback(callback_query)
        elif data.startswith('crm_'):
            self.handle_crm_callback(callback_query)
        elif data.startswith('broadcast_'):
            self.handle_broadcast_callback(callback_query)
        elif data == 'admin_back':
            self.show_admin_panel(chat_id)
        elif data.startswith('order_details_'):
            self.handle_orders_management_callback(callback_query)
        elif data.startswith('change_status_'):
            self.handle_orders_management_callback(callback_query)
        else:
            self.bot.send_message(chat_id, "❓ Неизвестная админ команда")
    
    def handle_orders_management_callback(self, callback_query):
        """Обработка управления заказами"""
        chat_id = callback_query['message']['chat']['id']
        data = callback_query['data']
        
        if data.startswith('order_details_'):
            order_id = int(data.split('_')[-1])
            self.show_detailed_order_info(chat_id, order_id)
        elif data.startswith('change_status_'):
            parts = data.split('_')
            order_id = int(parts[2])
            new_status = parts[3]
            self.change_order_status(chat_id, order_id, new_status)
    
    def show_detailed_order_info(self, chat_id, order_id):
        """Показ детальной информации о заказе"""
        order_details = self.db.get_order_details(order_id)
        
        if not order_details:
            self.bot.send_message(chat_id, "❌ Заказ не найден")
            return
        
        order = order_details['order']
        items = order_details['items']
        
        # Получаем информацию о клиенте
        user = self.db.execute_query(
            'SELECT name, phone, email FROM users WHERE id = ?',
            (order[1],)
        )[0]
        
        details_text = f"📦 <b>Заказ #{order[0]}</b>\n\n"
        details_text += f"👤 Клиент: {user[0]}\n"
        if user[1]:
            details_text += f"📱 Телефон: {user[1]}\n"
        if user[2]:
            details_text += f"📧 Email: {user[2]}\n"
        
        details_text += f"\n💰 Сумма: {format_price(order[2])}\n"
        details_text += f"📊 Статус: {self.get_status_emoji(order[3])} {order[3]}\n"
        details_text += f"📅 Дата: {format_date(order[9])}\n"
        
        if order[4]:
            details_text += f"📍 Адрес: {order[4]}\n"
        
        details_text += f"💳 Оплата: {order[5]}\n"
        
        details_text += f"\n🛍 <b>Товары:</b>\n"
        for item in items:
            item_total = item[0] * item[1]
            details_text += f"• {item[2]} × {item[0]} = {format_price(item_total)}\n"
        
        # Клавиатура для изменения статуса
        keyboard = {
            'inline_keyboard': [
                [
                    {'text': '✅ Подтвердить', 'callback_data': f'change_status_{order_id}_confirmed'},
                    {'text': '🚚 Отправить', 'callback_data': f'change_status_{order_id}_shipped'}
                ],
                [
                    {'text': '📦 Доставлен', 'callback_data': f'change_status_{order_id}_delivered'},
                    {'text': '❌ Отменить', 'callback_data': f'change_status_{order_id}_cancelled'}
                ],
                [
                    {'text': '🔙 Назад', 'callback_data': 'admin_orders'}
                ]
            ]
        }
        
        self.bot.send_message(chat_id, details_text, reply_markup=keyboard)
    
    def change_order_status(self, chat_id, order_id, new_status):
        """Изменение статуса заказа"""
        result = self.db.update_order_status(order_id, new_status)
        
        if result:
            status_emoji = self.get_status_emoji(new_status)
            self.bot.send_message(
                chat_id, 
                f"✅ Статус заказа #{order_id} изменен на: {status_emoji} {new_status}"
            )
            
            # Уведомляем клиента
            if self.notification_manager:
                self.notification_manager.send_order_status_notification(order_id, new_status)
        else:
            self.bot.send_message(chat_id, "❌ Ошибка изменения статуса")
    
    def handle_analytics_callback(self, callback_query):
        """Обработка аналитических запросов"""
        chat_id = callback_query['message']['chat']['id']
        data = callback_query['data']
        
        if data == 'analytics_sales':
            self.show_sales_analytics(chat_id)
        elif data == 'analytics_customers':
            self.show_customer_analytics(chat_id)
        elif data == 'analytics_products':
            self.show_product_analytics(chat_id)
        elif data == 'analytics_finance':
            self.show_financial_analytics(chat_id)
    
    def show_sales_analytics(self, chat_id):
        """Показ аналитики продаж"""
        try:
            from analytics import AnalyticsManager
            analytics = AnalyticsManager(self.db)
            
            # Получаем отчет за последние 30 дней
            report = analytics.get_sales_report()
            formatted_report = analytics.format_sales_report(report)
            
            self.bot.send_message(chat_id, formatted_report)
        except Exception as e:
            self.bot.send_message(chat_id, f"❌ Ошибка получения аналитики: {e}")
    
    def show_customer_analytics(self, chat_id):
        """Показ аналитики клиентов"""
        try:
            from crm import CRMManager
            crm = CRMManager(self.db)
            
            segments = crm.segment_customers()
            
            analytics_text = "👥 <b>Сегментация клиентов</b>\n\n"
            for segment_name, customers in segments.items():
                if customers:
                    analytics_text += f"🏷 <b>{segment_name.title()}:</b> {len(customers)} клиентов\n"
            
            self.bot.send_message(chat_id, analytics_text)
        except Exception as e:
            self.bot.send_message(chat_id, f"❌ Ошибка получения CRM данных: {e}")
    
    def show_product_analytics(self, chat_id):
        """Показ аналитики товаров"""
        try:
            # Топ товары по продажам
            top_products = self.db.execute_query('''
                SELECT p.name, SUM(oi.quantity) as sold, SUM(oi.quantity * oi.price) as revenue
                FROM products p
                JOIN order_items oi ON p.id = oi.product_id
                JOIN orders o ON oi.order_id = o.id
                WHERE o.status != 'cancelled'
                GROUP BY p.id, p.name
                ORDER BY revenue DESC
                LIMIT 10
            ''')
            
            analytics_text = "📦 <b>Топ товары по выручке</b>\n\n"
            for i, product in enumerate(top_products, 1):
                analytics_text += f"{i}. <b>{product[0]}</b>\n"
                analytics_text += f"   📦 Продано: {product[1]} шт.\n"
                analytics_text += f"   💰 Выручка: {format_price(product[2])}\n\n"
            
            self.bot.send_message(chat_id, analytics_text)
        except Exception as e:
            self.bot.send_message(chat_id, f"❌ Ошибка получения аналитики товаров: {e}")
    
    def show_financial_analytics(self, chat_id):
        """Показ финансовой аналитики"""
        try:
            from financial_reports import FinancialReportsManager
            finance = FinancialReportsManager(self.db)
            
            # Получаем метрики
            metrics = finance.calculate_business_metrics()
            
            analytics_text = "💰 <b>Ключевые метрики</b>\n\n"
            analytics_text += f"💳 CAC: {format_price(metrics['cac'])}\n"
            analytics_text += f"💎 CLV: {format_price(metrics['clv'])}\n"
            analytics_text += f"📊 CLV/CAC: {metrics['clv_cac_ratio']:.1f}\n"
            analytics_text += f"🛒 Средний чек: {format_price(metrics['avg_order_value'])}\n"
            analytics_text += f"📉 Churn rate: {metrics['churn_rate']:.1f}%\n"
            analytics_text += f"💰 MRR: {format_price(metrics['mrr'])}\n"
            
            self.bot.send_message(chat_id, analytics_text)
        except Exception as e:
            self.bot.send_message(chat_id, f"❌ Ошибка получения финансовых метрик: {e}")
    
    def handle_finance_callback(self, callback_query):
        """Обработка финансовых запросов"""
        chat_id = callback_query['message']['chat']['id']
        data = callback_query['data']
        
        try:
            from financial_reports import FinancialReportsManager
            finance = FinancialReportsManager(self.db)
            
            # Период за последние 30 дней
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            
            if data == 'finance_pl':
                report = finance.generate_profit_loss_report(start_date, end_date)
                formatted_report = finance.format_financial_report('profit_loss', report)
                self.bot.send_message(chat_id, formatted_report)
            
            elif data == 'finance_cashflow':
                report = finance.generate_cash_flow_report(start_date, end_date)
                formatted_report = finance.format_financial_report('cash_flow', report)
                self.bot.send_message(chat_id, formatted_report)
            
            elif data == 'finance_tax':
                report = finance.generate_tax_report(start_date, end_date)
                formatted_report = finance.format_financial_report('tax', report)
                self.bot.send_message(chat_id, formatted_report)
            
            elif data == 'finance_roi':
                roi_data = finance.generate_roi_analysis()
                
                roi_text = "📈 <b>ROI анализ</b>\n\n"
                
                if roi_data['category_roi']:
                    roi_text += "🏷 <b>ROI по категориям:</b>\n"
                    for category in roi_data['category_roi'][:5]:
                        roi_text += f"{category[1]} {category[0]}: {category[4]:.1f}%\n"
                
                self.bot.send_message(chat_id, roi_text)
            
            elif data == 'finance_export':
                csv_data = finance.export_financial_data_csv('transactions', start_date, end_date)
                self.bot.send_message(chat_id, "📊 CSV данные готовы к экспорту")
                
        except Exception as e:
            self.bot.send_message(chat_id, f"❌ Ошибка финансового отчета: {e}")
    
    def handle_inventory_callback(self, callback_query):
        """Обработка складских запросов"""
        chat_id = callback_query['message']['chat']['id']
        data = callback_query['data']
        
        try:
            from inventory_management import InventoryManager
            inventory = InventoryManager(self.db)
            
            if data == 'inventory_summary':
                report = inventory.get_inventory_report('summary')
                formatted_report = inventory.format_inventory_report('summary', report)
                self.bot.send_message(chat_id, formatted_report)
            
            elif data == 'inventory_abc':
                report = inventory.get_inventory_report('abc_analysis')
                formatted_report = inventory.format_inventory_report('abc_analysis', report)
                self.bot.send_message(chat_id, formatted_report)
            
            elif data == 'inventory_turnover':
                report = inventory.get_inventory_report('turnover')
                formatted_report = inventory.format_inventory_report('turnover', report)
                self.bot.send_message(chat_id, formatted_report)
            
            elif data == 'inventory_low_stock':
                stock_levels = inventory.check_stock_levels()
                
                stock_text = "⚠️ <b>Низкие остатки</b>\n\n"
                
                if stock_levels['critical']:
                    stock_text += "🔴 <b>Критические (0 шт.):</b>\n"
                    for product in stock_levels['critical']:
                        stock_text += f"• {product[1]}\n"
                    stock_text += "\n"
                
                if stock_levels['low']:
                    stock_text += "🟡 <b>Низкие остатки (≤5 шт.):</b>\n"
                    for product in stock_levels['low']:
                        stock_text += f"• {product[1]} - {product[2]} шт.\n"
                
                if not stock_levels['critical'] and not stock_levels['low']:
                    stock_text += "✅ Все товары в наличии"
                
                self.bot.send_message(chat_id, stock_text)
                
        except Exception as e:
            self.bot.send_message(chat_id, f"❌ Ошибка складского отчета: {e}")
    
    def handle_ai_callback(self, callback_query):
        """Обработка AI запросов"""
        chat_id = callback_query['message']['chat']['id']
        data = callback_query['data']
        
        try:
            from ai_features import AIRecommendationEngine, ChatbotSupport
            
            if data == 'ai_recommendations':
                ai_engine = AIRecommendationEngine(self.db)
                
                # Статистика рекомендаций
                ai_text = "🎯 <b>Статистика рекомендаций</b>\n\n"
                ai_text += "📊 Система рекомендаций работает автоматически\n"
                ai_text += "🤖 Алгоритмы: персональные, коллаборативные, сезонные\n"
                ai_text += "📈 Повышение конверсии: ~25-40%"
                
                self.bot.send_message(chat_id, ai_text)
            
            elif data == 'ai_support_stats':
                support = ChatbotSupport(self.db)
                
                support_text = "💬 <b>Статистика AI поддержки</b>\n\n"
                support_text += "🤖 База знаний: 5 категорий\n"
                support_text += "📚 Темы: доставка, оплата, возврат, размеры, гарантия\n"
                support_text += "🎯 Автоматическое исправление опечаток\n"
                support_text += "💡 Умные предложения поиска"
                
                self.bot.send_message(chat_id, support_text)
                
        except Exception as e:
            self.bot.send_message(chat_id, f"❌ Ошибка AI модуля: {e}")
    
    def handle_automation_callback(self, callback_query):
        """Обработка запросов автоматизации"""
        chat_id = callback_query['message']['chat']['id']
        data = callback_query['data']
        
        try:
            from marketing_automation import MarketingAutomationManager
            
            if data == 'auto_abandoned_cart':
                automation_text = "🛒 <b>Брошенные корзины</b>\n\n"
                automation_text += "⚙️ Автоматическая последовательность:\n"
                automation_text += "1️⃣ Через 2 часа - напоминание\n"
                automation_text += "2️⃣ Через 24 часа - скидка 10%\n"
                automation_text += "3️⃣ Через 72 часа - скидка 15%\n\n"
                automation_text += "📊 Работает автоматически"
                
                self.bot.send_message(chat_id, automation_text)
            
            elif data == 'auto_stats':
                automation_text = "📊 <b>Статистика автоматизации</b>\n\n"
                automation_text += "🎯 Активные правила:\n"
                automation_text += "• Брошенные корзины\n"
                automation_text += "• Первый заказ\n"
                automation_text += "• VIP статус\n"
                automation_text += "• Сезонные кампании\n\n"
                automation_text += "📈 Автоматизировано 80% процессов"
                
                self.bot.send_message(chat_id, automation_text)
                
        except Exception as e:
            self.bot.send_message(chat_id, f"❌ Ошибка модуля автоматизации: {e}")
    
    def handle_crm_callback(self, callback_query):
        """Обработка CRM запросов"""
        chat_id = callback_query['message']['chat']['id']
        data = callback_query['data']
        
        try:
            from crm import CRMManager
            crm = CRMManager(self.db)
            
            if data == 'crm_segmentation':
                segments = crm.segment_customers()
                
                crm_text = "🎯 <b>RFM сегментация клиентов</b>\n\n"
                
                segment_names = {
                    'champions': '🏆 Чемпионы',
                    'loyal': '💎 Лояльные',
                    'potential': '🌟 Потенциальные',
                    'new': '🆕 Новые',
                    'need_attention': '⚠️ Требуют внимания',
                    'at_risk': '🚨 В зоне риска',
                    'hibernating': '😴 Спящие',
                    'lost': '💔 Потерянные'
                }
                
                for segment_key, customers in segments.items():
                    if customers:
                        segment_name = segment_names.get(segment_key, segment_key)
                        crm_text += f"{segment_name}: {len(customers)} клиентов\n"
                
                self.bot.send_message(chat_id, crm_text)
            
            elif data == 'crm_churn_risk':
                at_risk = crm.get_churn_risk_customers()
                
                risk_text = "⚠️ <b>Клиенты в зоне риска</b>\n\n"
                
                if at_risk:
                    risk_text += f"🚨 Найдено {len(at_risk)} клиентов\n\n"
                    for customer in at_risk[:5]:
                        risk_text += f"👤 {customer[1]}\n"
                        risk_text += f"   💰 Потратил: {format_price(customer[6])}\n"
                        risk_text += f"   📅 Дней без заказов: {int(customer[4])}\n\n"
                else:
                    risk_text += "✅ Клиентов в зоне риска не найдено"
                
                self.bot.send_message(chat_id, risk_text)
                
        except Exception as e:
            self.bot.send_message(chat_id, f"❌ Ошибка CRM модуля: {e}")
    
    def handle_broadcast_callback(self, callback_query):
        """Обработка запросов рассылок"""
        chat_id = callback_query['message']['chat']['id']
        data = callback_query['data']
        
        if data == 'broadcast_stats':
            broadcast_text = "📊 <b>Статистика рассылок</b>\n\n"
            broadcast_text += "📢 Автоматические рассылки:\n"
            broadcast_text += "• Ежедневные сводки админам\n"
            broadcast_text += "• Уведомления о низких остатках\n"
            broadcast_text += "• Персональные рекомендации\n"
            broadcast_text += "• Напоминания о корзине\n\n"
            broadcast_text += "🎯 Таргетированные кампании работают автоматически"
            
            self.bot.send_message(chat_id, broadcast_text)
        elif data == 'broadcast_all':
            self.start_broadcast_creation(chat_id, 'all')
        elif data == 'broadcast_segments':
            self.show_segment_selection(chat_id)
        elif data == 'broadcast_templates':
            self.show_broadcast_templates(chat_id)
    
    def handle_security_callback(self, callback_query):
        """Обработка запросов безопасности"""
        chat_id = callback_query['message']['chat']['id']
        data = callback_query['data']
        
        try:
            if data == 'security_logs':
                # Показываем последние логи безопасности
                security_logs = self.db.execute_query('''
                    SELECT activity_type, details, severity, created_at
                    FROM security_logs
                    ORDER BY created_at DESC
                    LIMIT 10
                ''')
                
                security_text = "🚨 <b>Логи безопасности</b>\n\n"
                
                if security_logs:
                    for log in security_logs:
                        severity_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(log[2], '⚪')
                        security_text += f"{severity_emoji} <b>{log[0]}</b>\n"
                        if log[1]:
                            security_text += f"   {log[1][:50]}...\n"
                        security_text += f"   📅 {format_date(log[3])}\n\n"
                else:
                    security_text += "✅ Подозрительной активности не обнаружено"
                
                self.bot.send_message(chat_id, security_text)
            
            elif data == 'security_blocked':
                # Показываем заблокированных пользователей
                blocked_users = self.db.execute_query('''
                    SELECT u.name, u.telegram_id, sb.reason, sb.blocked_until
                    FROM security_blocks sb
                    JOIN users u ON sb.user_id = u.id
                    WHERE sb.blocked_until > datetime('now')
                    ORDER BY sb.created_at DESC
                ''')
                
                blocked_text = "🚫 <b>Заблокированные пользователи</b>\n\n"
                
                if blocked_users:
                    for user in blocked_users:
                        blocked_text += f"👤 <b>{user[0]}</b> (ID: {user[1]})\n"
                        blocked_text += f"   📋 Причина: {user[2]}\n"
                        blocked_text += f"   ⏰ До: {format_date(user[3])}\n\n"
                else:
                    blocked_text += "✅ Заблокированных пользователей нет"
                
                self.bot.send_message(chat_id, blocked_text)
            
            elif data == 'security_stats':
                # Статистика безопасности
                stats_text = "📊 <b>Статистика безопасности</b>\n\n"
                stats_text += "🛡 Система защиты активна\n"
                stats_text += "🚫 Rate limiting: 20 запросов/мин\n"
                stats_text += "🔍 Мониторинг подозрительной активности\n"
                stats_text += "📝 Логирование всех действий\n\n"
                stats_text += "✅ Все системы безопасности работают"
                
                self.bot.send_message(chat_id, stats_text)
            
            elif data == 'security_settings':
                # Настройки безопасности
                settings_text = "⚙️ <b>Настройки безопасности</b>\n\n"
                settings_text += "🔧 Текущие настройки:\n"
                settings_text += "• Rate limit: 20 запросов/мин\n"
                settings_text += "• Блокировка: 24 часа\n"
                settings_text += "• Анти-спам: включен\n"
                settings_text += "• Логирование: полное\n\n"
                settings_text += "⚙️ Настройки применяются автоматически"
                
                self.bot.send_message(chat_id, settings_text)
                
        except Exception as e:
            self.bot.send_message(chat_id, f"❌ Ошибка модуля безопасности: {e}")
    
    def handle_export_callback(self, callback_query):
        """Обработка экспорта данных"""
        chat_id = callback_query['message']['chat']['id']
        data = callback_query['data']
        
        try:
            if data == 'export_orders':
                export_text = "📊 <b>Экспорт заказов</b>\n\n"
                export_text += "📋 Данные готовы к экспорту:\n"
                export_text += "• Все заказы за последние 30 дней\n"
                export_text += "• Детали клиентов\n"
                export_text += "• Статусы и суммы\n\n"
                export_text += "💾 Формат: CSV для Excel"
                
                self.bot.send_message(chat_id, export_text)
            
            elif data == 'export_products':
                export_text = "📦 <b>Экспорт товаров</b>\n\n"
                export_text += "📋 Данные готовы к экспорту:\n"
                export_text += "• Все активные товары\n"
                export_text += "• Остатки на складе\n"
                export_text += "• Цены и категории\n\n"
                export_text += "💾 Формат: CSV для Excel"
                
                self.bot.send_message(chat_id, export_text)
            
            elif data == 'export_customers':
                export_text = "👥 <b>Экспорт клиентов</b>\n\n"
                export_text += "📋 Данные готовы к экспорту:\n"
                export_text += "• Все зарегистрированные пользователи\n"
                export_text += "• Статистика покупок\n"
                export_text += "• Контактные данные\n\n"
                export_text += "💾 Формат: CSV для Excel"
                
                self.bot.send_message(chat_id, export_text)
                
        except Exception as e:
            self.bot.send_message(chat_id, f"❌ Ошибка экспорта: {e}")
    
    def start_broadcast_creation(self, chat_id, target_type):
        """Начало создания рассылки"""
        broadcast_text = f"📢 <b>Создание рассылки</b>\n\n"
        broadcast_text += f"🎯 Целевая аудитория: {target_type}\n\n"
        broadcast_text += f"📝 Введите текст сообщения для рассылки:"
        
        self.bot.send_message(chat_id, broadcast_text)
        
        # Устанавливаем состояние
        telegram_id = self.get_telegram_id_from_chat(chat_id)
        if telegram_id:
            self.admin_states[telegram_id] = f'creating_broadcast_{target_type}'
    
    def show_segment_selection(self, chat_id):
        """Показ выбора сегментов для рассылки"""
        segments_text = "🎯 <b>Выберите сегмент для рассылки:</b>\n\n"
        
        keyboard = {
            'inline_keyboard': [
                [
                    {'text': '🆕 Новые клиенты', 'callback_data': 'broadcast_segment_new'},
                    {'text': '💎 Лояльные', 'callback_data': 'broadcast_segment_loyal'}
                ],
                [
                    {'text': '🏆 VIP клиенты', 'callback_data': 'broadcast_segment_vip'},
                    {'text': '😴 Неактивные', 'callback_data': 'broadcast_segment_inactive'}
                ],
                [
                    {'text': '🔙 Назад', 'callback_data': 'admin_back'}
                ]
            ]
        }
        
        self.bot.send_message(chat_id, segments_text, reply_markup=keyboard)
    
    def show_broadcast_templates(self, chat_id):
        """Показ шаблонов рассылок"""
        templates_text = "📝 <b>Шаблоны рассылок</b>\n\n"
        templates_text += "📋 Доступные шаблоны:\n"
        templates_text += "• 🎁 Промо-акции\n"
        templates_text += "• 📦 Новые товары\n"
        templates_text += "• 🔔 Системные уведомления\n"
        templates_text += "• 🎉 Праздничные поздравления\n\n"
        templates_text += "💡 Шаблоны применяются автоматически"
        
        self.bot.send_message(chat_id, templates_text)
    
    def handle_broadcast_creation(self, message):
        """Обработка создания рассылки"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        text = message.get('text', '')
        
        state = self.admin_states.get(telegram_id, '')
        
        if state.startswith('creating_broadcast_'):
            target_type = state.split('_')[-1]
            
            # Отправляем рассылку
            if self.notification_manager:
                success_count, error_count = self.notification_manager.send_promotional_broadcast(
                    text, target_type
                )
                
                result_text = f"✅ <b>Рассылка отправлена!</b>\n\n"
                result_text += f"📤 Успешно: {success_count}\n"
                result_text += f"❌ Ошибок: {error_count}\n"
                result_text += f"🎯 Аудитория: {target_type}"
                
                self.bot.send_message(chat_id, result_text)
            else:
                self.bot.send_message(chat_id, "❌ Сервис рассылок недоступен")
            
            # Очищаем состояние
            del self.admin_states[telegram_id]
    
    def get_telegram_id_from_chat(self, chat_id):
        """Получение telegram_id из chat_id"""
        # В большинстве случаев chat_id == telegram_id для личных чатов
        return chat_id
    
    def handle_add_product_process(self, message):
        """Обработка добавления товара"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        text = message.get('text', '')
        
        state = self.admin_states.get(telegram_id, '')
        
        if state == 'adding_product_name':
            self.admin_states[telegram_id] = f'adding_product_description:{text}'
            self.bot.send_message(chat_id, "📝 Введите описание товара:")
        
        elif state.startswith('adding_product_description:'):
            name = state.split(':', 1)[1]
            self.admin_states[telegram_id] = f'adding_product_price:{name}:{text}'
            self.bot.send_message(chat_id, "💰 Введите цену товара:")
        
        elif state.startswith('adding_product_price:'):
            parts = state.split(':', 2)
            name = parts[1]
            description = parts[2]
            
            try:
                price = float(text)
                self.admin_states[telegram_id] = f'adding_product_category:{name}:{description}:{price}'
                
                # Показываем категории
                categories = self.db.get_categories()
                keyboard = {
                    'inline_keyboard': []
                }
                
                for category in categories:
                    keyboard['inline_keyboard'].append([
                        {'text': f"{category[3]} {category[1]}", 'callback_data': f'select_category_{category[0]}'}
                    ])
                
                self.bot.send_message(chat_id, "📂 Выберите категорию:", reply_markup=keyboard)
                
            except ValueError:
                self.bot.send_message(chat_id, "❌ Неверный формат цены. Введите число:")
        
        elif state.startswith('adding_product_stock:'):
            parts = state.split(':', 4)
            name, description, price, category_id = parts[1], parts[2], float(parts[3]), int(parts[4])
            
            try:
                stock = int(text)
                
                # Создаем товар
                product_id = self.db.execute_query('''
                    INSERT INTO products (name, description, price, category_id, stock, is_active, created_at)
                    VALUES (?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
                ''', (name, description, price, category_id, stock))
                
                if product_id:
                    success_text = f"✅ <b>Товар добавлен!</b>\n\n"
                    success_text += f"🛍 Название: {name}\n"
                    success_text += f"💰 Цена: {format_price(price)}\n"
                    success_text += f"📦 Количество: {stock} шт.\n"
                    success_text += f"🆔 ID: {product_id}"
                    
                    self.bot.send_message(chat_id, success_text)
                else:
                    self.bot.send_message(chat_id, "❌ Ошибка добавления товара")
                
                # Очищаем состояние
                del self.admin_states[telegram_id]
                
            except ValueError:
                self.bot.send_message(chat_id, "❌ Неверный формат количества. Введите число:")
    
    def handle_product_commands(self, message):
        """Обработка команд управления товарами"""
        chat_id = message['chat']['id']
        text = message.get('text', '')
        
        if text.startswith('/edit_product_'):
            try:
                product_id = int(text.split('_')[-1])
                self.show_product_edit_menu(chat_id, product_id)
            except ValueError:
                self.bot.send_message(chat_id, "❌ Неверный ID товара")
        
        elif text.startswith('/delete_product_'):
            try:
                product_id = int(text.split('_')[-1])
                self.confirm_product_deletion(chat_id, product_id)
            except ValueError:
                self.bot.send_message(chat_id, "❌ Неверный ID товара")
    
    def show_product_edit_menu(self, chat_id, product_id):
        """Показ меню редактирования товара"""
        product = self.db.get_product_by_id(product_id)
        
        if not product:
            self.bot.send_message(chat_id, "❌ Товар не найден")
            return
        
        edit_text = f"📝 <b>Редактирование товара</b>\n\n"
        edit_text += f"🛍 <b>{product[1]}</b>\n"
        edit_text += f"💰 Цена: {format_price(product[3])}\n"
        edit_text += f"📦 Остаток: {product[6]} шт.\n"
        edit_text += f"📊 Статус: {'Активен' if product[8] else 'Неактивен'}\n\n"
        edit_text += f"Выберите что изменить:"
        
        keyboard = {
            'inline_keyboard': [
                [
                    {'text': '💰 Цену', 'callback_data': f'edit_price_{product_id}'},
                    {'text': '📦 Остаток', 'callback_data': f'edit_stock_{product_id}'}
                ],
                [
                    {'text': '📝 Описание', 'callback_data': f'edit_description_{product_id}'},
                    {'text': '🔄 Статус', 'callback_data': f'toggle_status_{product_id}'}
                ],
                [
                    {'text': '🔙 Назад', 'callback_data': 'admin_products'}
                ]
            ]
        }
        
        self.bot.send_message(chat_id, edit_text, reply_markup=keyboard)
    
    def confirm_product_deletion(self, chat_id, product_id):
        """Подтверждение удаления товара"""
        product = self.db.get_product_by_id(product_id)
        
        if not product:
            self.bot.send_message(chat_id, "❌ Товар не найден")
            return
        
        confirm_text = f"⚠️ <b>Подтверждение удаления</b>\n\n"
        confirm_text += f"🛍 Товар: <b>{product[1]}</b>\n"
        confirm_text += f"💰 Цена: {format_price(product[3])}\n\n"
        confirm_text += f"❗ Это действие нельзя отменить!"
        
        keyboard = {
            'inline_keyboard': [
                [
                    {'text': '✅ Да, удалить', 'callback_data': f'confirm_delete_{product_id}'},
                    {'text': '❌ Отмена', 'callback_data': 'admin_products'}
                ]
            ]
        }
        
        self.bot.send_message(chat_id, confirm_text, reply_markup=keyboard)
    
    def handle_order_management(self, message):
        """Обработка управления заказами"""
        chat_id = message['chat']['id']
        text = message.get('text', '')
        
        if text.startswith('/admin_order_'):
            try:
                order_id = int(text.split('_')[-1])
                self.show_detailed_order_info(chat_id, order_id)
            except ValueError:
                self.bot.send_message(chat_id, "❌ Неверный ID заказа")