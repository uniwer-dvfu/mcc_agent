"""
Хранилище результатов поиска партнёров (SQLite), чтобы повторное нажатие кнопки по той же точке
не вызывало 2ГИС и GigaChat заново.

Ключ: идентификатор организации + координаты (округлены до 5 знаков) + радиус.
Срок хранения: PARTNERS_CACHE_TTL_DAYS (по умолчанию 7 суток): данные 2ГИС со временем меняются.
"""
import json
import logging
import os
import sqlite3
import threading
import time

logger = logging.getLogger(__name__)

DB_PATH = os.getenv('PARTNERS_CACHE_DB', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache', 'partners_cache.db'))
TTL_SECONDS = float(os.getenv('PARTNERS_CACHE_TTL_DAYS', '7')) * 86400
_lock = threading.Lock()


def _connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.execute('CREATE TABLE IF NOT EXISTS partners_cache (key TEXT PRIMARY KEY, created REAL NOT NULL, payload TEXT NOT NULL)')
    return conn


def make_key(org_id, lat, lon, radius):
    return f"{str(org_id or '').split('_')[0]}|{round(float(lat), 5)}|{round(float(lon), 5)}|{radius}"


def get(key):
    """Запись из хранилища или None (нет записи, срок истёк, ошибка чтения)."""
    try:
        with _lock, _connect() as conn:
            row = conn.execute('SELECT created, payload FROM partners_cache WHERE key = ?', (key,)).fetchone()
        if not row or time.time() - row[0] > TTL_SECONDS:
            return None
        payload = json.loads(row[1])
        payload['created'] = row[0]
        return payload
    except Exception as e:
        logger.warning(f'⚠️ Хранилище партнёров: ошибка чтения: {e}')
        return None


def put(key, payload):
    try:
        with _lock, _connect() as conn:
            conn.execute('INSERT OR REPLACE INTO partners_cache (key, created, payload) VALUES (?, ?, ?)',
                         (key, time.time(), json.dumps(payload, ensure_ascii=False)))
    except Exception as e:
        logger.warning(f'⚠️ Хранилище партнёров: ошибка записи: {e}')