"""
Улучшенная система автоматических постов
"""

import threading
import time
from datetime import datetime
from logger import logger

class ScheduledPostsManager:
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db
        self.scheduler_running = False
        self.channel_id = "-1002566537425"
        
        # Фиксированное расписание - 3 раза в день
        self.schedule = {
            'morning': '09:00',
            'afternoon': '14:00', 
            'evening': '19:00'
        }
        
        self.start_scheduler()
    
    def start_scheduler(self):
        """Запуск планировщика постов"""
        if self.scheduler_running:
            return
        
        def scheduler_worker():
            while True:
                try:
                    self.check_and_send_posts()
                    time.sleep(60)  # Проверяем каждую минуту
                except Exception as e:
                    logger.error(f"Ошибка планировщика постов: {e}")
                    time.sleep(300)
        
        scheduler_thread = threading.Thread(target=scheduler_worker, daemon=True)
        scheduler_thread.start()
        self.scheduler_running = True
        logger.info("Планировщик автопостов запущен (3 раза в день)")
    
    def check_and_send_posts(self):
        """Проверка и отправка постов по расписанию"""
        current_time = time.strftime('%H:%M')
        current_date = time.strftime('%Y-%m-%d')
        
        # Проверяем каждое время в расписании
        for period, scheduled_time in self.schedule.items():
            if current_time == scheduled_time:
                # Проверяем, не отправляли ли уже сегодня в это время
                already_sent = self.db.execute_query('''
                    SELECT COUNT(*) FROM post_statistics 
                    WHERE time_period = ? AND DATE(sent_at) = ?
                ''', (period, current_date))
                
                if not already_sent or already_sent[0][0] == 0:
                    self.send_auto_post(period)
    
    def send_auto_post(self, period):
        """Отправка автоматического поста"""
        try:
            logger.info(f"🔄 Отправка автопоста ({period})...")
            
            # Получаем активные шаблоны
            templates = self.db.execute_query('''
                SELECT id, title, content, post_type, image_url
                FROM auto_post_templates 
                WHERE is_active = 1
                ORDER BY RANDOM()
                LIMIT 1
            ''')
            
            if not templates:
                logger.warning("⚠️ Нет активных шаблонов для автопостов")
                return
            
            template = templates[0]
            template_id, title, content, post_type, image_url = template
            
            # Форматируем сообщение
            message_text = self.format_auto_post(title, content, post_type, period)
            
            # Создаем кнопки
            keyboard = self.create_post_keyboard()
            
            # Отправляем в канал
            success = False
            try:
                if image_url:
                    result = self.bot.send_photo(self.channel_id, image_url, message_text, keyboard)
                else:
                    result = self.bot.send_message(self.channel_id, message_text, keyboard)
                
                if result and result.get('ok'):
                    success = True
                    logger.info(f"✅ Автопост отправлен в канал")
                else:
                    logger.error(f"❌ Ошибка отправки в канал: {result}")
            except Exception as e:
                logger.error(f"❌ Ошибка отправки автопоста: {e}")
            
            # Записываем статистику
            self.db.execute_query('''
                INSERT INTO post_statistics (
                    post_id, time_period, sent_count, error_count, sent_at
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                template_id, period, 1 if success else 0, 0 if success else 1,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            logger.info(f"📊 Статистика автопоста записана")
            
        except Exception as e:
            logger.error(f"❌ Критическая ошибка автопоста: {e}")
    
    def format_auto_post(self, title, content, post_type, period):
        """Форматирование автоматического поста"""
        time_emojis = {
            'morning': '🌅',
            'afternoon': '☀️',
            'evening': '🌆'
        }
        
        time_greetings = {
            'morning': 'Доброе утро',
            'afternoon': 'Добрый день',
            'evening': 'Добрый вечер'
        }
        
        emoji = time_emojis.get(period, '📢')
        greeting = time_greetings.get(period, 'Привет')
        
        # Базовое сообщение
        message = f"{emoji} <b>{greeting}!</b>\n\n"
        
        if title:
            message += f"📢 <b>{title}</b>\n\n"
        
        # Добавляем контент в зависимости от типа
        if post_type == 'greeting':
            message += content
        elif post_type == 'promotion':
            message += f"🔥 {content}\n\n"
            message += f"🎁 Специальные предложения ждут вас!"
        elif post_type == 'congratulation':
            message += f"🎉 {content}\n\n"
            message += f"💝 Отпразднуйте с нами!"
        else:
            message += content
        
        # Добавляем призыв к действию
        message += f"\n\n🛍 Перейти в каталог: /start"
        
        return message
    
    def create_post_keyboard(self):
        """Создание клавиатуры для постов"""
        return {
            'inline_keyboard': [
                [
                    {'text': '🛒 Заказать товары', 'url': 'https://t.me/your_bot_username'},
                    {'text': '🌐 Перейти на сайт', 'url': 'https://your-website.com'}
                ],
                [
                    {'text': '📱 Каталог в боте', 'url': 'https://t.me/your_bot_username?start=catalog'},
                    {'text': '💬 Поддержка', 'url': 'https://t.me/your_support_username'}
                ]
            ]
        }
    
    def create_template(self, title, content, post_type, image_url=None):
        """Создание шаблона автопоста"""
        return self.db.execute_query('''
            INSERT INTO auto_post_templates (
                title, content, post_type, image_url, is_active, created_at
            ) VALUES (?, ?, ?, ?, 1, ?)
        ''', (
            title, content, post_type, image_url,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
    
    def get_templates(self):
        """Получение всех шаблонов"""
        return self.db.execute_query('''
            SELECT id, title, content, post_type, image_url, is_active, created_at
            FROM auto_post_templates
            ORDER BY created_at DESC
        ''')
    
    def toggle_template_status(self, template_id):
        """Переключение статуса шаблона"""
        current_status = self.db.execute_query(
            'SELECT is_active FROM auto_post_templates WHERE id = ?',
            (template_id,)
        )
        
        if current_status:
            new_status = 0 if current_status[0][0] else 1
            return self.db.execute_query(
                'UPDATE auto_post_templates SET is_active = ? WHERE id = ?',
                (new_status, template_id)
            )
        return None
    
    def delete_template(self, template_id):
        """Удаление шаблона"""
        return self.db.execute_query(
            'DELETE FROM auto_post_templates WHERE id = ?',
            (template_id,)
        )
    
    def get_statistics(self, days=7):
        """Статистика автопостов"""
        return self.db.execute_query('''
            SELECT 
                apt.title,
                ps.time_period,
                SUM(ps.sent_count) as total_sent,
                SUM(ps.error_count) as total_errors,
                COUNT(*) as posts_count
            FROM post_statistics ps
            JOIN auto_post_templates apt ON ps.post_id = apt.id
            WHERE ps.sent_at >= date('now', '-{} days')
            GROUP BY apt.id, apt.title, ps.time_period
            ORDER BY ps.sent_at DESC
        '''.format(days))
    
    def send_manual_post(self, template_id):
        """Ручная отправка поста по шаблону"""
        template = self.db.execute_query(
            'SELECT title, content, post_type, image_url FROM auto_post_templates WHERE id = ?',
            (template_id,)
        )
        
        if not template:
            return False, "Шаблон не найден"
        
        title, content, post_type, image_url = template[0]
        
        try:
            message_text = self.format_auto_post(title, content, post_type, 'manual')
            keyboard = self.create_post_keyboard()
            
            if image_url:
                result = self.bot.send_photo(self.channel_id, image_url, message_text, keyboard)
            else:
                result = self.bot.send_message(self.channel_id, message_text, keyboard)
            
            if result and result.get('ok'):
                # Записываем статистику
                self.db.execute_query('''
                    INSERT INTO post_statistics (
                        post_id, time_period, sent_count, error_count, sent_at
                    ) VALUES (?, ?, 1, 0, ?)
                ''', (
                    template_id, 'manual',
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ))
                return True, "Пост отправлен успешно"
            else:
                return False, f"Ошибка Telegram API: {result}"
                
        except Exception as e:
            logger.error(f"Ошибка ручной отправки поста: {e}")
            return False, str(e)