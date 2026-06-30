from flask import Flask, render_template, request, jsonify, send_from_directory
import datetime
import os
import random
import time
import re
import requests
from urllib.parse import quote
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from werkzeug.utils import secure_filename
import json
from gigachat_service import enhance_with_gigachat, generate_sales_text_with_gigachat

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Конфигурация
DGIS_API_KEY = os.getenv('DGIS_API_KEY', '')

# Конфигурация Яндекс.Диска
YANDEX_DISK_TOKEN = os.getenv('YANDEX_DISK_TOKEN', '')
YANDEX_DISK_FOLDER = os.getenv('YANDEX_DISK_FOLDER', '/mcc_feedback')
YANDEX_DISK_API = 'https://cloud-api.yandex.net/v1/disk'

# Конфигурация Яндекс.Почты
YANDEX_EMAIL = os.getenv('YANDEX_EMAIL', '')
YANDEX_PASSWORD = os.getenv('YANDEX_PASSWORD', '')
FEEDBACK_EMAIL = os.getenv('FEEDBACK_EMAIL', YANDEX_EMAIL)

# Конфигурация для локального хранения файлов
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'txt'}

# Создаем папку для загрузок
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Конфигурация
DGIS_API_KEY = os.getenv('DGIS_API_KEY', '')

# Конфигурация Яндекс.Диска
YANDEX_DISK_TOKEN = os.getenv('YANDEX_DISK_TOKEN', '')
YANDEX_DISK_FOLDER = os.getenv('YANDEX_DISK_FOLDER', '/mcc_feedback')
YANDEX_DISK_API = 'https://cloud-api.yandex.net/v1/disk'

# Конфигурация Google Sheets
GOOGLE_SHEETS_URL = os.getenv('GOOGLE_SHEETS_WEBHOOK_URL', '')

# Конфигурация для локального хранения файлов
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'txt'}

# Создаем папку для загрузок
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

MCC_DATABASE = []

def load_mcc_database():
    """Загружает MCC-коды из JSON-файла"""
    global MCC_DATABASE
    try:
        json_path = os.path.join(os.path.dirname(__file__), 'mcc_database.json')
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                MCC_DATABASE = json.load(f)
            logger.info(f"✅ Загружено {len(MCC_DATABASE)} MCC-кодов из mcc_database.json")
        else:
            logger.error("❌ Файл mcc_database.json не найден")
            MCC_DATABASE = []
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки MCC-кодов: {e}")
        MCC_DATABASE = []

# Загружаем данные при запуске
load_mcc_database()

def allowed_file(filename):
    """Проверяет разрешен ли тип файла"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_file_locally(file):
    """Сохраняет файл локально"""
    try:
        # Безопасное имя файла
        filename = secure_filename(file.filename)
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        saved_filename = f"{timestamp}_{filename}"
        filepath = os.path.join(UPLOAD_FOLDER, saved_filename)

        # Сохраняем файл
        file.save(filepath)

        logger.info(f"✅ Файл сохранен локально: {filepath}")

        return {
            "success": True,
            "url": f"/uploads/{saved_filename}",
            "path": filepath,
            "filename": filename,
            "size": os.path.getsize(filepath)
        }
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения файла: {e}")
        return {"success": False, "error": str(e)}


def ensure_yandex_folder():
    """Создает папку на Яндекс.Диске, если её нет"""
    try:
        headers = {'Authorization': f'OAuth {YANDEX_DISK_TOKEN}'}

        # Убедимся, что путь начинается с /
        folder_path = YANDEX_DISK_FOLDER
        if not folder_path.startswith('/'):
            folder_path = '/' + folder_path

        logger.info(f"📁 Проверка папки: {folder_path}")

        # Проверяем существование папки
        response = requests.get(
            f"{YANDEX_DISK_API}/resources",
            headers=headers,
            params={'path': folder_path}
        )

        logger.info(f"📊 Статус проверки: {response.status_code}")

        if response.status_code == 200:
            logger.info(f"✅ Папка {folder_path} уже существует")
            return True
        elif response.status_code == 404:
            # Создаем папку
            logger.info(f"📁 Создаю папку {folder_path}...")
            create_response = requests.put(
                f"{YANDEX_DISK_API}/resources",
                headers=headers,
                params={'path': folder_path}
            )

            logger.info(f"📊 Статус создания: {create_response.status_code}")

            if create_response.status_code in [200, 201, 202]:
                logger.info(f"✅ Папка {folder_path} успешно создана")

                # Проверяем, что папка действительно создалась
                check_response = requests.get(
                    f"{YANDEX_DISK_API}/resources",
                    headers=headers,
                    params={'path': folder_path}
                )

                if check_response.status_code == 200:
                    logger.info(f"✅ Папка подтверждена")
                    return True
                else:
                    logger.error(f"❌ Папка не подтвердилась: {check_response.status_code}")
                    return False
            else:
                logger.error(f"❌ Ошибка создания папки: {create_response.text}")
                return False
        else:
            logger.error(f"❌ Ошибка проверки папки: {response.text}")
            return False

    except Exception as e:
        logger.error(f"❌ Ошибка при создании папки: {e}")
        return False


def get_next_folder_number():
    """
    Определяет следующий номер для папки
    """
    try:
        headers = {'Authorization': f'OAuth {YANDEX_DISK_TOKEN}'}

        # Получаем список папок в корне
        response = requests.get(
            f"{YANDEX_DISK_API}/resources",
            headers=headers,
            params={'path': YANDEX_DISK_FOLDER, 'limit': 100}
        )

        if response.status_code == 200:
            data = response.json()
            items = data.get('_embedded', {}).get('items', [])

            # Ищем папки с сегодняшней датой
            today = datetime.datetime.now().strftime('%Y%m%d')
            max_num = 0

            for item in items:
                if item['type'] == 'dir':
                    name = item['name']
                    if name.startswith(today):
                        try:
                            num = int(name.split('_')[1])
                            if num > max_num:
                                max_num = num
                        except:
                            pass

            return max_num + 1

    except Exception as e:
        logger.error(f"❌ Ошибка при определении номера папки: {e}")

    return 1


def create_dated_folder():
    """
    Создает папку с именем ГГГГММДД_НН
    """
    try:
        headers = {'Authorization': f'OAuth {YANDEX_DISK_TOKEN}'}

        # Получаем сегодняшнюю дату и следующий номер
        today = datetime.datetime.now().strftime('%Y%m%d')
        next_num = get_next_folder_number()
        folder_name = f"{today}_{next_num:02d}"
        folder_path = f"{YANDEX_DISK_FOLDER}/{folder_name}"

        logger.info(f"📁 Создание папки: {folder_path}")

        # Создаем папку
        response = requests.put(
            f"{YANDEX_DISK_API}/resources",
            headers=headers,
            params={'path': folder_path}
        )

        if response.status_code in [200, 201, 202]:
            logger.info(f"✅ Папка создана: {folder_path}")
            return folder_path
        else:
            logger.error(f"❌ Ошибка создания папки: {response.text}")
            return None

    except Exception as e:
        logger.error(f"❌ Ошибка при создании папки: {e}")
        return None


def create_info_file(folder_path, name, email, message, files):
    """
    Создает текстовый файл с информацией об обратной связи
    """
    try:
        headers = {'Authorization': f'OAuth {YANDEX_DISK_TOKEN}'}

        # Формируем содержимое файла
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        info_text = f"""=== ИНФОРМАЦИЯ ОБ ОБРАТНОЙ СВЯЗИ ===
Дата и время: {timestamp}

=== ДАННЫЕ ОТПРАВИТЕЛЯ ===
Имя: {name}
Email: {email}

=== СООБЩЕНИЕ ===
{message}

=== ПРИЛОЖЕННЫЕ ФАЙЛЫ ===
"""

        if files and len(files) > 0:
            for i, file in enumerate(files, 1):
                info_text += f"\n{i}. {file.get('filename', 'Файл')}"
                info_text += f"\n   Размер: {file.get('size', 0) // 1024} KB"
                info_text += f"\n   Ссылка: {file.get('url', '#')}\n"
        else:
            info_text += "\nФайлы не приложены\n"

        info_text += "\n" + "=" * 40

        # Создаем файл
        filename = f"info_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        file_path = f"{folder_path}/{filename}"

        # Получаем URL для загрузки
        response = requests.get(
            f"{YANDEX_DISK_API}/resources/upload",
            headers=headers,
            params={'path': file_path, 'overwrite': True}
        )

        if response.status_code != 200:
            logger.error(f"❌ Ошибка получения URL для info-файла: {response.text}")
            return None

        upload_url = response.json()['href']

        # Загружаем файл
        response = requests.put(upload_url, data=info_text.encode('utf-8'))

        if response.status_code in [200, 201]:
            logger.info(f"✅ Info-файл создан: {file_path}")

            # Делаем файл публичным
            publish_response = requests.put(
                f"{YANDEX_DISK_API}/resources/publish",
                headers=headers,
                params={'path': file_path}
            )

            if publish_response.status_code == 200:
                data = publish_response.json()
                return data.get('public_url')

        return None

    except Exception as e:
        logger.error(f"❌ Ошибка при создании info-файла: {e}")
        return None


def upload_to_yandex_disk(file, filename, folder_path=None):
    """Загружает файл на Яндекс.Диск в указанную папку"""
    try:
        headers = {'Authorization': f'OAuth {YANDEX_DISK_TOKEN}'}

        # Если папка не указана, используем корневую
        if not folder_path:
            folder_path = YANDEX_DISK_FOLDER

        # Уникальное имя файла с датой
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_filename = filename.replace(' ', '_').replace('(', '').replace(')', '')
        upload_path = f"{folder_path}/{timestamp}_{safe_filename}"

        logger.info(f"📤 Загрузка файла на Яндекс.Диск: {upload_path}")

        # Получаем URL для загрузки
        response = requests.get(
            f"{YANDEX_DISK_API}/resources/upload",
            headers=headers,
            params={'path': upload_path, 'overwrite': True}
        )

        if response.status_code != 200:
            logger.error(f"❌ Ошибка получения URL: {response.text}")
            return {"success": False, "error": f"Не удалось получить URL для загрузки: {response.status_code}"}

        upload_url = response.json()['href']

        # Загружаем файл
        file.seek(0)
        file_content = file.read()

        logger.info(f"📤 Размер файла: {len(file_content)} байт")

        upload_response = requests.put(upload_url, data=file_content)

        logger.info(f"📊 Статус загрузки: {upload_response.status_code}")

        if upload_response.status_code in [200, 201]:
            # Делаем файл публичным
            publish_response = requests.put(
                f"{YANDEX_DISK_API}/resources/publish",
                headers=headers,
                params={'path': upload_path}
            )

            if publish_response.status_code == 200:
                data = publish_response.json()
                public_url = data.get('public_url', '')
                if not public_url:
                    file_id = upload_path.split('/')[-1]
                    public_url = f"https://disk.yandex.ru/d/{file_id}"
            else:
                public_url = f"https://disk.yandex.ru/client/disk{upload_path}"

            logger.info(f"✅ Файл загружен: {public_url}")

            return {
                "success": True,
                "url": public_url,
                "path": upload_path,
                "filename": filename,
                "size": len(file_content)
            }
        else:
            logger.error(f"❌ Ошибка загрузки файла: {upload_response.text}")
            return {"success": False, "error": f"Ошибка при загрузке файла: {upload_response.status_code}"}

    except Exception as e:
        logger.error(f"❌ Исключение при загрузке: {e}")
        return {"success": False, "error": str(e)}


def send_to_google_sheets(name, email, message, files=None, status="Новое"):
    """
    Отправляет данные обратной связи в Google Sheets
    """
    try:
        if not GOOGLE_SHEETS_URL:
            logger.error("❌ GOOGLE_SHEETS_WEBHOOK_URL не настроен")
            return False, "URL не настроен"

        # Формируем данные для отправки
        payload = {
            'name': name,
            'email': email,
            'message': message,
            'status': status  # Добавляем статус
        }

        # Если есть файлы, добавляем информацию в message
        if files and len(files) > 0:
            files_info = "\n\n📎 Прикрепленные файлы:\n"
            for file in files:
                files_info += f"- {file.get('filename', 'Файл')}: {file.get('url', '#')}\n"
            payload['message'] = message + files_info

        logger.info(f"📤 Отправка в Google Sheets: {name} (статус: {status})")

        response = requests.post(
            GOOGLE_SHEETS_URL,
            json=payload,
            timeout=30,
            headers={'Content-Type': 'application/json'}
        )

        if response.status_code == 200:
            logger.info(f"✅ Данные сохранены в Google Sheets")
            return True, "Сохранено"
        else:
            logger.error(f"❌ Ошибка HTTP: {response.status_code}")
            return False, f"HTTP ошибка: {response.status_code}"

    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        return False, str(e)


def save_feedback_to_file(name, email, badge_number, message, files=None):
    """Сохраняет обратную связь в файл"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    feedback_entry = f"""
[{timestamp}]
👤 Имя: {name}
📧 Email: {email}
🏷️ Табельный номер: {badge_number}
💬 Сообщение: {message}
"""
    if files:
        feedback_entry += "📎 Файлы:\n"
        for f in files:
            feedback_entry += f"  - {f.get('filename', 'Файл')}: {f.get('url', '#')} ({f.get('size', 0) // 1024} KB)\n"
    else:
        feedback_entry += "📎 Файлы: не приложены\n"
    feedback_entry += "-" * 60 + "\n"

    try:
        with open('feedback.txt', 'a', encoding='utf-8') as f:
            f.write(feedback_entry)
        logger.info(f"✅ Запись сохранена в feedback.txt")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения: {e}")
        return False


def calculate_similarity(text, keywords):
    """Рассчитывает релевантность текста набору ключевых слов"""
    text_lower = text.lower()
    score = 0
    matches = []

    for keyword in keywords:
        # Точное вхождение слова (самое важное)
        if re.search(r'\b' + re.escape(keyword) + r'\b', text_lower):
            # Если ключевое слово - общее (доставка), даём меньший вес
            common_words = ['доставка', 'оплата', 'карта', 'наличный', 'qr']
            if keyword in common_words:
                score += 5
                matches.append(keyword + "*")
            else:
                score += 10
                matches.append(keyword)
        # Слово как часть другого слова
        elif keyword in text_lower:
            score += 2
            matches.append(keyword + "~")

    return score, matches


def search_organization_direct(org_name, address):
    """
    Этап 0: Прямой поиск организации по названию и адресу
    """
    try:
        # Формируем поисковый запрос: "название, адрес"
        search_query = f"{org_name}, {address}"

        response = requests.get(
            "https://catalog.api.2gis.com/3.0/items",
            params={
                'q': search_query,
                'key': DGIS_API_KEY,
                'type': 'branch',  # Ищем только организации
                'fields': 'items.id,items.name,items.address_name,items.rubrics,items.attribute_groups,items.purpose_name'
            },
            timeout=10
        )

        if response.status_code != 200:
            return None, f"Ошибка API: {response.status_code}"

        data = response.json()

        if 'result' not in data or 'items' not in data['result'] or not data['result']['items']:
            return None, "Организация не найдена"

        # Берём первый результат
        organization = data['result']['items'][0]
        logger.info(f"✅ Найдена организация прямым поиском: {organization.get('name')}")

        return organization, None

    except Exception as e:
        return None, str(e)


def find_organizations_in_building(building_id, org_name):
    """
    Находит ВСЕ организации в здании и выбирает наиболее релевантную
    """
    try:
        response = requests.get(
            "https://catalog.api.2gis.com/3.0/items",
            params={
                'building_id': building_id,
                'key': DGIS_API_KEY,
                'type': 'branch',
                'fields': 'items.name,items.address_name,items.rubrics,items.attribute_groups',
                'limit': 50  # Увеличиваем лимит для больших ТЦ
            },
            timeout=10
        )

        if response.status_code != 200:
            return None, f"Ошибка API: {response.status_code}"

        data = response.json()

        if 'result' not in data or 'items' not in data['result']:
            return None, "Нет организаций в здании"

        organizations = data['result'].get('items', [])

        if not organizations:
            return None, "В здании нет организаций"

        # Ищем наиболее релевантную по названию
        best_match = None
        best_score = 0
        search_words = set(org_name.lower().split())

        for org in organizations:
            org_name_lower = org.get('name', '').lower()

            # Считаем релевантность
            score = 0

            # Точное совпадение
            if org_name_lower == org_name.lower():
                score = 100
            # Название содержит искомое
            elif org_name.lower() in org_name_lower:
                score = 50
            # Искомое содержит название
            elif org_name_lower in org_name.lower():
                score = 40
            else:
                # Считаем совпадения слов
                org_words = set(org_name_lower.split())
                common_words = search_words & org_words
                score = len(common_words) * 10

            if score > best_score:
                best_score = score
                best_match = org

        if best_match:
            logger.info(f"✅ Найдена организация в здании: {best_match.get('name')} (релевантность: {best_score})")
            return best_match, None
        else:
            # Если ничего не нашли, возвращаем первую
            logger.warning(f"⚠️ Не найдено совпадений, возвращаю первую организацию: {organizations[0].get('name')}")
            return organizations[0], None

    except Exception as e:
        return None, str(e)

def get_rubrics_and_services(org):
    """
    Извлекает рубрики и услуги из организации.
    Услуги собираются из всех групп атрибутов (attribute_groups).
    """
    rubrics = []
    services = []

    if 'rubrics' in org:
        for rubric in org['rubrics']:
            if 'name' in rubric:
                rubrics.append(rubric['name'])
    if 'attribute_groups' in org and org['attribute_groups']:
        all_services = []
        for group in org['attribute_groups']:
            # Название группы услуг (например, "Диагностика", "Анализы", "Услуги")
            group_name = group.get('name', '')
            # Извлекаем все атрибуты (услуги) внутри группы
            if 'attributes' in group:
                for attr in group['attributes']:
                    service_name = attr.get('name')
                    if service_name:
                        # Добавляем услугу в общий список
                        all_services.append(service_name)

        # Убираем дубликаты, сохраняя порядок
        seen = set()
        unique_services = []
        for service in all_services:
            if service not in seen:
                seen.add(service)
                unique_services.append(service)

        # Ограничиваем количество услуг (первые 15)
        services = unique_services[:15]
    if 'external_content' in org:
        for content in org['external_content']:
            if content.get('type') == 'services' and 'items' in content:
                for service in content['items']:
                    if 'name' in service and service['name'] not in services:
                        services.append(service['name'])

    return rubrics, services


def calculate_relevance(text, keywords):
    """
    Рассчитывает релевантность текста набору ключевых слов
    Возвращает: (score, matches, match_count)
    """
    text_lower = text.lower()
    score = 0
    matches = []
    match_count = 0

    for keyword in keywords:
        # Точное совпадение целого слова (самое важное)
        if re.search(r'\b' + re.escape(keyword) + r'\b', text_lower):
            score += 10
            matches.append(keyword)
            match_count += 1
        # Слово как часть другого слова (менее важно)
        elif keyword in text_lower:
            score += 3
            matches.append(keyword + "~")
            match_count += 1

    return score, matches, match_count


def predict_mcc_from_org(organization, building_name, address):
    org_name = organization.get('name', '').lower()
    rubrics, services = get_rubrics_and_services(organization)

    # Формируем текст для поиска
    search_text = f"{org_name} {building_name} {address} {' '.join(rubrics)} {' '.join(services)}".lower()

    candidates = []
    for item in MCC_DATABASE:
        score, matches, match_count = calculate_relevance(search_text, item["keywords"])
        if match_count > 0:
            candidates.append({
                "code": item["code"],
                "name": item["name"],
                "description": item["description"],
                "score": score,
                "match_count": match_count,
                "matches": matches[:3],
                "item": item
            })

    if not candidates:
        return {
            "code": "????",
            "name": "Специфичная ниша",
            "confidence": 0,
            "found": False,
            "message": "Не удалось определить MCC-код для данной организации",
            "suggestions": get_suggestions(search_text)
        }

    candidates.sort(key=lambda x: (x["match_count"], x["score"]), reverse=True)
    best = candidates[0]
    confidence = min(98, 50 + best["match_count"] * 5 + best["score"] // 2)

    # --- НОВОЕ: улучшаем через GigaChat ---
    gigachat_result = enhance_with_gigachat(
        org_name=org_name,
        rubrics=rubrics,
        services=services,
        mcc_candidates=candidates[:5],
        current_mcc_code=best["code"],
        current_mcc_name=best["name"]
    )

    if gigachat_result and gigachat_result.get('mcc_code'):
        # Если GigaChat предложил другой код, ищем его в базе
        if gigachat_result['mcc_code'] != best["code"]:
            for item in MCC_DATABASE:
                if item['code'] == gigachat_result['mcc_code']:
                    best = {
                        "code": item["code"],
                        "name": item["name"],
                        "description": item["description"],
                        "matches": best["matches"],
                        "match_count": best["match_count"]
                    }
                    # Уверенность высокая, так как подтверждено ИИ
                    confidence = 97
                    break
        # Добавляем объяснение и продукты
        gigachat_explanation = gigachat_result.get('explanation', '')
        gigachat_products = gigachat_result.get('products', [])
    else:
        gigachat_explanation = ''
        gigachat_products = []

    return {
        "code": best["code"],
        "name": best["name"],
        "description": best.get("description", ""),
        "confidence": confidence,
        "found": True,
        "matches": best["matches"],
        "match_count": best["match_count"],
        "total_candidates": len(candidates),
        "gigachat_explanation": gigachat_explanation,
        "gigachat_products": gigachat_products
    }

def get_suggestions(text):
    """Возвращает подсказки на основе частичных совпадений"""
    suggestions = []
    # Здесь будут подсказки из вашей базы
    return suggestions[:3]


@app.route('/report_wrong_mcc', methods=['POST'])
def report_wrong_mcc():
    """Обрабатывает жалобу на неверный MCC-код"""
    try:
        data = request.get_json()

        org_name = data.get('org_name', '').strip()
        address = data.get('address', '').strip()
        wrong_mcc = data.get('wrong_mcc', '').strip()
        wrong_mcc_name = data.get('wrong_mcc_name', '').strip()
        building_name = data.get('building_name', '').strip()
        building_address = data.get('building_address', '').strip()
        rubrics = data.get('rubrics', [])
        services = data.get('services', [])

        # Валидация
        if not org_name or not address or not wrong_mcc:
            return jsonify({"success": False, "error": "Недостаточно данных для отправки"})

        # Формируем сообщение
        message = f"""
🚫 НЕВЕРНЫЙ MCC-КОД

📍 Торговая точка: {org_name}
🏠 Адрес: {address}
🏢 Здание: {building_name}
📌 Адрес здания: {building_address}

📋 Рубрики: {', '.join(rubrics) if rubrics else 'не указаны'}
🛠️ Услуги: {', '.join(services[:10]) if services else 'не указаны'}

❌ Ошибочный MCC: {wrong_mcc} - {wrong_mcc_name}
"""

        # Отправляем в Google Sheets с пометкой "Неверный МСС"
        sheets_success, sheets_message = send_to_google_sheets(
            name=org_name,
            email="report@system",
            message=message,
            files=None,
            status="Неверный МСС"
        )

        # Сохраняем локально
        save_report_to_file(org_name, address, wrong_mcc, wrong_mcc_name, rubrics, services)

        return jsonify({
            "success": True,
            "message": "Спасибо за обратную связь! Ошибка зафиксирована, мы улучшим алгоритм."
        })

    except Exception as e:
        logger.error(f"❌ Ошибка при отправке жалобы: {e}")
        return jsonify({"success": False, "error": str(e)})


def save_report_to_file(org_name, address, wrong_mcc, wrong_mcc_name, rubrics, services):
    """Сохраняет жалобу на неверный МСС в файл"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_entry = f"""
[{timestamp}] ⚠️ НЕВЕРНЫЙ МСС
📍 Торговая точка: {org_name}
🏠 Адрес: {address}
❌ Ошибочный MCC: {wrong_mcc} - {wrong_mcc_name}
📋 Рубрики: {', '.join(rubrics) if rubrics else 'не указаны'}
🛠️ Услуги: {', '.join(services[:5]) if services else 'не указаны'}
{'-' * 60}
"""
    try:
        with open('wrong_mcc_reports.txt', 'a', encoding='utf-8') as f:
            f.write(report_entry)
        logger.info(f"✅ Жалоба на неверный МСС сохранена")
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения: {e}")
@app.route('/test_yandex_folder', methods=['GET'])
def test_yandex_folder():
    """Тест создания папки на Яндекс.Диске"""
    logger.info("=" * 50)
    logger.info("🧪 ТЕСТ СОЗДАНИЯ ПАПКИ НА ДИСКЕ")

    # Проверяем корневую папку
    root_result = ensure_yandex_folder()

    # Создаем датированную папку
    dated_folder = create_dated_folder()

    response_data = {
        "root_folder_created": root_result,
        "dated_folder_created": dated_folder is not None,
        "dated_folder_path": dated_folder,
        "root_folder": YANDEX_DISK_FOLDER,
        "token_present": bool(YANDEX_DISK_TOKEN)
    }

    logger.info(f"Результат: {response_data}")
    logger.info("=" * 50)

    return jsonify(response_data)


@app.route('/')
def index():
    """Главная страница"""
    return render_template('index_simple.html')


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Доступ к загруженным файлам"""
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route('/search_organization', methods=['POST'])
def search_organization():
    """Поиск организации и определение MCC-кода"""
    data = request.get_json()
    org_name = data.get('org_name', '').strip()
    address = data.get('address', '').strip()

    if not org_name or not address:
        return jsonify({"success": False, "error": "Заполните все поля"})

    logger.info(f"🔍 Поиск: '{org_name}' по адресу '{address}'")

    # ЭТАП 0: Прямой поиск организации
    organization, error = search_organization_direct(org_name, address)

    if organization:
        # Нашли организацию напрямую
        building_info = {
            "name": organization.get('address_name', ''),
            "address": organization.get('address_name', ''),
            "purpose": organization.get('purpose_name', '')
        }
        logger.info(f"✅ Организация найдена прямым поиском")
    else:
        # ЭТАП 1: Поиск здания по адресу
        logger.info(f"🏢 Прямой поиск не дал результатов, ищу здание по адресу")
        item, error, item_type = search_building(address)

        if error:
            return jsonify({"success": False, "error": f"Ошибка поиска: {error}"})

        building_info = {
            "name": item.get('name', ''),
            "address": item.get('address_name', ''),
            "purpose": item.get('purpose_name', '')
        }

        # ЭТАП 2: Если нашли здание, ищем организации внутри
        if item_type == 'building':
            logger.info(f"🏢 Найдено здание: {building_info['name']}, ищу организацию внутри")
            organization, error = find_organizations_in_building(item.get('id'), org_name)

            if error or not organization:
                return jsonify({
                    "success": False,
                    "error": f"Организация '{org_name}' не найдена в здании",
                    "building": building_info
                })
        else:
            # Если нашли организацию как здание (неправильная классификация)
            logger.info(f"⚠️ Найден объект типа {item_type}, использую как организацию")
            organization = item

    # Получаем рубрики и услуги
    rubrics, services = get_rubrics_and_services(organization)

    # Определяем MCC-код
    mcc_result = predict_mcc_from_org(
        organization,
        building_info.get('name', ''),
        building_info.get('address', '')
    )

    return jsonify({
        "success": True,
        "building": building_info,
        "organization": {
            "name": organization.get('name', ''),
            "rubrics": rubrics,
            "services": services[:15]
        },
        "mcc": mcc_result
    })


@app.route('/send_feedback', methods=['POST'])
def send_feedback():
    """Обрабатывает отправку обратной связи"""
    try:
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        badge_number = request.form.get('badge_number', '').strip()
        message = request.form.get('message', '').strip()
        files = request.files.getlist('attachments')

        # Валидация
        if not name:
            return jsonify({"success": False, "error": "Укажите ваше имя"})

        if not email or '@' not in email or '.' not in email:
            return jsonify({"success": False, "error": "Укажите корректный email"})

        # Валидация табельного номера (7 цифр)
        if not badge_number:
            return jsonify({"success": False, "error": "Укажите табельный номер"})

        if not re.match(r'^\d{7}$', badge_number):
            return jsonify({"success": False, "error": "Табельный номер должен состоять из 7 цифр"})

        if not message or len(message) < 10:
            return jsonify({"success": False, "error": "Сообщение должно содержать минимум 10 символов"})

        # Проверка на наличие прикреплённых файлов
        if not files or len(files) == 0 or files[0].filename == '':
            return jsonify({"success": False, "error": "Прикрепите файлы (терминальный чек, фото вывески и т.д.)"})

        logger.info("=" * 50)
        logger.info("📨 НОВАЯ ОБРАТНАЯ СВЯЗЬ")
        logger.info(f"Имя: {name}")
        logger.info(f"Email: {email}")
        logger.info(f"🏷️ Табельный номер: {badge_number}")
        logger.info(f"Сообщение: {message[:50]}...")
        logger.info(f"Файлов: {len(files) if files else 0}")

        # Загружаем файлы на Яндекс.Диск
        saved_files = []
        if files and len(files) > 0:
            dated_folder = create_dated_folder()
            if dated_folder:
                for file in files:
                    if file and file.filename:
                        result = upload_to_yandex_disk(file, file.filename, dated_folder)
                        if result['success']:
                            saved_files.append(result)

        # Сохраняем локально
        save_feedback_to_file(name, email, badge_number, message, saved_files)

        # Формируем сообщение для Google Sheets
        google_message = f"🏷️ Табельный номер: {badge_number}\n\n{message}"

        # Отправляем в Google Sheets
        sheets_success, sheets_message = send_to_google_sheets(
            name,
            email,
            google_message,
            saved_files,
            "Обратная связь"
        )

        response_message = "Спасибо! "
        if saved_files:
            response_message += f"Загружено файлов: {len(saved_files)}. "
        if sheets_success:
            response_message += "Ваше сообщение отправлено."
        else:
            response_message += "Сообщение сохранено локально."

        return jsonify({
            "success": True,
            "message": response_message,
            "files": saved_files
        })

    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/test_google_sheets', methods=['GET'])
def test_google_sheets():
    """Тест отправки в Google Sheets"""
    logger.info("=" * 50)
    logger.info("🧪 ТЕСТ GOOGLE SHEETS")

    # Проверяем наличие URL
    sheets_url = os.getenv('GOOGLE_SHEETS_WEBHOOK_URL')
    if not sheets_url:
        return jsonify({
            "success": False,
            "error": "GOOGLE_SHEETS_WEBHOOK_URL не настроен",
            "url_configured": False
        })

    # Отправляем тестовые данные
    success, message = send_to_google_sheets(
        name="Тестовый пользователь",
        email="test@example.com",
        message="Это тестовое сообщение для проверки Google Sheets"
    )

    result = {
        "success": success,
        "message": message,
        "url_configured": True,
        "url_preview": sheets_url[:50] + "..."
    }

    logger.info(f"Результат теста: {result}")
    logger.info("=" * 50)

    return jsonify(result)


@app.route('/check_disk', methods=['GET'])
def check_disk():
    """Проверка подключения к Яндекс.Диску"""
    try:
        headers = {'Authorization': f'OAuth {YANDEX_DISK_TOKEN}'}

        response = requests.get(
            f"{YANDEX_DISK_API}",
            headers=headers
        )

        if response.status_code == 200:
            data = response.json()
            return jsonify({
                "success": True,
                "message": "Диск подключен",
                "user": data.get('user', {}),
                "total_space_gb": round(data.get('total_space', 0) / 1024 ** 3, 2),
                "used_space_gb": round(data.get('used_space', 0) / 1024 ** 3, 2)
            })
        else:
            return jsonify({
                "success": False,
                "error": f"Ошибка {response.status_code}",
                "details": response.text
            })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("🚀 MCC AI Agent с Яндекс.Диском и Google Sheets запущен!")
    print("📍 Адрес: http://localhost:5000")
    print("📁 Файлы сохраняются в папку: uploads/")
    print("📁 Яндекс.Диск: структура ГГГГММДД_НН")
    print("📊 Google Sheets: " + ("подключен" if GOOGLE_SHEETS_URL else "не настроен"))
    print("=" * 60 + "\n")

    # Проверяем Яндекс.Диск при запуске
    if YANDEX_DISK_TOKEN:
        if ensure_yandex_folder():
            print("✅ Яндекс.Диск подключен")
        else:
            print("❌ Ошибка подключения к Яндекс.Диску")

    app.run(debug=True, port=5000)
