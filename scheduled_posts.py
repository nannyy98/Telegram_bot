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
        self.channel_id = "-1002566537425"
        logger.info("✅ Менеджер постов инициализирован (только ручная отправка)")
    
    def format_post_message(self, title, content, post_type):
        """Форматирование сообщения поста"""
        message = f"📢 <b>{title}</b>\n\n"
        message += content
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
    