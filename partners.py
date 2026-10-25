"""
Поиск и отбор перспективных партнёров рядом с торговой точкой.

Схема:
  1. Запрос в 2ГИС: организации в радиусе RADIUS_M метров от точки.
  2. Для каждой организации определяется МСС (быстрый алгоритм без GigaChat) и считается оценка
     по шести критериям — взвешенная сумма оценок от 0 до 1.
  3. Лучшие кандидаты (с учётом разнообразия категорий) передаются в GigaChat, который выбирает три
     и обосновывает выбор. Если GigaChat недоступен, берутся три лучших по расчёту.
Баллы пользователю не показываются: они нужны для отбора и как контекст для GigaChat.
"""
import logging
import math
import os
import re

from products import applicable_products, clean_product_text
from sources import distance_m, format_schedule

logger = logging.getLogger(__name__)

RADIUS_M = int(os.getenv('PARTNERS_RADIUS_M', '500'))
SHORTLIST_SIZE = 8       # сколько кандидатов передаётся в GigaChat
RESULT_SIZE = 3          # сколько партнёров выводится
DIVERSITY_PENALTY = 0.85  # множитель оценки за каждого уже выбранного кандидата с тем же МСС

# Стартовые веса критериев (экспертные), в сумме 1.0
WEIGHTS = {
    'card_need': 0.25,   # потребность в приёме карт по категории МСС
    'turnover': 0.25,    # ожидаемый оборот: отзывы и режим работы
    'products': 0.20,    # применимость продуктов банка
    'proximity': 0.15,   # близость к исходной точке
    'reliability': 0.10, # надёжность определения МСС
    'independence': 0.05 # самостоятельность решения (не филиал сети)
}

# Экспертная шкала потребности в приёме карт по диапазонам МСС (выбирается самый узкий диапазон)
CARD_NEED_RANGES = [
    (5411, 5499, 1.0),  # продукты питания
    (5811, 5814, 1.0),  # общепит
    (5912, 5912, 0.9),  # аптеки
    (5541, 5542, 0.9),  # АЗС
    (5200, 5999, 0.9),  # розничная торговля
    (5000, 5199, 0.4),  # оптовая торговля
    (7011, 7033, 0.8),  # гостиницы
    (7210, 7299, 0.8),  # бытовые услуги, красота
    (7300, 7399, 0.5),  # услуги для бизнеса
    (7500, 7549, 0.8),  # автосервис, парковки
    (7800, 7999, 0.7),  # развлечения, спорт
    (8000, 8099, 0.8),  # медицина
    (8200, 8299, 0.6),  # образование
    (8300, 8999, 0.5),  # прочие услуги
    (1500, 1799, 0.4),  # подрядчики
    (4000, 4799, 0.7),  # транспорт
    (4800, 4999, 0.4),  # связь и коммунальные услуги
    (6000, 6999, 0.2),  # финансовые организации
    (9000, 9999, 0.1),  # государственные услуги
]
CARD_NEED_DEFAULT = 0.6

# Пункты выдачи заказов не рассматриваются как партнёры никогда
EXCLUDED_PATTERN = re.compile(
    r'(?<![a-zа-яё0-9])(ozon|озон|wildberries|вайлдберриз|вайлдберис|вайлдбериз|wb|lamoda|ламода|100\s?sp)(?![a-zа-яё0-9])',
    re.IGNORECASE)


# Государственный сектор не рассматривается как партнёры никогда
GOV_NAME_PATTERN = re.compile(
    r'\b(администраци\w*|правительств\w*|мэри[яиюей]\w*|министерств\w*|мфц|загс|фнс|'
    r'налогов\w+\s+(?:инспекц\w*|служб\w*)|прокуратур\w*|судебн\w*|следственн\w*|военкомат\w*|'
    r'пенсионн\w+\s+фонд\w*|социальн\w+\s+фонд\w*|росреестр|гибдд|мвд|полици\w*|росгвард\w*|'
    r'избирательн\w*|роспотребнадзор|дума)\b', re.IGNORECASE)
GOV_RUBRIC_PATTERN = re.compile(
    r'(органы\s+(?:государственной\s+)?власти|органы\s+местного|администраци\w*|'
    r'государственн\w+\s+(?:учреждени|орган|служб)\w*|муниципальн\w+\s+(?:учреждени|орган|служб)\w*|'
    r'налоговые\s+инспекци\w*|\bсуды\b|судебн\w*|прокуратур\w*|полици\w*|мфц|'
    r'многофункциональные\s+центры|загс|военкомат\w*|пенсионн\w*|избирательн\w*)', re.IGNORECASE)


def is_government(name, rubrics=(), mcc_code=None):
    """True для органов власти и госучреждений: по названию, рубрикам или МСС группы 9xxx."""
    if str(mcc_code or '').startswith('9'):
        return True
    if GOV_NAME_PATTERN.search(name or ''):
        return True
    return any(GOV_RUBRIC_PATTERN.search(r or '') for r in rubrics)


def is_excluded(name, brand=''):
    """True для пунктов выдачи Ozon, Wildberries, Lamoda, 100sp (по названию или бренду)."""
    return bool(EXCLUDED_PATTERN.search(f'{name or ""} {brand or ""}'))

PAGES = int(os.getenv('PARTNERS_PAGES', '3'))                  # страниц поиска (демо-ключ: 3 по 10)
PAGE_SIZE = int(os.getenv('PARTNERS_PAGE_SIZE', '10'))
DETAIL_LIMIT = int(os.getenv('PARTNERS_DETAIL_LIMIT', '12'))   # сколько организаций после первичного отбора проверяем по рубрикам

SEARCH_FIELDS = 'items.id,items.name,items.address_name,items.point'
# Для второго запроса: от полного набора к базовому (если ключ не поддерживает часть полей)
DETAIL_FIELD_SETS = [
    'items.id,items.name,items.address_name,items.point,items.rubrics,items.brand,items.schedule,items.reviews',
    'items.id,items.name,items.address_name,items.point,items.rubrics,items.brand,items.schedule',
    'items.id,items.name,items.address_name,items.point,items.rubrics',
]


# ---------------------------------------------------------------------------
# Запросы в 2ГИС
# ---------------------------------------------------------------------------
def _base_id(item_id):
    return str(item_id or '').split('_')[0]


def _log_request(label, params, response):
    """В лог — запрос без ключа (его можно повторить в браузере) и сводка ответа."""
    query = '&'.join(f'{k}={v}' for k, v in params.items() if k != 'key')
    try:
        body = response.json()
        meta, result = body.get('meta', {}), body.get('result', {})
        summary = f"code={meta.get('code')}, total={result.get('total')}, items={len(result.get('items', []) or [])}"
        if meta.get('error'):
            summary += f", error={meta['error']}"
    except Exception:
        summary = 'ответ не разобран'
    logger.info(f'🌐 2ГИС {label}?{query}&key=… → HTTP {response.status_code}, {summary}')


def fetch_nearby_pages(fetch, lat, lon, radius=RADIUS_M, pages=PAGES):
    """
    Шаг 1. Организации в радиусе (type=branch, по расстоянию), только базовые поля, по страницам.
    fetch(params) -> requests.Response (ключ добавляет вызывающий код).
    Возвращает список организаций или None, если 2ГИС не ответил успешно ни на один запрос.
    """
    base = {
        'type': 'branch', 'point': f'{lon},{lat}', 'radius': radius, 'sort': 'distance',
        'page_size': PAGE_SIZE, 'fields': SEARCH_FIELDS,
    }
    items, seen, answered = [], set(), False
    for page in range(1, pages + 1):
        params = {**base, 'page': page}
        try:
            response = fetch(params)
        except Exception as e:
            logger.warning(f'⚠️ Поиск соседних точек, страница {page}: {e}')
            break
        _log_request('items', params, response)
        if response.status_code != 200:
            break
        answered = True
        page_items = response.json().get('result', {}).get('items', []) or []
        for item in page_items:
            if _base_id(item.get('id')) not in seen:
                seen.add(_base_id(item.get('id')))
                items.append(item)
        if len(page_items) < PAGE_SIZE:
            break  # страницы закончились
    logger.info(f'📍 Соседних организаций получено: {len(items)}')
    return items if answered else None


def primary_selection(items, lat, lon, exclude_id, classify, limit=DETAIL_LIMIT, radius=RADIUS_M):
    """
    Шаг 2. Первичный отбор по дешёвым признакам (рубрик ещё нет): близость и МСС по названию.
    Организации с неопределённым по названию МСС не отбрасываются (нейтральная оценка 0.5),
    чтобы не потерять точки вроде «Хлебница». Исходная точка исключается.
    """
    exclude = _base_id(exclude_id)
    scored = []
    for item in items:
        if exclude and _base_id(item.get('id')) == exclude:
            continue
        if is_excluded(item.get('name'), brand_name(item)) or is_government(item.get('name')):
            continue
        point = item.get('point') if isinstance(item.get('point'), dict) else {}
        if point.get('lat') is None or point.get('lon') is None:
            continue
        distance = distance_m(lat, lon, point['lat'], point['lon'])
        if distance > radius * 1.1:
            continue
        guess = classify(item.get('name') or '', [], [])
        need = card_need_score(guess[0]) if guess else 0.5
        scored.append((0.6 * max(0.0, 1 - distance / radius) + 0.4 * need, item))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    selected = [item for _, item in scored[:limit]]
    logger.info(f'🧮 Первичный отбор: из {len(items)} организаций оставлено {len(selected)}')
    return selected


def fetch_details(fetch_byid, items):
    """
    Шаг 3. Один запрос /3.0/items/byid по отобранным организациям: рубрики, отзывы, график, бренд.
    Если ключ не поддерживает часть полей, набор сокращается. Возвращает {базовый id: организация}.
    """
    ids = ','.join(str(item.get('id')) for item in items if item.get('id'))
    if not ids:
        return {}
    for fields in DETAIL_FIELD_SETS:
        params = {'id': ids, 'fields': fields}
        try:
            response = fetch_byid(params)
        except Exception as e:
            logger.warning(f'⚠️ Запрос рубрик: {e}')
            return {}
        _log_request('items/byid', params, response)
        if response.status_code == 200:
            found = response.json().get('result', {}).get('items', []) or []
            return {_base_id(item.get('id')): item for item in found}
    return {}


def merge_details(items, details):
    """Дополняет организации из шага 1 данными шага 3 (по базовому id)."""
    merged = []
    for item in items:
        extra = details.get(_base_id(item.get('id')), {})
        merged.append({**item, **{k: v for k, v in extra.items() if v not in (None, '', [])}})
    return merged


# ---------------------------------------------------------------------------
# Критерии
# ---------------------------------------------------------------------------
def card_need_score(mcc_code):
    try:
        code = int(mcc_code)
    except (TypeError, ValueError):
        return CARD_NEED_DEFAULT
    matching = [(hi - lo, coef) for lo, hi, coef in CARD_NEED_RANGES if lo <= code <= hi]
    return min(matching)[1] if matching else CARD_NEED_DEFAULT


def _hours(value):
    match = re.match(r'(\d{1,2}):(\d{2})', value or '')
    return int(match.group(1)) + int(match.group(2)) / 60 if match else None


def schedule_score(schedule):
    """Оценка режима работы от 0 до 1 или None, если графика нет."""
    if not isinstance(schedule, dict):
        return None
    if schedule.get('is_24x7'):
        return 1.0
    days, total = 0, 0.0
    for key in ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'):
        day = schedule.get(key)
        spans = [h for h in (day.get('working_hours') or [])] if isinstance(day, dict) else []
        hours = 0.0
        for span in spans:
            start, end = _hours(span.get('from')), _hours(span.get('to'))
            if start is not None and end is not None:
                hours += (end - start) % 24 or 24
        if hours:
            days += 1
            total += hours
    if not days:
        return None
    return 0.5 * days / 7 + 0.5 * min(1.0, (total / days) / 14)


def reviews_info(item):
    reviews = item.get('reviews') if isinstance(item.get('reviews'), dict) else {}
    count = reviews.get('general_review_count') or reviews.get('org_review_count') or 0
    rating = reviews.get('general_rating') or reviews.get('org_rating')
    try:
        count = int(count)
    except (TypeError, ValueError):
        count = 0
    try:
        rating = float(rating) if rating is not None else None
    except (TypeError, ValueError):
        rating = None
    return count, rating


def turnover_score(item):
    """Ожидаемый оборот: отзывы (популярность) и режим работы. Нет данных — нейтральные 0.5."""
    schedule = schedule_score(item.get('schedule'))
    count, rating = reviews_info(item)
    reviews = None
    if count > 0:
        popularity = min(1.0, math.log10(1 + count) / math.log10(1 + 300))
        reviews = 0.85 * popularity + 0.15 * ((rating or 0) / 5)
    if reviews is not None and schedule is not None:
        return 0.6 * reviews + 0.4 * schedule
    if reviews is not None:
        return reviews
    if schedule is not None:
        return schedule
    return 0.5


def brand_name(item):
    brand = item.get('brand')
    if isinstance(brand, dict):
        brand = brand.get('name')
    elif isinstance(brand, list) and brand and isinstance(brand[0], dict):
        brand = brand[0].get('name')
    return brand if isinstance(brand, str) else ''


def total_score(criteria):
    return sum(WEIGHTS[name] * value for name, value in criteria.items())


# ---------------------------------------------------------------------------
# Кандидаты и отбор
# ---------------------------------------------------------------------------
def build_candidates(items, lat, lon, exclude_id, classify, radius=RADIUS_M):
    """
    classify(name, rubric_names, primary_rubric_names) -> (код, название, надёжность 0..1) или None.
    Возвращает список кандидатов с критериями и итоговой оценкой, отсортированный по оценке.
    """
    exclude = _base_id(exclude_id)
    result, seen = [], set()
    for item in items:
        item_id = _base_id(item.get('id'))
        if (exclude and item_id == exclude) or (item_id and item_id in seen):
            continue
        seen.add(item_id)

        point = item.get('point') if isinstance(item.get('point'), dict) else {}
        if point.get('lat') is not None and point.get('lon') is not None:
            distance = distance_m(lat, lon, point['lat'], point['lon'])
        elif isinstance(item.get('dist'), (int, float)):
            distance = float(item['dist'])
        else:
            distance = None
        if distance is None or distance > radius * 1.1:
            continue

        name = item.get('name') or ''
        if is_excluded(name, brand_name(item)):
            continue
        rubrics = [r.get('name') for r in item.get('rubrics') or [] if r.get('name')]
        primary = [r['name'] for r in item.get('rubrics') or [] if r.get('kind') == 'primary' and r.get('name')]
        mcc = classify(name, rubrics, primary)
        if not mcc:
            continue
        code, mcc_name, reliability = mcc
        if is_government(name, rubrics, code):
            continue

        products, products_score = applicable_products(code)
        brand = brand_name(item)
        count, rating = reviews_info(item)
        criteria = {
            'card_need': card_need_score(code),
            'turnover': turnover_score(item),
            'products': products_score,
            'proximity': max(0.0, 1 - distance / radius),
            'reliability': reliability,
            'independence': 0.3 if brand else 1.0,
        }
        result.append({
            'name': name,
            'address': item.get('address_name', ''),
            'distance_m': int(round(distance)),
            'mcc_code': code,
            'mcc_name': mcc_name,
            'products': products,
            'rubrics': rubrics[:3],
            'brand': brand,
            'rating': rating,
            'reviews': count,
            'schedule': format_schedule(item.get('schedule')),
            'score': total_score(criteria),
        })
    result.sort(key=lambda c: c['score'], reverse=True)
    return result


def make_shortlist(candidates, size=SHORTLIST_SIZE):
    """Жадный отбор с учётом разнообразия: повтор МСС снижает оценку следующего кандидата."""
    pool, chosen, used = list(candidates), [], {}
    while pool and len(chosen) < size:
        best = max(pool, key=lambda c: c['score'] * DIVERSITY_PENALTY ** used.get(c['mcc_code'], 0))
        pool.remove(best)
        used[best['mcc_code']] = used.get(best['mcc_code'], 0) + 1
        chosen.append(best)
    return chosen


def _rules_reason(c):
    parts = [f"{c['mcc_name']}, {c['distance_m']} м от точки"]
    if c['reviews']:
        parts.append(f"{c['reviews']} отзывов")
    if c['schedule']:
        parts.append(c['schedule'])
    parts.append('подходят: ' + ', '.join(c['products']))
    return '; '.join(parts) + '.'


def pick_partners(shortlist, llm_choose):
    """
    Выбирает RESULT_SIZE партнёров. llm_choose(shortlist) -> [{'id': номер из списка (с 1), 'reason': текст}] или None.
    Возвращает (партнёры без оценок, использовался_ли_GigaChat).
    """
    chosen, used_ai = [], False
    answer = llm_choose(shortlist) if shortlist else None
    if isinstance(answer, list):
        for entry in answer:
            try:
                index = int(entry.get('id')) - 1
            except (TypeError, ValueError, AttributeError):
                continue
            original = str(entry.get('reason') or '').strip()
            if not (0 <= index < len(shortlist)) or not original or any(index == i for i, _ in chosen):
                continue
            # POS-кредитование в обосновании допустимо только для разрешённых МСС
            reason = clean_product_text(original, shortlist[index]['mcc_code']) or _rules_reason(shortlist[index])
            chosen.append((index, reason))
            if len(chosen) == RESULT_SIZE:
                break
        used_ai = bool(chosen)
    for index, candidate in enumerate(shortlist):  # добор по расчёту, если GigaChat выбрал меньше трёх
        if len(chosen) >= RESULT_SIZE:
            break
        if all(index != i for i, _ in chosen):
            chosen.append((index, _rules_reason(candidate)))

    partners = []
    for index, reason in chosen:
        c = shortlist[index]
        partners.append({
            'name': c['name'], 'address': c['address'], 'distance_m': c['distance_m'],
            'mcc_code': c['mcc_code'], 'mcc_name': c['mcc_name'],
            'products': c['products'], 'reason': reason,
        })
    return partners, used_ai