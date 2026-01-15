"""
Модуль для работы с внешним AI (OpenAI) как fallback
"""
import config
import openai
from openai import APIError
from typing import Optional

# Инициализация OpenAI клиента
client = None
if config.AI_CONFIG['enabled']:
    try:
        client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
    except Exception as e:
        print(f"[WARNING] OpenAI не инициализирован: {e}")
        client = None

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
        
        # Получаем модель из конфига
        model = config.OPENAI_MODEL.strip() if config.OPENAI_MODEL else 'gpt-3.5-turbo'
        
        # Список известных поддерживаемых моделей OpenAI
        known_models = [
            'gpt-3.5-turbo', 'gpt-3.5-turbo-16k',
            'gpt-4', 'gpt-4-turbo', 'gpt-4-turbo-preview',
            'gpt-4o', 'gpt-4o-2024-05-13', 'gpt-4o-2024-08-06',
            'gpt-4o-mini', 'gpt-4o-mini-2024-07-18',
            'o1', 'o1-mini', 'o1-preview', 'o1-2024-12-17',
            'gpt-5-mini', 'gpt-5 mini'  # На случай если такая модель появится
        ]
        
        # Если модель не указана, используем gpt-3.5-turbo
        if not model:
            model = 'gpt-3.5-turbo'
            print(f"[INFO] Модель не указана, используется по умолчанию: {model}")
        # Если модель не в списке известных, все равно пробуем использовать её
        # (API вернет ошибку если модель не существует)
        elif model.lower() not in [m.lower() for m in known_models]:
            print(f"[INFO] Используется модель '{model}' (не в списке известных, но попробуем)")
        
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
