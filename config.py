"""
Конфигурационный файл для Telegram-бота QA Ментор
Использует переменные окружения для безопасного хранения токена
"""
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Токен бота из переменных окружения
BOT_TOKEN = os.getenv('BOT_TOKEN', '')

# Название бота (централизованное - измени здесь, и оно обновится везде)
BOT_NAME = "QA Ментор"

# Настройки для поиска по базе знаний
SEARCH_CONFIG = {
    'min_relevance_score': 0.3,  # Минимальный порог релевантности для показа результатов
    'max_results': 5,  # Максимальное количество результатов поиска
    'use_synonyms': True,  # Использовать синонимы при поиске
}

# Параметры форматирования ответов
FORMATTING_CONFIG = {
    'max_message_length': 4096,  # Максимальная длина сообщения Telegram
    'use_markdown': True,  # Использовать Markdown форматирование
    'default_detail_level': 'detailed',  # Уровень детализации по умолчанию: 'brief', 'detailed', 'full'
}

# Настройки безопасности
SECURITY_CONFIG = {
    'max_query_length': 500,  # Максимальная длина пользовательского запроса
    'max_search_length': 300,  # Максимальная длина поискового запроса
    'enable_prompt_injection_detection': True,  # Включить обнаружение промпт-хакинга
    'enable_input_sanitization': True,  # Включить очистку входных данных
    'strict_mode': False,  # Строгий режим (более агрессивная фильтрация)
}

# Проверка наличия токена
if not BOT_TOKEN:
    raise ValueError(
        "BOT_TOKEN не найден! Создайте файл .env и добавьте в него BOT_TOKEN=ваш_токен_бота"
    )

