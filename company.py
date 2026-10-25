"""
Сведения о юридических лицах по названию торговой точки (DaData, данные ЕГРЮЛ/ЕГРИП).

Результат состоит из двух частей:
  * «по адресу точки» — записи, у которых совпали название, улица и дом;
  * «другие точки» — остальные записи с совпавшим названием (сначала из того же города).
ИНН в результат не включается: он нужен только самому источнику.
"""
import logging
import os
import re

import requests
from dotenv import load_dotenv

load_dotenv()  # .env должен быть загружен до чтения переменных ниже
logger = logging.getLogger(__name__)

DADATA_API_KEY = os.getenv('DADATA_API_KEY', '')
DADATA_URL = os.getenv(
    'DADATA_PARTY_URL', 'https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/party')
DADATA_TIMEOUT = float(os.getenv('DADATA_TIMEOUT', '6'))
MAX_OTHERS = 15

STATUS_NAMES = {
    'ACTIVE': 'Действует',
    'LIQUIDATING': 'Ликвидируется',
    'LIQUIDATED': 'Ликвидирована',
    'BANKRUPT': 'Банкротство',
    'REORGANIZING': 'Реорганизация',
}
_LEGAL_FORMS = {'ооо', 'оао', 'зао', 'пао', 'ао', 'ип', 'нко', 'мбу', 'му', 'гуп', 'муп', 'фгуп'}


def _norm(text):
    """Нижний регистр, ё→е, без кавычек, знаков препинания и организационно-правовых форм."""
    text = (text or '').lower().replace('ё', 'е')
    words = re.findall(r'[a-zа-я0-9]+', text)
    return ' '.join(w for w in words if w not in _LEGAL_FORMS)


def _house_tokens(text):
    """Номера домов из строки адреса: 8, 8а, 8/2."""
    found = re.findall(r'(?<![\w])(\d+(?:\s?[а-яa-z])?(?:/\d+)?)(?![\w])', (text or '').lower())
    return {t.replace(' ', '') for t in found}


def _addr_data(s):
    return ((s.get('data') or {}).get('address') or {}).get('data') or {}


def _candidate_names(s):
    data = s.get('data') or {}
    name = data.get('name') or {}
    values = [s.get('value'), name.get('short_with_opf'), name.get('full_with_opf'),
              name.get('short'), name.get('full')]
    return [_norm(v) for v in values if v]


def _name_matches(org_norm, cand_names):
    return len(org_norm) >= 3 and any(org_norm in n for n in cand_names)


def _address_matches(s, address_text):
    """Совпадение улицы и дома кандидата с адресом точки."""
    addr = _addr_data(s)
    street, house = _norm(addr.get('street')), (addr.get('house') or '').lower().replace(' ', '')
    if not street or not house:
        return False
    return street in _norm(address_text) and house in _house_tokens(address_text)


def _city(s):
    addr = _addr_data(s)
    return _norm(addr.get('city') or addr.get('settlement'))


def _address_line(s):
    addr = _addr_data(s)
    parts = [addr.get('city') or addr.get('settlement'), addr.get('street'), addr.get('house')]
    line = ', '.join(p for p in parts if p)
    return line or ((s.get('data') or {}).get('address') or {}).get('value') or ''


def _form(data):
    if data.get('type') == 'INDIVIDUAL':
        return 'ИП'
    opf = data.get('opf') or {}
    return opf.get('short') or opf.get('full') or 'Юридическое лицо'


def _entry(s):
    """Запись для вывода: без ИНН."""
    data = s.get('data') or {}
    name = (data.get('name') or {}).get('short_with_opf') or s.get('value') or ''
    return {
        'name': name,
        'address': _address_line(s),
        'form': _form(data),
        'status': STATUS_NAMES.get((data.get('state') or {}).get('status'), ''),
        'okved': data.get('okved') or '',
        'branch': data.get('branch_type') == 'BRANCH',
    }


def split_candidates(org_name, brand, address_text, suggestions):
    """
    Делит кандидатов с совпавшим названием на «по адресу» и «другие».
    Возвращает (по_адресу, другие) — списки записей DaData без дублей.
    """
    short = (org_name or '').split(',')[0]  # в 2ГИС название бывает с пояснением: «Хлебница, пекарня»
    org_norms = [n for n in {_norm(org_name), _norm(short), _norm(brand)} if n]

    matched, seen = [], set()
    for s in suggestions:
        data = s.get('data') or {}
        if not data.get('inn') or not any(_name_matches(n, _candidate_names(s)) for n in org_norms):
            continue
        key = (data.get('inn'), data.get('kpp'), _address_line(s))
        if key in seen:
            continue
        seen.add(key)
        matched.append(s)

    by_address = [s for s in matched if _address_matches(s, address_text)]
    text = _norm(address_text)
    others = [s for s in matched if s not in by_address]
    others.sort(key=lambda s: 0 if _city(s) and _city(s) in text else 1)  # сортировка устойчива
    return by_address, others


def lookup_company(org_name, brand, address_text):
    """
    Возвращает {'state': 'ok'|'disabled'|'not_found'|'error',
                'info': {'at_address': [...], 'others': [...]} | None}.
    """
    if not DADATA_API_KEY:
        logger.info('ℹ️ DaData отключён: в .env не задан DADATA_API_KEY (или приложение не перезапущено)')
        return {'state': 'disabled', 'info': None}
    query = (org_name or '').split(',')[0].strip()
    if not query:
        return {'state': 'not_found', 'info': None}
    try:
        response = requests.post(
            DADATA_URL,
            json={'query': query, 'count': 20},
            headers={'Authorization': f'Token {DADATA_API_KEY}', 'Accept': 'application/json'},
            timeout=DADATA_TIMEOUT)
        if response.status_code != 200:
            logger.warning(f'⚠️ DaData вернул {response.status_code}')
            return {'state': 'error', 'info': None}
        suggestions = response.json().get('suggestions', [])
        logger.info(f'🏛️ DaData: запрос «{query}», получено кандидатов: {len(suggestions)}')
    except Exception as e:
        logger.warning(f'⚠️ Ошибка запроса к DaData: {e}')
        return {'state': 'error', 'info': None}

    at_address, others = split_candidates(org_name, brand, address_text, suggestions)
    if not at_address and not others:
        logger.info('ℹ️ DaData: ни один кандидат не совпал по названию')
        return {'state': 'not_found', 'info': None}
    logger.info(f'✅ DaData: по адресу точки {len(at_address)}, других {len(others)}')
    return {'state': 'ok', 'info': {
        'at_address': [_entry(s) for s in at_address],
        'others': [_entry(s) for s in others[:MAX_OTHERS]],
    }}