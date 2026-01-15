"""
Модуль для работы с внешним AI (OpenAI) как fallback
"""
import config
import openai
from openai import APIError
from typing import Optional

# Список разрешённых моделей:
# - одна линейка 3.5
# - все актуальные модели семейства gpt-4*
ALLOWED_MODELS = [
    'gpt-3.5-turbo',
    'gpt-4',
    'gpt-4-turbo',
    'gpt-4-turbo-preview',
    'gpt-4o',
    'gpt-4o-2024-05-13',
    'gpt-4o-2024-08-06',
    'gpt-4o-mini',
    'gpt-4o-mini-2024-07-18',
]

# Инициализация OpenAI клиента
client = None
if config.AI_CONFIG['enabled']:
    try:
        client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
    except Exception as e:
        print(f"[WARNING] OpenAI не инициализирован: {e}")
        client = None

def validate_model(model_name: str) -> str:
    """Валидирует и нормализует имя модели"""
    if not model_name:
        return 'gpt-3.5-turbo'
    
    model = model_name.strip()
    model_lower = model.lower()
    
    # Находим соответствующую модель из списка разрешенных (с учетом регистра)
    for allowed_model in ALLOWED_MODELS:
        if model_lower == allowed_model.lower():
            # Возвращаем оригинальное название из списка (нормализованное)
            return allowed_model
    
    # Если модель не найдена, используем fallback
    print(f"[WARNING] Модель '{model}' не разрешена. Используется gpt-3.5-turbo.")
    return 'gpt-3.5-turbo'

def ask_ai(question: str) -> Optional[str]:
    """
    Запрашивает ответ у внешнего AI
    
    Args:
        question: Вопрос пользователя
        
    Returns:
        Ответ от AI или None в случае ошибки
    """
    if not config.AI_CONFIG['enabled'] or not client:
        return None
    
    try:
        system_prompt = """Ты помощник по тестированию программного обеспечения (QA).
Твоя задача - отвечать на вопросы о тестировании ПО простым и понятным языком.
Отвечай кратко, структурированно, с примерами когда это уместно.
Если вопрос не связан с тестированием, вежливо укажи на это."""
        
        # Получаем и валидируем модель из конфига
        model = validate_model(config.OPENAI_MODEL)
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ],
            max_tokens=config.AI_CONFIG['max_tokens'],
            temperature=config.AI_CONFIG['temperature']
        )
        
        answer = response.choices[0].message.content.strip()
        return answer
        
    except APIError as e:
        print(f"[ERROR] OpenAI API ошибка: {e}")
        return None
    except Exception as e:
        print(f"[ERROR] Ошибка при запросе к AI: {e}")
        return None

def check_relevance(user_question: str, found_question: str, found_answer: str) -> bool:
    """
    Проверяет через AI, релевантен ли найденный ответ вопросу пользователя
    
    Args:
        user_question: Вопрос пользователя
        found_question: Найденный вопрос в базе
        found_answer: Найденный ответ в базе
        
    Returns:
        True если релевантен, False если нет
    """
    if not config.AI_CONFIG['enabled'] or not client:
        # Если AI не доступен, возвращаем None - это сигнал использовать AI fallback
        return None
    
    if not config.SEARCH_CONFIG.get('use_ai_relevance_check', False):
        return True  # Если проверка отключена, считаем релевантным
    
    try:
        # Получаем и валидируем модель
        model = validate_model(config.OPENAI_MODEL)
        
        prompt = f"""Ты эксперт по тестированию ПО. Оцени, релевантен ли найденный ответ вопросу пользователя.

Вопрос пользователя: "{user_question}"

Найденный вопрос в базе знаний: "{found_question}"

Ответь ТОЛЬКО одним словом: "ДА" если ответ релевантен и отвечает на вопрос пользователя, "НЕТ" если не релевантен или не отвечает на вопрос."""
        
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
            temperature=0.1
        )
        
        answer = response.choices[0].message.content.strip().upper()
        is_relevant = "ДА" in answer or "YES" in answer or "TRUE" in answer
        
        if not is_relevant:
            print(f"[INFO] AI определил, что ответ не релевантен для вопроса: '{user_question}'")
        
        return is_relevant
        
    except Exception as e:
        print(f"[WARNING] Ошибка при проверке релевантности через AI: {e}")
        # В случае ошибки возвращаем None - это сигнал использовать AI fallback
        return None
