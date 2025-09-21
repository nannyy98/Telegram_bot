"""
Обработчики сообщений для телеграм-бота
"""

import os
import time
import threading
from keyboards import *
from utils import *
from localization import t, get_user_language

class MessageHandler:
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db
        self.user_states = {}
        self.notification_manager = None
        self.payment_processor = None
        self.data_monitor_running = False
        self.start_data_monitor()
    
    def start_data_monitor(self):
        """Запуск мониторинга обновлений данных"""
        if self.data_monitor_running:
            return
            
        def monitor_worker():
            while True:
                try:
                    self.check_data_updates()
                    time.sleep(5)  # Проверяем каждые 5 секунд
                except Exception as e:
                    print(f"Ошибка мониторинга данных: {e}")
                    time.sleep(30)
        
        monitor_thread = threading.Thread(target=monitor_worker, daemon=True)
        monitor_thread.start()
        self.data_monitor_running = True
        print("✅ Мониторинг обновлений данных запущен")
    
    def check_data_updates(self):
        """Проверка флагов обновления данных"""
        update_flag = 'data_update_flag.txt'
        force_flag = 'force_reload_flag.txt'
        
        if os.path.exists(force_flag):
            print("🔄 Принудительная перезагрузка данных...")
            self.reload_all_data()
            try:
                os.remove(force_flag)
            except:
                pass
        elif os.path.exists(update_flag):
            print("🔄 Обновление данных...")
            self.reload_cached_data()
            try:
                os.remove(update_flag)
            except:
                pass
    
    def reload_all_data(self):
        """Полная перезагрузка всех данных"""
        try:
            # Очищаем кэш
            if hasattr(self.bot, 'data_cache'):
                self.bot.data_cache.clear()
            
            # Перезагружаем автопосты
            if hasattr(self.bot, 'scheduled_posts') and self.bot.scheduled_posts:
                self.bot.scheduled_posts.load_schedule_from_database()
            
            print("✅ Данные полностью перезагружены")
        except Exception as e:
            print(f"Ошибка перезагрузки данных: {e}")
    
    def reload_cached_data(self):
        """Перезагрузка кэшированных данных"""
        try:
            # Обновляем кэш категорий и товаров
            if hasattr(self.bot, 'data_cache'):
                self.bot.data_cache['categories'] = self.db.get_categories()
                self.bot.data_cache['products'] = self.db.execute_query(
                    'SELECT * FROM products WHERE is_active = 1'
                )
            
            print("✅ Кэш данных обновлен")
        except Exception as e:
            print(f"Ошибка обновления кэша: {e}")
    
    def handle_message(self, message):
        """Основной обработчик сообщений"""
        try:
            chat_id = message['chat']['id']
            telegram_id = message['from']['id']
            text = message.get('text', '')
            
            # Логируем сообщение
            log_user_action(telegram_id, 'message', text[:50])
            
            # Получаем пользователя
            user_data = self.db.get_user_by_telegram_id(telegram_id)
            
            if not user_data:
                # Новый пользователь - начинаем регистрацию
                self.start_registration(message)
                return
            
            user_id = user_data[0][0]
            language = user_data[0][5]
            
            # Проверяем состояние пользователя
            user_state = self.user_states.get(telegram_id, '')
            
            if user_state.startswith('registration_'):
                self.handle_registration(message, user_state)
            elif user_state.startswith('search_'):
                self.handle_search_process(message)
            elif user_state.startswith('review_'):
                self.handle_review_process(message)
            elif user_state.startswith('order_'):
                self.handle_order_process(message)
            elif text == '/start':
                self.handle_start_command(message)
            elif text == '/help' or text == 'ℹ️ Помощь':
                self.handle_help_command(message)
            elif text == '🛍 Каталог':
                self.show_categories(message)
            elif text == '🛒 Корзина':
                self.show_cart(message)
            elif text == '📋 Мои заказы':
                self.show_user_orders(message)
            elif text == '👤 Профиль':
                self.show_user_profile(message)
            elif text == '🔍 Поиск':
                self.start_search(message)
            elif text.startswith('📱') or text.startswith('👕') or text.startswith('🏠'):
                self.handle_category_selection(message)
            elif text.startswith('🍎') or text.startswith('✔️') or text.startswith('👖') or text.startswith('☕') or text.startswith('👟') or text.startswith('💎'):
                self.handle_subcategory_selection(message)
            elif text.startswith('🛍'):
                self.handle_product_selection(message)
            elif text == '🔙 Назад' or text == '🔙 К категориям':
                self.show_categories(message)
            elif text == '🔙 К категориям':
                self.show_categories(message)
            elif text == '🏠 Главная':
                self.show_main_menu(message)
            elif text.startswith('/order_'):
                self.show_order_details(message)
            elif text.startswith('/track_'):
                self.handle_tracking(message)
            elif text.startswith('/promo_'):
                self.handle_promo_code(message)
            else:
                # Обработка как поискового запроса
                self.handle_search_query(message, text)
                
        except Exception as e:
            print(f"Ошибка обработки сообщения: {e}")
            self.send_error_message(chat_id, language if 'language' in locals() else 'ru')
    
    def handle_callback_query(self, callback_query):
        """Обработка inline кнопок"""
        try:
            data = callback_query['data']
            chat_id = callback_query['message']['chat']['id']
            message_id = callback_query['message']['message_id']
            telegram_id = callback_query['from']['id']
            
            # Получаем пользователя
            user_data = self.db.get_user_by_telegram_id(telegram_id)
            if not user_data:
                return
            
            user_id = user_data[0][0]
            language = user_data[0][5]
            
            if data.startswith('add_to_cart_'):
                product_id = int(data.split('_')[3])
                self.add_product_to_cart(callback_query, product_id)
            elif data.startswith('cart_increase_'):
                cart_item_id = int(data.split('_')[2])
                self.update_cart_quantity(callback_query, cart_item_id, 1)
            elif data.startswith('cart_decrease_'):
                cart_item_id = int(data.split('_')[2])
                self.update_cart_quantity(callback_query, cart_item_id, -1)
            elif data.startswith('cart_remove_'):
                cart_item_id = int(data.split('_')[2])
                self.remove_from_cart(callback_query, cart_item_id)
            elif data.startswith('rate_'):
                parts = data.split('_')
                product_id = int(parts[1])
                rating = int(parts[2])
                self.handle_product_rating(callback_query, product_id, rating)
            elif data.startswith('add_to_favorites_'):
                product_id = int(data.split('_')[3])
                self.add_to_favorites(callback_query, product_id)
            elif data.startswith('pay_'):
                self.handle_payment_selection(callback_query)
            elif data == 'show_cart':
                # Создаем фиктивное сообщение для показа корзины
                fake_message = {
                    'chat': {'id': chat_id},
                    'from': {'id': telegram_id}
                }
                self.show_cart(fake_message)
            elif data == 'continue_shopping':
                fake_message = {
                    'chat': {'id': chat_id},
                    'from': {'id': telegram_id}
                }
                self.show_categories(fake_message)
            else:
                # Отвечаем на callback
                self.answer_callback_query(callback_query['id'], "Функция в разработке")
                
        except Exception as e:
            print(f"Ошибка обработки callback: {e}")
    
    def answer_callback_query(self, callback_query_id, text=""):
        """Ответ на callback query"""
        try:
            import urllib.request
            import urllib.parse
            import json
            
            url = f"{self.bot.base_url}/answerCallbackQuery"
            data = {
                'callback_query_id': callback_query_id,
                'text': text
            }
            
            data_encoded = urllib.parse.urlencode(data).encode('utf-8')
            req = urllib.request.Request(url, data=data_encoded, method='POST')
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get('ok', False)
        except Exception as e:
            print(f"Ошибка ответа на callback: {e}")
            return False
    
    def start_registration(self, message):
        """Начало регистрации"""
        try:
            chat_id = message['chat']['id']
            telegram_id = message['from']['id']
            
            # Получаем имя из Telegram
            first_name = message['from'].get('first_name', '')
            last_name = message['from'].get('last_name', '')
            suggested_name = f"{first_name} {last_name}".strip()
            
            self.user_states[telegram_id] = 'registration_name'
            
            welcome_text = """🛍 <b>Добро пожаловать в наш интернет-магазин!</b>

Для начала работы пройдите быструю регистрацию.

👤 <b>Как вас зовут?</b>"""
            
            keyboard = create_registration_keyboard('name', suggested_name)
            self.bot.send_message(chat_id, welcome_text, keyboard)
            
        except Exception as e:
            print(f"Ошибка начала регистрации: {e}")
    
    def handle_registration(self, message, state):
        """Обработка процесса регистрации"""
        try:
            chat_id = message['chat']['id']
            telegram_id = message['from']['id']
            text = message.get('text', '')
            
            if text == '❌ Отмена':
                self.user_states.pop(telegram_id, None)
                self.bot.send_message(chat_id, "Регистрация отменена. Отправьте /start для повторной попытки.")
                return
            
            if state == 'registration_name':
                if len(text) < 2:
                    self.bot.send_message(chat_id, "❌ Имя должно содержать минимум 2 символа. Попробуйте еще раз:")
                    return
                
                self.user_states[telegram_id] = f'registration_phone_{text}'
                
                phone_text = """📱 <b>Укажите ваш номер телефона</b>

Это поможет нам связаться с вами по заказу."""
                
                keyboard = create_registration_keyboard('phone')
                self.bot.send_message(chat_id, phone_text, keyboard)
            
            elif state.startswith('registration_phone_'):
                name = state.split('_', 2)[2]
                phone = None
                
                if text != '⏭ Пропустить':
                    if 'contact' in message:
                        phone = message['contact']['phone_number']
                    else:
                        phone = validate_phone(text)
                        if not phone:
                            self.bot.send_message(chat_id, "❌ Неверный формат номера. Попробуйте еще раз или нажмите 'Пропустить':")
                            return
                
                self.user_states[telegram_id] = f'registration_email_{name}_{phone or ""}'
                
                email_text = """📧 <b>Укажите ваш email</b>

Будем присылать уведомления о заказах и акциях."""
                
                keyboard = create_registration_keyboard('email')
                self.bot.send_message(chat_id, email_text, keyboard)
            
            elif state.startswith('registration_email_'):
                parts = state.split('_', 3)
                name = parts[2]
                phone = parts[3] if len(parts) > 3 and parts[3] else None
                email = None
                
                if text != '⏭ Пропустить':
                    if validate_email(text):
                        email = text
                    else:
                        self.bot.send_message(chat_id, "❌ Неверный формат email. Попробуйте еще раз или нажмите 'Пропустить':")
                        return
                
                self.user_states[telegram_id] = f'registration_language_{name}_{phone or ""}_{email or ""}'
                
                language_text = """🌍 <b>Выберите язык</b>

Выберите удобный для вас язык интерфейса."""
                
                keyboard = create_registration_keyboard('language')
                self.bot.send_message(chat_id, language_text, keyboard)
            
            elif state.startswith('registration_language_'):
                parts = state.split('_', 4)
                name = parts[2]
                phone = parts[3] if len(parts) > 3 and parts[3] else None
                email = parts[4] if len(parts) > 4 and parts[4] else None
                
                language = 'ru'
                if text == '🇺🇿 O\'zbekcha':
                    language = 'uz'
                
                # Создаем пользователя
                user_id = self.db.add_user(telegram_id, name, phone, email, language)
                
                if user_id:
                    # Очищаем состояние
                    self.user_states.pop(telegram_id, None)
                    
                    # Создаем запись лояльности
                    self.db.execute_query(
                        'INSERT OR IGNORE INTO loyalty_points (user_id) VALUES (?)',
                        (user_id,)
                    )
                    
                    # Отправляем приветствие
                    welcome_text = t('registration_complete', language=language)
                    keyboard = create_main_keyboard()
                    self.bot.send_message(chat_id, welcome_text, keyboard)
                    
                    # Запускаем приветственную серию
                    if hasattr(self.bot, 'marketing_automation') and self.bot.marketing_automation:
                        self.bot.marketing_automation.create_welcome_series(user_id)
                else:
                    self.bot.send_message(chat_id, "❌ Ошибка регистрации. Попробуйте позже.")
                    
        except Exception as e:
            print(f"Ошибка обработки регистрации: {e}")
    
    def handle_start_command(self, message):
        """Обработка команды /start"""
        try:
            chat_id = message['chat']['id']
            telegram_id = message['from']['id']
            
            user_data = self.db.get_user_by_telegram_id(telegram_id)
            
            if user_data:
                language = user_data[0][5]
                welcome_text = t('welcome_back', language=language)
                keyboard = create_main_keyboard()
                self.bot.send_message(chat_id, welcome_text, keyboard)
            else:
                self.start_registration(message)
                
        except Exception as e:
            print(f"Ошибка команды start: {e}")
    
    def handle_help_command(self, message):
        """Обработка команды помощи"""
        try:
            chat_id = message['chat']['id']
            telegram_id = message['from']['id']
            
            user_data = self.db.get_user_by_telegram_id(telegram_id)
            language = user_data[0][5] if user_data else 'ru'
            
            help_text = """ℹ️ <b>Справка по использованию бота:</b>

🛍 <b>Каталог</b> - просмотр товаров по категориям
🛒 <b>Корзина</b> - ваши выбранные товары
📋 <b>Мои заказы</b> - история ваших покупок
👤 <b>Профиль</b> - управление вашими данными

<b>Как сделать заказ:</b>
1️⃣ Выберите товары в каталоге
2️⃣ Добавьте их в корзину
3️⃣ Перейдите в корзину и оформите заказ
4️⃣ Укажите адрес и способ оплаты

❓ По вопросам обращайтесь к администратору."""
            
            keyboard = create_main_keyboard()
            self.bot.send_message(chat_id, help_text, keyboard)
            
        except Exception as e:
            print(f"Ошибка команды help: {e}")
    
    def show_categories(self, message):
        """Показ категорий товаров"""
        try:
            chat_id = message['chat']['id']
            
            categories = self.db.get_categories()
            
            if categories:
                text = "🛍 <b>Выберите категорию товаров:</b>"
                keyboard = create_categories_keyboard(categories)
                self.bot.send_message(chat_id, text, keyboard)
            else:
                self.bot.send_message(chat_id, "❌ Категории товаров не найдены")
                
        except Exception as e:
            print(f"Ошибка показа категорий: {e}")
    
    def handle_category_selection(self, message):
        """Обработка выбора категории"""
        try:
            chat_id = message['chat']['id']
            text = message.get('text', '')
            
            # Извлекаем название категории
            category_name = text.split(' ', 1)[1] if ' ' in text else text
            
            # Находим категорию
            categories = self.db.get_categories()
            category_id = None
            
            for category in categories:
                if category[1] == category_name:
                    category_id = category[0]
                    break
            
            if category_id:
                self.show_subcategories_by_category(message, category_id)
            else:
                self.bot.send_message(chat_id, "❌ Категория не найдена")
                
        except Exception as e:
            print(f"Ошибка выбора категории: {e}")
    
    def show_subcategories_by_category(self, message, category_id):
        """Показ подкатегорий по категории"""
        try:
            chat_id = message['chat']['id']
            
            subcategories = self.db.get_products_by_category(category_id)
            
            if subcategories:
                text = "🏷 <b>Выберите бренд или подкатегорию:</b>"
                keyboard = create_subcategories_keyboard(subcategories)
                self.bot.send_message(chat_id, text, keyboard)
            else:
                self.bot.send_message(chat_id, "❌ Подкатегории не найдены")
                
        except Exception as e:
            print(f"Ошибка показа подкатегорий: {e}")
    
    def handle_subcategory_selection(self, message):
        """Обработка выбора подкатегории/бренда"""
        try:
            chat_id = message['chat']['id']
            text = message.get('text', '')
            
            # Извлекаем название подкатегории
            subcategory_name = text.split(' ', 1)[1] if ' ' in text else text
            
            # Находим подкатегорию
            subcategories = self.db.execute_query(
                'SELECT id FROM subcategories WHERE name = ? AND is_active = 1',
                (subcategory_name,)
            )
            
            if subcategories:
                subcategory_id = subcategories[0][0]
                self.show_products_by_subcategory(message, subcategory_id)
            else:
                self.bot.send_message(chat_id, "❌ Подкатегория не найдена")
                
        except Exception as e:
            print(f"Ошибка выбора подкатегории: {e}")
    
    def show_products_by_subcategory(self, message, subcategory_id, page=1):
        """Показ товаров по подкатегории"""
        try:
            chat_id = message['chat']['id']
            
            products = self.db.get_products_by_subcategory(subcategory_id, limit=5, offset=(page-1)*5)
            
            if products:
                for product in products:
                    self.show_product_card(chat_id, product)
            else:
                self.bot.send_message(chat_id, "❌ Товары в этой подкатегории не найдены")
                
        except Exception as e:
            print(f"Ошибка показа товаров по подкатегории: {e}")
    
    def show_product_card(self, chat_id, product):
        """Показ карточки товара"""
        try:
            product_id = product[0]
            name = product[1]
            description = product[2]
            price = product[3]
            image_url = product[5]
            stock = product[6]
            
            # Увеличиваем счетчик просмотров
            self.db.increment_product_views(product_id)
            
            card_text = create_product_card(product)
            keyboard = create_product_inline_keyboard(product_id)
            
            if image_url:
                self.bot.send_photo(chat_id, image_url, card_text, keyboard)
            else:
                self.bot.send_message(chat_id, card_text, keyboard)
                
        except Exception as e:
            print(f"Ошибка показа карточки товара: {e}")
    
    def show_cart(self, message):
        """Показ корзины"""
        try:
            chat_id = message['chat']['id']
            telegram_id = message['from']['id']
            
            user_data = self.db.get_user_by_telegram_id(telegram_id)
            if not user_data:
                return
            
            user_id = user_data[0][0]
            language = user_data[0][5]
            cart_items = self.db.get_cart_items(user_id)
            
            if not cart_items:
                empty_text = t('empty_cart', language=language)
                keyboard = create_cart_keyboard(False)
                self.bot.send_message(chat_id, empty_text, keyboard)
                return
            
            # Показываем товары в корзине
            cart_text = "🛒 <b>Ваша корзина:</b>\n\n"
            total_amount = 0
            
            for item in cart_items:
                item_total = item[2] * item[3]
                total_amount += item_total
                
                cart_text += f"🛍 <b>{item[1]}</b>\n"
                cart_text += f"💰 {format_price(item[2])} × {item[3]} = {format_price(item_total)}\n\n"
            
            cart_text += f"💳 <b>Итого: {format_price(total_amount)}</b>"
            
            keyboard = create_cart_keyboard(True)
            self.bot.send_message(chat_id, cart_text, keyboard)
            
            # Показываем управление каждым товаром
            for item in cart_items:
                item_text = f"🛍 <b>{item[1]}</b>\n"
                item_text += f"💰 {format_price(item[2])} × {item[3]} = {format_price(item[2] * item[3])}"
                
                item_keyboard = create_cart_item_keyboard(item[0], item[3])
                self.bot.send_message(chat_id, item_text, item_keyboard)
                
        except Exception as e:
            print(f"Ошибка показа корзины: {e}")
    
    def show_user_orders(self, message):
        """Показ заказов пользователя"""
        try:
            chat_id = message['chat']['id']
            telegram_id = message['from']['id']
            
            user_data = self.db.get_user_by_telegram_id(telegram_id)
            if not user_data:
                return
            
            user_id = user_data[0][0]
            orders = self.db.get_user_orders(user_id)
            
            if not orders:
                self.bot.send_message(chat_id, "📋 У вас пока нет заказов")
                return
            
            orders_text = "📋 <b>Ваши заказы:</b>\n\n"
            
            for order in orders[:10]:  # Показываем последние 10
                status_emoji = get_order_status_emoji(order[3])
                orders_text += f"{status_emoji} <b>Заказ #{order[0]}</b>\n"
                orders_text += f"💰 {format_price(order[2])}\n"
                orders_text += f"📅 {format_date(order[9])}\n"
                orders_text += f"📋 {get_order_status_text(order[3])}\n\n"
            
            keyboard = create_back_keyboard()
            self.bot.send_message(chat_id, orders_text, keyboard)
            
        except Exception as e:
            print(f"Ошибка показа заказов: {e}")
    
    def show_user_profile(self, message):
        """Показ профиля пользователя"""
        try:
            chat_id = message['chat']['id']
            telegram_id = message['from']['id']
            
            user_data = self.db.get_user_by_telegram_id(telegram_id)
            if not user_data:
                return
            
            user = user_data[0]
            
            profile_text = f"👤 <b>Ваш профиль:</b>\n\n"
            profile_text += f"📝 Имя: {user[2]}\n"
            
            if user[3]:
                profile_text += f"📱 Телефон: {user[3]}\n"
            if user[4]:
                profile_text += f"📧 Email: {user[4]}\n"
            
            profile_text += f"🌍 Язык: {'🇷🇺 Русский' if user[5] == 'ru' else '🇺🇿 O\'zbekcha'}\n"
            profile_text += f"📅 Регистрация: {format_date(user[7])}\n"
            
            # Статистика заказов
            orders_stats = self.db.execute_query('''
                SELECT COUNT(*), COALESCE(SUM(total_amount), 0)
                FROM orders WHERE user_id = ? AND status != 'cancelled'
            ''', (user[0],))
            
            if orders_stats:
                profile_text += f"\n📊 <b>Статистика:</b>\n"
                profile_text += f"📦 Заказов: {orders_stats[0][0]}\n"
                profile_text += f"💰 Потрачено: {format_price(orders_stats[0][1])}\n"
            
            keyboard = create_back_keyboard()
            self.bot.send_message(chat_id, profile_text, keyboard)
            
        except Exception as e:
            print(f"Ошибка показа профиля: {e}")
    
    def start_search(self, message):
        """Начало поиска"""
        try:
            chat_id = message['chat']['id']
            telegram_id = message['from']['id']
            
            self.user_states[telegram_id] = 'search_query'
            
            search_text = """🔍 <b>Поиск товаров</b>

Введите название товара или ключевые слова:"""
            
            keyboard = create_back_keyboard()
            self.bot.send_message(chat_id, search_text, keyboard)
            
        except Exception as e:
            print(f"Ошибка начала поиска: {e}")
    
    def handle_search_query(self, message, query):
        """Обработка поискового запроса"""
        try:
            chat_id = message['chat']['id']
            telegram_id = message['from']['id']
            
            # Логируем поиск
            user_data = self.db.get_user_by_telegram_id(telegram_id)
            if user_data:
                user_id = user_data[0][0]
                self.db.execute_query(
                    'INSERT INTO user_activity_logs (user_id, action, search_query) VALUES (?, ?, ?)',
                    (user_id, 'search', query)
                )
            
            # Ищем товары
            products = self.db.search_products(query, limit=10)
            
            if products:
                search_text = f"🔍 <b>Результаты поиска '{query}':</b>\n\n"
                search_text += f"Найдено {len(products)} товаров:"
                
                self.bot.send_message(chat_id, search_text)
                
                for product in products:
                    self.show_product_card(chat_id, product)
            else:
                not_found_text = f"❌ По запросу '{query}' ничего не найдено.\n\n"
                not_found_text += "💡 Попробуйте:\n"
                not_found_text += "• Изменить запрос\n"
                not_found_text += "• Использовать другие ключевые слова\n"
                not_found_text += "• Просмотреть каталог"
                
                self.bot.send_message(chat_id, not_found_text)
                
        except Exception as e:
            print(f"Ошибка поиска: {e}")
    
    def add_product_to_cart(self, callback_query, product_id):
        """Добавление товара в корзину"""
        try:
            chat_id = callback_query['message']['chat']['id']
            telegram_id = callback_query['from']['id']
            
            user_data = self.db.get_user_by_telegram_id(telegram_id)
            if not user_data:
                return
            
            user_id = user_data[0][0]
            
            # Проверяем есть ли товар уже в корзине
            existing_cart = self.db.execute_query(
                'SELECT id, quantity FROM cart WHERE user_id = ? AND product_id = ?',
                (user_id, product_id)
            )
            
            result = self.db.add_to_cart(user_id, product_id, 1)
            
            if result:
                # Получаем обновленное количество в корзине
                cart_items = self.db.get_cart_items(user_id)
                cart_count = sum(item[3] for item in cart_items) if cart_items else 0
                
                # Получаем количество этого товара в корзине
                current_item = self.db.execute_query(
                    'SELECT quantity FROM cart WHERE user_id = ? AND product_id = ?',
                    (user_id, product_id)
                )
                item_quantity = current_item[0][0] if current_item else 1
                
                product = self.db.get_product_by_id(product_id)
                success_text = f"✅ <b>{product[1]}</b>\n\n"
                success_text += f"📦 Количество: {item_quantity} шт.\n"
                success_text += f"🛒 Всего в корзине: {cart_count} товар(ов)"
                
                # Создаем клавиатуру с обновленным количеством
                keyboard = {
                    'inline_keyboard': [
                        [
                            {'text': '🛒 Перейти в корзину', 'callback_data': 'go_to_cart'},
                            {'text': '➕ Добавить еще', 'callback_data': f'add_to_cart_{product_id}'}
                        ],
                        [
                            {'text': '🛍 Продолжить покупки', 'callback_data': 'continue_shopping'}
                        ]
                    ]
                }
                
                self.bot.send_message(chat_id, success_text, keyboard)
            else:
                self.bot.send_message(chat_id, "❌ Товар недоступен или недостаточно на складе")
                
        except Exception as e:
            print(f"Ошибка добавления в корзину: {e}")
    
    def update_cart_quantity(self, callback_query, cart_item_id, change):
        """Изменение количества товара в корзине"""
        try:
            chat_id = callback_query['message']['chat']['id']
            
            # Получаем текущее количество
            cart_item = self.db.execute_query(
                'SELECT quantity FROM cart WHERE id = ?',
                (cart_item_id,)
            )
            
            if cart_item:
                current_quantity = cart_item[0][0]
                new_quantity = current_quantity + change
                
                if new_quantity <= 0:
                    self.db.remove_from_cart(cart_item_id)
                    self.bot.send_message(chat_id, "🗑 Товар удален из корзины")
                    self.answer_callback_query(callback_query['id'], "Товар удален")
                else:
                    self.db.update_cart_quantity(cart_item_id, new_quantity)
                    self.bot.send_message(chat_id, f"✅ Количество изменено на {new_quantity}")
                    self.answer_callback_query(callback_query['id'], f"Количество: {new_quantity}")
                    
        except Exception as e:
            print(f"Ошибка изменения количества: {e}")
    
    def remove_from_cart(self, callback_query, cart_item_id):
        """Удаление товара из корзины"""
        try:
            chat_id = callback_query['message']['chat']['id']
            
            result = self.db.remove_from_cart(cart_item_id)
            
            if result is not None:
                self.bot.send_message(chat_id, "🗑 Товар удален из корзины")
                self.answer_callback_query(callback_query['id'], "Товар удален")
            else:
                self.bot.send_message(chat_id, "❌ Ошибка удаления товара")
                self.answer_callback_query(callback_query['id'], "Ошибка удаления")
                
        except Exception as e:
            print(f"Ошибка удаления из корзины: {e}")
    
    def handle_product_rating(self, callback_query, product_id, rating):
        """Обработка оценки товара"""
        try:
            chat_id = callback_query['message']['chat']['id']
            telegram_id = callback_query['from']['id']
            
            user_data = self.db.get_user_by_telegram_id(telegram_id)
            if not user_data:
                return
            
            user_id = user_data[0][0]
            
            # Добавляем оценку
            result = self.db.add_review(user_id, product_id, rating, "")
            
            if result:
                stars = '⭐' * rating
                self.bot.send_message(chat_id, f"✅ Спасибо за оценку! {stars}")
                self.answer_callback_query(callback_query['id'], f"Оценка: {stars}")
            else:
                self.bot.send_message(chat_id, "❌ Ошибка сохранения оценки")
                self.answer_callback_query(callback_query['id'], "Ошибка сохранения")
                
        except Exception as e:
            print(f"Ошибка оценки товара: {e}")
    
    def add_to_favorites(self, callback_query, product_id):
        """Добавление в избранное"""
        try:
            chat_id = callback_query['message']['chat']['id']
            telegram_id = callback_query['from']['id']
            
            user_data = self.db.get_user_by_telegram_id(telegram_id)
            if not user_data:
                return
            
            user_id = user_data[0][0]
            
            result = self.db.add_to_favorites(user_id, product_id)
            
            if result:
                product = self.db.get_product_by_id(product_id)
                self.bot.send_message(chat_id, f"❤️ <b>{product[1]}</b> добавлен в избранное!")
                self.answer_callback_query(callback_query['id'], "Добавлено в избранное!")
            else:
                self.bot.send_message(chat_id, "❌ Товар уже в избранном")
                self.answer_callback_query(callback_query['id'], "Уже в избранном")
                
        except Exception as e:
            print(f"Ошибка добавления в избранное: {e}")
    
    def handle_payment_selection(self, callback_query):
        """Обработка выбора способа оплаты"""
        try:
            chat_id = callback_query['message']['chat']['id']
            data = callback_query['data']
            
            # Парсим данные callback
            parts = data.split('_')
            payment_method = parts[1]
            order_id = int(parts[2])
            
            if payment_method == 'cash':
                # Наличная оплата
                self.db.execute_query(
                    'UPDATE orders SET payment_method = "cash", status = "confirmed" WHERE id = ?',
                    (order_id,)
                )
                
                success_text = "✅ <b>Заказ оформлен!</b>\n\n"
                success_text += f"📦 Заказ #{order_id}\n"
                success_text += f"💵 Оплата наличными при получении\n\n"
                success_text += f"📞 Мы свяжемся с вами в ближайшее время"
                
                self.bot.send_message(chat_id, success_text)
                self.answer_callback_query(callback_query['id'], "Заказ оформлен!")
                
                # Уведомляем админов
                if self.notification_manager:
                    self.notification_manager.send_order_notification_to_admins(order_id)
            else:
                # Онлайн оплата
                amount = float(parts[3]) if len(parts) > 3 else 0
                
                # Получаем данные пользователя
                user_data = self.db.get_user_by_telegram_id(callback_query['from']['id'])
                user_info = {
                    'telegram_id': callback_query['from']['id'],
                    'name': user_data[0][2] if user_data else '',
                    'phone': user_data[0][3] if user_data else '',
                    'email': user_data[0][4] if user_data else ''
                }
                
                # Создаем платеж
                if self.payment_processor:
                    payment_result = self.payment_processor.create_payment(
                        payment_method, amount, order_id, user_info
                    )
                    
                    if payment_result:
                        from payments import format_payment_info
                        payment_text = format_payment_info(payment_result)
                        self.bot.send_message(chat_id, payment_text)
                        self.answer_callback_query(callback_query['id'], "Переход к оплате")
                    else:
                        self.bot.send_message(chat_id, "❌ Ошибка создания платежа")
                        self.answer_callback_query(callback_query['id'], "Ошибка платежа")
                        
        except Exception as e:
            print(f"Ошибка обработки платежа: {e}")
    
    def show_main_menu(self, message):
        """Показ главного меню"""
        try:
            chat_id = message['chat']['id']
            telegram_id = message['from']['id']
            
            user_data = self.db.get_user_by_telegram_id(telegram_id)
            language = user_data[0][5] if user_data else 'ru'
            
            welcome_text = t('welcome_back', language=language)
            keyboard = create_main_keyboard()
            self.bot.send_message(chat_id, welcome_text, keyboard)
            
        except Exception as e:
            print(f"Ошибка показа главного меню: {e}")
    
    def send_error_message(self, chat_id, language='ru'):
        """Отправка сообщения об ошибке"""
        try:
            error_text = "❌ Произошла ошибка. Попробуйте позже или обратитесь к администратору."
            if language == 'uz':
                error_text = "❌ Xatolik yuz berdi. Keyinroq urinib ko'ring yoki administrator bilan bog'laning."
            
            keyboard = create_main_keyboard()
            self.bot.send_message(chat_id, error_text, keyboard)
            
        except Exception as e:
            print(f"Ошибка отправки сообщения об ошибке: {e}")
    
    def handle_search_process(self, message):
        """Обработка процесса поиска"""
        try:
            chat_id = message['chat']['id']
            telegram_id = message['from']['id']
            text = message.get('text', '')
            
            if text == '🔙 Назад':
                self.user_states.pop(telegram_id, None)
                self.show_main_menu(message)
                return
            
            # Выполняем поиск
            self.handle_search_query(message, text)
            
            # Очищаем состояние
            self.user_states.pop(telegram_id, None)
            
        except Exception as e:
            print(f"Ошибка процесса поиска: {e}")
    
    def handle_review_process(self, message):
        """Обработка процесса написания отзыва"""
        try:
            chat_id = message['chat']['id']
            telegram_id = message['from']['id']
            text = message.get('text', '')
            
            state = self.user_states.get(telegram_id, '')
            
            if text == '❌ Отмена':
                self.user_states.pop(telegram_id, None)
                self.bot.send_message(chat_id, "Написание отзыва отменено")
                return
            
            if state.startswith('review_comment_'):
                product_id = int(state.split('_')[2])
                rating = int(state.split('_')[3])
                
                user_data = self.db.get_user_by_telegram_id(telegram_id)
                if user_data:
                    user_id = user_data[0][0]
                    
                    # Сохраняем отзыв
                    result = self.db.add_review(user_id, product_id, rating, text)
                    
                    if result:
                        self.bot.send_message(chat_id, "✅ Спасибо за отзыв!")
                    else:
                        self.bot.send_message(chat_id, "❌ Ошибка сохранения отзыва")
                
                self.user_states.pop(telegram_id, None)
                
        except Exception as e:
            print(f"Ошибка процесса отзыва: {e}")
    
    def handle_order_process(self, message):
        """Обработка процесса оформления заказа"""
        try:
            chat_id = message['chat']['id']
            telegram_id = message['from']['id']
            text = message.get('text', '')
            
            state = self.user_states.get(telegram_id, '')
            
            if text == '❌ Отмена заказа':
                self.user_states.pop(telegram_id, None)
                self.bot.send_message(chat_id, "Оформление заказа отменено")
                return
            
            if state == 'order_address':
                # Сохраняем адрес и переходим к оплате
                self.user_states[telegram_id] = f'order_payment_{text}'
                
                payment_text = "💳 <b>Выберите способ оплаты:</b>"
                
                keyboard = create_payment_methods_keyboard()
                self.bot.send_message(chat_id, payment_text, keyboard)
            
            elif state.startswith('order_payment_'):
                address = state.split('_', 2)[2]
                
                # Создаем заказ
                user_data = self.db.get_user_by_telegram_id(telegram_id)
                if user_data:
                    user_id = user_data[0][0]
                    cart_items = self.db.get_cart_items(user_id)
                    
                    if cart_items:
                        total_amount = calculate_cart_total(cart_items)
                        
                        # Создаем заказ
                        order_id = self.db.create_order(user_id, total_amount, address, text)
                        
                        if order_id:
                            # Добавляем товары в заказ
                            self.db.add_order_items(order_id, cart_items)
                            
                            # Очищаем корзину
                            self.db.clear_cart(user_id)
                            
                            # Показываем способы оплаты
                            if text == '💵 Наличными при получении':
                                self.db.execute_query(
                                    'UPDATE orders SET payment_method = "cash", status = "confirmed" WHERE id = ?',
                                    (order_id,)
                                )
                                
                                success_text = "✅ <b>Заказ успешно оформлен!</b>\n\n"
                                success_text += f"📦 Заказ #{order_id}\n"
                                success_text += f"💰 Сумма: {format_price(total_amount)}\n"
                                success_text += f"💵 Оплата наличными при получении\n\n"
                                success_text += f"📞 Мы свяжемся с вами в ближайшее время"
                                
                                self.bot.send_message(chat_id, success_text)
                                
                                # Уведомляем админов
                                if self.notification_manager:
                                    self.notification_manager.send_order_notification_to_admins(order_id)
                            else:
                                # Онлайн оплата
                                from payments import create_payment_keyboard
                                payment_keyboard = create_payment_keyboard(order_id, total_amount)
                                
                                payment_text = f"💳 <b>Оплата заказа #{order_id}</b>\n\n"
                                payment_text += f"💰 Сумма: {format_price(total_amount)}\n\n"
                                payment_text += f"Выберите способ оплаты:"
                                
                                self.bot.send_message(chat_id, payment_text, payment_keyboard)
                        else:
                            self.bot.send_message(chat_id, "❌ Ошибка создания заказа")
                
                self.user_states.pop(telegram_id, None)
                
        except Exception as e:
            print(f"Ошибка процесса заказа: {e}")
    
    def show_order_details(self, message):
        """Показ деталей заказа"""
        try:
            chat_id = message['chat']['id']
            text = message.get('text', '')
            
            order_id = int(text.split('_')[1])
            order_details = self.db.get_order_details(order_id)
            
            if order_details:
                order = order_details['order']
                items = order_details['items']
                
                details_text = f"📦 <b>Заказ #{order[0]}</b>\n\n"
                details_text += f"📅 Дата: {format_date(order[9])}\n"
                details_text += f"💰 Сумма: {format_price(order[2])}\n"
                details_text += f"📋 Статус: {get_order_status_text(order[3])}\n"
                
                if order[4]:
                    details_text += f"📍 Адрес: {order[4]}\n"
                
                details_text += f"\n🛍 <b>Товары:</b>\n"
                for item in items:
                    details_text += f"• {item[2]} × {item[0]} = {format_price(item[1] * item[0])}\n"
                
                keyboard = create_order_details_keyboard(order_id)
                self.bot.send_message(chat_id, details_text, keyboard)
            else:
                self.bot.send_message(chat_id, "❌ Заказ не найден")
                
        except Exception as e:
            print(f"Ошибка показа деталей заказа: {e}")
    
    def handle_tracking(self, message):
        """Обработка отслеживания посылки"""
        try:
            chat_id = message['chat']['id']
            text = message.get('text', '')
            
            tracking_number = text.split('_')[1]
            
            if hasattr(self.bot, 'logistics_manager'):
                tracking_info = self.bot.logistics_manager.track_shipment(tracking_number)
                
                if tracking_info:
                    track_text = f"📦 <b>Отслеживание {tracking_number}</b>\n\n"
                    track_text += f"📋 Статус: {tracking_info['current_status']}\n"
                    track_text += f"📅 Ожидаемая доставка: {format_date(tracking_info['estimated_delivery'])}\n\n"
                    track_text += f"📍 <b>История:</b>\n"
                    
                    for event in tracking_info['history']:
                        track_text += f"• {event['description']} - {format_date(event['timestamp'])}\n"
                    
                    self.bot.send_message(chat_id, track_text)
                else:
                    self.bot.send_message(chat_id, "❌ Трек-номер не найден")
            else:
                self.bot.send_message(chat_id, "❌ Система отслеживания недоступна")
                
        except Exception as e:
            print(f"Ошибка отслеживания: {e}")
    
    def handle_promo_code(self, message):
        """Обработка промокода"""
        try:
            chat_id = message['chat']['id']
            telegram_id = message['from']['id']
            text = message.get('text', '')
            
            promo_code = text.split('_')[1]
            
            user_data = self.db.get_user_by_telegram_id(telegram_id)
            if not user_data:
                return
            
            user_id = user_data[0][0]
            cart_items = self.db.get_cart_items(user_id)
            
            if not cart_items:
                self.bot.send_message(chat_id, "❌ Сначала добавьте товары в корзину")
                return
            
            cart_total = calculate_cart_total(cart_items)
            
            if hasattr(self.bot, 'promotion_manager'):
                validation = self.bot.promotion_manager.validate_promo_code(promo_code, user_id, cart_total)
                
                if validation['valid']:
                    promo_text = f"🎁 <b>Промокод применен!</b>\n\n"
                    promo_text += f"🏷 Код: {promo_code}\n"
                    promo_text += f"💰 Скидка: {format_price(validation['discount_amount'])}\n"
                    promo_text += f"📝 {validation['description']}\n\n"
                    promo_text += f"🛒 Перейдите в корзину для оформления заказа"
                    
                    self.bot.send_message(chat_id, promo_text)
                else:
                    self.bot.send_message(chat_id, f"❌ {validation['error']}")
            else:
                self.bot.send_message(chat_id, "❌ Система промокодов недоступна")
                
        except Exception as e:
            print(f"Ошибка обработки промокода: {e}")
    
    def handle_product_selection(self, message):
        """Обработка выбора товара"""
        try:
            chat_id = message['chat']['id']
            text = message.get('text', '')
            
            # Извлекаем название товара из текста кнопки
            if text.startswith('🛍 '):
                product_info = text[2:]  # Убираем эмодзи
                product_name = product_info.split(' - $')[0]  # Убираем цену
                
                # Ищем товар по названию
                products = self.db.search_products(product_name, limit=1)
                
                if products:
                    self.show_product_card(chat_id, products[0])
                else:
                    self.bot.send_message(chat_id, "❌ Товар не найден")
                    
        except Exception as e:
            print(f"Ошибка выбора товара: {e}")