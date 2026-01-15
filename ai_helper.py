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
        
        # Проверяем и исправляем имя модели
        model = config.OPENAI_MODEL
        # Если модель не указана или неверная, используем gpt-3.5-turbo
        if not model or model not in ['gpt-3.5-turbo', 'gpt-4', 'gpt-4-turbo', 'gpt-4o', 'gpt-4o-mini']:
            model = 'gpt-3.5-turbo'
            print(f"[WARNING] Используется модель по умолчанию: {model}")
        
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
