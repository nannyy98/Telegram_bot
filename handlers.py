"""
Обработчики сообщений для телеграм-бота
"""

from datetime import datetime
from keyboards import (
    create_main_keyboard, create_categories_keyboard, create_subcategories_keyboard,
    create_products_keyboard, create_product_inline_keyboard, create_cart_keyboard,
    create_registration_keyboard, create_order_keyboard, create_back_keyboard,
    create_confirmation_keyboard, create_search_filters_keyboard,
    create_price_filter_keyboard, create_rating_keyboard, create_language_keyboard,
    create_payment_methods_keyboard, create_cart_item_keyboard
)
from utils import (
    format_price, format_date, validate_email, validate_phone, 
    truncate_text, calculate_cart_total, format_cart_summary,
    create_product_card, log_user_action
)
from localization import t, get_user_language
from config import MESSAGES, ORDER_STATUSES, PAYMENT_METHODS
from logger import logger

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
            
            # Логируем действие пользователя
            log_user_action(telegram_id, 'message', text[:50])
            
            # Проверяем регистрацию пользователя
            user_data = self.db.get_user_by_telegram_id(telegram_id)
            
            if not user_data and text != '/start':
                self._send_registration_prompt(chat_id)
                return
            
            # Обрабатываем команды
            if text == '/start':
                self._handle_start_command(message)
            elif text == '/help':
                self._handle_help_command(message)
            elif text.startswith('/order_'):
                self._handle_order_command(message)
            elif text.startswith('/track_'):
                self._handle_track_command(message)
            elif text.startswith('/promo_'):
                self._handle_promo_command(message)
            elif text.startswith('/restore_'):
                self._handle_restore_command(message)
            elif text == '🛍 Каталог':
                self._show_categories(chat_id, telegram_id)
            elif text == '🛒 Корзина':
                self._show_cart(chat_id, telegram_id)
            elif text == '📋 Мои заказы':
                self._show_user_orders(chat_id, telegram_id)
            elif text == '👤 Профиль':
                self._show_user_profile(chat_id, telegram_id)
            elif text == '🔍 Поиск':
                self._start_search(chat_id, telegram_id)
            elif text == 'ℹ️ Помощь':
                self._handle_help_command(message)
            elif text == '⭐ Программа лояльности':
                self._show_loyalty_program(chat_id, telegram_id)
            elif text == '🎁 Промокоды':
                self._show_available_promos(chat_id, telegram_id)
            elif text == '🔙 Главная':
                self._show_main_menu(chat_id, telegram_id)
            elif text == '🌍 Сменить язык':
                self._start_language_change(chat_id, telegram_id)
            else:
                self._handle_text_input(message)
                
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}", exc_info=True)
            self.bot.send_message(chat_id, "❌ Произошла ошибка. Попробуйте еще раз.")
    
    def handle_callback_query(self, callback_query):
        """Обработка inline кнопок"""
        try:
            data = callback_query['data']
            chat_id = callback_query['message']['chat']['id']
            message_id = callback_query['message']['message_id']
            telegram_id = callback_query['from']['id']
            
            # Логируем действие
            log_user_action(telegram_id, 'callback', data)
            
            if data.startswith('add_to_cart_'):
                self._handle_add_to_cart_callback(callback_query)
            elif data.startswith('add_to_favorites_'):
                self._handle_add_to_favorites_callback(callback_query)
            elif data.startswith('reviews_'):
                self._handle_reviews_callback(callback_query)
            elif data.startswith('rate_product_'):
                self._handle_rate_product_callback(callback_query)
            elif data.startswith('rate_'):
                self._handle_rating_callback(callback_query)
            elif data.startswith('cart_'):
                self._handle_cart_action_callback(callback_query)
            elif data.startswith('pay_'):
                self._handle_payment_callback(callback_query)
            elif data.startswith('sort_') or data.startswith('price_'):
                self._handle_search_filter_callback(callback_query)
            else:
                self._handle_unknown_callback(callback_query)
                
        except Exception as e:
            logger.error(f"Ошибка обработки callback: {e}", exc_info=True)
    
    def _handle_start_command(self, message):
        """Обработка команды /start"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        
        user_data = self.db.get_user_by_telegram_id(telegram_id)
        
        if user_data:
            # Существующий пользователь
            user_language = user_data[0][5]
            welcome_text = t('welcome_back', language=user_language)
            self.bot.send_message(chat_id, welcome_text, create_main_keyboard())
        else:
            # Новый пользователь - начинаем регистрацию
            self._start_registration(message)
    
    def _handle_help_command(self, message):
        """Обработка команды /help"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        
        user_language = get_user_language(self.db, telegram_id)
        help_text = t('help', language=user_language)
        
        self.bot.send_message(chat_id, help_text, create_main_keyboard())
    
    def _handle_order_command(self, message):
        """Обработка команды /order_ID"""
        try:
            order_id = int(message['text'].split('_')[1])
            chat_id = message['chat']['id']
            telegram_id = message['from']['id']
            
            # Проверяем принадлежность заказа пользователю
            user_data = self.db.get_user_by_telegram_id(telegram_id)
            if not user_data:
                return
            
            user_id = user_data[0][0]
            order_details = self.db.get_order_details(order_id)
            
            if not order_details or order_details['order'][1] != user_id:
                self.bot.send_message(chat_id, "❌ Заказ не найден или не принадлежит вам")
                return
            
            self._show_order_details(chat_id, order_details)
            
        except (ValueError, IndexError):
            self.bot.send_message(message['chat']['id'], "❌ Неверный формат команды")
    
    def _handle_track_command(self, message):
        """Обработка команды /track_НОМЕР"""
        try:
            tracking_number = message['text'].split('_')[1]
            chat_id = message['chat']['id']
            
            # Здесь должна быть интеграция с системой отслеживания
            tracking_info = self._get_tracking_info(tracking_number)
            
            if tracking_info:
                self._show_tracking_info(chat_id, tracking_info)
            else:
                self.bot.send_message(chat_id, "❌ Трек-номер не найден")
                
        except IndexError:
            self.bot.send_message(message['chat']['id'], "❌ Неверный формат трек-номера")
    
    def _handle_promo_command(self, message):
        """Обработка команды /promo_КОД"""
        try:
            promo_code = message['text'].split('_')[1]
            chat_id = message['chat']['id']
            telegram_id = message['from']['id']
            
            user_data = self.db.get_user_by_telegram_id(telegram_id)
            if not user_data:
                return
            
            user_id = user_data[0][0]
            
            # Проверяем промокод
            from promotions import PromotionManager
            promo_manager = PromotionManager(self.db)
            
            # Для проверки используем сумму корзины
            cart_items = self.db.get_cart_items(user_id)
            cart_total = calculate_cart_total(cart_items)
            
            validation = promo_manager.validate_promo_code(promo_code, user_id, cart_total)
            
            if validation['valid']:
                promo_text = f"✅ <b>Промокод действителен!</b>\n\n"
                promo_text += f"🎁 {validation['description']}\n"
                promo_text += f"💰 Скидка: {format_price(validation['discount_amount'])}\n\n"
                promo_text += f"🛒 Добавьте товары в корзину и используйте промокод при оформлении заказа"
            else:
                promo_text = f"❌ <b>Промокод недействителен</b>\n\n{validation['error']}"
            
            self.bot.send_message(chat_id, promo_text)
            
        except IndexError:
            self.bot.send_message(message['chat']['id'], "❌ Неверный формат промокода")
    
    def _handle_restore_command(self, message):
        """Обработка команды /restore_ID"""
        try:
            restore_id = message['text'].split('_')[1]
            chat_id = message['chat']['id']
            
            # Здесь должна быть логика восстановления сохраненного заказа
            self.bot.send_message(chat_id, f"🔄 Восстановление заказа {restore_id}...")
            
        except IndexError:
            self.bot.send_message(message['chat']['id'], "❌ Неверный формат команды")
    
    def _start_registration(self, message):
        """Начало процесса регистрации"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        
        # Получаем имя из Telegram
        suggested_name = message['from'].get('first_name', '')
        if message['from'].get('last_name'):
            suggested_name += f" {message['from']['last_name']}"
        
        welcome_text = MESSAGES['welcome_new']
        self.bot.send_message(chat_id, welcome_text)
        
        # Начинаем регистрацию
        self.user_states[telegram_id] = 'registration_name'
        
        name_text = "👤 <b>Как вас зовут?</b>\n\nВведите ваше имя:"
        keyboard = create_registration_keyboard('name', suggested_name)
        
        self.bot.send_message(chat_id, name_text, keyboard)
    
    def _handle_text_input(self, message):
        """Обработка текстового ввода в зависимости от состояния"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        text = message.get('text', '')
        
        state = self.user_states.get(telegram_id)
        
        if state == 'registration_name':
            self._process_registration_name(message)
        elif state == 'registration_phone':
            self._process_registration_phone(message)
        elif state == 'registration_email':
            self._process_registration_email(message)
        elif state == 'registration_language':
            self._process_registration_language(message)
        elif state == 'search_query':
            self._process_search_query(message)
        elif state == 'order_address':
            self._process_order_address(message)
        elif state == 'rating_comment':
            self._process_rating_comment(message)
        elif text.startswith('🛍 ') and ' - $' in text:
            self._handle_product_selection(message)
        elif self._is_category_button(text):
            self._handle_category_selection(message)
        else:
            self._handle_unknown_text(message)
    
    def _process_registration_name(self, message):
        """Обработка ввода имени при регистрации"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        text = message.get('text', '')
        
        if text == '❌ Отмена':
            self._cancel_registration(chat_id, telegram_id)
            return
        
        if len(text) < 2:
            self.bot.send_message(chat_id, "❌ Имя слишком короткое. Попробуйте еще раз:")
            return
        
        # Сохраняем имя и переходим к телефону
        self.user_states[telegram_id] = 'registration_phone'
        self.user_states[f'{telegram_id}_name'] = text
        
        phone_text = "📱 <b>Ваш номер телефона</b>\n\nПоделитесь номером или введите вручную:"
        keyboard = create_registration_keyboard('phone')
        
        self.bot.send_message(chat_id, phone_text, keyboard)
    
    def _process_registration_phone(self, message):
        """Обработка ввода телефона при регистрации"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        text = message.get('text', '')
        
        if text == '❌ Отмена':
            self._cancel_registration(chat_id, telegram_id)
            return
        elif text == '⏭ Пропустить':
            phone = None
        elif 'contact' in message:
            phone = message['contact']['phone_number']
        else:
            phone = validate_phone(text)
            if not phone:
                self.bot.send_message(chat_id, "❌ Неверный формат телефона. Попробуйте еще раз:")
                return
        
        # Сохраняем телефон и переходим к email
        self.user_states[telegram_id] = 'registration_email'
        self.user_states[f'{telegram_id}_phone'] = phone
        
        email_text = "📧 <b>Ваш email (необязательно)</b>\n\nВведите email или пропустите:"
        keyboard = create_registration_keyboard('email')
        
        self.bot.send_message(chat_id, email_text, keyboard)
    
    def _process_registration_email(self, message):
        """Обработка ввода email при регистрации"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        text = message.get('text', '')
        
        if text == '❌ Отмена':
            self._cancel_registration(chat_id, telegram_id)
            return
        elif text == '⏭ Пропустить':
            email = None
        else:
            if not validate_email(text):
                self.bot.send_message(chat_id, "❌ Неверный формат email. Попробуйте еще раз:")
                return
            email = text
        
        # Сохраняем email и переходим к выбору языка
        self.user_states[telegram_id] = 'registration_language'
        self.user_states[f'{telegram_id}_email'] = email
        
        language_text = "🌍 <b>Выберите язык</b>\n\nВыберите предпочитаемый язык:"
        keyboard = create_registration_keyboard('language')
        
        self.bot.send_message(chat_id, language_text, keyboard)
    
    def _process_registration_language(self, message):
        """Обработка выбора языка при регистрации"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        text = message.get('text', '')
        
        if text == '🇷🇺 Русский':
            language = 'ru'
        elif text == '🇺🇿 O\'zbekcha':
            language = 'uz'
        else:
            self.bot.send_message(chat_id, "❌ Выберите язык из предложенных вариантов:")
            return
        
        # Завершаем регистрацию
        self._complete_registration(message, language)
    
    def _complete_registration(self, message, language):
        """Завершение регистрации"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        
        name = self.user_states.get(f'{telegram_id}_name')
        phone = self.user_states.get(f'{telegram_id}_phone')
        email = self.user_states.get(f'{telegram_id}_email')
        
        # Создаем пользователя
        user_id = self.db.add_user(telegram_id, name, phone, email, language)
        
        if user_id:
            # Очищаем состояние
            self._clear_user_state(telegram_id)
            
            # Отправляем сообщение о завершении
            success_text = t('registration_complete', language=language)
            self.bot.send_message(chat_id, success_text, create_main_keyboard())
            
            # Создаем приветственную серию уведомлений
            if hasattr(self, 'marketing_automation') and self.marketing_automation:
                self.marketing_automation.create_welcome_series(user_id)
        else:
            self.bot.send_message(chat_id, "❌ Ошибка регистрации. Попробуйте позже.")
    
    def _cancel_registration(self, chat_id, telegram_id):
        """Отмена регистрации"""
        self._clear_user_state(telegram_id)
        self.bot.send_message(chat_id, "❌ Регистрация отменена. Для использования бота необходимо зарегистрироваться.")
    
    def _clear_user_state(self, telegram_id):
        """Очистка состояния пользователя"""
        keys_to_remove = [key for key in self.user_states.keys() if str(telegram_id) in str(key)]
        for key in keys_to_remove:
            del self.user_states[key]
    
    def _send_registration_prompt(self, chat_id):
        """Приглашение к регистрации"""
        prompt_text = "👋 Для использования бота необходимо зарегистрироваться.\n\nНажмите /start для начала регистрации."
        self.bot.send_message(chat_id, prompt_text)
    
    def _show_main_menu(self, chat_id, telegram_id):
        """Показ главного меню"""
        user_language = get_user_language(self.db, telegram_id)
        welcome_text = t('welcome_back', language=user_language)
        self.bot.send_message(chat_id, welcome_text, create_main_keyboard())
    
    def _show_categories(self, chat_id, telegram_id):
        """Показ категорий товаров"""
        try:
            categories = self.db.get_categories()
        except Exception as e:
            logger.error(f"Ошибка получения категорий: {e}")
            self.bot.send_message(chat_id, "❌ Ошибка загрузки каталога")
            return
        
        if categories:
            categories_text = "🛍 <b>Выберите категорию:</b>"
            keyboard = create_categories_keyboard(categories)
            self.bot.send_message(chat_id, categories_text, keyboard)
        else:
            self.bot.send_message(chat_id, "❌ Категории товаров не найдены")
    
    def _show_cart(self, chat_id, telegram_id):
        """Показ корзины"""
        user_data = self.db.get_user_by_telegram_id(telegram_id)
        if not user_data:
            return
        
        user_id = user_data[0][0]
        cart_items = self.db.get_cart_items(user_id)
        
        if not cart_items:
            user_language = user_data[0][5]
            empty_text = t('empty_cart', language=user_language)
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
        
        # Показываем inline кнопки для каждого товара
        for item in cart_items:
            item_keyboard = create_cart_item_keyboard(item[0], item[3])
            item_text = f"🛍 {item[1]} - {format_price(item[2])}"
            
            if item[4]:  # Если есть изображение
                self.bot.send_photo(chat_id, item[4], item_text, item_keyboard)
            else:
                self.bot.send_message(chat_id, item_text, item_keyboard)
    
    def _show_user_orders(self, chat_id, telegram_id):
        """Показ заказов пользователя"""
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
            status_emoji = ORDER_STATUSES.get(order[3], '❓')
            orders_text += f"{status_emoji} <b>Заказ #{order[0]}</b>\n"
            orders_text += f"💰 {format_price(order[2])}\n"
            orders_text += f"📅 {format_date(order[7])}\n"
            orders_text += f"👆 /order_{order[0]} - подробнее\n\n"
        
        if len(orders) > 10:
            orders_text += f"... и еще {len(orders) - 10} заказов"
        
        self.bot.send_message(chat_id, orders_text, create_back_keyboard())
    
    def _show_user_profile(self, chat_id, telegram_id):
        """Показ профиля пользователя"""
        user_data = self.db.get_user_by_telegram_id(telegram_id)
        if not user_data:
            return
        
        user = user_data[0]
        user_id = user[0]
        
        # Получаем статистику пользователя
        orders_stats = self.db.execute_query('''
            SELECT COUNT(*), SUM(total_amount), MAX(created_at)
            FROM orders 
            WHERE user_id = ? AND status != 'cancelled'
        ''', (user_id,))
        
        loyalty_data = self.db.get_user_loyalty_points(user_id)
        
        profile_text = f"👤 <b>Ваш профиль</b>\n\n"
        profile_text += f"📝 Имя: {user[2]}\n"
        
        if user[3]:
            profile_text += f"📱 Телефон: {user[3]}\n"
        if user[4]:
            profile_text += f"📧 Email: {user[4]}\n"
        
        profile_text += f"🌍 Язык: {'🇷🇺 Русский' if user[5] == 'ru' else '🇺🇿 O\'zbekcha'}\n"
        profile_text += f"📅 Регистрация: {format_date(user[6])}\n\n"
        
        if orders_stats and orders_stats[0][0] > 0:
            profile_text += f"📊 <b>Статистика:</b>\n"
            profile_text += f"📦 Заказов: {orders_stats[0][0]}\n"
            profile_text += f"💰 Потрачено: {format_price(orders_stats[0][1] or 0)}\n"
            profile_text += f"📅 Последний заказ: {format_date(orders_stats[0][2])}\n\n"
        
        if loyalty_data:
            profile_text += f"⭐ <b>Программа лояльности:</b>\n"
            profile_text += f"🏆 Уровень: {loyalty_data[4]}\n"
            profile_text += f"💎 Баллы: {loyalty_data[2]}\n"
        
        keyboard = {
            'keyboard': [
                ['🌍 Сменить язык'],
                ['🔙 Главная']
            ],
            'resize_keyboard': True
        }
        
        self.bot.send_message(chat_id, profile_text, keyboard)
    
    def _handle_add_to_cart_callback(self, callback_query):
        """Обработка добавления в корзину"""
        try:
            product_id = int(callback_query['data'].split('_')[-1])
            chat_id = callback_query['message']['chat']['id']
            telegram_id = callback_query['from']['id']
            
            user_data = self.db.get_user_by_telegram_id(telegram_id)
            if not user_data:
                return
            
            user_id = user_data[0][0]
            
            # Добавляем в корзину
            result = self.db.add_to_cart(user_id, product_id, 1)
            
            if result:
                self.bot.send_message(chat_id, "✅ Товар добавлен в корзину!")
            else:
                self.bot.send_message(chat_id, "❌ Не удалось добавить товар в корзину")
                
        except (ValueError, IndexError) as e:
            logger.error(f"Ошибка добавления в корзину: {e}")
    
    def _handle_add_to_favorites_callback(self, callback_query):
        """Обработка добавления в избранное"""
        try:
            product_id = int(callback_query['data'].split('_')[-1])
            chat_id = callback_query['message']['chat']['id']
            telegram_id = callback_query['from']['id']
            
            user_data = self.db.get_user_by_telegram_id(telegram_id)
            if not user_data:
                return
            
            user_id = user_data[0][0]
            
            # Добавляем в избранное
            result = self.db.add_to_favorites(user_id, product_id)
            
            if result:
                self.bot.send_message(chat_id, "❤️ Товар добавлен в избранное!")
            else:
                self.bot.send_message(chat_id, "❌ Не удалось добавить в избранное")
                
        except (ValueError, IndexError) as e:
            logger.error(f"Ошибка добавления в избранное: {e}")
    
    def _handle_cart_action_callback(self, callback_query):
        """Обработка действий с корзиной"""
        try:
            data_parts = callback_query['data'].split('_')
            action = data_parts[1]
            cart_item_id = int(data_parts[2])
            chat_id = callback_query['message']['chat']['id']
            
            if action == 'increase':
                # Увеличиваем количество
                current_quantity = self._get_cart_item_quantity(cart_item_id)
                self.db.update_cart_quantity(cart_item_id, current_quantity + 1)
                self.bot.send_message(chat_id, "✅ Количество увеличено")
                
            elif action == 'decrease':
                # Уменьшаем количество
                current_quantity = self._get_cart_item_quantity(cart_item_id)
                if current_quantity > 1:
                    self.db.update_cart_quantity(cart_item_id, current_quantity - 1)
                    self.bot.send_message(chat_id, "✅ Количество уменьшено")
                else:
                    self.db.remove_from_cart(cart_item_id)
                    self.bot.send_message(chat_id, "🗑 Товар удален из корзины")
                    
            elif action == 'remove':
                # Удаляем товар
                self.db.remove_from_cart(cart_item_id)
                self.bot.send_message(chat_id, "🗑 Товар удален из корзины")
                
        except (ValueError, IndexError) as e:
            logger.error(f"Ошибка действия с корзиной: {e}")
    
    def _get_cart_item_quantity(self, cart_item_id):
        """Получение текущего количества товара в корзине"""
        result = self.db.execute_query(
            'SELECT quantity FROM cart WHERE id = ?',
            (cart_item_id,)
        )
        return result[0][0] if result else 1
    
    def _handle_unknown_callback(self, callback_query):
        """Обработка неизвестного callback"""
        chat_id = callback_query['message']['chat']['id']
        self.bot.send_message(chat_id, "❌ Неизвестная команда")
    
    def _handle_unknown_text(self, message):
        """Обработка неизвестного текста"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        text = message.get('text', '')
        
        # Пробуем найти ответ через AI поддержку
        if hasattr(self.bot, 'chatbot_support') and self.bot.chatbot_support:
            ai_response = self.bot.chatbot_support.find_best_answer(text)
            self.bot.send_message(chat_id, ai_response)
        else:
            # Стандартный ответ
            help_text = "❓ Не понимаю команду. Используйте меню ниже или /help для справки."
            self.bot.send_message(chat_id, help_text, create_main_keyboard())
    
    def _get_tracking_info(self, tracking_number):
        """Получение информации о трекинге"""
        # Заглушка для системы трекинга
        return {
            'tracking_number': tracking_number,
            'status': 'В пути',
            'location': 'Сортировочный центр',
            'estimated_delivery': '2024-01-15'
        }
    
    def _show_tracking_info(self, chat_id, tracking_info):
        """Показ информации о трекинге"""
        tracking_text = f"📦 <b>Отслеживание посылки</b>\n\n"
        tracking_text += f"📍 Номер: {tracking_info['tracking_number']}\n"
        tracking_text += f"📋 Статус: {tracking_info['status']}\n"
        tracking_text += f"🌍 Местоположение: {tracking_info['location']}\n"
        tracking_text += f"📅 Ожидаемая доставка: {tracking_info['estimated_delivery']}"
        
        self.bot.send_message(chat_id, tracking_text, create_back_keyboard())
    
    def _show_order_details(self, chat_id, order_details):
        """Показ деталей заказа"""
        order = order_details['order']
        items = order_details['items']
        
        details_text = f"📦 <b>Заказ #{order[0]}</b>\n\n"
        details_text += f"📅 Дата: {format_date(order[7])}\n"
        details_text += f"📋 Статус: {ORDER_STATUSES.get(order[3], order[3])}\n"
        details_text += f"💳 Оплата: {PAYMENT_METHODS.get(order[5], order[5])}\n"
        
        if order[4]:
            details_text += f"📍 Адрес: {order[4]}\n"
        
        details_text += f"\n🛍 <b>Товары:</b>\n"
        
        for item in items:
            item_total = item[0] * item[1]
            details_text += f"• {item[2]} × {item[0]} = {format_price(item_total)}\n"
        
        details_text += f"\n💰 <b>Итого: {format_price(order[2])}</b>"
        
        self.bot.send_message(chat_id, details_text, create_back_keyboard())