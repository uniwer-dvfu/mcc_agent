import os
import json
import re
import logging
from gigachat import GigaChat

logger = logging.getLogger(__name__)

# Загрузка переменных окружения
GIGACHAT_CREDENTIALS = os.getenv('GIGACHAT_CREDENTIALS', '')
GIGACHAT_SCOPE = os.getenv('GIGACHAT_SCOPE', 'GIGACHAT_API_PERS')
GIGACHAT_VERIFY_SSL = os.getenv('GIGACHAT_VERIFY_SSL_CERTS', 'True').lower() == 'true'


def get_gigachat_client():
    """
    Инициализирует и возвращает клиент GigaChat.
    Если credentials не настроены или ошибка — возвращает None.
    """
    if not GIGACHAT_CREDENTIALS or GIGACHAT_CREDENTIALS == 'ваш_ключ_авторизации':
        logger.info("ℹ️ GigaChat не настроен (нет credentials). Работаем без ИИ.")
        return None
    try:
        client = GigaChat(
            credentials=GIGACHAT_CREDENTIALS,
            scope=GIGACHAT_SCOPE,
            verify_ssl_certs=GIGACHAT_VERIFY_SSL
        )
        logger.info("✅ GigaChat клиент успешно создан")
        return client
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации GigaChat: {e}")
        return None


def enhance_with_gigachat(org_name, rubrics, services, mcc_candidates, current_mcc_code, current_mcc_name):
    """
    Отправляет запрос к GigaChat для уточнения MCC-кода и получения объяснения.
    Возвращает словарь с полями:
        - mcc_code (str)
        - mcc_name (str)
        - is_correct (bool)
        - explanation (str)
        - products (list)
    Если GigaChat недоступен или ошибка — возвращает None.
    """
    client = get_gigachat_client()
    if not client:
        return None

    # Формируем данные для промта без лишних переносов строк
    rubrics_text = ', '.join(rubrics[:5]) if rubrics else 'не указаны'
    services_text = ', '.join(services[:5]) if services else 'не указаны'

    # Строим список кандидатов в виде строки
    candidates_text = '\n'.join([
        f"- {c['code']}: {c['name']} (совпадений: {c.get('match_count', 0)})"
        for c in mcc_candidates[:5]
    ])

    # Формируем промт с экранированными фигурными скобками ({{ и }})
    prompt = f"""
Ты — ИИ-агент по определению MCC-кодов для банковского эквайринга.

Данные о торговой точке:
- Название: {org_name}
- Рубрики: {rubrics_text}
- Услуги: {services_text}

Кандидаты MCC (отсортированы по релевантности):
{candidates_text}

Текущий выбор алгоритма: {current_mcc_code} - {current_mcc_name}

Задание:
1. Подтверди или опровергни правильность выбранного MCC-кода.
2. Если код неверен, предложи правильный из списка кандидатов или свой вариант.
3. Дай краткое объяснение (2-3 предложения).
4. Предложи 2-3 продукта для продажи (например, POS-кредитование, СберЧаевые, эквайринг).

Ответ строго в формате JSON без дополнительного текста.
Используй только обычные двойные кавычки (") для ключей и строк.
Не используй символы « » ” ”.

Пример правильного ответа:
{{
  "mcc_code": "5812",
  "mcc_name": "Рестораны быстрого питания",
  "is_correct": true,
  "explanation": "Объяснение решения",
  "products": ["POS-кредитование", "СберЧаевые"]
}}
"""
    try:
        response = client.chat(prompt)
        content = response.choices[0].message.content
        logger.info(f"📩 Получен ответ от GigaChat (первые 300 символов): {content[:300]}...")

        # Очищаем ответ от лишних символов
        cleaned_content = clean_gigachat_response(content)
        logger.info(f"🧹 Очищенный ответ: {cleaned_content[:300]}...")

        # Пробуем найти JSON в ответе
        json_match = re.search(r'\{.*\}', cleaned_content, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            try:
                result = json.loads(json_str)
                logger.info(f"✅ GigaChat успешно ответил: {result.get('mcc_code')} - {result.get('mcc_name')}")
                return result
            except json.JSONDecodeError as e:
                logger.error(f"❌ Ошибка парсинга JSON от GigaChat: {e}")
                logger.error(f"Строка JSON: {json_str}")
                # Пробуем восстановить JSON
                repaired = repair_json(json_str)
                if repaired:
                    try:
                        result = json.loads(repaired)
                        logger.info(f"✅ JSON восстановлен: {result.get('mcc_code')}")
                        return result
                    except:
                        pass
                return None
        else:
            logger.warning("⚠️ GigaChat не вернул JSON в ответе")
            logger.warning(f"Ответ: {content[:200]}")
            return None

    except Exception as e:
        logger.error(f"❌ Ошибка при запросе к GigaChat: {e}")
        return None


def clean_gigachat_response(content):
    """
    Очищает ответ от GigaChat от невалидных символов
    """
    # Заменяем « » ” “ на обычные кавычки
    content = content.replace('«', '"')
    content = content.replace('»', '"')
    content = content.replace('”', '"')
    content = content.replace('“', '"')

    # Удаляем управляющие символы
    import re
    content = re.sub(r'[\x00-\x1f\x7f]', '', content)

    return content


def repair_json(json_str):
    """
    Пытается восстановить повреждённый JSON
    """
    import re

    # Заменяем неправильные кавычки в полях
    json_str = re.sub(r'»,«', '", "', json_str)
    json_str = re.sub(r'»,', '",', json_str)
    json_str = re.sub(r'«', '"', json_str)
    json_str = re.sub(r'»', '"', json_str)

    # Удаляем лишние запятые перед закрывающими скобками
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)

    # Проверяем, не обрезан ли JSON
    if json_str.count('{') > json_str.count('}'):
        json_str += '}'
    if json_str.count('[') > json_str.count(']'):
        json_str += ']'

    return json_str


def clean_gigachat_response(content):
    """
    Очищает ответ от GigaChat от невалидных символов
    """
    # Заменяем « и » на обычные кавычки (но это не всегда правильно для JSON)
    # В JSON должны быть только "
    content = content.replace('«', '"')
    content = content.replace('»', '"')
    content = content.replace('”', '"')
    content = content.replace('“', '"')

    # Удаляем управляющие символы
    import re
    content = re.sub(r'[\x00-\x1f\x7f]', '', content)

    return content


def repair_json(json_str):
    """
    Пытается восстановить повреждённый JSON
    """
    import re

    # Заменяем неправильные кавычки в полях
    # Например: "mcc_code": "5812»,«" -> "mcc_code": "5812"
    json_str = re.sub(r'»,«', '", "', json_str)
    json_str = re.sub(r'»,', '",', json_str)
    json_str = re.sub(r'«', '"', json_str)
    json_str = re.sub(r'»', '"', json_str)

    # Удаляем лишние запятые перед закрывающими скобками
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)

    # Проверяем, не обрезан ли JSON
    if json_str.count('{') > json_str.count('}'):
        json_str += '}'
    if json_str.count('[') > json_str.count(']'):
        json_str += ']'

    return json_str

def generate_sales_text_with_gigachat(org_name, mcc_code, mcc_name, rubrics, services):
    """
    Генерирует персонализированный текст рекомендаций по продажам.
    Возвращает строку или None.
    """
    client = get_gigachat_client()
    if not client:
        return None

    rubrics_text = ', '.join(rubrics[:5]) if rubrics else 'не указаны'
    services_text = ', '.join(services[:5]) if services else 'не указаны'

    prompt = f"""
Ты — консультант по продажам эквайринговых продуктов.

Торговая точка:
- Название: {org_name}
- MCC-код: {mcc_code} - {mcc_name}
- Рубрики: {rubrics_text}
- Услуги: {services_text}

Напиши краткую (3-5 предложений) рекомендацию для менеджера по продажам:
- Какие продукты (эквайринг, POS-кредитование, СберЧаевые, другие сервисы) подходят этому клиенту
- Ключевые аргументы для презентации
- Возможные возражения и как их обработать

Ответ должен быть в виде связного текста.
"""
    try:
        response = client.chat(prompt)
        text = response.choices[0].message.content.strip()
        return text
    except Exception as e:
        logger.error(f"❌ Ошибка генерации рекомендаций через GigaChat: {e}")
        return None


def enhance_with_gigachat_with_retry(org_name, rubrics, services, mcc_candidates, current_mcc_code, current_mcc_name, max_retries=2):
    """Пытается получить ответ от GigaChat с повторными попытками"""
    for attempt in range(max_retries):
        result = enhance_with_gigachat(
            org_name, rubrics, services, mcc_candidates, current_mcc_code, current_mcc_name
        )
        if result:
            return result
        logger.warning(f"⚠️ Попытка {attempt + 1} не удалась, повторяем...")
        time.sleep(1)
    return None

