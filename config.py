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

# OpenAI API ключ (опционально - для fallback к AI)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')  # или 'gpt-4'

# Название бота (централизованное - измени здесь, и оно обновится везде)
BOT_NAME = "QA Ментор"

# Настройки для поиска по базе знаний
SEARCH_CONFIG = {
    'min_relevance_score': 5.0,  # Минимальный порог релевантности для показа результатов (повышен с 2.0)
    'high_relevance_score': 8.0,  # Высокий порог - показывать только этот результат
    'max_results': 3,  # Максимальное количество результатов поиска
    'use_synonyms': True,  # Использовать синонимы при поиске
    'use_ai_relevance_check': True,  # Использовать AI для проверки релевантности найденных ответов
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

# Настройки для AI fallback
AI_CONFIG = {
    'enabled': bool(OPENAI_API_KEY),  # Включен только если есть ключ
    'use_fallback': True,  # Использовать AI если не найдено в базе
    'max_tokens': 500,  # Максимальная длина ответа
    'temperature': 0.7,  # Креативность ответов
}

# Проверка наличия токена
if not BOT_TOKEN:
    raise ValueError(
        "BOT_TOKEN не найден! Создайте файл .env и добавьте в него BOT_TOKEN=ваш_токен_бота"
    )

