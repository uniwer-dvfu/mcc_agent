"""
Дополнительные источники данных для определения МСС-кода.

Каждый источник возвращает «сигнал» — предложенный МСС-код с пояснением, откуда он получен.
Сбой любого источника не должен ломать основной поиск: все внешние вызовы обёрнуты в try/except
и имеют короткий таймаут.

Источники:
  * основная рубрика 2ГИС (kind == "primary");
  * OpenStreetMap через Overpass API (теги shop/amenity/... рядом с точкой).
Справочная информация (бренд, график, координаты, ближайшие объекты) выводится отдельно и на выбор кода не влияет.
"""
import logging
import math
import os
import re

import requests
from dotenv import load_dotenv

load_dotenv()  # .env должен быть загружен до чтения переменных ниже
logger = logging.getLogger(__name__)

OSM_ENABLED = os.getenv('OSM_ENABLED', 'true').lower() == 'true'
OVERPASS_URL = os.getenv('OVERPASS_URL', 'https://overpass-api.de/api/interpreter')
# Заголовки HTTP допускают только латиницу, поэтому кириллица из .env отбрасывается
OSM_USER_AGENT = (os.getenv('OSM_USER_AGENT') or 'GeoSales-MCC-Agent/1.0 (educational prototype)').encode('ascii', 'ignore').decode().strip() or 'GeoSales-MCC-Agent/1.0'
OSM_TIMEOUT = float(os.getenv('OSM_TIMEOUT', '8'))
OSM_MATCH_RADIUS_M = 100   # радиус поиска самой точки
OSM_NEARBY_RADIUS_M = 150  # радиус поиска соседних объектов

# Соответствие тегов OpenStreetMap и МСС-кодов. Используются только коды, которые есть в mcc_database.json.
OSM_TAG_TO_MCC = {
    ('amenity', 'restaurant'): '5812', ('amenity', 'cafe'): '5812', ('amenity', 'food_court'): '5812',
    ('amenity', 'fast_food'): '5814', ('amenity', 'bar'): '5813', ('amenity', 'pub'): '5813',
    ('amenity', 'pharmacy'): '5912', ('amenity', 'fuel'): '5541', ('amenity', 'dentist'): '8021',
    ('amenity', 'doctors'): '8011', ('amenity', 'clinic'): '8011', ('amenity', 'hospital'): '8062',
    ('amenity', 'veterinary'): '0742', ('amenity', 'cinema'): '7832', ('amenity', 'car_wash'): '7542',
    ('amenity', 'parking'): '7523', ('amenity', 'taxi'): '4121',
    ('shop', 'supermarket'): '5411', ('shop', 'convenience'): '5499', ('shop', 'bakery'): '5462',
    ('shop', 'clothes'): '5651', ('shop', 'shoes'): '5661', ('shop', 'electronics'): '5732',
    ('shop', 'mobile_phone'): '5732', ('shop', 'computer'): '5732', ('shop', 'books'): '5942',
    ('shop', 'florist'): '5992', ('shop', 'jewelry'): '5944', ('shop', 'sports'): '5941',
    ('shop', 'toys'): '5945', ('shop', 'furniture'): '5712', ('shop', 'hardware'): '5251',
    ('shop', 'doityourself'): '5200', ('shop', 'car'): '5511', ('shop', 'car_repair'): '7538',
    ('shop', 'optician'): '8043', ('shop', 'laundry'): '7211', ('shop', 'dry_cleaning'): '7216',
    ('shop', 'gift'): '5947', ('shop', 'pet'): '5995', ('shop', 'cosmetics'): '5977',
    ('shop', 'perfumery'): '5977', ('shop', 'alcohol'): '5921', ('shop', 'department_store'): '5311',
    ('shop', 'variety_store'): '5331', ('shop', 'tobacco'): '5993', ('shop', 'hairdresser'): '7230',
    ('shop', 'beauty'): '7230', ('shop', 'children'): '5641',
    ('tourism', 'hotel'): '7011', ('tourism', 'hostel'): '7011', ('tourism', 'guest_house'): '7011',
    ('leisure', 'fitness_centre'): '7997', ('leisure', 'sports_centre'): '7997',
    ('craft', 'hairdresser'): '7230',
}
OSM_TAG_KEYS = ('amenity', 'shop', 'tourism', 'leisure', 'craft')


# ---------------------------------------------------------------------------
# Данные 2ГИС: основная рубрика и справочная информация
# ---------------------------------------------------------------------------
def get_primary_rubrics(org):
    """Названия основных рубрик организации (kind == 'primary')."""
    result = []
    for rubric in org.get('rubrics') or []:
        if rubric.get('kind') == 'primary' and rubric.get('name'):
            result.append(rubric['name'])
    return result


def _format_schedule(schedule):
    """Краткая запись графика работы из поля schedule 2ГИС. Возвращает строку или ''."""
    if not isinstance(schedule, dict):
        return ''
    if schedule.get('is_24x7'):
        return 'круглосуточно'
    names = [('Mon', 'Пн'), ('Tue', 'Вт'), ('Wed', 'Ср'), ('Thu', 'Чт'), ('Fri', 'Пт'), ('Sat', 'Сб'), ('Sun', 'Вс')]
    per_day = []
    for key, label in names:
        day = schedule.get(key)
        hours = ''
        if isinstance(day, dict):
            parts = [f"{h.get('from', '')}–{h.get('to', '')}" for h in day.get('working_hours', []) if h]
            hours = ', '.join(p for p in parts if p.strip('–'))
        per_day.append((label, hours))
    known = [h for _, h in per_day if h]
    if not known:
        return ''
    if len(known) == 7 and len(set(known)) == 1:
        return f'ежедневно {known[0]}'
    return '; '.join(f'{label} {hours}' for label, hours in per_day if hours)


def extract_extra_info(org):
    """Справочная информация из ответа 2ГИС: бренд, график, координаты."""
    brand = org.get('brand')
    if isinstance(brand, dict):
        brand = brand.get('name')
    elif isinstance(brand, list) and brand and isinstance(brand[0], dict):
        brand = brand[0].get('name')
    if not isinstance(brand, str):
        brand = ''

    point = org.get('point') if isinstance(org.get('point'), dict) else {}
    lat, lon = point.get('lat'), point.get('lon')
    return {
        'brand': brand,
        'schedule': _format_schedule(org.get('schedule')),
        'lat': lat,
        'lon': lon,
        'primary_rubrics': get_primary_rubrics(org),
    }


# ---------------------------------------------------------------------------
# OpenStreetMap (Overpass)
# ---------------------------------------------------------------------------
def _distance_m(lat1, lon1, lat2, lon2):
    """Расстояние между двумя точками в метрах (формула гаверсинусов)."""
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _name_words(text):
    return {w for w in re.findall(r'[\w]+', (text or '').lower()) if len(w) >= 3}


def _same_place(osm_name, org_name):
    """Названия считаются совпадающими, если одно содержит другое или есть общее слово из 3+ букв."""
    a, b = (osm_name or '').lower().strip(), (org_name or '').lower().strip()
    if not a or not b:
        return False
    if a in b or b in a:
        return True
    return bool(_name_words(a) & _name_words(b))


def _element_coords(el):
    if 'lat' in el and 'lon' in el:
        return el['lat'], el['lon']
    center = el.get('center') or {}
    return center.get('lat'), center.get('lon')


def _osm_code(tags):
    for key in OSM_TAG_KEYS:
        value = tags.get(key)
        if value and (key, value) in OSM_TAG_TO_MCC:
            return OSM_TAG_TO_MCC[(key, value)], f'{key}={value}'
    return None, None


def osm_lookup(lat, lon, org_name, mcc_names=None):
    """
    Ищет в OpenStreetMap саму точку (по названию) и соседние объекты.
    Возвращает словарь:
      status  — 'ok' | 'disabled' | 'no_coords' | 'error'
      code    — МСС-код по тегам найденной точки или None
      evidence— строка вида 'shop=bakery (OSM: «Название»)' или ''
      nearby  — список соседних объектов [{name, category, distance_m, code}]
    mcc_names — словарь {код: название} для подписей категорий.
    """
    result = {'status': 'ok', 'code': None, 'evidence': '', 'nearby': []}
    mcc_names = mcc_names or {}

    if not OSM_ENABLED:
        result['status'] = 'disabled'
        return result
    if lat is None or lon is None:
        result['status'] = 'no_coords'
        return result

    query = (
        f'[out:json][timeout:{int(OSM_TIMEOUT)}];'
        f'nwr(around:{OSM_NEARBY_RADIUS_M},{lat},{lon})["name"];'
        f'out tags center 60;'
    )
    try:
        response = requests.post(
            OVERPASS_URL, data={'data': query},
            headers={'User-Agent': OSM_USER_AGENT}, timeout=OSM_TIMEOUT
        )
        if response.status_code != 200:
            logger.warning(f'⚠️ Overpass вернул {response.status_code}')
            result['status'] = 'error'
            return result
        elements = response.json().get('elements', [])
    except Exception as e:
        logger.warning(f'⚠️ Ошибка запроса к Overpass: {e}')
        result['status'] = 'error'
        return result

    candidates = []
    for el in elements:
        tags = el.get('tags') or {}
        name = tags.get('name')
        el_lat, el_lon = _element_coords(el)
        if not name or el_lat is None or el_lon is None:
            continue
        code, tag = _osm_code(tags)
        has_category = code or any(tags.get(k) for k in OSM_TAG_KEYS)
        if not has_category:
            continue
        candidates.append({
            'name': name, 'code': code, 'tag': tag, 'tags': tags,
            'distance_m': int(round(_distance_m(lat, lon, el_lat, el_lon))),
        })
    candidates.sort(key=lambda c: c['distance_m'])

    matched = None
    for c in candidates:
        if c['code'] and c['distance_m'] <= OSM_MATCH_RADIUS_M and _same_place(c['name'], org_name):
            matched = c
            break
    if matched:
        result['code'] = matched['code']
        result['evidence'] = f"{matched['tag']} (OSM: «{matched['name']}»)"

    for c in candidates:
        if c is matched or _same_place(c['name'], org_name):
            continue
        category = mcc_names.get(c['code']) if c['code'] else None
        if not category:
            category = next((c['tags'][k] for k in OSM_TAG_KEYS if c['tags'].get(k)), '')
        result['nearby'].append({
            'name': c['name'], 'category': category,
            'distance_m': c['distance_m'], 'code': c['code'],
        })
        if len(result['nearby']) >= 5:
            break
    return result


# Публичные имена для других модулей
distance_m = _distance_m
format_schedule = _format_schedule