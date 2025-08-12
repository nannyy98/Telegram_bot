# utils/texts.py
TEXTS = {
    'welcome': {
        'ru': "🇷🇺 Выберите язык",
        'uz': "🇺🇿 Tilni tanlang"
    },
    'lang_set': {
        'ru': "✅ Язык установлен! Выберите действие:",
        'uz': "✅ Til tanlandi! Quyidagilardan birini tanlang:"
    },
    # добавляйте другие ключи...
}

def t(key, lang='ru'):
    return TEXTS.get(key, {}).get(lang, TEXTS.get(key, {}).get('ru', ''))
