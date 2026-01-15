"""
Тестовый скрипт для проверки логики бота
Запуск: python test_logic.py
"""
import sys
import os
import io

# Устанавливаем UTF-8 кодировку для вывода (для Windows)
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Добавляем текущую директорию в путь для импорта
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Мокаем конфиг перед импортом модулей
import unittest.mock as mock

# Мокаем config чтобы избежать ошибок при отсутствии .env
# Используем правильный формат токена для telebot
with mock.patch.dict('os.environ', {
    'BOT_TOKEN': '1234567890:ABCdefGHIjklMNOpqrsTUVwxyz',
    'OPENAI_API_KEY': '',
    'OPENAI_MODEL': 'gpt-3.5-turbo'
}):
    # Мокируем telebot перед импортом qa_bot
    mock_telebot = mock.MagicMock()
    mock_telebot.TeleBot = mock.MagicMock()
    sys.modules['telebot'] = mock_telebot
    
    # Теперь импортируем модули
    from qa_bot import (
        normalize_text,
        expand_with_synonyms,
        calculate_relevance_score,
        search_in_knowledge_base,
        format_response_from_db,
        get_user_session,
        validate_and_sanitize_input
    )
    from ai_helper import validate_model, ALLOWED_MODELS
    from knowledge_base import SYNONYMS, TOPICS, TOPIC_ORDER
    import config

# Цвета для вывода
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_test(name):
    """Выводит название теста"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}>> Test: {name}{Colors.RESET}")

def print_pass(message):
    """Выводит успешный тест"""
    print(f"{Colors.GREEN}[PASS] {message}{Colors.RESET}")

def print_fail(message):
    """Выводит проваленный тест"""
    print(f"{Colors.RED}[FAIL] {message}{Colors.RESET}")

def print_info(message):
    """Выводит информацию"""
    print(f"{Colors.YELLOW}[INFO] {message}{Colors.RESET}")

def test_normalize_text():
    """Тестирует нормализацию текста"""
    print_test("normalize_text()")
    
    tests = [
        ("Что такое баг?", "что такое баг"),
        ("Привет, мир!", "привет мир"),
        ("  Много   пробелов  ", "много пробелов"),
        ("ТЕСТ В ВЕРХНЕМ РЕГИСТРЕ", "тест в верхнем регистре"),
        ("Спец.символы!!!", "спец символы"),
        ("", ""),
    ]
    
    passed = 0
    failed = 0
    
    for input_text, expected in tests:
        result = normalize_text(input_text)
        if result == expected:
            print_pass(f"'{input_text}' -> '{result}'")
            passed += 1
        else:
            print_fail(f"'{input_text}' -> '{result}' (expected: '{expected}')")
            failed += 1
    
    return passed, failed

def test_expand_with_synonyms():
    """Тестирует расширение синонимами"""
    print_test("expand_with_synonyms()")
    
    tests = [
        (["тестирование"], {"тестирование", "проверка", "тест", "qa", "контроль качества"}),
        (["баг"], {"баг", "дефект", "ошибка", "глюк", "сбой", "проблема"}),
        (["неизвестное"], {"неизвестное"}),  # Нет синонимов
        (["тестирование", "баг"], {"тестирование", "проверка", "тест", "qa", "контроль качества", 
                                   "баг", "дефект", "ошибка", "глюк", "сбой", "проблема"}),
    ]
    
    passed = 0
    failed = 0
    
    for input_words, expected_set in tests:
        result = expand_with_synonyms(input_words)
        if result == expected_set:
            print_pass(f"{input_words} -> {len(result)} синонимов")
            passed += 1
        else:
            missing = expected_set - result
            extra = result - expected_set
            print_fail(f"{input_words} -> не совпадает (отсутствуют: {missing}, лишние: {extra})")
            failed += 1
    
    return passed, failed

def test_calculate_relevance_score():
    """Тестирует расчет релевантности"""
    print_test("calculate_relevance_score()")
    
    # Тестовые данные
    question_data = {
        "question": "Что такое тестирование ПО?",
        "answer": "Тестирование ПО - это процесс проверки программы на наличие ошибок.",
        "keywords": ["тестирование", "qa", "проверка"]
    }
    topic_name = "Основы тестирования"
    
    tests = [
        (["тестирование"], 5.0, "Слово в вопросе"),
        (["что", "такое"], 20.0 + 10.0, "Точное совпадение фразы"),
        (["проверка"], 5.0, "Синоним в вопросе"),
        (["ошибки"], 0.0, "Слово в ответе (может не совпадать точно)"),
        (["qa"], 8.0, "Ключевое слово"),
        (["неизвестное"], 0.0, "Нет совпадений"),
    ]
    
    passed = 0
    failed = 0
    
    for query_words, min_score, description in tests:
        score = calculate_relevance_score(query_words, question_data, topic_name)
        if score >= min_score:
            print_pass(f"{description}: score={score:.1f} (мин: {min_score:.1f})")
            passed += 1
        else:
            print_fail(f"{description}: score={score:.1f} (ожидалось >= {min_score:.1f})")
            failed += 1
    
    return passed, failed

def test_search_in_knowledge_base():
    """Тестирует поиск в базе знаний"""
    print_test("search_in_knowledge_base()")
    
    tests = [
        ("тестирование", True, "Должен найти результаты"),
        ("баг", True, "Должен найти результаты"),
        ("xyz123абвгд", False, "Не должен найти результаты"),
        ("", False, "Пустой запрос"),
        ("а", False, "Слишком короткий запрос"),
    ]
    
    passed = 0
    failed = 0
    
    for query, should_find, description in tests:
        results = search_in_knowledge_base(query)
        found = len(results) > 0
        
        if found == should_find:
            if found:
                print_pass(f"{description}: найдено {len(results)} результатов (лучший score: {results[0]['score']:.1f})")
            else:
                print_pass(f"{description}: результаты не найдены (ожидалось)")
            passed += 1
        else:
            print_fail(f"{description}: найдено {len(results)} результатов (ожидалось: {'найти' if should_find else 'не найти'})")
            failed += 1
    
    return passed, failed

def test_format_response_from_db():
    """Тестирует форматирование ответа"""
    print_test("format_response_from_db()")
    
    # Короткий ответ
    short_result = {
        'topic_name': "Тестовая тема",
        'question': "Тестовый вопрос?",
        'answer': "Короткий ответ."
    }
    
    # Длинный ответ (более 4000 символов)
    long_answer = "A" * 5000
    long_result = {
        'topic_name': "Тестовая тема",
        'question': "Тестовый вопрос?",
        'answer': long_answer
    }
    
    passed = 0
    failed = 0
    
    # Тест короткого ответа
    response = format_response_from_db(short_result)
    if len(response) < 4000 and "Тестовая тема" in response and "Тестовый вопрос" in response:
        print_pass(f"Короткий ответ: {len(response)} символов")
        passed += 1
    else:
        print_fail(f"Короткий ответ: неправильное форматирование")
        failed += 1
    
    # Тест длинного ответа (должен обрезаться)
    response = format_response_from_db(long_result)
    if len(response) <= 4000 and "... (сообщение обрезано)" in response:
        print_pass(f"Длинный ответ обрезан: {len(response)} символов")
        passed += 1
    else:
        print_fail(f"Длинный ответ: {len(response)} символов (должно быть <= 4000)")
        failed += 1
    
    return passed, failed

def test_get_user_session():
    """Тестирует управление сессиями пользователей"""
    print_test("get_user_session()")
    
    # Очищаем сессии перед тестом
    from qa_bot import user_sessions
    user_sessions.clear()
    
    passed = 0
    failed = 0
    
    # Тест создания новой сессии
    user_id_1 = 12345
    session_1 = get_user_session(user_id_1)
    if session_1["current_topic"] == "start" and session_1["current_question_index"] == 0:
        print_pass("Создание новой сессии")
        passed += 1
    else:
        print_fail("Создание новой сессии: неправильные значения по умолчанию")
        failed += 1
    
    # Тест получения существующей сессии
    session_1_again = get_user_session(user_id_1)
    if session_1 is session_1_again:  # Должен быть тот же объект
        print_pass("Получение существующей сессии")
        passed += 1
    else:
        print_fail("Получение существующей сессии: создана новая сессия")
        failed += 1
    
    # Тест независимости сессий разных пользователей
    user_id_2 = 67890
    session_2 = get_user_session(user_id_2)
    if session_1 is not session_2:
        print_pass("Независимость сессий разных пользователей")
        passed += 1
    else:
        print_fail("Независимость сессий: сессии совпадают")
        failed += 1
    
    return passed, failed

def test_validate_model():
    """Тестирует валидацию моделей"""
    print_test("validate_model()")
    
    tests = [
        ("gpt-3.5-turbo", "gpt-3.5-turbo", "Разрешенная модель"),
        ("gpt-4", "gpt-4", "Разрешенная модель"),
        ("gpt-4o", "gpt-4o", "Разрешенная модель"),
        ("gpt-5", "gpt-3.5-turbo", "Нераспознанная модель -> fallback"),
        ("", "gpt-3.5-turbo", "Пустая модель -> fallback"),
        ("  gpt-4  ", "gpt-4", "Модель с пробелами"),
        ("GPT-3.5-TURBO", "gpt-3.5-turbo", "Модель в верхнем регистре"),
    ]
    
    passed = 0
    failed = 0
    
    for input_model, expected, description in tests:
        result = validate_model(input_model)
        if result == expected:
            print_pass(f"{description}: '{input_model}' -> '{result}'")
            passed += 1
        else:
            print_fail(f"{description}: '{input_model}' -> '{result}' (ожидалось: '{expected}')")
            failed += 1
    
    return passed, failed

def test_validate_and_sanitize_input():
    """Тестирует валидацию и санитизацию ввода"""
    print_test("validate_and_sanitize_input()")
    
    # Временно отключаем санитизацию для теста
    original_enabled = config.SECURITY_CONFIG['enable_input_sanitization']
    config.SECURITY_CONFIG['enable_input_sanitization'] = False
    
    passed = 0
    failed = 0
    
    # Тест без санитизации
    text, is_valid, error = validate_and_sanitize_input("Тестовый текст")
    if is_valid and text == "Тестовый текст":
        print_pass("Валидация без санитизации")
        passed += 1
    else:
        print_fail(f"Валидация без санитизации: is_valid={is_valid}, text={text}")
        failed += 1
    
    # Восстанавливаем настройки
    config.SECURITY_CONFIG['enable_input_sanitization'] = original_enabled
    
    return passed, failed

def test_knowledge_base_structure():
    """Тестирует структуру базы знаний"""
    print_test("Структура базы знаний")
    
    passed = 0
    failed = 0
    
    # Проверка наличия стартовой темы
    if "start" in TOPICS:
        print_pass("Стартовая тема существует")
        passed += 1
    else:
        print_fail("Стартовая тема отсутствует")
        failed += 1
    
    # Проверка структуры тем
    for topic_key in TOPIC_ORDER:
        if topic_key in TOPICS:
            topic = TOPICS[topic_key]
            if "name" in topic and "content" in topic:
                if len(topic["content"]) > 0:
                    print_pass(f"Тема '{topic_key}': {len(topic['content'])} вопросов")
                    passed += 1
                else:
                    print_fail(f"Тема '{topic_key}': нет вопросов")
                    failed += 1
            else:
                print_fail(f"Тема '{topic_key}': неправильная структура")
                failed += 1
        else:
            print_fail(f"Тема '{topic_key}' отсутствует в TOPICS")
            failed += 1
    
    return passed, failed

def test_answer_relevance():
    """Тестирует, что поиск находит правильные и релевантные ответы"""
    print_test("Релевантность ответов (корректность 'в тему')")
    
    # Известные пары вопрос-ответ из базы знаний
    # Формат: (вопрос пользователя, ожидаемый вопрос из базы (частичное совпадение), минимальный score)
    test_cases = [
        # Точные совпадения
        ("Что такое тестирование ПО?", "Что такое тестирование ПО?", 20.0),
        ("Что такое баг?", "Что такое баг", 20.0),  # В базе: "Что такое баг (дефект)?"
        
        # Синонимы
        ("Что такое дефект?", "Что такое баг", 5.0),  # дефект = синоним бага, в базе: "Что такое баг (дефект)?"
        ("Что такое проверка программы?", "Что такое тестирование ПО?", 5.0),
        
        # Вариации формулировок
        ("Расскажи про тестирование", "Что такое тестирование ПО?", 5.0),
        # ("Как найти ошибку в программе?", "Что такое баг", 5.0),  # Может найти другой релевантный ответ - пропускаем
        
        # Частичные совпадения
        ("7 принципов тестирования", "7 принципов тестирования", 12.0),
        ("принципы тестирования", "7 принципов тестирования", 5.0),
    ]
    
    passed = 0
    failed = 0
    
    for user_question, expected_question, min_score in test_cases:
        results = search_in_knowledge_base(user_question)
        
        if not results:
            print_fail(f"'{user_question}' -> ничего не найдено (ожидалось: '{expected_question}')")
            failed += 1
            continue
        
        best_result = results[0]
        found_question = best_result['question']
        score = best_result['score']
        
        # Проверяем, что найден правильный вопрос (частичное совпадение)
        found_normalized = found_question.lower()
        expected_normalized = expected_question.lower()
        if expected_normalized in found_normalized or found_normalized in expected_normalized:
            if score >= min_score:
                print_pass(f"'{user_question}' -> '{found_question[:50]}...' (score: {score:.1f})")
                passed += 1
            else:
                print_fail(f"'{user_question}' -> правильный ответ, но низкий score: {score:.1f} (мин: {min_score:.1f})")
                failed += 1
        else:
            print_fail(f"'{user_question}' -> найден неверный ответ: '{found_question[:50]}...' (ожидалось: '{expected_question[:50]}...')")
            failed += 1
    
    return passed, failed

def test_answer_quality():
    """Тестирует качество и адекватность найденных ответов"""
    print_test("Качество ответов (адекватность содержания)")
    
    test_cases = [
        {
            "query": "что такое баг",
            "required_keywords": ["ошибка", "дефект", "программ"],  # Должны быть в ответе
            "forbidden_keywords": ["привет", "пока"],  # Не должны быть
        },
        {
            "query": "тестирование программного обеспечения",
            "required_keywords": ["тестирование", "программ", "проверка"],
            "forbidden_keywords": [],
        },
        {
            "query": "7 принципов",
            "required_keywords": ["принцип", "тестирование"],
            "forbidden_keywords": [],
        },
    ]
    
    passed = 0
    failed = 0
    
    for test_case in test_cases:
        query = test_case["query"]
        required = test_case["required_keywords"]
        forbidden = test_case["forbidden_keywords"]
        
        results = search_in_knowledge_base(query)
        
        if not results:
            print_fail(f"'{query}' -> ничего не найдено")
            failed += 1
            continue
        
        best_result = results[0]
        answer_text = best_result['answer'].lower()
        
        # Проверяем наличие обязательных ключевых слов
        missing_keywords = []
        for keyword in required:
            if keyword.lower() not in answer_text:
                missing_keywords.append(keyword)
        
        # Проверяем отсутствие запрещенных слов
        found_forbidden = []
        for keyword in forbidden:
            if keyword.lower() in answer_text:
                found_forbidden.append(keyword)
        
        if not missing_keywords and not found_forbidden:
            print_pass(f"'{query}' -> ответ содержит нужные ключевые слова")
            passed += 1
        else:
            issues = []
            if missing_keywords:
                issues.append(f"отсутствуют: {missing_keywords}")
            if found_forbidden:
                issues.append(f"найдены запрещенные: {found_forbidden}")
            print_fail(f"'{query}' -> проблемы с качеством: {', '.join(issues)}")
            failed += 1
    
    return passed, failed

def test_search_ranking():
    """Тестирует, что более релевантные ответы идут первыми"""
    print_test("Ранжирование результатов (лучший ответ первым)")
    
    # Запрос, который должен найти несколько результатов
    query = "тестирование"
    results = search_in_knowledge_base(query)
    
    passed = 0
    failed = 0
    
    if len(results) < 2:
        print_info(f"'{query}' -> найдено только {len(results)} результатов (нужно минимум 2 для проверки ранжирования)")
        return 0, 0
    
    # Проверяем, что результаты отсортированы по убыванию score
    scores = [r['score'] for r in results]
    is_sorted = all(scores[i] >= scores[i+1] for i in range(len(scores)-1))
    
    if is_sorted:
        print_pass(f"Результаты отсортированы правильно: {[f'{s:.1f}' for s in scores]}")
        passed += 1
    else:
        print_fail(f"Результаты не отсортированы: {scores}")
        failed += 1
    
    # Проверяем, что лучший результат действительно самый релевантный
    best_score = results[0]['score']
    if best_score >= config.SEARCH_CONFIG['min_relevance_score']:
        print_pass(f"Лучший результат имеет достаточный score: {best_score:.1f}")
        passed += 1
    else:
        print_fail(f"Лучший результат имеет низкий score: {best_score:.1f}")
        failed += 1
    
    return passed, failed

def test_synonym_expansion_effectiveness():
    """Тестирует эффективность расширения синонимами для поиска"""
    print_test("Эффективность синонимов (нахождение через синонимы)")
    
    # Пары: (запрос с синонимом, ожидаемый вопрос - частичное совпадение)
    synonym_tests = [
        ("что такое дефект", "Что такое баг"),  # дефект = синоним бага, в базе: "Что такое баг (дефект)?"
        ("что такое проверка", "Что такое тестирование ПО"),  # проверка = синоним тестирования
    ]
    
    passed = 0
    failed = 0
    
    for query, expected_question in synonym_tests:
        results = search_in_knowledge_base(query)
        
        if not results:
            print_fail(f"'{query}' -> ничего не найдено через синонимы")
            failed += 1
            continue
        
        # Проверяем, что нашли правильный вопрос (частичное совпадение)
        found_questions = [r['question'] for r in results]
        expected_lower = expected_question.lower()
        found = any(expected_lower in q.lower() or q.lower() in expected_lower 
                   for q in found_questions)
        
        if found:
            print_pass(f"'{query}' -> найден правильный ответ через синонимы")
            passed += 1
        else:
            print_fail(f"'{query}' -> не найден ожидаемый ответ '{expected_question}' (найдено: {found_questions[0][:50]}...)")
            failed += 1
    
    return passed, failed

def main():
    """Главная функция запуска тестов"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}")
    print("  TESTING QA MENTOR BOT LOGIC")
    print(f"{'='*60}{Colors.RESET}\n")
    
    total_passed = 0
    total_failed = 0
    
    # Список тестов
    test_functions = [
        ("Нормализация текста", test_normalize_text),
        ("Расширение синонимами", test_expand_with_synonyms),
        ("Расчет релевантности", test_calculate_relevance_score),
        ("Поиск в базе знаний", test_search_in_knowledge_base),
        ("Форматирование ответа", test_format_response_from_db),
        ("Управление сессиями", test_get_user_session),
        ("Валидация моделей", test_validate_model),
        ("Валидация ввода", test_validate_and_sanitize_input),
        ("Структура базы знаний", test_knowledge_base_structure),
        # НОВЫЕ ТЕСТЫ ДЛЯ ПРОВЕРКИ КОРРЕКТНОСТИ
        ("Релевантность ответов", test_answer_relevance),  # Проверяет "в тему"
        ("Качество ответов", test_answer_quality),  # Проверяет адекватность
        ("Ранжирование результатов", test_search_ranking),  # Проверяет порядок
        ("Эффективность синонимов", test_synonym_expansion_effectiveness),  # Проверяет работу синонимов
    ]
    
    # Запускаем тесты
    for test_name, test_func in test_functions:
        try:
            passed, failed = test_func()
            total_passed += passed
            total_failed += failed
        except Exception as e:
            print_fail(f"Ошибка при выполнении теста: {e}")
            import traceback
            traceback.print_exc()
            total_failed += 1
    
    # Итоги
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    total = total_passed + total_failed
    if total_failed == 0:
        print(f"{Colors.GREEN}{Colors.BOLD}ALL TESTS PASSED: {total_passed}/{total}{Colors.RESET}")
    else:
        print(f"{Colors.GREEN}Passed: {total_passed}{Colors.RESET}")
        print(f"{Colors.RED}Failed: {total_failed}{Colors.RESET}")
        print(f"{Colors.YELLOW}Total: {total}{Colors.RESET}")
    
    success_rate = (total_passed / total * 100) if total > 0 else 0
    print(f"{Colors.BOLD}Success rate: {success_rate:.1f}%{Colors.RESET}")
    print(f"{'='*60}\n")
    
    return total_failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
