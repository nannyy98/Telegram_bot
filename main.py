"""
Главный файл запуска телеграм-бота интернет-магазина
"""

import json
import urllib.request
import urllib.parse
import os
import time
import signal
import sys
import threading
from datetime import datetime
from database import DatabaseManager
from handlers import MessageHandler
from notifications import NotificationManager
from utils import format_date
from payments import PaymentProcessor
from logistics import LogisticsManager
from promotions import PromotionManager
from crm import CRMManager
from logger import logger
from health_check import HealthMonitor
from database_backup import DatabaseBackup
from scheduled_posts import ScheduledPostsManager
from config import BOT_CONFIG, ENVIRONMENT

# Импорты с обработкой ошибок
try:
    from admin import AdminHandler
except ImportError:
    AdminHandler = None
    logger.warning("AdminHandler не найден, админ-функции недоступны")

try:
    from security import SecurityManager
except ImportError:
    SecurityManager = None
    logger.warning("SecurityManager не найден, функции безопасности ограничены")

try:
    from analytics import AnalyticsManager
except ImportError:
    AnalyticsManager = None
    logger.warning("AnalyticsManager не найден, аналитика недоступна")

try:
    from financial_reports import FinancialReportsManager
except ImportError:
    FinancialReportsManager = None
    logger.warning("FinancialReportsManager не найден, финансовые отчеты недоступны")

try:
    from inventory_management import InventoryManager
except ImportError:
    InventoryManager = None
    logger.warning("InventoryManager не найден, управление складом недоступно")

try:
    from ai_features import AIRecommendationEngine, ChatbotSupport, SmartNotificationAI
except ImportError:
    AIRecommendationEngine = None
    ChatbotSupport = None
    SmartNotificationAI = None
    logger.warning("AI модули не найдены, AI функции недоступны")

try:
    from marketing_automation import MarketingAutomationManager
except ImportError:
    MarketingAutomationManager = None
    logger.warning("MarketingAutomationManager не найден, автоматизация недоступна")

class TelegramShopBot:
    def __init__(self, token):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.offset = 0
        self.running = True
        self.error_count = 0
        self.max_errors = 10
        self.data_cache = {}
        self.last_data_reload = time.time()
        
        # Инициализация компонентов
        self._initialize_core_components()
        self._initialize_business_modules()
        self._initialize_ai_features()
        self._setup_automation()
        self._setup_signal_handlers()
        
        logger.info("✅ Бот инициализирован успешно")
    
    def _initialize_core_components(self):
        """Инициализация основных компонентов"""
        self.db = DatabaseManager()
        self._setup_admin_from_env()
        self.backup_manager = DatabaseBackup(self.db.db_path)
        self.message_handler = MessageHandler(self, self.db)
        self.notification_manager = NotificationManager(self, self.db)
        self.payment_processor = PaymentProcessor()
        self.health_monitor = HealthMonitor(self.db, self)
        
        # Связываем компоненты
        self.message_handler.notification_manager = self.notification_manager
        self.message_handler.payment_processor = self.payment_processor
    
    def _initialize_business_modules(self):
        """Инициализация бизнес-модулей"""
        self.logistics_manager = LogisticsManager(self.db)
        self.promotion_manager = PromotionManager(self.db)
        self.crm_manager = CRMManager(self.db)
        
        # Инициализация админ-панели
        if AdminHandler:
            self.admin_handler = AdminHandler(self, self.db)
            self.admin_handler.notification_manager = self.notification_manager
        else:
            self.admin_handler = None
        
        # Инициализация безопасности
        if SecurityManager:
            self.security_manager = SecurityManager(self.db)
        else:
            self.security_manager = None
        
        # Инициализация аналитики
        if AnalyticsManager:
            self.analytics = AnalyticsManager(self.db)
            self.analytics.schedule_analytics_reports()
        else:
            self.analytics = None
        
        # Инициализация финансовой отчетности
        if FinancialReportsManager:
            self.financial_reports = FinancialReportsManager(self.db)
        else:
            self.financial_reports = None
        
        # Инициализация управления складом
        if InventoryManager:
            self.inventory_manager = InventoryManager(self.db)
            self.inventory_manager.bot = self
            self._schedule_inventory_checks()
        else:
            self.inventory_manager = None
    
    def _initialize_ai_features(self):
        """Инициализация AI функций"""
        if AIRecommendationEngine:
            self.ai_recommendations = AIRecommendationEngine(self.db)
        else:
            self.ai_recommendations = None
            
        if ChatbotSupport:
            self.chatbot_support = ChatbotSupport(self.db)
        else:
            self.chatbot_support = None
            
        if SmartNotificationAI:
            self.smart_notifications = SmartNotificationAI(self.db)
        else:
            self.smart_notifications = None
    
    def _setup_automation(self):
        """Настройка автоматизации"""
        # Инициализация маркетинговой автоматизации
        if MarketingAutomationManager:
            self.marketing_automation = MarketingAutomationManager(self.db, self.notification_manager)
            self._setup_default_automation_rules()
        else:
            self.marketing_automation = None
        
        # Инициализация системы автоматических постов
        try:
            self.scheduled_posts = ScheduledPostsManager(self, self.db)
            self.scheduled_posts.bot = self
            logger.info("✅ Система автоматических постов инициализирована")
        except Exception as e:
            logger.warning(f"⚠️ Автопосты недоступны: {e}")
            self.scheduled_posts = None
        
        # Запуск мониторинга обновлений данных
        self._start_data_sync_monitor()
    
    def _setup_signal_handlers(self):
        """Настройка обработчиков сигналов"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Обработчик сигналов для graceful shutdown"""
        logger.info(f"Получен сигнал {signum}, завершение работы...")
        self.running = False
        sys.exit(0)
    
    def _setup_admin_from_env(self):
        """Настройка админа из переменных окружения"""
        admin_telegram_id = BOT_CONFIG.get('admin_telegram_id')
        admin_name = BOT_CONFIG.get('admin_name', 'Admin')
        
        if not admin_telegram_id:
            logger.warning("ADMIN_TELEGRAM_ID не установлен в конфигурации")
            return
        
        try:
            admin_telegram_id = int(admin_telegram_id)
            
            existing_admin = self.db.execute_query(
                'SELECT id, is_admin FROM users WHERE telegram_id = ?',
                (admin_telegram_id,)
            )
            
            if existing_admin:
                if existing_admin[0][1] != 1:
                    self.db.execute_query(
                        'UPDATE users SET is_admin = 1 WHERE telegram_id = ?',
                        (admin_telegram_id,)
                    )
                    logger.info(f"✅ Права админа обновлены для {admin_name}")
                else:
                    logger.info(f"✅ Админ уже существует: {admin_name}")
            else:
                self.db.execute_query('''
                    INSERT INTO users (telegram_id, name, is_admin, language, created_at)
                    VALUES (?, ?, 1, 'ru', CURRENT_TIMESTAMP)
                ''', (admin_telegram_id, admin_name))
                logger.info(f"✅ Новый админ создан: {admin_name} (ID: {admin_telegram_id})")
                
        except ValueError:
            logger.error(f"❌ Неверный ADMIN_TELEGRAM_ID: {admin_telegram_id}")
        except Exception as e:
            logger.error(f"❌ Ошибка создания админа: {e}")
    
    def _schedule_inventory_checks(self):
        """Планирование проверок склада"""
        def inventory_worker():
            while self.running:
                try:
                    if self.inventory_manager:
                        self.inventory_manager.check_reorder_alerts()
                        self.inventory_manager.process_automatic_reorders()
                    time.sleep(21600)  # 6 часов
                except Exception as e:
                    logger.error(f"Ошибка проверки склада: {e}")
                    time.sleep(3600)  # Повтор через час при ошибке
        
        inventory_thread = threading.Thread(target=inventory_worker, daemon=True)
        inventory_thread.start()
    
    def _setup_default_automation_rules(self):
        """Настройка базовых правил автоматизации"""
        try:
            if not self.marketing_automation:
                return
            
            # Правило для брошенных корзин
            self.marketing_automation.create_automation_rule(
                "Брошенные корзины 24ч",
                "cart_abandonment",
                {"hours_since_last_activity": 24, "min_cart_value": 20},
                [{"type": "send_notification", "target_audience": "abandoned_cart", 
                  "message_template": "🛒 {name}, не забудьте о товарах в корзине!"}]
            )
            
            # Правило для первого заказа
            self.marketing_automation.create_automation_rule(
                "Первый заказ - благодарность",
                "customer_milestone",
                {"milestone_type": "first_order"},
                [{"type": "send_notification", "target_audience": "first_time_buyers",
                  "message_template": "🎉 Спасибо за первый заказ, {name}!"}]
            )
            
            # Правило для VIP клиентов
            self.marketing_automation.create_automation_rule(
                "VIP статус достигнут",
                "customer_milestone", 
                {"milestone_type": "spending_threshold", "spending_amount": 500},
                [{"type": "send_personalized_offer", "target_segment": "champions"}]
            )
        except Exception as e:
            logger.error(f"Ошибка настройки автоматизации: {e}")
    
    def _start_data_sync_monitor(self):
        """Запуск мониторинга обновлений данных"""
        def sync_worker():
            while self.running:
                try:
                    self._check_for_data_updates()
                    time.sleep(5)
                except Exception as e:
                    logger.error(f"Ошибка синхронизации данных: {e}")
                    time.sleep(30)
        
        sync_thread = threading.Thread(target=sync_worker, daemon=True)
        sync_thread.start()
        logger.info("Мониторинг синхронизации данных запущен")
    
    def _check_for_data_updates(self):
        """Проверка обновлений данных"""
        update_flag_file = 'data_update_flag.txt'
        force_reload_flag = 'force_reload_flag.txt'
        
        # Проверяем принудительную перезагрузку
        if os.path.exists(force_reload_flag):
            try:
                logger.info("🔄 ПРИНУДИТЕЛЬНАЯ ПЕРЕЗАГРУЗКА данных...")
                self._full_data_reload()
                os.remove(force_reload_flag)
                logger.info("✅ Принудительная перезагрузка завершена")
            except Exception as e:
                logger.error(f"Ошибка принудительной перезагрузки: {e}")
                try:
                    os.remove(force_reload_flag)
                except:
                    pass
        
        # Проверяем обычное обновление
        elif os.path.exists(update_flag_file):
            try:
                with open(update_flag_file, 'r') as f:
                    update_time_str = f.read().strip()
                
                update_time = float(update_time_str)
                
                if update_time > self.last_data_reload:
                    logger.info("🔄 Обнаружено обновление данных, перезагружаем...")
                    self._reload_data_cache()
                    self.last_data_reload = update_time
                    os.remove(update_flag_file)
                    logger.info("✅ Данные обновлены в боте")
                    
            except Exception as e:
                logger.error(f"Ошибка обработки флага обновления: {e}")
                try:
                    os.remove(update_flag_file)
                except:
                    pass
    
    def _full_data_reload(self):
        """Полная перезагрузка всех данных и компонентов"""
        try:
            self.db = DatabaseManager()
            self._reload_data_cache()
            
            if self.scheduled_posts:
                self.scheduled_posts.load_schedule_from_database()
            
            if self.marketing_automation:
                self._setup_default_automation_rules()
            
            logger.info("✅ Полная перезагрузка данных завершена")
            
        except Exception as e:
            logger.error(f"Ошибка полной перезагрузки: {e}")
    
    def _reload_data_cache(self):
        """Перезагрузка кэша данных"""
        try:
            self.data_cache.clear()
            self.data_cache['categories'] = self.db.get_categories()
            self.data_cache['products'] = self.db.execute_query(
                'SELECT * FROM products WHERE is_active = 1 ORDER BY name'
            )
            
            if self.scheduled_posts:
                self.scheduled_posts.load_schedule_from_database()
            
            self._notify_admins_about_update()
            
        except Exception as e:
            logger.error(f"Ошибка перезагрузки данных: {e}")
    
    def _notify_admins_about_update(self):
        """Уведомление админов об обновлении данных"""
        try:
            admins = self.db.execute_query('SELECT telegram_id FROM users WHERE is_admin = 1')
            
            update_message = "🔄 <b>Данные обновлены!</b>\n\n"
            update_message += "✅ Каталог товаров синхронизирован\n"
            update_message += "✅ Категории обновлены\n"
            update_message += "✅ Автопосты перезагружены\n\n"
            update_message += f"⏰ {datetime.now().strftime('%H:%M:%S')}"
            
            for admin in admins:
                try:
                    self.send_message(admin[0], update_message)
                except Exception as e:
                    logger.error(f"Ошибка уведомления админа {admin[0]}: {e}")
                    
        except Exception as e:
            logger.error(f"Ошибка уведомления админов: {e}")
    
    def send_message(self, chat_id, text, reply_markup=None):
        """Отправка сообщения"""
        url = f"{self.base_url}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }
        
        if reply_markup:
            data['reply_markup'] = json.dumps(reply_markup)
        
        try:
            data_encoded = urllib.parse.urlencode(data).encode('utf-8')
            req = urllib.request.Request(url, data=data_encoded, method='POST')
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                if not result.get('ok'):
                    logger.error(f"Ошибка отправки сообщения: {result}")
                return result
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения: {e}")
            return None
    
    def send_photo(self, chat_id, photo_url, caption="", reply_markup=None):
        """Отправка фото"""
        url = f"{self.base_url}/sendPhoto"
        data = {
            'chat_id': chat_id,
            'photo': photo_url,
            'caption': caption,
            'parse_mode': 'HTML'
        }
        
        if reply_markup:
            data['reply_markup'] = json.dumps(reply_markup)
        
        try:
            data_encoded = urllib.parse.urlencode(data).encode('utf-8')
            req = urllib.request.Request(url, data=data_encoded, method='POST')
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                if not result.get('ok'):
                    logger.error(f"Ошибка отправки фото: {result}")
                return result
        except Exception as e:
            logger.error(f"Ошибка отправки фото: {e}")
            return None
    
    def get_updates(self):
        """Получение обновлений"""
        url = f"{self.base_url}/getUpdates"
        params = {'offset': self.offset, 'timeout': 30}
        
        try:
            url_with_params = f"{url}?{urllib.parse.urlencode(params)}"
            with urllib.request.urlopen(url_with_params) as response:
                data = json.loads(response.read().decode('utf-8'))
                return data
        except Exception as e:
            logger.error(f"Ошибка получения обновлений: {e}")
            return None
    
    def run(self):
        """Запуск бота"""
        logger.info("🛍 Телеграм-бот интернет-магазина запущен!")
        logger.info("📱 Ожидание сообщений...")
        logger.info("Нажмите Ctrl+C для остановки")
        
        try:
            while self.running:
                updates = self.get_updates()
                
                if updates and updates.get('ok'):
                    self.error_count = 0
                    
                    for update in updates['result']:
                        self.offset = update['update_id'] + 1
                        
                        try:
                            self.health_monitor.increment_messages()
                            self._process_update(update)
                        except Exception as e:
                            logger.error(f"Ошибка обработки обновления: {e}", exc_info=True)
                            self.health_monitor.increment_errors(str(e))
                else:
                    self.error_count += 1
                    if self.error_count >= self.max_errors:
                        logger.critical("Превышено максимальное количество ошибок, перезапуск...")
                        time.sleep(60)
                        self.error_count = 0
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("🛑 Бот остановлен пользователем")
        except Exception as e:
            logger.critical(f"Критическая ошибка: {e}", exc_info=True)
        finally:
            logger.info("🔄 Закрытие соединений...")
            self.running = False
    
    def _process_update(self, update):
        """Обработка обновления"""
        if 'message' in update:
            message = update['message']
            text = message.get('text', '')
            telegram_id = message['from']['id']
            
            logger.info(f"Сообщение от {telegram_id}: {text[:50]}...")
            
            # Проверяем админ команды
            if self._is_admin_command(text):
                if self.admin_handler:
                    self.admin_handler.handle_admin_command(message)
                else:
                    self.send_message(message['chat']['id'], "❌ Админ-панель недоступна")
            elif text == '/notifications':
                self._show_user_notifications(message)
            else:
                self.message_handler.handle_message(message)
                
        elif 'callback_query' in update:
            callback_query = update['callback_query']
            data = callback_query['data']
            
            if self._is_admin_callback(data):
                if self.admin_handler:
                    self.admin_handler.handle_callback_query(callback_query)
                else:
                    self.send_message(callback_query['message']['chat']['id'], "❌ Админ-панель недоступна")
            else:
                self.message_handler.handle_callback_query(callback_query)
    
    def _is_admin_command(self, text):
        """Проверка является ли команда админской"""
        admin_commands = [
            '/admin', '📊 Статистика', '📦 Заказы', '🛠 Товары', '👥 Пользователи',
            '🔙 Пользовательский режим', '📈 Аналитика', '🛡 Безопасность',
            '💰 Финансы', '📦 Склад', '🤖 AI', '🎯 Автоматизация', '👥 CRM', '📢 Рассылка'
        ]
        
        return (text.startswith('/admin') or text in admin_commands or 
                text.startswith('/edit_product_') or text.startswith('/delete_product_'))
    
    def _is_admin_callback(self, data):
        """Проверка является ли callback админским"""
        admin_prefixes = [
            'admin_', 'change_status_', 'order_details_', 'analytics_',
            'period_', 'export_', 'security_', 'unblock_user_', 'broadcast_'
        ]
        
        return any(data.startswith(prefix) for prefix in admin_prefixes)
    
    def _show_user_notifications(self, message):
        """Показ уведомлений пользователя"""
        chat_id = message['chat']['id']
        telegram_id = message['from']['id']
        
        user_data = self.db.get_user_by_telegram_id(telegram_id)
        if not user_data:
            return
        
        user_id = user_data[0][0]
        notifications = self.db.get_unread_notifications(user_id)
        
        if not notifications:
            self.send_message(chat_id, "🔔 У вас нет новых уведомлений")
            return
        
        for notif in notifications:
            type_emoji = {
                'order': '📦',
                'order_status': '📋',
                'promotion': '🎁',
                'system': '⚙️',
                'info': 'ℹ️'
            }.get(notif[4], 'ℹ️')
            
            notif_text = f"{type_emoji} <b>{notif[2]}</b>\n\n"
            notif_text += f"{notif[3]}\n\n"
            notif_text += f"📅 {format_date(notif[6])}"
            
            self.send_message(chat_id, notif_text)
            self.db.mark_notification_read(notif[0])
    
    def edit_message_reply_markup(self, chat_id, message_id, reply_markup):
        """Редактирование клавиатуры сообщения"""
        url = f"{self.base_url}/editMessageReplyMarkup"
        data = {
            'chat_id': chat_id,
            'message_id': message_id,
            'reply_markup': json.dumps(reply_markup)
        }
        
        try:
            data_encoded = urllib.parse.urlencode(data).encode('utf-8')
            req = urllib.request.Request(url, data=data_encoded, method='POST')
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get('ok', False)
        except Exception as e:
            logger.error(f"Ошибка редактирования клавиатуры: {e}")
            return False

def main():
    """Главная функция"""
    # Получение токена
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not token:
        token = "8292684103:AAH0TKL-lCOaKVeppjtAdmsx0gdeMrGtjdQ"
    
    if not token or token == 'YOUR_BOT_TOKEN':
        logger.error("❌ ОШИБКА: Не указан токен бота!")
        print("\n📋 Инструкция по настройке:")
        print("1. Создайте бота через @BotFather в Telegram")
        print("2. Получите токен бота")
        print("3. Установите переменную окружения:")
        print("   export TELEGRAM_BOT_TOKEN='ваш_токен'")
        print("\n🔗 Подробная инструкция в README.md")
        return
    
    try:
        bot = TelegramShopBot(token)
        bot.run()
    except Exception as e:
        logger.critical(f"❌ Критическая ошибка запуска бота: {e}", exc_info=True)

if __name__ == "__main__":
    main()