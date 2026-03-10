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

MCC_DATABASE = [
    # Рестораны и кафе
    {
        "code": "5812",
        "name": "Рестораны",
        "keywords": ["ресторан", "кафе", "кофейня", "столовая", "общепит", "питание", "еда", "обед", "ужин", "меню"],
        "description": "Места общественного питания: рестораны, кафе, кофейни, столовые, закусочные"
    },
    {
        "code": "5812",
        "name": "Кофейни",
        "keywords": ["кофе", "кофейня", "капучино", "латте", "эспрессо", "кофейный", "чай"],
        "description": "Заведения специализирующиеся на продаже кофе и чая, часто с десертами"
    },
    {
        "code": "5814",
        "name": "Рестораны быстрого питания",
        "keywords": ["быстрое питание","пиццерия" ,"фастфуд", "макдональдс", "бургер", "пицца", "быстрое питание", "бургерная", "шаурма", "хот-дог",
                     "fast food"],
        "description": "Заведения быстрого питания: бургерные, пиццерии, шаурмичные, точки с едой на вынос"
    },

    # АЗС
    {
        "code": "5541",
        "name": "Автозаправочные станции",
        "keywords": ["азс", "заправка", "бензин", "топливо", "газпромнефть", "лукойл", "shell", "bp", "дт", "дизель"],
        "description": "Автозаправочные станции, продажа бензина, дизельного топлива, газа"
    },

    # Больницы и медицина
    {
        "code": "8062",
        "name": "Больницы",
        "keywords": ["больница", "стационар", "клиника", "лечение", "медицина", "госпиталь", "поликлиника"],
        "description": "Медицинские учреждения с круглосуточным стационаром, больницы, госпитали"
    },
    {
        "code": "8090",
        "name": "Медицинские услуги",
        "keywords": ["медицинский центр", "диагностика", "анализы", "узи", "мрт", "врач", "доктор", "прием врача",
                     "медуслуги"],
        "description": "Платные медицинские услуги, диагностические центры, консультации врачей"
    },
    # Косметика и парфюмерия
    {
        "code": "5977",
        "name": "Косметика и парфюмерия",
        "keywords": [
            "косметика", "парфюмерия", "духи", "помада", "тушь", "тональный крем",
            "уход за кожей", "кремы", "маски для лица", "сыворотка", "лосьон",
            "декоративная косметика", "уходовая косметика", "бьюти", "beauty",
            "макияж", "брови", "ресницы", "ногти", "лак для ногтей",
            "золотое яблоко", "лэтуаль", "рив гош", "иль де ботэ", "sephora",
            "парфюмерный", "косметический", "бьюти-бутик", "бренды косметики",
            "люксовая косметика", "профессиональная косметика", "аптечная косметика",
            "натуральная косметика", "органическая косметика", "эко-косметика"
        ],
        "description": "Магазины косметики и парфюмерии: парфюмерные бутики, сетевые магазины косметики, бьюти-маркеты"
    },
    {
        "code": "5977",
        "name": "Парфюмерные магазины",
        "keywords": [
            "парфюм", "духи", "туалетная вода", "одеколон", "ароматы",
            "селективная парфюмерия", "нишевая парфюмерия", "элитная парфюмерия",
            "пробники духов", "наборы парфюмерии", "подарочные наборы косметики"
        ],
        "description": "Магазины парфюмерии, бутики элитной и нишевой парфюмерии"
    },
    {
        "code": "5977",
        "name": "Бьюти-маркеты",
        "keywords": [
            "бьюти", "beauty", "бьюти-маркет", "бьюти-бутик", "бьюти-пространство",
            "золотое яблоко", "лэтуаль", "рив гош", "иль де ботэ", "подружка",
            "улыбка радуги", "магнит косметик", "sephora", "nyx", "mac cosmetics"
        ],
        "description": "Сетевые бьюти-маркеты и магазины косметики"
    },
    {
        "code": "8021",
        "name": "Стоматологические клиники",
        "keywords": ["стоматология", "зубной", "дантист", "зубы", "лечение зубов", "пломба", "ортодонт", "имплант"],
        "description": "Стоматологические клиники и кабинеты, лечение зубов, протезирование"
    },
    {
        "code": "5912",
        "name": "Аптеки",
        "keywords": ["аптека", "лекарство", "таблетки", "медикаменты", "препараты", "витамины", "здоровье", "фармация",
                     "продажа лекарства", "лекарственные средства"],
        "description": "Аптеки, аптечные пункты, продажа лекарственных препаратов и медицинских изделий"
    },
    {
        "code": "742",
        "name": "Ветеринарные клиники",
        "keywords": ["ветеринар", "ветклиника", "животные", "собака", "кошка", "лечение животных", "ветаптека"],
        "description": "Ветеринарные клиники и аптеки, лечение домашних животных"
    },

    # Магазины одежды
    {
        "code": "5651",
        "name": "Магазины одежды",
        "keywords": ["одежда", "zara", "h&m", "adidas", "nike", "магазин одежды", "бутик", "платье", "рубашка",
                     "брюки"],
        "description": "Магазины одежды, бутики, сетевые магазины одежды"
    },
    {
        "code": "5651",
        "name": "Спортивная одежда",
        "keywords": ["спортивная одежда", "спорттовары", "экипировка", "adidas", "nike", "puma", "спортмастер"],
        "description": "Магазины спортивной одежды и экипировки"
    },
    {
        "code": "5661",
        "name": "Магазины обуви",
        "keywords": ["обувь", "ботинки", "туфли", "кроссовки", "сапоги", "кеды", "обувной"],
        "description": "Магазины обуви, обувные бутики"
    },

    # Продукты
    {
        "code": "5411",
        "name": "Продуктовые магазины",
        "keywords": ["продукты", "магазин продуктов", "гастроном", "кулинария", "еда", "бакалея", "овощи", "фрукты",
                     "мясо", "молоко"],
        "description": "Продуктовые магазины, гастрономы, отделы кулинарии"
    },
    {
        "code": "5411",
        "name": "Супермаркеты",
        "keywords": ["супермаркет", "магнит", "пятерочка", "перекресток", "ашан", "лента", "дика", "гипермаркет",
                     "универсам"],
        "description": "Сетевые супермаркеты и гипермаркеты с широким ассортиментом продуктов"
    },

    # Развлечения - Парки развлечений, океанариумы, зоопарки
    {
        "code": "7996",
        "name": "Парки развлечений",
        "keywords": ["парк развлечений", "аттракционы", "аквапарк", "лунапарк", "диснейленд", "карусели",
                     "американские горки", "колесо обозрения", "детский парк", "развлекательный парк"],
        "description": "Парки развлечений, лунапарки, парки с аттракционами, аквапарки"
    },
    {
        "code": "7996",
        "name": "Аквапарки",
        "keywords": ["аквапарк", "водные горки", "бассейны", "водные аттракционы", "аквазона"],
        "description": "Аквапарки, водные развлекательные комплексы с горками и бассейнами"
    },
    {
        "code": "7996",
        "name": "Зоопарки",
        "keywords": ["зоопарк", "зоосад", "зверинец", "животные", "зоологический парк", "террариум", "экзотариум"],
        "description": "Зоопарки, зоологические парки, места содержания и показа животных"
    },
    {
        "code": "7996",
        "name": "Океанариумы",
        "keywords": ["океанариум", "дельфинарий", "аквариум", "морские животные", "дельфины", "тюлени", "морской музей",
                     "подводный мир"],
        "description": "Океанариумы, дельфинарии, аквариумы с морскими животными и рыбами"
    },
    {
        "code": "7996",
        "name": "Дельфинарии",
        "keywords": ["дельфинарий", "дельфины", "шоу с дельфинами", "плавание с дельфинами", "морские млекопитающие"],
        "description": "Дельфинарии, места проведения шоу с дельфинами и морскими животными"
    },

    # Развлечения - другие
    {
        "code": "7832",
        "name": "Кинотеатры",
        "keywords": ["кино", "кинотеатр", "фильм", "кинозал", "кинопоказ", "премьера"],
        "description": "Кинотеатры, кинозалы, места для просмотра фильмов"
    },
    {
        "code": "7922",
        "name": "Театры",
        "keywords": ["театр", "спектакль", "опера", "балет", "представление", "сцена"],
        "description": "Театры, оперные и балетные театры, драматические театры"
    },
    {
        "code": "7997",
        "name": "Фитнес-клубы",
        "keywords": ["фитнес", "тренажерный зал", "спортзал", "качалка", "тренировки", "йога", "пилатес", "аэробика"],
        "description": "Фитнес-центры, тренажерные залы, студии йоги и групповых занятий"
    },
    {
        "code": "7997",
        "name": "Спортивные клубы",
        "keywords": ["спортклуб", "спортивный комплекс", "бассейн", "теннис", "футбол", "баскетбол", "волейбол"],
        "description": "Спортивные клубы и комплексы, секции, спортивные площадки"
    },

    # Красота и здоровье
    {
        "code": "7230",
        "name": "Парикмахерские",
        "keywords": ["парикмахерская", "стрижка", "прическа", "барбершоп", "мужская стрижка"],
        "description": "Парикмахерские, барбершопы, салоны стрижки"
    },
    {
        "code": "7230",
        "name": "Салоны красоты",
        "keywords": ["салон красоты", "косметология", "маникюр", "педикюр", "ногти", "брови", "ресницы"],
        "description": "Салоны красоты, косметологические кабинеты, ногтевые студии"
    },
    {
        "code": "7298",
        "name": "Спа-салоны",
        "keywords": ["спа", "массаж", "сауна", "баня", "хамам", "релакс", "оздоровление"],
        "description": "Спа-салоны, массажные кабинеты, сауны, бани"
    },

    # Транспорт
    {
        "code": "4121",
        "name": "Такси",
        "keywords": ["такси", "uber", "яндекс такси", "извоз", "перевозки", "пассажирские перевозки"],
        "description": "Службы такси, пассажирские перевозки на легковых автомобилях"
    },
    {
        "code": "4111",
        "name": "Общественный транспорт",
        "keywords": ["метро", "автобус", "трамвай", "троллейбус", "электричка", "проезд", "транспорт"],
        "description": "Общественный транспорт, проездные билеты, транспортные карты"
    },
    {
        "code": "4511",
        "name": "Авиакомпании",
        "keywords": ["авиабилеты", "самолет", "авиаперелеты", "аэрофлот", "победа", "s7", "авиакасса"],
        "description": "Авиакомпании, продажа авиабилетов, авиаперевозки"
    },
    {
        "code": "4112",
        "name": "Железнодорожные перевозки",
        "keywords": ["жд билеты", "поезд", "ржд", "железная дорога", "вокзал", "плацкарт", "купе"],
        "description": "Железнодорожные перевозки, продажа билетов на поезда"
    },

    # Отели
    {
        "code": "7011",
        "name": "Отели",
        "keywords": ["отель", "гостиница", "хостел", "проживание", "номер", "гостиничный комплекс"],
        "description": "Отели, гостиницы, хостелы, места для временного проживания"
    },

    # Образование
    {
        "code": "8211",
        "name": "Школы",
        "keywords": ["школа", "гимназия", "лицей", "образование", "учеба", "ученики"],
        "description": "Общеобразовательные школы, гимназии, лицеи"
    },
    {
        "code": "8220",
        "name": "Высшее образование",
        "keywords": ["университет", "институт", "академия", "вуз", "высшее образование", "студенты"],
        "description": "Высшие учебные заведения, университеты, институты, академии"
    },
    {
        "code": "8299",
        "name": "Образовательные курсы",
        "keywords": ["курсы", "обучение", "тренинг", "семинар", "повышение квалификации", "репетитор"],
        "description": "Образовательные курсы, тренинги, семинары, репетиторство"
    },
    # Магазины тканей и рукоделия
    {
        "code": "5949",
        "name": "Магазины тканей и рукоделия",
        "keywords": [
            "ткани", "магазин тканей", "текстиль", "шитье", "швейная фурнитура",
            "нитки", "пряжа", "выкройки", "пуговицы", "заклепки", "шнурки",
            "кружева", "молнии", "застежки", "тесьма", "подкладочная ткань",
            "отделка для одежды", "атлас", "шелк", "хлопок", "лен", "шерсть",
            "вязание", "рукоделие", "вышивка", "пяльцы", "канва", "мулине",
            "бисер", "бусины", "фурнитура для бижутерии", "леска", "спицы",
            "крючки для вязания", "наборы для шитья", "ножницы", "раскройный нож",
            "сантиметровая лента", "булавки", "иглы", "наперстки", "швейные машины",
            "консультации по шитью", "курсы кройки и шитья", "мастер-классы по шитью"
        ],
        "description": "Магазины тканей, швейной фурнитуры и товаров для рукоделия: ткани, нитки, пряжа, пуговицы, молнии, кружева, а также консультации по шитью"
    },
    {
        "code": "5949",
        "name": "Магазины пряжи и вязания",
        "keywords": [
            "пряжа", "вязание", "спицы", "крючки", "шерсть", "ангора", "мохер",
            "акрил", "меланж", "секционная пряжа", "наборы для вязания",
            "журналы по вязанию", "схемы вязания", "клубок", "моток"
        ],
        "description": "Магазины пряжи и товаров для вязания"
    },
    {
        "code": "5949",
        "name": "Магазины для вышивания",
        "keywords": [
            "вышивка", "мулине", "канва", "пяльцы", "схемы для вышивки",
            "наборы для вышивания", "вышивка крестом", "вышивка гладью",
            "вышивка бисером", "нитки для вышивания", "гобелен", "ришелье"
        ],
        "description": "Магазины товаров для вышивания"
    },

    # Специализированные розничные магазины
    {
        "code": "5999",
        "name": "Специализированные розничные магазины",
        "keywords": [
            "специализированный магазин", "уникальные товары", "сувениры",
            "подарки", "магазин подарков", "хендмейд", "handmade", "магазин сувениров",
            "эзотерика", "магические товары", "амулеты", "талисманы", "обереги",
            "карты таро", "руны", "магические свечи", "благовония", "аромалампы",
            "вечеринки", "товары для праздника", "праздничные украшения",
            "воздушные шары", "пиньяты", "колпаки", "аксессуары для вечеринок",
            "атласы", "географические карты", "путеводители", "карты мира",
            "дистиллированная вода", "льдов", "сухой лед", "питьевая вода",
            "аксессуары для красоты", "профессиональная косметика", "инструменты для макияжа",
            "кисти для макияжа", "спонжи", "щипцы для завивки", "бигуди",
            "магазин приколов", "розыгрыши", "фокусы", "магия", "эксклюзивные товары"
        ],
        "description": "Специализированные розничные магазины с уникальными товарами: сувениры, эзотерика, товары для праздников, карты и атласы, дистиллированная вода, аксессуары для красоты и другие специализированные товары"
    },
    {
        "code": "5999",
        "name": "Магазины эзотерики",
        "keywords": [
            "эзотерика", "магические товары", "амулеты", "талисманы", "обереги",
            "карты таро", "руны", "магические свечи", "благовония", "аромалампы",
            "маятники", "рамки", "оракулы", "книги по эзотерике", "хиромантия",
            "нумерология", "астрология", "фэн-шуй", "камни", "кристаллы", "минералы"
        ],
        "description": "Магазины эзотерических и магических товаров"
    },
    {
        "code": "5999",
        "name": "Магазины товаров для праздника",
        "keywords": [
            "товары для праздника", "праздничные украшения", "воздушные шары",
            "пиньяты", "колпаки", "аксессуары для вечеринок", "день рождения",
            "новый год", "свадьба", "корпоратив", "декор", "гирлянды",
            "праздничная посуда", "свечи для торта", "хлопушки", "конфетти",
            "маскарадные костюмы", "аквагрим", "фотозона", "праздничный декор"
        ],
        "description": "Магазины товаров для праздников и вечеринок"
    },

    # Различные продовольственные магазины
    {
        "code": "5499",
        "name": "Различные продовольственные магазины",
        "keywords": [
            "продукты", "продуктовый магазин", "магазин у дома", "минимаркет",
            "продукты на вынос", "специализированные продукты", "деликатесы",
            "элитные продукты", "деликатесный магазин", "гастроном",
            "диетические продукты", "здоровое питание", "полезные продукты",
            "эко-продукты", "био-продукты", "органические продукты",
            "без глютена", "без лактозы", "веганские продукты", "вегетарианские продукты",
            "сыры", "сырная лавка", "колбасы", "мясная лавка", "домашняя птица",
            "мясные деликатесы", "рыбный магазин", "морепродукты", "свежая рыба",
            "овощной магазин", "фруктовый магазин", "овощи и фрукты", "зелень",
            "фермерские продукты", "фермерский рынок", "рынок выходного дня",
            "кофейня", "кофе с собой", "кофейный бутик", "кофе зерновой",
            "чайный магазин", "чайная лавка", "свежеобжаренный кофе",
            "мороженое", "магазин мороженого", "йогурты", "десерты",
            "полуфабрикаты", "замороженные продукты", "готовая еда", "кулинария",
            "хлебобулочные изделия", "пекарня", "свежая выпечка", "хлеб",
            "кондитерская", "пирожные", "торты", "сладости", "восточные сладости",
            "мед", "варенье", "джемы", "соусы", "маринады", "соленья"
        ],
        "description": "Различные продовольственные магазины: специализированные продуктовые рынки, магазины деликатесов, диетических продуктов, овощные и фруктовые магазины, кофейни, магазины мороженого и полуфабрикатов, небольшие магазины у дома"
    },
    {
        "code": "5499",
        "name": "Магазины деликатесов",
        "keywords": [
            "деликатесы", "элитные продукты", "гастрономия", "фуа-гра",
            "трюфели", "икра", "лосось", "пармезан", "хамон", "прошутто",
            "сырная тарелка", "мясная тарелка", "винные деликатесы",
            "итальянские продукты", "французские продукты", "испанские продукты"
        ],
        "description": "Магазины элитных продуктов и деликатесов"
    },
    {
        "code": "5499",
        "name": "Магазины здорового питания",
        "keywords": [
            "здоровое питание", "диетические продукты", "без глютена",
            "без лактозы", "веганские продукты", "вегетарианские продукты",
            "органические продукты", "эко-продукты", "био-продукты",
            "суперфуды", "чиа", "киноа", "спирулина", "протеиновые батончики",
            "зож", "правильное питание", "пп", "фитнес-питание"
        ],
        "description": "Магазины диетических и здоровых продуктов питания"
    },
    {
        "code": "5499",
        "name": "Фермерские магазины",
        "keywords": [
            "фермерские продукты", "фермерский магазин", "эко-продукты",
            "натуральные продукты", "деревенские продукты", "молоко фермерское",
            "яйца домашние", "мясо фермерское", "овощи с грядки",
            "фрукты сезонные", "зелень свежая", "мед натуральный",
            "сыр домашний", "творог", "сметана", "масло сливочное"
        ],
        "description": "Фермерские магазины и лавки с натуральными продуктами"
    },
    {
        "code": "5499",
        "name": "Овощные и фруктовые магазины",
        "keywords": [
            "овощной магазин", "фруктовый магазин", "овощи и фрукты",
            "зелень", "фруктовая лавка", "овощная лавка", "фреш маркет",
            "сезонные овощи", "сезонные фрукты", "ягоды", "экзотические фрукты",
            "сухофрукты", "орехи", "свежие овощи", "свежие фрукты"
        ],
        "description": "Магазины свежих овощей и фруктов"
    },

    # Другое
    {
        "code": "5995",
        "name": "Зоомагазины",
        "keywords": ["зоомагазин", "зоотовары", "корм для животных", "аксессуары для животных"],
        "description": "Магазины товаров для животных, зоомагазины"
    },
    {
        "code": "5251",
        "name": "Хозяйственные магазины",
        "keywords": ["хозтовары", "хозяйственный магазин", "бытовая химия", "товары для дома"],
        "description": "Магазины хозяйственных товаров, бытовой химии"
    },
    {
        "code": "5712",
        "name": "Магазины мебели",
        "keywords": ["мебель", "мебельный магазин", "шкаф", "кровать", "стол", "стул", "диван"],
        "description": "Магазины мебели, мебельные салоны"
    },
    {
        "code": "5211",
        "name": "Строительные материалы",
        "keywords": ["стройматериалы", "строительный магазин", "инструменты", "ремонт", "стройка"],
        "description": "Магазины строительных материалов, инструментов, товаров для ремонта"
    },
    {
        "code": "5992",
        "name": "Цветочные магазины",
        "keywords": ["цветы", "букет", "цветочный магазин", "флористика", "растения"],
        "description": "Цветочные магазины, салоны флористики"
    },
    {
        "code": "5944",
        "name": "Ювелирные магазины",
        "keywords": ["ювелирный", "золото", "серебро", "украшения", "кольца", "серьги", "бриллианты"],
        "description": "Ювелирные магазины, салоны, продажа украшений"
    },
    {
        "code": "5942",
        "name": "Книжные магазины",
        "keywords": ["книги", "книжный магазин", "литература", "учебники", "бестселлеры"],
        "description": "Книжные магазины, магазины учебной литературы"
    },
    {
        "code": "5921",
        "name": "Алкогольные магазины",
        "keywords": ["алкоголь", "вино", "водка", "пиво", "ликер", "алкомаркет", "красное и белое"],
        "description": "Магазины алкогольной продукции, алкомаркеты"
    },
    {
        "code": "5993",
        "name": "Табачные магазины",
        "keywords": ["табак", "сигареты", "табачный магазин", "вейп", "кальяны"],
        "description": "Табачные магазины, продажа сигарет и табачных изделий"
    },
    {
        "code": "7699",
        "name": "Ремонтные мастерские",
        "keywords": ["ремонт", "мастерская", "починка", "обувь ремонт", "часы ремонт", "техника ремонт"],
        "description": "Ремонтные мастерские, услуги по ремонту различных товаров"
    },
    {
        "code": "2842",
        "name": "Химчистки",
        "keywords": ["химчистка", "чистка одежды", "стирка", "пятна"],
        "description": "Химчистки, услуги по химической чистке одежды"
    }
]

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
    """Создает папку на Яндекс.Диске, если её нет - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
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

            # Сначала создаем родительские папки, если нужно
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


def upload_to_yandex_disk(file, filename):
    """Загружает файл на Яндекс.Диск - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    try:
        headers = {'Authorization': f'OAuth {YANDEX_DISK_TOKEN}'}

        # Сначала убедимся, что папка существует
        if not ensure_yandex_folder():
            logger.error("❌ Не удалось создать/проверить папку")
            return {"success": False, "error": "Папка на диске не доступна"}

        # Уникальное имя файла с датой
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_filename = filename.replace(' ', '_').replace('(', '').replace(')', '')

        # Убедимся, что путь правильный
        folder_path = YANDEX_DISK_FOLDER
        if not folder_path.startswith('/'):
            folder_path = '/' + folder_path

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
                    # Формируем ссылку вручную
                    file_id = upload_path.split('/')[-1]
                    public_url = f"https://disk.yandex.ru/d/{file_id}"
            else:
                # Если не удалось опубликовать, даем ссылку на файл в Диске
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


def send_feedback_email(name, email, message, files=None):
    """
    Отправляет обратную связь на почту через Gmail SMTP
    """
    try:
        logger.info("=" * 50)
        logger.info("📧 НАЧАЛО ОТПРАВКИ ПИСЬМА (Gmail)")
        logger.info(f"Отправитель: {YANDEX_EMAIL}")  # теперь это будет Gmail
        logger.info(f"Получатель: {FEEDBACK_EMAIL}")
        logger.info(f"Имя отправителя: {name}")
        logger.info(f"Email отправителя: {email}")

        # Настройки Gmail
        smtp_server = "smtp.gmail.com"
        smtp_port = 587

        # Создаем письмо
        msg = MIMEMultipart()
        msg['From'] = YANDEX_EMAIL  # ваш Gmail
        msg['To'] = FEEDBACK_EMAIL  # куда отправлять (может быть тот же или Яндекс)
        msg['Subject'] = f"📬 Обратная связь от {name}"

        # Формируем текст письма
        current_time = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")

        body = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .header {{ background: #4CAF50; color: white; padding: 20px; border-radius: 10px 10px 0 0; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .footer {{ padding: 15px; color: #666; font-size: 12px; text-align: center; }}
                .file-list {{ background: #e3f2fd; padding: 10px; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>📬 Новая обратная связь с MCC AI Agent</h2>
            </div>
            <div class="content">
                <p><strong>👤 Имя:</strong> {name}</p>
                <p><strong>📧 Email:</strong> {email}</p>
                <p><strong>🕐 Время:</strong> {current_time}</p>

                <h3>💬 Сообщение:</h3>
                <p style="background: white; padding: 15px; border-radius: 5px;">{message}</p>
        """

        # Добавляем информацию о файлах
        if files and len(files) > 0:
            body += f"""
                <h3>📎 Прикрепленные файлы:</h3>
                <div class="file-list">
                    <ul>
            """
            for file in files:
                body += f'<li><a href="{file["url"]}">{file["filename"]}</a> ({file["size"] // 1024} KB)</li>'
            body += """
                    </ul>
                </div>
            """

        body += """
            </div>
            <div class="footer">
                Отправлено с сайта MCC AI Agent • {current_time}
            </div>
        </body>
        </html>
        """.format(current_time=current_time)

        msg.attach(MIMEText(body, 'html', 'utf-8'))

        # Отправляем через Gmail
        logger.info("📡 Подключаюсь к Gmail SMTP...")
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()

        logger.info("🔑 Выполняю вход...")
        server.login(YANDEX_EMAIL, YANDEX_PASSWORD)  # YANDEX_EMAIL теперь должен быть Gmail

        logger.info("📤 Отправляю письмо...")
        server.send_message(msg)

        logger.info("👋 Закрываю соединение...")
        server.quit()

        logger.info("✅ ПИСЬМО УСПЕШНО ОТПРАВЛЕНО через Gmail")
        logger.info("=" * 50)

        return True, "Письмо успешно отправлено"

    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"❌ Ошибка аутентификации Gmail: {e}")
        logger.error("Проверьте пароль приложения и двухфакторную аутентификацию")
        return False, "Ошибка аутентификации Gmail"

    except smtplib.SMTPException as e:
        logger.error(f"❌ SMTP ошибка: {e}")
        return False, f"SMTP ошибка: {e}"

    except Exception as e:
        logger.error(f"❌ Неизвестная ошибка: {e}")
        return False, str(e)

def save_feedback_to_file(name, email, message, files=None):
    """Сохраняет обратную связь в файл"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    feedback_entry = f"""
[{timestamp}]
👤 Имя: {name}
📧 Email: {email}
💬 Сообщение: {message}
"""
    if files:
        feedback_entry += "📎 Файлы:\n"
        for f in files:
            feedback_entry += f"  - {f.get('filename', 'Файл')}: {f.get('url', '#')} ({f.get('size', 0) // 1024} KB)\n"
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
        if re.search(r'\b' + re.escape(keyword) + r'\b', text_lower):
            score += 10
            matches.append(keyword)
        elif keyword in text_lower:
            score += 5
            matches.append(keyword + "*")
        elif len(keyword) > 4 and keyword[:-2] in text_lower:
            score += 3
            matches.append(keyword[:-2] + "~")

    return score, matches


def search_building(address):
    """Этап 1: Поиск здания по адресу"""
    try:
        response = requests.get(
            "https://catalog.api.2gis.com/3.0/items",
            params={
                'q': address,
                'type': 'building',
                'key': DGIS_API_KEY,
                'fields': 'items.id,items.name,items.address_name,items.purpose_name'
            },
            timeout=10
        )

        if response.status_code != 200:
            return None, f"Ошибка API: {response.status_code}"

        data = response.json()

        if 'result' not in data or 'items' not in data['result'] or not data['result']['items']:
            return None, "Здание не найдено"

        building = data['result']['items'][0]
        return building, None

    except Exception as e:
        return None, str(e)


def find_organization(building_id, org_name):
    """Этап 2: Поиск организации по названию внутри здания"""
    try:
        response = requests.get(
            "https://catalog.api.2gis.com/3.0/items",
            params={
                'q': org_name,
                'building_id': building_id,
                'key': DGIS_API_KEY,
                'type': 'branch',
                'fields': 'items.name,items.address_name,items.rubrics,items.external_content'
            },
            timeout=10
        )

        if response.status_code != 200:
            return None, f"Ошибка API: {response.status_code}"

        data = response.json()

        if 'result' not in data or 'items' not in data['result'] or not data['result']['items']:
            return None, "Организация не найдена"

        organizations = data['result']['items']
        best_match = None
        best_score = 0

        for org in organizations:
            org_name_lower = org.get('name', '').lower()
            search_name_lower = org_name.lower()

            if search_name_lower in org_name_lower:
                score = 10
            elif any(word in org_name_lower for word in search_name_lower.split()):
                score = 5
            else:
                score = 0

            if score > best_score:
                best_score = score
                best_match = org

        return best_match, None

    except Exception as e:
        return None, str(e)


def get_rubrics_and_services(org):
    """Извлекает рубрики и услуги из организации"""
    rubrics = []
    services = []

    if 'rubrics' in org:
        for rubric in org['rubrics']:
            if 'name' in rubric:
                rubrics.append(rubric['name'])

    if 'external_content' in org:
        for content in org['external_content']:
            if content.get('type') == 'services' and 'items' in content:
                for service in content['items']:
                    if 'name' in service:
                        services.append(service['name'])

    return rubrics, services


def predict_mcc_from_org(organization, building_name, address):
    """Определяет MCC-код по информации об организации"""
    org_name = organization.get('name', '')
    rubrics, services = get_rubrics_and_services(organization)

    # Объединяем всю информацию для поиска
    search_text = f"{org_name} {building_name} {address} {' '.join(rubrics)} {' '.join(services)}".lower()

    best_match = None
    best_score = 0
    best_matches = []

    # Проходим по всей базе MCC_DATABASE
    for item in MCC_DATABASE:
        score, matches = calculate_similarity(search_text, item["keywords"])
        if score > best_score:
            best_score = score
            best_match = item
            best_matches = matches

    # Если нашли совпадение с достаточным баллом
    if best_match and best_score >= 5:
        # Нормализуем уверенность (макс 98%)
        confidence = min(98, 50 + best_score * 2)
        return {
            "code": best_match["code"],
            "name": best_match["name"],
            "description": best_match["description"],
            "confidence": confidence,
            "found": True,
            "matches": best_matches[:3]
        }
    else:
        # Если ничего не нашли, возвращаем предположения
        suggestions = get_suggestions(search_text)
        return {
            "code": "????",
            "name": "Специфичная ниша",
            "confidence": 0,
            "found": False,
            "message": "Не удалось определить MCC-код для данной организации",
            "suggestions": suggestions[:3]
        }

def get_suggestions(text):
    """Возвращает подсказки на основе частичных совпадений"""
    suggestions = []
    # Здесь будут подсказки из вашей базы
    return suggestions[:3]


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

    building, error = search_building(address)
    if error:
        return jsonify({"success": False, "error": f"Ошибка поиска здания: {error}"})

    building_id = building.get('id')
    building_name = building.get('name', '')
    building_address = building.get('address_name', '')
    building_purpose = building.get('purpose_name', '')

    organization, error = find_organization(building_id, org_name)
    if error:
        return jsonify({
            "success": False,
            "error": f"Организация не найдена в здании",
            "building": {
                "name": building_name,
                "address": building_address,
                "purpose": building_purpose
            }
        })

    rubrics, services = get_rubrics_and_services(organization)
    mcc_result = predict_mcc_from_org(organization, building_name, building_address)

    return jsonify({
        "success": True,
        "building": {
            "name": building_name,
            "address": building_address,
            "purpose": building_purpose
        },
        "organization": {
            "name": organization.get('name', ''),
            "rubrics": rubrics,
            "services": services[:8]
        },
        "mcc": mcc_result
    })


@app.route('/send_feedback', methods=['POST'])
def send_feedback():
    """Обрабатывает отправку обратной связи"""
    try:
        # Получаем данные из формы
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        message = request.form.get('message', '').strip()
        files = request.files.getlist('attachments')

        # Валидация
        if not name:
            return jsonify({"success": False, "error": "Укажите ваше имя"})

        if not email or '@' not in email or '.' not in email:
            return jsonify({"success": False, "error": "Укажите корректный email"})

        if not message or len(message) < 10:
            return jsonify({"success": False, "error": "Сообщение должно содержать минимум 10 символов"})

        logger.info("=" * 50)
        logger.info("📨 НОВАЯ ОБРАТНАЯ СВЯЗЬ")
        logger.info(f"Имя: {name}")
        logger.info(f"Email: {email}")
        logger.info(f"Сообщение: {message[:50]}...")
        logger.info(f"Файлов: {len(files) if files else 0}")

        # Сохраняем файлы локально
        saved_files = []
        if files:
            for file in files:
                if file and file.filename:
                    # Пробуем загрузить на Яндекс.Диск
                    if YANDEX_DISK_TOKEN:
                        result = upload_to_yandex_disk(file, file.filename)
                    else:
                        # Если нет токена, сохраняем локально
                        result = save_file_locally(file)

                    if result['success']:
                        saved_files.append(result)

        # Сохраняем в файл
        save_feedback_to_file(name, email, message, saved_files)

        # Отправляем email
        email_success, email_message = send_feedback_email(name, email, message, saved_files)

        if email_success:
            response = {
                "success": True,
                "message": "Спасибо! Ваше сообщение отправлено на почту",
                "files": saved_files
            }
        else:
            response = {
                "success": True,
                "message": "Спасибо! Сообщение сохранено локально",
                "files": saved_files
            }

        logger.info(f"Ответ: {response}")
        logger.info("=" * 50)

        return jsonify(response)

    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        return jsonify({"success": False, "error": str(e)})


@app.route('/test_email', methods=['GET'])
def test_email():
    """Тест отправки письма"""
    logger.info("=" * 50)
    logger.info("🧪 ТЕСТОВАЯ ОТПРАВКА ПИСЬМА")

    success, message = send_feedback_email(
        name="Тестовый пользователь",
        email="test@example.com",
        message="Это тестовое сообщение для проверки работы почты"
    )

    result = {
        "success": success,
        "message": message,
        "time": datetime.datetime.now().isoformat(),
        "config": {
            "email": YANDEX_EMAIL,
            "recipient": FEEDBACK_EMAIL,
            "password_length": len(YANDEX_PASSWORD) if YANDEX_PASSWORD else 0
        }
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
    print("🚀 MCC AI Agent запущен!")
    print("📍 Адрес: http://localhost:5000")
    print("📁 Файлы сохраняются в папку: uploads/")
    print("📧 Почта настроена для:", YANDEX_EMAIL)
    print("🔑 Токен диска:", "есть" if YANDEX_DISK_TOKEN else "нет")
    print("=" * 60 + "\n")

    # Проверяем Яндекс.Диск при запуске
    if YANDEX_DISK_TOKEN:
        if ensure_yandex_folder():
            print("✅ Яндекс.Диск подключен")
        else:
            print("❌ Ошибка подключения к Яндекс.Диску")

    app.run(debug=True, port=5000)