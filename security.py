"""
Модуль безопасности для Telegram-бота QA Ментор
Защита от промпт-хакинга, инъекций и других уязвимостей
"""
import re
import html


# Паттерны промпт-хакинга (на русском и английском)
PROMPT_INJECTION_PATTERNS = [
    # Игнорирование инструкций
    r'игнорир[уй]й?\s+(предыдущ|все|эти)\s+инструкц',
    r'ignore\s+(previous|all|these)\s+instructions?',
    r'forget\s+(previous|all|everything)',
    r'забудь\s+(предыдущ|все|это)',
    
    # Системные промпты
    r'системн[ыйойая]\s+промпт',
    r'system\s+prompt',
    r'you\s+are\s+(now|a|an)',
    r'ты\s+(теперь|сейчас)\s+(есть|являешься)',
    
    # Переопределение роли
    r'act\s+as\s+(if\s+)?you\s+are',
    r'представь\s+себя',
    r'pretend\s+to\s+be',
    
    # Извлечение промпта
    r'покажи\s+(мне\s+)?(системн|исходн|полн)',
    r'show\s+(me\s+)?(system|original|full|complete)\s+prompt',
    r'what\s+(are|is)\s+your\s+instructions?',
    r'какие\s+твои\s+инструкции',
    
    # Выполнение команд
    r'выполни\s+команду',
    r'execute\s+command',
    r'run\s+(command|code|script)',
    
    # SQL/Code инъекции (базовые)
    r';\s*(drop|delete|update|insert|select)',
    r'union\s+select',
    r'<script',
    r'javascript:',
    
    # Попытки обхода
    r'\[system\]',
    r'\[instruction\]',
    r'\[prompt\]',
    r'#\s*(system|instruction|prompt)',
]

# Подозрительные символы и паттерны
SUSPICIOUS_PATTERNS = [
    r'[<>{}[\]\\|`]',  # Специальные символы
    r'(.)\1{10,}',  # Повторяющиеся символы (возможная DoS атака)
    r'\x00',  # Null байты
]

# Максимальная длина запроса
MAX_QUERY_LENGTH = 500

# Максимальная длина для поиска
MAX_SEARCH_LENGTH = 300


def escape_markdown(text):
    """
    Экранирует специальные символы Markdown для безопасного отображения
    
    Args:
        text: Текст для экранирования
        
    Returns:
        Экранированный текст
    """
    if not text:
        return ""
    
    # Экранируем специальные символы Markdown
    # Telegram Markdown: * _ ` [ ] ( )
    escape_chars = ['*', '_', '`', '[', ']', '(', ')']
    
    for char in escape_chars:
        text = text.replace(char, '\\' + char)
    
    return text


def escape_markdown_v2(text):
    """
    Экранирует специальные символы MarkdownV2 для безопасного отображения
    
    Args:
        text: Текст для экранирования
        
    Returns:
        Экранированный текст
    """
    if not text:
        return ""
    
    # MarkdownV2 требует экранирования больше символов
    escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    for char in escape_chars:
        text = text.replace(char, '\\' + char)
    
    return text


def detect_prompt_injection(text):
    """
    Обнаруживает попытки промпт-хакинга в тексте
    
    Args:
        text: Текст для проверки
        
    Returns:
        tuple: (is_suspicious, reason) - флаг подозрительности и причина
    """
    if not text:
        return False, None
    
    text_lower = text.lower()
    
    # Проверяем паттерны промпт-хакинга
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True, f"Обнаружен подозрительный паттерн: {pattern}"
    
    # Проверяем подозрительные символы
    for pattern in SUSPICIOUS_PATTERNS:
        if re.search(pattern, text):
            return True, f"Обнаружены подозрительные символы"
    
    return False, None


def validate_query_length(text, max_length=MAX_QUERY_LENGTH):
    """
    Проверяет длину запроса
    
    Args:
        text: Текст для проверки
        max_length: Максимальная допустимая длина
        
    Returns:
        tuple: (is_valid, error_message) - флаг валидности и сообщение об ошибке
    """
    if not text:
        return False, "Запрос не может быть пустым"
    
    if len(text) > max_length:
        return False, f"Запрос слишком длинный (максимум {max_length} символов)"
    
    return True, None


def sanitize_input(text, max_length=MAX_QUERY_LENGTH, check_injection=True):
    """
    Полная очистка и валидация пользовательского ввода
    
    Args:
        text: Текст для очистки
        max_length: Максимальная длина
        check_injection: Проверять ли на промпт-хакинг
        
    Returns:
        tuple: (sanitized_text, is_valid, error_message)
    """
    if not text:
        return "", False, "Ввод не может быть пустым"
    
    # Удаляем начальные и конечные пробелы
    text = text.strip()
    
    # Проверка длины
    is_valid, error = validate_query_length(text, max_length)
    if not is_valid:
        return text[:max_length], False, error
    
    # Проверка на промпт-хакинг
    if check_injection:
        is_suspicious, reason = detect_prompt_injection(text)
        if is_suspicious:
            # Логируем попытку (в будущем можно добавить логирование)
            # Пока просто обрезаем подозрительные части или отклоняем
            return text, False, "Обнаружен подозрительный запрос. Пожалуйста, переформулируйте вопрос."
    
    # Удаляем null байты
    text = text.replace('\x00', '')
    
    # Ограничиваем количество пробелов подряд
    text = re.sub(r'\s+', ' ', text)
    
    return text, True, None


def safe_format_message(text, user_query=None):
    """
    Безопасное форматирование сообщения с пользовательским запросом
    
    Args:
        text: Базовый текст сообщения
        user_query: Пользовательский запрос (будет экранирован)
        
    Returns:
        Безопасно отформатированное сообщение
    """
    if user_query:
        # Экранируем пользовательский запрос
        safe_query = escape_markdown(user_query)
        return text.format(query=safe_query)
    
    return escape_markdown(text)


def is_safe_for_display(text):
    """
    Проверяет, безопасен ли текст для отображения
    
    Args:
        text: Текст для проверки
        
    Returns:
        bool: True если безопасен
    """
    if not text:
        return True
    
    # Проверяем на промпт-хакинг
    is_suspicious, _ = detect_prompt_injection(text)
    if is_suspicious:
        return False
    
    # Проверяем длину
    is_valid, _ = validate_query_length(text)
    if not is_valid:
        return False
    
    return True

