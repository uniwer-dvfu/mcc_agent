import os
import json
import re
import time
import logging
from gigachat import GigaChat

logger = logging.getLogger(__name__)

# Загрузка переменных окружения
GIGACHAT_CREDENTIALS = os.getenv('GIGACHAT_CREDENTIALS', '')
GIGACHAT_SCOPE = os.getenv('GIGACHAT_SCOPE', 'GIGACHAT_API_PERS')
GIGACHAT_VERIFY_SSL = os.getenv('GIGACHAT_VERIFY_SSL_CERTS', 'True').lower() == 'true'
# Новые версии SDK требуют явно указать модель (GigaChat-2, GigaChat-2-Pro, GigaChat-2-Max, GigaChat-3-Ultra)
GIGACHAT_MODEL = os.getenv('GIGACHAT_MODEL', 'GigaChat-2')


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
            verify_ssl_certs=GIGACHAT_VERIFY_SSL,
            model=GIGACHAT_MODEL
        )
        logger.info(f"✅ GigaChat клиент успешно создан (модель: {GIGACHAT_MODEL})")
        return client
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации GigaChat: {e}")
        return None


def enhance_with_gigachat(org_name, rubrics, services, mcc_candidates, current_mcc_code, current_mcc_name, extra_context='', allowed_products=None):
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

    extra_block = f"\nДополнительные данные из других источников:\n{extra_context}\n" if extra_context else ''

    # Разрешённые продукты задаёт код проекта (списки МСС), GigaChat их не расширяет
    if allowed_products:
        products_rule = ('4. Предложи 2-3 продукта ТОЛЬКО из списка разрешённых для этой категории: '
                         + ', '.join(allowed_products)
                         + '. Продукты вне списка, в том числе POS-кредитование и рассрочку, предлагать запрещено.')
        example_products = ', '.join(f'"{p}"' for p in allowed_products[:2])
    else:
        products_rule = '4. Предложи 2-3 продукта для продажи (например, эквайринг, СберЧаевые).'
        example_products = '"Эквайринг"'

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
{extra_block}
Кандидаты MCC (отсортированы по релевантности):
{candidates_text}

Текущий выбор алгоритма: {current_mcc_code} - {current_mcc_name}

Задание:
1. Подтверди или опровергни правильность выбранного MCC-кода.
2. Если код неверен, предложи правильный из списка кандидатов или свой вариант.
3. Дай краткое объяснение (2-3 предложения).
{products_rule}

Ответ строго в формате JSON без дополнительного текста.
Используй только обычные двойные кавычки (") для ключей и строк.
Не используй символы « » ” ”.

Пример правильного ответа:
{{
  "mcc_code": "5812",
  "mcc_name": "Рестораны быстрого питания",
  "is_correct": true,
  "explanation": "Объяснение решения",
  "products": [{example_products}]
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


def choose_partners_with_gigachat(base, shortlist, count=3):
    """
    Просит GigaChat выбрать count наиболее перспективных партнёров из списка и обосновать выбор.
    base — исходная точка {name, mcc_code, mcc_name}; shortlist — кандидаты из partners.make_shortlist.
    Возвращает список [{'id': номер из списка (с 1), 'reason': текст}] или None.
    """
    client = get_gigachat_client()
    if not client or not shortlist:
        return None

    lines = []
    for number, c in enumerate(shortlist, start=1):
        facts = [f"{c['distance_m']} м от точки", f"МСС {c['mcc_code']} ({c['mcc_name']})",
                 'продукты: ' + ', '.join(c['products'])]
        if c.get('reviews'):
            facts.append(f"отзывов: {c['reviews']}" + (f", рейтинг {c['rating']}" if c.get('rating') else ''))
        if c.get('schedule'):
            facts.append('график: ' + c['schedule'])
        if c.get('brand'):
            facts.append('сеть: ' + c['brand'])
        facts.append(f"расчётная оценка {round(c['score'] * 100)} из 100")
        lines.append(f"{number}. {c['name']} — " + '; '.join(facts))
    candidates_text = '\n'.join(lines)

    prompt = f"""
Ты — аналитик банка по привлечению торговых точек на эквайринг.

Менеджер находится у торговой точки «{base.get('name', '')}» (МСС {base.get('mcc_code', '')}, {base.get('mcc_name', '')}).
В радиусе 500 м найдены организации-кандидаты:
{candidates_text}

Расчётная оценка учитывает потребность категории в приёме карт, ожидаемый оборот, применимость продуктов банка, близость, надёжность определения МСС и самостоятельность решения (филиалы сетей оцениваются ниже).

Задание: выбери {count} наиболее перспективных партнёров для подключения эквайринга и продажи продуктов.
Для каждого напиши обоснование в 2-3 предложения: почему именно он и какие продукты предложить.
Опирайся только на данные выше, ничего не выдумывай. Не упоминай расчётную оценку и номера критериев.
Предлагай только продукты из поля «продукты» выбранного кандидата. Если POS-кредитования нет в его списке продуктов, не упоминай ни POS-кредитование, ни рассрочку, ни кредит.

Ответ строго в формате JSON без дополнительного текста. Только обычные двойные кавычки.
Поле id — номер кандидата из списка.

{{
  "partners": [
    {{"id": 1, "reason": "Обоснование"}},
    {{"id": 2, "reason": "Обоснование"}},
    {{"id": 3, "reason": "Обоснование"}}
  ]
}}
"""
    try:
        response = client.chat(prompt)
        content = clean_gigachat_response(response.choices[0].message.content)
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if not match:
            logger.warning('⚠️ GigaChat не вернул JSON при выборе партнёров')
            return None
        try:
            data = json.loads(match.group())
        except json.JSONDecodeError:
            data = json.loads(repair_json(match.group()))
        partners = data.get('partners')
        logger.info(f'✅ GigaChat выбрал партнёров: {len(partners) if isinstance(partners, list) else 0}')
        return partners if isinstance(partners, list) else None
    except Exception as e:
        logger.error(f'❌ Ошибка выбора партнёров через GigaChat: {e}')
        return None


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

# def generate_sales_text_with_gigachat(org_name, mcc_code, mcc_name, rubrics, services):
#     """
#     Генерирует персонализированный текст рекомендаций по продажам.
#     Возвращает строку или None.
#     """
#     client = get_gigachat_client()
#     if not client:
#         return None
#
#     rubrics_text = ', '.join(rubrics[:5]) if rubrics else 'не указаны'
#     services_text = ', '.join(services[:5]) if services else 'не указаны'
#
#     prompt = f"""
# Ты — консультант по продажам эквайринговых продуктов.
#
# Торговая точка:
# - Название: {org_name}
# - MCC-код: {mcc_code} - {mcc_name}
# - Рубрики: {rubrics_text}
# - Услуги: {services_text}
#
# Напиши краткую (3-5 предложений) рекомендацию для менеджера по продажам:
# - Какие продукты (эквайринг, POS-кредитование, СберЧаевые, другие сервисы) подходят этому клиенту
# - Ключевые аргументы для презентации
# - Возможные возражения и как их обработать
#
# Ответ должен быть в виде связного текста.
# """
#     try:
#         response = client.chat(prompt)
#         text = response.choices[0].message.content.strip()
#         return text
#     except Exception as e:
#         logger.error(f"❌ Ошибка генерации рекомендаций через GigaChat: {e}")
#         return None


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