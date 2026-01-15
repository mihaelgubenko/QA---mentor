import telebot
from telebot import types
import config
import re
from knowledge_base import TOPICS, TOPIC_ORDER, SYNONYMS
import security
import ai_helper

# Инициализация бота
bot = telebot.TeleBot(config.BOT_TOKEN)

# Словарь для хранения состояния пользователей
# Формат: {user_id: {"current_topic": "start", "current_question_index": 0}}
user_sessions = {}

def get_user_session(user_id):
    """Получаем или создаем сессию для пользователя"""
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "current_topic": "start",
            "current_question_index": 0,
            "previous_state": None  # Для кнопки "Назад"
        }
    return user_sessions[user_id]

def normalize_text(text):
    """Нормализация текста для поиска: приведение к нижнему регистру, удаление знаков препинания"""
    text = text.lower()
    # Удаляем знаки препинания, оставляем только буквы, цифры и пробелы
    text = re.sub(r'[^\w\s]', ' ', text)
    # Удаляем множественные пробелы
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def expand_with_synonyms(words):
    """Расширяет список слов синонимами"""
    expanded = set(words)
    for word in words:
        if word in SYNONYMS:
            expanded.update(SYNONYMS[word])
    return expanded

def calculate_relevance_score(query_words, question_data, topic_name):
    """Вычисляет релевантность вопроса запросу пользователя"""
    score = 0.0
    
    # Получаем текст для поиска
    question_text = normalize_text(question_data.get("question", ""))
    answer_text = normalize_text(question_data.get("answer", ""))
    keywords = question_data.get("keywords", [])
    topic_text = normalize_text(topic_name)
    
    # Проверка на точное совпадение фразы (высокий приоритет)
    query_phrase = ' '.join(query_words)
    query_phrase_2 = ' '.join(query_words[:2]) if len(query_words) >= 2 else ""
    query_phrase_3 = ' '.join(query_words[:3]) if len(query_words) >= 3 else ""
    
    # Очень высокий бонус за точное совпадение фразы в вопросе
    if query_phrase in question_text:
        score += 20.0
    elif query_phrase_3 and query_phrase_3 in question_text:
        score += 15.0
    elif query_phrase_2 and query_phrase_2 in question_text:
        score += 12.0
    
    # Высокий бонус за точное совпадение фразы в ответе
    if query_phrase in answer_text:
        score += 10.0
    elif query_phrase_3 and query_phrase_3 in answer_text:
        score += 7.0
    elif query_phrase_2 and query_phrase_2 in answer_text:
        score += 5.0
    
    # Расширяем запрос синонимами
    expanded_query = expand_with_synonyms(query_words)
    
    # Подсчет совпадений отдельных слов
    for word in expanded_query:
        # Совпадение в вопросе - очень высокий вес
        if word in question_text:
            score += 5.0
        # Совпадение в keywords - максимальный вес
        if word in [normalize_text(kw) for kw in keywords]:
            score += 8.0
        # Совпадение в ответе - средний вес
        if word in answer_text:
            score += 2.0
        # Совпадение в названии темы - средний вес
        if word in topic_text:
            score += 3.0
    
    # Бонус если все слова запроса найдены в вопросе
    words_in_question = sum(1 for word in query_words if word in question_text)
    if words_in_question == len(query_words) and len(query_words) > 0:
        score += 10.0
    
    return score

def search_in_knowledge_base(query):
    """Интеллектуальный поиск по базе знаний"""
    if not query or len(query.strip()) < 2:
        return []
    
    # Нормализуем запрос
    normalized_query = normalize_text(query)
    query_words = normalized_query.split()
    
    if not query_words:
        return []
    
    # Расширяем запрос синонимами
    expanded_query = expand_with_synonyms(query_words)
    
    results = []
    
    # Ищем по всем темам и вопросам
    for topic_key, topic_data in TOPICS.items():
        topic_name = topic_data.get("name", "")
        
        for question_data in topic_data.get("content", []):
            score = calculate_relevance_score(query_words, question_data, topic_name)
            
            if score >= config.SEARCH_CONFIG['min_relevance_score']:
                results.append({
                    'score': score,
                    'topic_key': topic_key,
                    'topic_name': topic_name,
                    'question': question_data.get("question", ""),
                    'answer': question_data.get("answer", ""),
                    'keywords': question_data.get("keywords", [])
                })
    
    # Сортируем по релевантности (от большего к меньшему)
    results.sort(key=lambda x: x['score'], reverse=True)
    
    # Возвращаем топ результатов
    return results[:config.SEARCH_CONFIG['max_results']]

def create_keyboard(with_start=False, with_back=False, with_prev=False, with_next=False, with_home=False, with_cancel=False, with_commands=False):
    """Создаем клавиатуру с нужными кнопками"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = []

    if with_start:
        buttons.append("Старт 🚀")
    if with_back:
        buttons.append("Назад ◀️")
    if with_prev:
        buttons.append("Предыдущий вопрос ↩️")
    if with_next:
        buttons.append("Следующая тема ➡️")
    if with_home:
        buttons.append("На главную 🏠")
    if with_cancel:
        buttons.append("Задать вопрос ❓")
    if with_commands:
        buttons.append("📋 Команды")
        buttons.append("📖 Список тем")

    markup.add(*buttons)
    return markup

# Константы для сообщений
NOT_FOUND_MESSAGE = """😔 Я не нашел точного ответа на твой вопрос.

*Попробуй:*
• Переформулировать вопрос другими словами
• Использовать /topics для просмотра всех тем
• Изучать темы по порядку через навигацию"""

SEARCH_NOT_FOUND_MESSAGE = """Попробуй:
• Использовать другие слова
• Проверить правописание
• Использовать /topics для просмотра всех тем"""

def format_response_from_db(result):
    """Форматирует ответ из базы знаний"""
    response = f"*{result['topic_name']}*\n\n"
    response += f"*{result['question']}*\n\n"
    response += result['answer']
    
    if len(response) > 4000:
        response = response[:4000] + "\n\n... (сообщение обрезано)"
    
    return response

def send_ai_response(chat_id, question):
    """Отправляет ответ от AI, если он доступен"""
    if not config.AI_CONFIG['enabled'] or not config.AI_CONFIG['use_fallback']:
        return False
    
    bot.send_chat_action(chat_id, 'typing')
    ai_response = ai_helper.ask_ai(question)
    
    if ai_response:
        response = f"🤖 *Ответ от AI:*\n\n{ai_response}\n\n"
        response += "💡 *Совет:* Используй /topics для изучения структурированных тем."
        
        if len(response) > 4000:
            response = response[:4000] + "\n\n... (сообщение обрезано)"
        
        bot.send_message(
            chat_id,
            response,
            parse_mode="Markdown",
            reply_markup=create_keyboard(with_home=True)
        )
        return True
    
    return False

def send_not_found_message(chat_id, query=None, is_search=False):
    """Отправляет сообщение о том, что ничего не найдено"""
    if is_search and query:
        safe_query = security.escape_markdown(query)
        message = f"😔 По запросу '*{safe_query}*' ничего не найдено.\n\n{SEARCH_NOT_FOUND_MESSAGE}"
    elif is_search:
        message = f"😔 По запросу ничего не найдено.\n\n{SEARCH_NOT_FOUND_MESSAGE}"
    else:
        message = NOT_FOUND_MESSAGE
    
    bot.send_message(
        chat_id,
        message,
        parse_mode="Markdown",
        reply_markup=create_keyboard(with_home=True) if not is_search else None
    )

def validate_and_sanitize_input(raw_input, max_length=None, is_search=False):
    """Валидирует и очищает пользовательский ввод"""
    if not max_length:
        max_length = config.SECURITY_CONFIG['max_search_length'] if is_search else config.SECURITY_CONFIG['max_query_length']
    
    if config.SECURITY_CONFIG['enable_input_sanitization']:
        sanitized, is_valid, error_msg = security.sanitize_input(
            raw_input,
            max_length=max_length,
            check_injection=config.SECURITY_CONFIG['enable_prompt_injection_detection']
        )
        
        if not is_valid:
            return None, False, error_msg
        
        return sanitized, True, None
    else:
        return raw_input, True, None

def process_search_results(chat_id, query, results, is_search=False):
    """Обрабатывает результаты поиска и отправляет ответ"""
    if not results:
        # Ничего не найдено - используем AI
        if not send_ai_response(chat_id, query):
            send_not_found_message(chat_id, query=query, is_search=is_search)
        return
    
    result = results[0]
    score = result['score']
    
    # Если очень высокий score - показываем сразу
    if score >= config.SEARCH_CONFIG['high_relevance_score']:
        response = format_response_from_db(result)
        bot.send_message(
            chat_id,
            response,
            parse_mode="Markdown",
            reply_markup=create_keyboard(with_home=True)
        )
        return
    
    # Если средний score - проверяем релевантность через AI
    if score >= config.SEARCH_CONFIG['min_relevance_score']:
        is_relevant = ai_helper.check_relevance(
            query,
            result['question'],
            result['answer']
        )
        
        # Если AI недоступен (None) или считает нерелевантным (False) - используем AI fallback
        if is_relevant is None or not is_relevant:
            if not send_ai_response(chat_id, query):
                # AI не настроен - показываем найденный ответ (лучше чем ничего)
                response = format_response_from_db(result)
                bot.send_message(
                    chat_id,
                    response,
                    parse_mode="Markdown",
                    reply_markup=create_keyboard(with_home=True)
                )
            return
        else:
            # AI подтвердил релевантность - показываем ответ из базы
            response = format_response_from_db(result)
            bot.send_message(
                chat_id,
                response,
                parse_mode="Markdown",
                reply_markup=create_keyboard(with_home=True)
            )
            return
    
    # Score слишком низкий (< 5.0) - используем AI
    if not send_ai_response(chat_id, query):
        send_not_found_message(chat_id, query=query, is_search=is_search)

def show_question(user_id, chat_id):
    """Показываем текущий вопрос пользователю"""
    session = get_user_session(user_id)
    topic_key = session["current_topic"]
    question_index = session["current_question_index"]

    topic = TOPICS[topic_key]
    question_data = topic["content"][question_index]

    # Отправляем вопрос (для стартовой темы не показываем название)
    if topic_key == "start" and "is_welcome" in question_data:
        # Для стартового сообщения показываем только вопрос без названия темы
        bot.send_message(
            chat_id,
            question_data['question'],
            parse_mode="Markdown"
        )
    else:
        # Для остальных тем показываем название темы
        bot.send_message(
            chat_id,
            f"**{topic['name']}**\n\n*Вопрос:* {question_data['question']}",
            parse_mode="Markdown"
        )

    # Определяем, какие кнопки показывать
    is_first_topic = topic_key == "start"
    is_last_topic = topic_key == TOPIC_ORDER[-1]
    is_first_question = question_index == 0
    is_last_question = question_index == len(topic["content"]) - 1
    has_welcome = "is_welcome" in question_data
    has_final = "is_final" in question_data

    # Создаем клавиатуру
    markup = create_keyboard(
        with_back=not is_first_topic and is_first_question,
        with_prev=not is_first_question,
        with_next=(is_last_question and not is_last_topic) or has_welcome,
        with_home=not is_first_topic,
        with_cancel=True,
        with_commands=is_first_topic  # Показываем команды только на старте
    )

    # Отправляем ответ (возможно, с задержкой для эффекта "печатает")
    bot.send_chat_action(chat_id, 'typing')
    # Имитируем небольшую задержку для лучшего UX
    import time
    time.sleep(0.5)

    # Расчет прогресса темы (только для не-стартовых тем)
    answer_text = question_data["answer"]
    # Заменяем {bot_name} на реальное название бота
    if "{bot_name}" in answer_text:
        answer_text = answer_text.format(bot_name=config.BOT_NAME)
    if not is_first_topic:
        total_questions = len(topic["content"])
        current_question_num = question_index + 1
        progress_percent = int((current_question_num / total_questions) * 100)
        
        # Простой трекер прогресса в начале ответа
        progress_text = f"📊 *Прогресс:* {progress_percent}% ({current_question_num}/{total_questions})\n\n"
        answer_text = progress_text + answer_text
        
        # Добавляем индикатор завершения темы, если это последний вопрос
        if is_last_question and not is_last_topic:
            answer_text += "\n\n---\n✅ *Тема завершена!* Нажми «Следующая тема ➡️» для продолжения."
        elif has_final:
            answer_text += "\n\n---\n🎉 *Поздравляю!* Вы завершили базовый курс!"

    bot.send_message(
        chat_id,
        answer_text,
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    session = get_user_session(user_id)
    session["current_topic"] = "start"
    session["current_question_index"] = 0

    show_question(user_id, message.chat.id)

@bot.message_handler(commands=['help'])
def send_help(message):
    """Обработчик команды /help"""
    help_text = f"""
*📚 {config.BOT_NAME} — Учитель по тестированию*

*Основные команды:*
/start — Начать обучение с начала
/help — Показать эту справку
/search <запрос> — Найти информацию по запросу
/topics — Показать список всех тем
/license — Информация о лицензии

*Как использовать:*
1. Используй кнопки навигации для изучения тем по порядку
2. Задавай вопросы в свободной форме — я найду подходящий ответ
3. Используй /search для быстрого поиска

*Примеры запросов:*
• "Что такое баг?"
• "Как написать тест-кейс?"
• "Какие инструменты нужны тестировщику?"

💡 *Совет:* Я понимаю синонимы! Можешь спросить "дефект" вместо "баг", "тест-кейс" вместо "test case".

Удачи в обучении! 🚀

---
© 2025 QA Ментор создан Михаилом Губенко. Все права защищены.
Лицензия: GPL-3.0
    """
    bot.send_message(message.chat.id, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['license'])
def send_license(message):
    """Обработчик команды /license"""
    license_text = f"""
*📜 Лицензия*

© 2025 {config.BOT_NAME}. Все права защищены.

*Лицензия:* GNU General Public License v3.0 (GPL-3.0)

*Условия использования:*
• ✅ Свободное использование и изучение кода
• ✅ Возможность модификации
• ⚠️ Производные работы должны быть под GPL-3.0
• ⚠️ При распространении необходим исходный код

*Исходный код:*
https://github.com/mihaelgubenko/QA---mentor

Полный текст лицензии: /help
    """
    bot.send_message(message.chat.id, license_text, parse_mode="Markdown")

@bot.message_handler(commands=['topics'])
def send_topics(message):
    """Обработчик команды /topics"""
    topics_text = "*📖 Список тем для изучения:*\n\n"
    
    for i, topic_key in enumerate(TOPIC_ORDER, 1):
        topic = TOPICS.get(topic_key, {})
        name = topic.get("name", "Неизвестная тема")
        description = topic.get("description", "")
        topics_text += f"{i}. {name}\n"
        if description:
            topics_text += f"   _{description}_\n"
        topics_text += "\n"
    
    topics_text += "Используй кнопки навигации или /start для начала обучения!"
    bot.send_message(message.chat.id, topics_text, parse_mode="Markdown")

@bot.message_handler(commands=['search'])
def handle_search(message):
    """Обработчик команды /search"""
    # Извлекаем запрос из команды
    raw_query = message.text.replace('/search', '').strip()
    
    if not raw_query:
        bot.send_message(
            message.chat.id,
            "❌ Укажи запрос для поиска!\n\n"
            "*Пример:* /search что такое баг",
            parse_mode="Markdown"
        )
        return
    
    # Валидация и очистка запроса
    query, is_valid, error_msg = validate_and_sanitize_input(raw_query, is_search=True)
    
    if not is_valid:
        bot.send_message(
            message.chat.id,
            f"⚠️ {error_msg}\n\n"
            "Пожалуйста, переформулируй запрос.",
            parse_mode="Markdown"
        )
        return
    
    bot.send_chat_action(message.chat.id, 'typing')
    
    # Выполняем поиск и обрабатываем результаты
    results = search_in_knowledge_base(query)
    process_search_results(message.chat.id, query, results, is_search=True)

@bot.message_handler(func=lambda message: message.text == "Старт 🚀")
def start_over(message):
    """Начать сначала"""
    send_welcome(message)

@bot.message_handler(func=lambda message: message.text == "На главную 🏠")
def go_home(message):
    """Вернуться на главную (к первой теме)"""
    user_id = message.from_user.id
    session = get_user_session(user_id)
    session["current_topic"] = "start"
    session["current_question_index"] = 0
    show_question(user_id, message.chat.id)

@bot.message_handler(func=lambda message: message.text == "Назад ◀️")
def go_back(message):
    """Перейти к предыдущей теме"""
    user_id = message.from_user.id
    session = get_user_session(user_id)
    current_index = TOPIC_ORDER.index(session["current_topic"])

    if current_index > 0:
        session["current_topic"] = TOPIC_ORDER[current_index - 1]
        session["current_question_index"] = 0
        show_question(user_id, message.chat.id)
    else:
        bot.send_message(message.chat.id, "Вы уже в начале обучения!")

@bot.message_handler(func=lambda message: message.text == "Предыдущий вопрос ↩️")
def prev_question(message):
    """Показать предыдущий вопрос в текущей теме"""
    user_id = message.from_user.id
    session = get_user_session(user_id)
    if session["current_question_index"] > 0:
        session["current_question_index"] -= 1
        show_question(user_id, message.chat.id)
    else:
        bot.send_message(message.chat.id, "Это первый вопрос в теме.")

@bot.message_handler(func=lambda message: message.text == "Следующая тема ➡️")
def next_topic(message):
    """Перейти к следующей теме"""
    user_id = message.from_user.id
    session = get_user_session(user_id)
    current_index = TOPIC_ORDER.index(session["current_topic"])

    if current_index < len(TOPIC_ORDER) - 1:
        session["current_topic"] = TOPIC_ORDER[current_index + 1]
        session["current_question_index"] = 0
        show_question(user_id, message.chat.id)
    else:
        bot.send_message(message.chat.id, "Поздравляю! Вы завершили базовый курс! 🎉")

@bot.message_handler(func=lambda message: message.text == "Задать вопрос ❓")
def ask_question_prompt(message):
    """Подсказка для задавания вопроса"""
    bot.send_message(
        message.chat.id,
        "💬 *Задай свой вопрос о тестировании!*\n\n"
        "*Примеры вопросов:*\n"
        "• Что такое баг?\n"
        "• Как написать тест-кейс?\n"
        "• Какие инструменты нужны тестировщику?\n"
        "• Что такое регрессионное тестирование?\n"
        "• Как проверить работу API?\n"
        "• Что такое smoke-тестирование?\n\n"
        "Просто напиши свой вопрос, и я найду ответ! 🔍",
        parse_mode="Markdown",
        reply_markup=create_keyboard(with_home=True)
    )

@bot.message_handler(func=lambda message: message.text == "📋 Команды")
def show_commands_button(message):
    """Показать команды при нажатии кнопки"""
    send_help(message)

@bot.message_handler(func=lambda message: message.text == "📖 Список тем")
def show_topics_button(message):
    """Показать темы при нажатии кнопки"""
    send_topics(message)

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    """Обработчик текстовых сообщений (для произвольных вопросов)"""
    user_input = message.text.lower()

    # Если пользователь просто нажал на кнопку, она уже обработана выше
    button_texts = ["Старт 🚀", "На главную 🏠", "Назад ◀️", "Предыдущий вопрос ↩️", 
                    "Следующая тема ➡️", "Задать вопрос ❓", "📋 Команды", "📖 Список тем"]
    if message.text in button_texts:
        return

    # Команды для продолжения обучения (без "следующая тема" - она для разделов)
    continue_words = ["продолжай", "дальше", "next", "ок", "окей", "ok", 
                      "продолжить", "вперед", "далее", "следующий", "продолжи"]
    if any(word in user_input for word in continue_words):
        # Переходим к следующему вопросу или следующей теме
        user_id = message.from_user.id
        session = get_user_session(user_id)
        topic_key = session["current_topic"]
        question_index = session["current_question_index"]
        
        topic = TOPICS[topic_key]
        is_last_question = question_index >= len(topic["content"]) - 1
        
        if is_last_question:
            # Последний вопрос в теме - переходим к следующей теме
            current_index = TOPIC_ORDER.index(topic_key)
            if current_index < len(TOPIC_ORDER) - 1:
                session["current_topic"] = TOPIC_ORDER[current_index + 1]
                session["current_question_index"] = 0
                show_question(user_id, message.chat.id)
            else:
                bot.send_message(message.chat.id, "Поздравляю! Вы завершили базовый курс! 🎉")
        else:
            # Не последний вопрос - показываем следующий вопрос в текущей теме
            session["current_question_index"] += 1
            show_question(user_id, message.chat.id)
        return
    
    # Команды для возврата назад
    back_words = ["назад", "предыдущая", "previous", "back", "вернуться"]
    if any(word in user_input for word in back_words):
        user_id = message.from_user.id
        session = get_user_session(user_id)
        question_index = session["current_question_index"]
        
        if question_index > 0:
            # Возврат к предыдущему вопросу в теме
            session["current_question_index"] -= 1
            show_question(user_id, message.chat.id)
        else:
            # Первый вопрос - переходим к предыдущей теме
            current_index = TOPIC_ORDER.index(session["current_topic"])
            if current_index > 0:
                prev_topic = TOPIC_ORDER[current_index - 1]
                session["current_topic"] = prev_topic
                prev_topic_data = TOPICS[prev_topic]
                session["current_question_index"] = len(prev_topic_data["content"]) - 1
                show_question(user_id, message.chat.id)
            else:
                bot.send_message(message.chat.id, "Вы уже в начале обучения!")
        return

    # Валидация и очистка пользовательского ввода
    raw_user_text = message.text
    user_text, is_valid, error_msg = validate_and_sanitize_input(raw_user_text)
    
    if not is_valid:
        bot.send_message(
            message.chat.id,
            f"⚠️ {error_msg}\n\n"
            "Пожалуйста, переформулируй вопрос.",
            parse_mode="Markdown"
        )
        return
    
    # Ответ на произвольный вопрос пользователя
    bot.send_chat_action(message.chat.id, 'typing')
    import time
    time.sleep(0.5)

    # Простые приветствия и благодарности
    if any(word in user_input for word in ["привет", "здравств", "hello", "hi"]):
        bot.send_message(
            message.chat.id, 
            "Привет! 👋 Я здесь, чтобы помочь тебе с тестированием.\n\n"
            "Можешь задавать вопросы в свободной форме или использовать команды:\n"
            "/help — справка\n"
            "/search <запрос> — поиск\n"
            "/topics — список тем",
            parse_mode="Markdown"
        )
        return
    
    elif any(word in user_input for word in ["спасибо", "благодар"]):
        bot.send_message(message.chat.id, "Всегда рад помочь! Удачи в обучении! 💪")
        return
    
    # Интеллектуальный поиск по базе знаний и обработка результатов
    results = search_in_knowledge_base(user_text)
    process_search_results(message.chat.id, user_text, results)

# Запуск бота
if __name__ == "__main__":
    print("=" * 50)
    print(f"  {config.BOT_NAME} - Telegram Bot")
    print("=" * 50)
    print()
    
    # Проверка токена перед запуском
    if not config.BOT_TOKEN or config.BOT_TOKEN == 'your_bot_token_here' or config.BOT_TOKEN.strip() == '':
        print("[ОШИБКА] Токен бота не настроен!")
        print()
        print("Создайте файл .env и добавьте:")
        print("  BOT_TOKEN=ваш_токен_от_BotFather")
        print()
        print("Как получить токен:")
        print("1. Откройте Telegram")
        print("2. Найдите @BotFather")
        print("3. Отправьте /newbot")
        print("4. Следуйте инструкциям")
        print("5. Скопируйте токен в файл .env")
        exit(1)
    
    # Проверка формата токена
    if ':' not in config.BOT_TOKEN or len(config.BOT_TOKEN) < 20:
        print("[ОШИБКА] Неверный формат токена!")
        print()
        print("Токен должен быть вида: 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz")
        print(f"Текущий токен: {config.BOT_TOKEN[:20]}... (обрезан)")
        print()
        print("Проверьте файл .env - токен должен быть без пробелов и кавычек")
        exit(1)
    
    print(f"✓ Токен загружен: {config.BOT_TOKEN[:10]}...{config.BOT_TOKEN[-5:]}")
    print("✓ Подключение к Telegram API...")
    print()
    print("Бот запущен! Нажмите Ctrl+C для остановки.")
    print()
    
    try:
        # Проверка доступности бота через getMe
        bot_info = bot.get_me()
        if bot_info:
            print(f"✓ Бот успешно подключен!")
            print(f"  Имя: {bot_info.first_name}")
            if bot_info.username:
                print(f"  Username: @{bot_info.username}")
            print()
            print("Бот готов к работе! Найдите его в Telegram:")
            if bot_info.username:
                print(f"  https://t.me/{bot_info.username}")
            print()
    except Exception as e:
        print(f"[ОШИБКА] Не удалось проверить подключение!")
        print(f"Детали: {e}")
        print()
        print("Возможные причины:")
        print("1. Неверный токен - проверьте файл .env")
        print("2. Проблемы с интернет-соединением")
        print("3. Telegram API недоступен")
        print()
        print("Продолжаю попытку подключения...")
        print()
    
    try:
        bot.infinity_polling(none_stop=True, interval=0, timeout=20)
    except KeyboardInterrupt:
        print()
        print("Бот остановлен пользователем.")
    except Exception as e:
        error_str = str(e)
        if "409" in error_str or "Conflict" in error_str:
            print()
            print("[ОШИБКА] Конфликт: запущено несколько экземпляров бота!")
            print("Детали: Conflict: terminated by other getUpdates request")
            print()
            print("Решение:")
            print("1. Убедитесь, что бот не запущен локально")
            print("2. Проверьте, что на Railway запущен только один экземпляр")
            print("3. Подождите 10-20 секунд и перезапустите бота")
            print("4. Если проблема сохраняется, остановите все экземпляры и запустите заново")
        else:
            print()
            print(f"[ОШИБКА] Бот остановлен из-за ошибки!")
            print(f"Детали: {type(e).__name__}: {e}")
            print()
            print("Проверьте:")
            print("1. Правильность токена в .env файле")
            print("2. Подключение к интернету")
            print("3. Доступность Telegram API")
            print("4. Не заблокирован ли Telegram в вашей стране/сети")
        exit(1)
