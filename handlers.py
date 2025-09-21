"""
Обработчики сообщений для телеграм-бота
"""

import json
import re
from datetime import datetime, timedelta
from database import DatabaseManager
from keyboards import (
    create_main_keyboard, create_categories_keyboard, create_subcategories_keyboard,
    create_products_keyboard, create_product_inline_keyboard, create_cart_keyboard,
    create_registration_keyboard, create_order_keyboard, create_back_keyboard,
    create_confirmation_keyboard, create_search_filters_keyboard, create_rating_keyboard,
    create_language_keyboard, create_payment_methods_keyboard, create_cart_item_keyboard
)
from utils import format_price, format_date, validate_email, validate_phone, create_product_card
from localization import t, get_user_language
from config import MESSAGES, ORDER_STATUSES, PAYMENT_METHODS

class MessageHandler:
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db
        self.user_states = {}
        self.notification_manager = None
        self.payment_processor = None
    
    def handle_message(self, message):
        """Основной обработчик сообщений"""
        try:
            chat_id = message['chat']['id']
            telegram_id = message['from']['id']
            text = message.get('text', '')
            
            # Получаем или создаем пользователя
            user_data = self.db.get_user_by_telegram_id(telegram_id)
            
            if not user_data:
                if text == '/start':
                    self.start_registration(message)
                else:
                    self.bot.send_message(
                        chat_id,
                        "👋 Добро пожаловать! Для начала работы отправьте /start"
                    )
                return
            
            user_id = user_data[0][0]
            language = user_data[0][5]
            
            # Проверяем состояние пользователя
            user_state = self.user_states.get(telegram_id, '')
            
            # Обработка состояний регистрации
            if user_state.startswith('registration_'):
                self.handle_registration_step(message, user_state)
                return
            elif user_state.startswith('search_'):
                self.handle_search_process(message, user_state)
                return
            elif user_state.startswith('review_'):
                self.handle_review_process(message, user_state)
                return
            elif user_state.startswith('order_'):
                self.handle_order_process(message, user_state)
                return
            
            # Основные команды
            if text == '/start':
                self.show_main_menu(message, user_data[0])
            elif text == '/help':
                self.show_help(message, language)
            elif text.startswith('/order_'):
                self.show_order_details(message, text)
            elif text.startswith('/track_'):
                self.track_shipment(message, text)
            elif text.startswith('/promo_'):
                self.apply_promo_code(message, text)
            elif text.startswith('/restore_'):
                self.restore_saved_order(message, text)
            
            # Кнопки главного меню
            elif text == '🛍 Каталог':
                self.show_catalog(message, language)
            elif text == '🛒 Корзина':
                self.show_cart(message, user_id, language)
            elif text == '📋 Мои заказы':
                self.show_user_orders(message, user_id, language)
            elif text == '👤 Профиль':
                self.show_profile(message, user_data[0])
            elif text == '🔍 Поиск':
                self.start_search(message, language)
            elif text == 'ℹ️ Помощь':
                self.show_help(message, language)
            elif text == '⭐ Программа лояльности':
                self.show_loyalty_program(message, user_id, language)
            elif text == '🎁 Промокоды':
                self.show_available_promos(message, user_id, language)
            elif text == '🔧 Расширенный поиск':
                self.show_advanced_search(message, language)
            elif text == '📦 Отследить заказ':
                self.start_tracking(message, language)
            elif text == '🌍 Сменить язык':
                self.change_language(message, language)
            
            # Навигация
            elif text == '🔙 Главная' or text == '🏠 Главная':
                self.show_main_menu(message, user_data[0])
            elif text == '🔙 К категориям':
                self.show_catalog(message, language)
            elif text == '🔙 Назад':
                self.handle_back_navigation(message, user_id, language)
            
            # Категории товаров
            elif text.startswith('📱') or text.startswith('👕') or text.startswith('🏠') or text.startswith('⚽') or text.startswith('💄') or text.startswith('📚'):
                self.handle_category_selection(message, text, language)
            
            # Подкатегории/бренды
            elif text.startswith('🍎') or text.startswith('✔️') or text.startswith('👖') or text.startswith('☕') or text.startswith('👟') or text.startswith('💎') or text.startswith('📖'):
                self.handle_subcategory_selection(message, text, language)
            
            # Товары
            elif text.startswith('🛍'):
                self.handle_product_selection(message, text, user_id, language)
            
            # Корзина
            elif text == '📦 Оформить заказ':
                self.start_order_process(message, user_id, language)
            elif text == '🗑 Очистить корзину':
                self.clear_cart(message, user_id, language)
            elif text == '➕ Добавить товары':
                self.show_catalog(message, language)
            elif text == '🛍 Перейти в каталог':
                self.show_catalog(message, language)
            
            # Заказы
            elif text.startswith('📦 Заказ #'):
                order_id = text.split('#')[1]
                self.show_order_details_by_id(message, order_id, user_id, language)
            
            # Поиск
            elif self.user_states.get(telegram_id) == 'searching':
                self.perform_search(message, text, language)
            
            # Голосовые сообщения
            elif 'voice' in message:
                self.handle_voice_search(message, user_id, language)
            
            # Фото (поиск по штрихкоду)
            elif 'photo' in message:
                self.handle_barcode_search(message, user_id, language)
            
            # Неизвестная команда
            else:
                self.handle_unknown_command(message, text, user_id, language)
                
        except Exception as e:
            print(f"Ошибка обработки сообщения: {e}")
            self.bot.send_message(
                message['chat']['id'],
                "❌ Произошла ошибка. Попробуйте еще раз или обратитесь к администратору."
            )
    
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
            
            # Добавление в корзину
            if data.startswith('add_to_cart_'):
                product_id = int(data.split('_')[3])
                self.add_to_cart_callback(callback_query, product_id, user_id, language)
            
            # Добавление в избранное
            elif data.startswith('add_to_favorites_'):
                product_id = int(data.split('_')[3])
                self.add_to_favorites_callback(callback_query, product_id, user_id, language)
            
            # Управление корзиной
            elif data.startswith('cart_'):
                self.handle_cart_callback(callback_query, data, user_id, language)
            
            # Оценка товара
            elif data.startswith('rate_'):
                self.handle_rating_callback(callback_query, data, user_id, language)
            
            # Отзывы
            elif data.startswith('reviews_'):
                product_id = int(data.split('_')[1])
                self.show_product_reviews(callback_query, product_id, language)
            
            # Фильтры поиска
            elif data.startswith('sort_') or data.startswith('price_') or data == 'reset_filters':
                self.handle_search_filter(callback_query, data, language)
            
            # Оплата
            elif data.startswith('pay_'):
                self.handle_payment_callback(callback_query, data, user_id, language)
            
        except Exception as e:
            print(f"Ошибка обработки callback: {e}")
    
    def start_registration(self, message):
        """Начало регистрации"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        
        # Получаем имя из Telegram
        first_name = message['from'].get('first_name', '')
        last_name = message['from'].get('last_name', '')
        suggested_name = f"{first_name} {last_name}".strip()
        
        self.user_states[telegram_id] = 'registration_name'
        
        welcome_text = "🛍 <b>Добро пожаловать в наш интернет-магазин!</b>\n\n"
        welcome_text += "Для начала работы пройдите быструю регистрацию.\n\n"
        welcome_text += "👤 <b>Как вас зовут?</b>"
        
        keyboard = create_registration_keyboard('name', suggested_name)
        
        self.bot.send_message(chat_id, welcome_text, keyboard)
    
    def handle_registration_step(self, message, state):
        """Обработка шагов регистрации"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        text = message.get('text', '')
        
        if text == '❌ Отмена':
            del self.user_states[telegram_id]
            self.bot.send_message(
                chat_id,
                "❌ Регистрация отменена. Для начала работы отправьте /start"
            )
            return
        
        if state == 'registration_name':
            if len(text) < 2:
                self.bot.send_message(
                    chat_id,
                    "❌ Имя должно содержать минимум 2 символа. Попробуйте еще раз:"
                )
                return
            
            self.user_states[telegram_id] = f'registration_phone:{text}'
            
            phone_text = f"📱 <b>Укажите ваш номер телефона</b>\n\n"
            phone_text += "Это поможет нам связаться с вами по заказу."
            
            keyboard = create_registration_keyboard('phone')
            self.bot.send_message(chat_id, phone_text, keyboard)
        
        elif state.startswith('registration_phone:'):
            name = state.split(':', 1)[1]
            phone = None
            
            if text != '⏭ Пропустить':
                if 'contact' in message:
                    phone = message['contact']['phone_number']
                else:
                    phone = validate_phone(text)
                    if not phone:
                        self.bot.send_message(
                            chat_id,
                            "❌ Неверный формат номера. Попробуйте еще раз или нажмите 'Пропустить':"
                        )
                        return
            
            self.user_states[telegram_id] = f'registration_email:{name}:{phone or ""}'
            
            email_text = f"📧 <b>Укажите ваш email (необязательно)</b>\n\n"
            email_text += "Для отправки чеков и уведомлений о заказах."
            
            keyboard = create_registration_keyboard('email')
            self.bot.send_message(chat_id, email_text, keyboard)
        
        elif state.startswith('registration_email:'):
            parts = state.split(':', 2)
            name = parts[1]
            phone = parts[2] if parts[2] else None
            email = None
            
            if text != '⏭ Пропустить':
                if not validate_email(text):
                    self.bot.send_message(
                        chat_id,
                        "❌ Неверный формат email. Попробуйте еще раз или нажмите 'Пропустить':"
                    )
                    return
                email = text
            
            self.user_states[telegram_id] = f'registration_language:{name}:{phone or ""}:{email or ""}'
            
            language_text = f"🌍 <b>Выберите язык интерфейса</b>\n\n"
            language_text += "Вы сможете изменить его позже в настройках."
            
            keyboard = create_registration_keyboard('language')
            self.bot.send_message(chat_id, language_text, keyboard)
        
        elif state.startswith('registration_language:'):
            parts = state.split(':', 3)
            name = parts[1]
            phone = parts[2] if parts[2] else None
            email = parts[3] if parts[3] else None
            
            language = 'ru'
            if text == '🇺🇿 O\'zbekcha':
                language = 'uz'
            
            # Создаем пользователя
            user_id = self.db.add_user(telegram_id, name, phone, email, language)
            
            if user_id:
                del self.user_states[telegram_id]
                
                # Создаем запись баллов лояльности
                self.db.execute_query(
                    'INSERT OR IGNORE INTO loyalty_points (user_id) VALUES (?)',
                    (user_id,)
                )
                
                # Отправляем приветствие
                success_text = t('registration_complete', language=language)
                keyboard = create_main_keyboard()
                
                self.bot.send_message(chat_id, success_text, keyboard)
                
                # Запускаем приветственную серию
                if hasattr(self, 'marketing_automation') and self.marketing_automation:
                    self.marketing_automation.create_welcome_series(user_id)
            else:
                self.bot.send_message(
                    chat_id,
                    "❌ Ошибка регистрации. Попробуйте позже."
                )
    
    def show_main_menu(self, message, user_data):
        """Показ главного меню"""
        chat_id = message['chat']['id']
        name = user_data[1]
        language = user_data[5]
        
        welcome_text = t('welcome_back', language=language)
        welcome_text = welcome_text.replace('{name}', name)
        
        keyboard = create_main_keyboard()
        self.bot.send_message(chat_id, welcome_text, keyboard)
    
    def show_catalog(self, message, language):
        """Показ каталога товаров"""
        chat_id = message['chat']['id']
        
        categories = self.db.get_categories()
        
        if categories:
            catalog_text = f"🛍 <b>{t('catalog_title', language=language)}</b>\n\n"
            catalog_text += f"{t('choose_category', language=language)}"
            
            keyboard = create_categories_keyboard(categories)
            self.bot.send_message(chat_id, catalog_text, keyboard)
        else:
            self.bot.send_message(
                chat_id,
                "❌ Каталог временно недоступен"
            )
    
    def handle_category_selection(self, message, text, language):
        """Обработка выбора категории"""
        chat_id = message['chat']['id']
        
        # Извлекаем название категории из текста
        category_name = text.split(' ', 1)[1] if ' ' in text else text[2:]
        
        # Находим категорию
        category = self.db.execute_query(
            'SELECT id FROM categories WHERE name = ? AND is_active = 1',
            (category_name,)
        )
        
        if category:
            category_id = category[0][0]
            
            # Получаем подкатегории/бренды
            subcategories = self.db.get_products_by_category(category_id)
            
            if subcategories:
                subcategory_text = f"📂 <b>{category_name}</b>\n\n"
                subcategory_text += "Выберите бренд или подкатегорию:"
                
                keyboard = create_subcategories_keyboard(subcategories)
                self.bot.send_message(chat_id, subcategory_text, keyboard)
            else:
                self.bot.send_message(
                    chat_id,
                    f"❌ В категории '{category_name}' пока нет товаров"
                )
    
    def handle_subcategory_selection(self, message, text, language):
        """Обработка выбора подкатегории"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        
        # Извлекаем название подкатегории
        subcategory_name = text.split(' ', 1)[1] if ' ' in text else text[2:]
        
        # Находим подкатегорию
        subcategory = self.db.execute_query(
            'SELECT id FROM subcategories WHERE name = ? AND is_active = 1',
            (subcategory_name,)
        )
        
        if subcategory:
            subcategory_id = subcategory[0][0]
            
            # Получаем товары
            products = self.db.get_products_by_subcategory(subcategory_id, limit=10)
            
            if products:
                products_text = f"🛍 <b>{subcategory_name}</b>\n\n"
                products_text += "Выберите товар для просмотра:"
                
                keyboard = create_products_keyboard(products)
                self.bot.send_message(chat_id, products_text, keyboard)
            else:
                self.bot.send_message(
                    chat_id,
                    f"❌ В подкатегории '{subcategory_name}' пока нет товаров"
                )
    
    def handle_product_selection(self, message, text, user_id, language):
        """Обработка выбора товара"""
        chat_id = message['chat']['id']
        
        # Извлекаем название товара из текста
        product_text = text.replace('🛍 ', '')
        product_name = product_text.split(' - $')[0]
        
        # Находим товар
        product = self.db.execute_query(
            'SELECT * FROM products WHERE name = ? AND is_active = 1',
            (product_name,)
        )
        
        if product:
            product_data = product[0]
            product_id = product_data[0]
            
            # Увеличиваем счетчик просмотров
            self.db.increment_product_views(product_id)
            
            # Создаем карточку товара
            product_card = create_product_card(product_data)
            
            # Получаем отзывы
            reviews = self.db.get_product_reviews(product_id)
            if reviews:
                avg_rating = sum(review[0] for review in reviews) / len(reviews)
                product_card += f"\n⭐ Рейтинг: {avg_rating:.1f}/5 ({len(reviews)} отзывов)"
            
            keyboard = create_product_inline_keyboard(product_id)
            
            if product_data[5]:  # image_url
                self.bot.send_photo(chat_id, product_data[5], product_card, keyboard)
            else:
                self.bot.send_message(chat_id, product_card, keyboard)
    
    def add_to_cart_callback(self, callback_query, product_id, user_id, language):
        """Добавление товара в корзину через callback"""
        chat_id = callback_query['message']['chat']['id']
        
        result = self.db.add_to_cart(user_id, product_id, 1)
        
        if result:
            product = self.db.get_product_by_id(product_id)
            success_text = f"✅ <b>{product[1]}</b> добавлен в корзину!"
            
            # Показываем кнопку перехода в корзину
            keyboard = {
                'inline_keyboard': [
                    [
                        {'text': '🛒 Перейти в корзину', 'callback_data': 'go_to_cart'},
                        {'text': '➕ Добавить еще', 'callback_data': f'add_to_cart_{product_id}'}
                    ]
                ]
            }
            
            self.bot.send_message(chat_id, success_text, keyboard)
        else:
            self.bot.send_message(
                chat_id,
                "❌ Не удалось добавить товар в корзину. Возможно, товар закончился."
            )
    
    def show_cart(self, message, user_id, language):
        """Показ корзины"""
        chat_id = message['chat']['id']
        
        cart_items = self.db.get_cart_items(user_id)
        
        if not cart_items:
            empty_text = t('empty_cart', language=language)
            keyboard = create_cart_keyboard(False)
            self.bot.send_message(chat_id, empty_text, keyboard)
            return
        
        cart_text = f"🛒 <b>{t('your_cart', language=language)}</b>\n\n"
        total_amount = 0
        
        for item in cart_items:
            cart_item_id, name, price, quantity, image_url, product_id = item
            item_total = price * quantity
            total_amount += item_total
            
            cart_text += f"🛍 <b>{name}</b>\n"
            cart_text += f"💰 {format_price(price)} × {quantity} = {format_price(item_total)}\n\n"
        
        cart_text += f"💳 <b>Итого: {format_price(total_amount)}</b>"
        
        keyboard = create_cart_keyboard(True)
        self.bot.send_message(chat_id, cart_text, keyboard)
        
        # Отправляем inline управление для каждого товара
        for item in cart_items:
            cart_item_id, name, price, quantity, image_url, product_id = item
            
            item_text = f"🛍 <b>{name}</b>\n"
            item_text += f"💰 {format_price(price)} × {quantity} шт."
            
            keyboard = create_cart_item_keyboard(cart_item_id, quantity)
            
            if image_url:
                self.bot.send_photo(chat_id, image_url, item_text, keyboard)
            else:
                self.bot.send_message(chat_id, item_text, keyboard)
    
    def handle_cart_callback(self, callback_query, data, user_id, language):
        """Обработка управления корзиной"""
        chat_id = callback_query['message']['chat']['id']
        message_id = callback_query['message']['message_id']
        
        parts = data.split('_')
        action = parts[1]
        cart_item_id = int(parts[2])
        
        if action == 'increase':
            # Увеличиваем количество
            current_item = self.db.execute_query(
                'SELECT quantity FROM cart WHERE id = ?',
                (cart_item_id,)
            )
            
            if current_item:
                new_quantity = current_item[0][0] + 1
                self.db.update_cart_quantity(cart_item_id, new_quantity)
                
                # Обновляем клавиатуру
                new_keyboard = create_cart_item_keyboard(cart_item_id, new_quantity)
                self.bot.edit_message_reply_markup(chat_id, message_id, new_keyboard)
        
        elif action == 'decrease':
            # Уменьшаем количество
            current_item = self.db.execute_query(
                'SELECT quantity FROM cart WHERE id = ?',
                (cart_item_id,)
            )
            
            if current_item:
                new_quantity = max(0, current_item[0][0] - 1)
                
                if new_quantity == 0:
                    self.db.remove_from_cart(cart_item_id)
                    self.bot.send_message(chat_id, "🗑 Товар удален из корзины")
                else:
                    self.db.update_cart_quantity(cart_item_id, new_quantity)
                    new_keyboard = create_cart_item_keyboard(cart_item_id, new_quantity)
                    self.bot.edit_message_reply_markup(chat_id, message_id, new_keyboard)
        
        elif action == 'remove':
            # Удаляем товар
            self.db.remove_from_cart(cart_item_id)
            self.bot.send_message(chat_id, "🗑 Товар удален из корзины")
    
    def start_order_process(self, message, user_id, language):
        """Начало оформления заказа"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        
        cart_items = self.db.get_cart_items(user_id)
        
        if not cart_items:
            self.bot.send_message(
                chat_id,
                t('empty_cart', language=language)
            )
            return
        
        self.user_states[telegram_id] = 'order_address'
        
        address_text = f"📍 <b>{t('delivery_address', language=language)}</b>\n\n"
        address_text += f"{t('enter_address', language=language)}"
        
        keyboard = create_back_keyboard()
        self.bot.send_message(chat_id, address_text, keyboard)
    
    def handle_order_process(self, message, state):
        """Обработка процесса заказа"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        text = message.get('text', '')
        
        if text in ['🔙 Назад', '❌ Отмена заказа']:
            del self.user_states[telegram_id]
            self.show_cart(message, self.get_user_id_by_telegram(telegram_id), 
                          get_user_language(self.db, telegram_id))
            return
        
        if state == 'order_address':
            if len(text) < 10:
                self.bot.send_message(
                    chat_id,
                    "❌ Адрес слишком короткий. Укажите полный адрес доставки:"
                )
                return
            
            self.user_states[telegram_id] = f'order_payment:{text}'
            
            payment_text = f"💳 <b>Способ оплаты</b>\n\n"
            payment_text += "Выберите удобный способ оплаты:"
            
            keyboard = create_payment_methods_keyboard(get_user_language(self.db, telegram_id))
            self.bot.send_message(chat_id, payment_text, keyboard)
        
        elif state.startswith('order_payment:'):
            address = state.split(':', 1)[1]
            payment_method = text
            
            # Создаем заказ
            user_id = self.get_user_id_by_telegram(telegram_id)
            cart_items = self.db.get_cart_items(user_id)
            total_amount = sum(item[2] * item[3] for item in cart_items)
            
            order_id = self.db.create_order(user_id, total_amount, address, payment_method)
            
            if order_id:
                # Добавляем товары в заказ
                self.db.add_order_items(order_id, cart_items)
                
                # Очищаем корзину
                self.db.clear_cart(user_id)
                
                # Удаляем состояние
                del self.user_states[telegram_id]
                
                # Отправляем подтверждение
                success_text = f"✅ <b>Заказ #{order_id} успешно оформлен!</b>\n\n"
                success_text += f"💰 Сумма: {format_price(total_amount)}\n"
                success_text += f"📍 Адрес: {address}\n"
                success_text += f"💳 Оплата: {payment_method}\n\n"
                success_text += f"📞 Мы свяжемся с вами в ближайшее время для подтверждения.\n\n"
                success_text += f"Спасибо за покупку! 🎉"
                
                keyboard = create_main_keyboard()
                self.bot.send_message(chat_id, success_text, keyboard)
                
                # Уведомляем админов
                if self.notification_manager:
                    self.notification_manager.send_order_notification_to_admins(order_id)
                
                # Начисляем баллы лояльности
                points_earned = int(total_amount * 0.05)  # 5% от суммы
                self.db.update_loyalty_points(user_id, points_earned)
                
                if points_earned > 0:
                    points_text = f"⭐ Начислено {points_earned} баллов лояльности!"
                    self.bot.send_message(chat_id, points_text)
            else:
                self.bot.send_message(
                    chat_id,
                    "❌ Ошибка создания заказа. Попробуйте позже."
                )
    
    def show_user_orders(self, message, user_id, language):
        """Показ заказов пользователя"""
        chat_id = message['chat']['id']
        
        orders = self.db.get_user_orders(user_id)
        
        if not orders:
            no_orders_text = f"📋 <b>{t('no_orders', language=language)}</b>\n\n"
            no_orders_text += f"{t('make_first_order', language=language)}"
            
            keyboard = create_main_keyboard()
            self.bot.send_message(chat_id, no_orders_text, keyboard)
            return
        
        orders_text = f"📋 <b>{t('your_orders', language=language)}</b>\n\n"
        
        for order in orders[:10]:  # Показываем последние 10
            order_id, user_id, total_amount, status, delivery_address, payment_method, created_at = order[:7]
            
            status_emoji = {
                'pending': '⏳',
                'confirmed': '✅',
                'shipped': '🚚',
                'delivered': '📦',
                'cancelled': '❌'
            }.get(status, '❓')
            
            orders_text += f"{status_emoji} <b>Заказ #{order_id}</b>\n"
            orders_text += f"💰 {format_price(total_amount)}\n"
            orders_text += f"📅 {format_date(created_at)}\n"
            orders_text += f"📦 {ORDER_STATUSES.get(status, status)}\n\n"
        
        if len(orders) > 10:
            orders_text += f"... и еще {len(orders) - 10} заказов\n\n"
        
        orders_text += f"📋 Для детального просмотра: /order_ID"
        
        keyboard = create_back_keyboard()
        self.bot.send_message(chat_id, orders_text, keyboard)
    
    def show_order_details(self, message, command):
        """Показ деталей заказа"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        
        try:
            order_id = int(command.split('_')[1])
        except (IndexError, ValueError):
            self.bot.send_message(chat_id, "❌ Неверный формат команды")
            return
        
        user_id = self.get_user_id_by_telegram(telegram_id)
        
        # Проверяем принадлежность заказа пользователю
        order = self.db.execute_query(
            'SELECT * FROM orders WHERE id = ? AND user_id = ?',
            (order_id, user_id)
        )
        
        if not order:
            self.bot.send_message(chat_id, "❌ Заказ не найден")
            return
        
        order_details = self.db.get_order_details(order_id)
        
        if order_details:
            order_data = order_details['order']
            items = order_details['items']
            
            details_text = f"📦 <b>Заказ #{order_data[0]}</b>\n\n"
            details_text += f"📅 Дата: {format_date(order_data[7])}\n"
            details_text += f"📦 Статус: {ORDER_STATUSES.get(order_data[3], order_data[3])}\n"
            details_text += f"💳 Оплата: {PAYMENT_METHODS.get(order_data[5], order_data[5])}\n"
            
            if order_data[4]:
                details_text += f"📍 Адрес: {order_data[4]}\n"
            
            details_text += f"\n🛍 <b>Товары:</b>\n"
            
            for item in items:
                quantity, price, name, image_url = item
                details_text += f"• {name} × {quantity} = {format_price(price * quantity)}\n"
            
            details_text += f"\n💰 <b>Итого: {format_price(order_data[2])}</b>"
            
            keyboard = create_back_keyboard()
            self.bot.send_message(chat_id, details_text, keyboard)
    
    def start_search(self, message, language):
        """Начало поиска"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        
        self.user_states[telegram_id] = 'searching'
        
        search_text = f"🔍 <b>{t('search_products', language=language)}</b>\n\n"
        search_text += f"{t('enter_search_query', language=language)}"
        
        keyboard = create_back_keyboard()
        self.bot.send_message(chat_id, search_text, keyboard)
    
    def perform_search(self, message, query, language):
        """Выполнение поиска"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        
        # Удаляем состояние поиска
        if telegram_id in self.user_states:
            del self.user_states[telegram_id]
        
        # Логируем поиск
        user_id = self.get_user_id_by_telegram(telegram_id)
        self.db.execute_query(
            'INSERT INTO user_activity_logs (user_id, action, search_query) VALUES (?, ?, ?)',
            (user_id, 'search', query)
        )
        
        # Выполняем поиск
        products = self.db.search_products(query, limit=10)
        
        if products:
            search_text = f"🔍 <b>Результаты поиска: '{query}'</b>\n\n"
            search_text += f"Найдено {len(products)} товар(ов):"
            
            keyboard = create_products_keyboard(products, show_back=False)
            self.bot.send_message(chat_id, search_text, keyboard)
            
            # Показываем фильтры
            filters_text = "🔧 Используйте фильтры для уточнения поиска:"
            filters_keyboard = create_search_filters_keyboard()
            self.bot.send_message(chat_id, filters_text, filters_keyboard)
        else:
            no_results_text = f"❌ <b>По запросу '{query}' ничего не найдено</b>\n\n"
            
            # Предлагаем похожие товары
            if hasattr(self, 'ai_recommendations') and self.ai_recommendations:
                suggestions = self.ai_recommendations.get_smart_search_suggestions(query)
                if suggestions:
                    no_results_text += "💡 Возможно, вас заинтересует:\n"
                    for suggestion in suggestions:
                        no_results_text += f"• {suggestion}\n"
            
            keyboard = create_back_keyboard()
            self.bot.send_message(chat_id, no_results_text, keyboard)
    
    def show_profile(self, message, user_data):
        """Показ профиля пользователя"""
        chat_id = message['chat']['id']
        user_id, telegram_id, name, phone, email, language = user_data[:6]
        
        profile_text = f"👤 <b>{t('your_profile', language=language)}</b>\n\n"
        profile_text += f"📝 Имя: {name}\n"
        
        if phone:
            profile_text += f"📱 Телефон: {phone}\n"
        if email:
            profile_text += f"📧 Email: {email}\n"
        
        profile_text += f"🌍 Язык: {'🇷🇺 Русский' if language == 'ru' else '🇺🇿 O\'zbekcha'}\n"
        
        # Статистика заказов
        order_stats = self.db.execute_query('''
            SELECT COUNT(*), COALESCE(SUM(total_amount), 0)
            FROM orders WHERE user_id = ? AND status != 'cancelled'
        ''', (user_id,))
        
        if order_stats:
            orders_count, total_spent = order_stats[0]
            profile_text += f"\n📊 <b>Статистика:</b>\n"
            profile_text += f"📦 Заказов: {orders_count}\n"
            profile_text += f"💰 Потрачено: {format_price(total_spent)}\n"
        
        # Баллы лояльности
        loyalty_data = self.db.get_user_loyalty_points(user_id)
        if loyalty_data:
            profile_text += f"⭐ Баллы: {loyalty_data[2]} ({loyalty_data[4]})\n"
        
        keyboard = {
            'keyboard': [
                ['🌍 Сменить язык', '📧 Изменить контакты'],
                ['🔙 Главная']
            ],
            'resize_keyboard': True
        }
        
        self.bot.send_message(chat_id, profile_text, keyboard)
    
    def show_loyalty_program(self, message, user_id, language):
        """Показ программы лояльности"""
        chat_id = message['chat']['id']
        
        loyalty_data = self.db.get_user_loyalty_points(user_id)
        
        loyalty_text = f"⭐ <b>{t('loyalty_program', language=language)}</b>\n\n"
        
        if loyalty_data:
            current_points = loyalty_data[2]
            total_earned = loyalty_data[3]
            current_tier = loyalty_data[4]
            
            loyalty_text += f"💎 Ваш уровень: <b>{current_tier}</b>\n"
            loyalty_text += f"⭐ Текущие баллы: <b>{current_points}</b>\n"
            loyalty_text += f"🏆 Всего заработано: <b>{total_earned}</b>\n\n"
            
            # Показываем уровни
            tier_thresholds = {
                'Bronze': 0,
                'Silver': 100,
                'Gold': 500,
                'Platinum': 1500,
                'Diamond': 5000
            }
            
            loyalty_text += f"🏅 <b>Уровни лояльности:</b>\n"
            for tier, threshold in tier_thresholds.items():
                if current_points >= threshold:
                    loyalty_text += f"✅ {tier} (от {threshold} баллов)\n"
                else:
                    loyalty_text += f"🔒 {tier} (от {threshold} баллов)\n"
        
        keyboard = create_back_keyboard()
        self.bot.send_message(chat_id, loyalty_text, keyboard)
    
    def show_available_promos(self, message, user_id, language):
        """Показ доступных промокодов"""
        chat_id = message['chat']['id']
        
        # Получаем доступные промокоды
        available_promos = self.db.execute_query('''
            SELECT code, discount_type, discount_value, min_order_amount, description
            FROM promo_codes
            WHERE is_active = 1
            AND (expires_at IS NULL OR expires_at > datetime('now'))
            AND (max_uses IS NULL OR (
                SELECT COUNT(*) FROM promo_uses WHERE promo_code_id = promo_codes.id
            ) < max_uses)
            AND id NOT IN (
                SELECT promo_code_id FROM promo_uses WHERE user_id = ?
            )
            ORDER BY discount_value DESC
        ''', (user_id,))
        
        if available_promos:
            promo_text = f"🎁 <b>{t('available_promos', language=language)}</b>\n\n"
            
            for promo in available_promos:
                code, discount_type, discount_value, min_amount, description = promo
                
                promo_text += f"🏷 <code>{code}</code>\n"
                
                if discount_type == 'percentage':
                    promo_text += f"💰 Скидка {discount_value}%"
                else:
                    promo_text += f"💰 Скидка {format_price(discount_value)}"
                
                if min_amount > 0:
                    promo_text += f" (от {format_price(min_amount)})"
                
                promo_text += f"\n📝 {description}\n\n"
            
            promo_text += f"💡 Для применения: /promo_КОД"
        else:
            promo_text = f"🎁 <b>{t('no_promos', language=language)}</b>\n\n"
            promo_text += f"{t('check_later', language=language)}"
        
        keyboard = create_back_keyboard()
        self.bot.send_message(chat_id, promo_text, keyboard)
    
    def handle_unknown_command(self, message, text, user_id, language):
        """Обработка неизвестной команды"""
        chat_id = message['chat']['id']
        
        # Пытаемся найти ответ через AI поддержку
        if hasattr(self, 'chatbot_support') and self.chatbot_support:
            ai_response = self.chatbot_support.find_best_answer(text)
            if ai_response:
                self.bot.send_message(chat_id, ai_response)
                return
        
        # Стандартный ответ
        unknown_text = f"❓ <b>{t('unknown_command', language=language)}</b>\n\n"
        unknown_text += f"{t('use_menu_buttons', language=language)}"
        
        keyboard = create_main_keyboard()
        self.bot.send_message(chat_id, unknown_text, keyboard)
    
    def get_user_id_by_telegram(self, telegram_id):
        """Получение ID пользователя по telegram_id"""
        user_data = self.db.get_user_by_telegram_id(telegram_id)
        return user_data[0][0] if user_data else None
    
    def handle_voice_search(self, message, user_id, language):
        """Обработка голосового поиска"""
        chat_id = message['chat']['id']
        
        # Заглушка для голосового поиска
        voice_text = f"🎤 <b>{t('voice_search', language=language)}</b>\n\n"
        voice_text += f"{t('voice_search_coming_soon', language=language)}\n\n"
        voice_text += f"💡 Пока используйте текстовый поиск: 🔍 Поиск"
        
        keyboard = create_back_keyboard()
        self.bot.send_message(chat_id, voice_text, keyboard)
    
    def handle_barcode_search(self, message, user_id, language):
        """Обработка поиска по штрихкоду"""
        chat_id = message['chat']['id']
        
        # Заглушка для поиска по штрихкоду
        barcode_text = f"📷 <b>{t('barcode_search', language=language)}</b>\n\n"
        barcode_text += f"{t('barcode_search_coming_soon', language=language)}\n\n"
        barcode_text += f"💡 Пока используйте текстовый поиск: 🔍 Поиск"
        
        keyboard = create_back_keyboard()
        self.bot.send_message(chat_id, barcode_text, keyboard)
    
    def show_help(self, message, language):
        """Показ справки"""
        chat_id = message['chat']['id']
        
        help_text = t('help', language=language)
        keyboard = create_back_keyboard()
        
        self.bot.send_message(chat_id, help_text, keyboard)
    
    def clear_cart(self, message, user_id, language):
        """Очистка корзины"""
        chat_id = message['chat']['id']
        
        self.db.clear_cart(user_id)
        
        cleared_text = f"🗑 <b>{t('cart_cleared', language=language)}</b>\n\n"
        cleared_text += f"{t('cart_cleared_message', language=language)}"
        
        keyboard = create_main_keyboard()
        self.bot.send_message(chat_id, cleared_text, keyboard)
    
    def change_language(self, message, current_language):
        """Смена языка"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        
        self.user_states[telegram_id] = 'changing_language'
        
        language_text = "🌍 <b>Выберите язык / Tilni tanlang</b>\n\n"
        language_text += "🇷🇺 Русский\n"
        language_text += "🇺🇿 O'zbekcha"
        
        keyboard = create_language_keyboard()
        self.bot.send_message(chat_id, language_text, keyboard)
    
    def handle_back_navigation(self, message, user_id, language):
        """Обработка навигации назад"""
        # Простая реализация - возврат в главное меню
        user_data = self.db.execute_query('SELECT * FROM users WHERE id = ?', (user_id,))[0]
        self.show_main_menu(message, user_data)
    
    def track_shipment(self, message, command):
        """Отслеживание посылки"""
        chat_id = message['chat']['id']
        
        try:
            tracking_number = command.split('_', 1)[1]
        except IndexError:
            self.bot.send_message(chat_id, "❌ Неверный формат команды")
            return
        
        # Здесь должна быть интеграция с системой отслеживания
        tracking_text = f"📦 <b>Отслеживание посылки</b>\n\n"
        tracking_text += f"📍 Трек-номер: <code>{tracking_number}</code>\n\n"
        tracking_text += f"🚚 Статус: В пути\n"
        tracking_text += f"📅 Ожидаемая доставка: завтра\n\n"
        tracking_text += f"📞 Для уточнений обращайтесь в поддержку"
        
        keyboard = create_back_keyboard()
        self.bot.send_message(chat_id, tracking_text, keyboard)
    
    def apply_promo_code(self, message, command):
        """Применение промокода"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        
        try:
            promo_code = command.split('_', 1)[1].upper()
        except IndexError:
            self.bot.send_message(chat_id, "❌ Неверный формат команды")
            return
        
        user_id = self.get_user_id_by_telegram(telegram_id)
        
        # Проверяем корзину
        cart_items = self.db.get_cart_items(user_id)
        if not cart_items:
            self.bot.send_message(
                chat_id,
                "❌ Сначала добавьте товары в корзину"
            )
            return
        
        cart_total = sum(item[2] * item[3] for item in cart_items)
        
        # Проверяем промокод
        from promotions import PromotionManager
        promo_manager = PromotionManager(self.db)
        
        validation = promo_manager.validate_promo_code(promo_code, user_id, cart_total)
        
        if validation['valid']:
            promo_text = f"✅ <b>Промокод применен!</b>\n\n"
            promo_text += f"🏷 Код: <code>{promo_code}</code>\n"
            promo_text += f"💰 Скидка: {format_price(validation['discount_amount'])}\n"
            promo_text += f"📝 {validation['description']}\n\n"
            promo_text += f"🛒 Оформите заказ для применения скидки"
        else:
            promo_text = f"❌ <b>Ошибка промокода</b>\n\n"
            promo_text += f"🏷 Код: <code>{promo_code}</code>\n"
            promo_text += f"📝 {validation['error']}"
        
        keyboard = create_back_keyboard()
        self.bot.send_message(chat_id, promo_text, keyboard)
    
    def restore_saved_order(self, message, command):
        """Восстановление сохраненного заказа"""
        chat_id = message['chat']['id']
        
        # Заглушка для восстановления заказа
        restore_text = f"💾 <b>Восстановление заказа</b>\n\n"
        restore_text += f"Функция восстановления сохраненных заказов будет добавлена в следующей версии.\n\n"
        restore_text += f"💡 Пока используйте корзину для создания заказов"
        
        keyboard = create_back_keyboard()
        self.bot.send_message(chat_id, restore_text, keyboard)
    
    def show_advanced_search(self, message, language):
        """Расширенный поиск"""
        chat_id = message['chat']['id']
        
        advanced_text = f"🔧 <b>{t('advanced_search', language=language)}</b>\n\n"
        advanced_text += f"{t('advanced_search_description', language=language)}"
        
        keyboard = create_search_filters_keyboard()
        self.bot.send_message(chat_id, advanced_text, keyboard)
    
    def start_tracking(self, message, language):
        """Начало отслеживания"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        
        self.user_states[telegram_id] = 'tracking'
        
        tracking_text = f"📦 <b>{t('track_order', language=language)}</b>\n\n"
        tracking_text += f"{t('enter_tracking_number', language=language)}"
        
        keyboard = create_back_keyboard()
        self.bot.send_message(chat_id, tracking_text, keyboard)
    
    def add_to_favorites_callback(self, callback_query, product_id, user_id, language):
        """Добавление в избранное"""
        chat_id = callback_query['message']['chat']['id']
        
        result = self.db.add_to_favorites(user_id, product_id)
        
        if result:
            product = self.db.get_product_by_id(product_id)
            favorites_text = f"❤️ <b>{product[1]}</b> добавлен в избранное!"
        else:
            favorites_text = "❤️ Товар уже в избранном!"
        
        self.bot.send_message(chat_id, favorites_text)
    
    def handle_rating_callback(self, callback_query, data, user_id, language):
        """Обработка оценки товара"""
        chat_id = callback_query['message']['chat']['id']
        
        parts = data.split('_')
        product_id = int(parts[1])
        rating = int(parts[2])
        
        # Сохраняем оценку
        self.db.add_review(user_id, product_id, rating, "")
        
        rating_text = f"⭐ Спасибо за оценку!\n\n"
        rating_text += f"Вы поставили {rating} звезд товару."
        
        self.bot.send_message(chat_id, rating_text)
    
    def show_product_reviews(self, callback_query, product_id, language):
        """Показ отзывов о товаре"""
        chat_id = callback_query['message']['chat']['id']
        
        reviews = self.db.get_product_reviews(product_id)
        product = self.db.get_product_by_id(product_id)
        
        if reviews:
            reviews_text = f"📊 <b>Отзывы: {product[1]}</b>\n\n"
            
            avg_rating = sum(review[0] for review in reviews) / len(reviews)
            reviews_text += f"⭐ Средняя оценка: {avg_rating:.1f}/5 ({len(reviews)} отзывов)\n\n"
            
            for review in reviews[:5]:  # Показываем первые 5
                rating, comment, created_at, user_name = review
                stars = '⭐' * rating
                
                reviews_text += f"{stars} <b>{user_name}</b>\n"
                if comment:
                    reviews_text += f"💭 {comment}\n"
                reviews_text += f"📅 {format_date(created_at)}\n\n"
        else:
            reviews_text = f"📊 <b>Отзывы: {product[1]}</b>\n\n"
            reviews_text += "Пока нет отзывов об этом товаре.\n"
            reviews_text += "Станьте первым, кто оставит отзыв!"
        
        self.bot.send_message(chat_id, reviews_text)
    
    def handle_search_filter(self, callback_query, data, language):
        """Обработка фильтров поиска"""
        chat_id = callback_query['message']['chat']['id']
        
        if data == 'sort_price_low':
            filter_text = "💰 Сортировка по возрастанию цены"
        elif data == 'sort_price_high':
            filter_text = "💰 Сортировка по убыванию цены"
        elif data == 'sort_popular':
            filter_text = "🔥 Показ популярных товаров"
        elif data == 'sort_newest':
            filter_text = "🆕 Показ новинок"
        elif data == 'sort_sales':
            filter_text = "📊 Показ продаваемых товаров"
        elif data == 'reset_filters':
            filter_text = "🔍 Фильтры сброшены"
        else:
            filter_text = "🔧 Фильтр применен"
        
        self.bot.send_message(chat_id, filter_text)
    
    def handle_payment_callback(self, callback_query, data, user_id, language):
        """Обработка выбора способа оплаты"""
        chat_id = callback_query['message']['chat']['id']
        
        parts = data.split('_')
        provider = parts[1]
        order_id = int(parts[2])
        
        if provider == 'cash':
            # Наличная оплата
            cash_text = f"💵 <b>Оплата наличными</b>\n\n"
            cash_text += f"📦 Заказ #{order_id}\n"
            cash_text += f"💰 Оплата при получении\n\n"
            cash_text += f"📞 Курьер свяжется с вами для уточнения времени доставки"
            
            self.bot.send_message(chat_id, cash_text)
        else:
            # Онлайн оплата
            if self.payment_processor:
                try:
                    amount = float(parts[3])
                    user_data = self.db.execute_query(
                        'SELECT name, phone, email FROM users WHERE id = ?',
                        (user_id,)
                    )[0]
                    
                    payment_data = {
                        'telegram_id': callback_query['from']['id'],
                        'name': user_data[0],
                        'phone': user_data[1],
                        'email': user_data[2]
                    }
                    
                    payment_result = self.payment_processor.create_payment(
                        provider, amount, order_id, payment_data
                    )
                    
                    if payment_result:
                        from payments import format_payment_info
                        payment_text = format_payment_info(payment_result)
                        self.bot.send_message(chat_id, payment_text)
                    else:
                        self.bot.send_message(
                            chat_id,
                            "❌ Ошибка создания платежа. Попробуйте другой способ."
                        )
                except Exception as e:
                    print(f"Ошибка создания платежа: {e}")
                    self.bot.send_message(
                        chat_id,
                        "❌ Ошибка обработки платежа"
                    )