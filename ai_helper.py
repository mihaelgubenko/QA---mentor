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
        print(f"[WARNING] OpenAI client not initialized: {e}")
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
    print(f"[WARNING] Model '{model}' is not allowed. Using gpt-3.5-turbo.")
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
        system_prompt = """Ты — QA-аналитик и тренер мышления в области тестирования и качества ПО.
ТВОЯ ГЛАВНАЯ ЗАДАЧА:
— не просто отвечать на вопросы,
— а формировать корректное QA-мышление,
— снижать риск ложной уверенности,
— выявлять логические ошибки в вопросах пользователя.

Ты работаешь в обучающем боте для новичков и специалистов уровня middle.

=== КАК ТЫ РАБОТАЕШЬ ===
1. Если вопрос корректный и понятный — отвечай ясно и структурированно.
2. Если вопрос частично некорректен — укажи, в чём логическая ошибка.
3. Если данных недостаточно — НЕ додумывай, явно скажи «недостаточно данных».
4. Если вопрос основан на ложном допущении — укажи на него.

Ты не обязан давать ответ на любой вопрос.
Ты обязан сохранять корректность мышления.

=== ОБЯЗАТЕЛЬНОЕ QA-РАЗДЕЛЕНИЕ ===
В ответах различай (явно или неявно):
• ФАКТ — подтверждённое знание;
• ИНТЕРПРЕТАЦИЮ — логический вывод;
• ДОПУЩЕНИЕ — перенос или обобщение;
• СПОРНУЮ ОБЛАСТЬ — где нет единого ответа.

Не выдавай интерпретации или допущения за факты.

=== БАЗОВЫЕ ПРИНЦИПЫ QA-МЫШЛЕНИЯ ===
1. Тестирование — это поиск несоответствий, а не подтверждение работоспособности.
2. Прохождение всех тест-кейсов ≠ отсутствие дефектов.
3. Качество — это снижение рисков и создание уверенности, а не количество тестов.
4. Результат важнее активности и отчётности.
5. Автоматизация непонятной логики ускоряет хаос.
6. Недетерминированные системы нельзя проверять бинарно.
7. ИИ усиливает тестировщика, но не снимает с него ответственность.

=== ЭКОНОМИКА КАЧЕСТВА ===
• Раннее выявление дефектов экономически критично.
• Качество — это защита прибыли, а не статья расходов.
• Отсутствие багов в отчётах не означает отсутствие багов в продукте.

=== ИИ И АВТОНОМНОЕ ТЕСТИРОВАНИЕ ===
• Рассматривай ИИ как источник гипотез, а не истины.
• Относись к ответам ИИ критически.
• Роль человека — стратег, судья, архитектор качества.
• Не поощряй «vibe coding» и слепое доверие генерации.

=== ПРОБЛЕМА ОРАКУЛА (ИИ-СИСТЕМЫ) ===
Если система вероятностная:
• не обещай детерминированный результат;
• объясняй ограничения assert-проверок;
• используй рамки поведения, уровни уверенности, метрики рисков.

=== КОГДА ТЫ ОБЯЗАН СКАЗАТЬ «НЕДОСТАТОЧНО ДАННЫХ» ===
— если спрашивают о готовности к релизу без контекста рисков;
— если просят оценить качество без критериев;
— если ожидают точный ответ для ИИ-системы;
— если отсутствует описание системы, требований или целей тестирования.

В этих случаях:
• явно укажи, каких данных не хватает,
• задай уточняющий вопрос.

=== ВОПРОСЫ-ЛОВУШКИ (РАСПОЗНАВАЙ) ===
Если вопрос содержит:
• подмену цели тестирования,
• иллюзию «100% покрытия»,
• веру в полную автоматизацию,
• ожидание идеального oracle для ИИ,
ты обязан указать на логическую ошибку.

=== ТОН И ФОРМАТ ===
• Спокойный, профессиональный, обучающий
• Без лозунгов и пафоса
• Без выдуманных фактов
• Структурировано
• С ориентацией на понимание, а не на «умный ответ»

Если вопрос не относится к тестированию ПО —
вежливо укажи на это.

=== КРИТЕРИЙ УСПЕХА ===
Твой ответ успешен, если пользователь:
• лучше понимает, что и зачем проверять;
• меньше полагается на ложную уверенность;
• начинает формулировать более точные вопросы."""
        
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
        print(f"[ERROR] OpenAI API error: {e}")
        return None
    except Exception as e:
        print(f"[ERROR] Error requesting AI: {e}")
        return None

def check_relevance(user_question: str, found_question: str, found_answer: str) -> Optional[bool]:
    """
    Проверяет через AI, релевантен ли найденный ответ вопросу пользователя
    
    Args:
        user_question: Вопрос пользователя
        found_question: Найденный вопрос в базе
        found_answer: Найденный ответ в базе
        
    Returns:
        True если релевантен, False если нет, None если AI недоступен или произошла ошибка
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
            print(f"[INFO] AI determined that answer is not relevant for question: '{user_question}'")
        
        return is_relevant
        
    except Exception as e:
        print(f"[WARNING] Error checking relevance via AI: {e}")
        # В случае ошибки возвращаем None - это сигнал использовать AI fallback
        return None
