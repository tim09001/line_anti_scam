import os
import sys
import re
import time
import asyncio
import sqlite3
import hashlib
import pytz
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from babel.dates import format_date

from pyrogram import Client, filters, enums, errors
from pyrogram.types import (
    Message, ChatPermissions, InlineKeyboardButton, 
    InlineKeyboardMarkup, ReplyKeyboardMarkup, 
    CallbackQuery, ReplyKeyboardRemove
)
from pyrogram.errors import ChatAdminRequired, UserAdminInvalid

# ========== КОНФИГУРАЦИЯ ==========
OWNER_ID = [6257985367, 7724765203]
API_ID = 28760873
API_HASH = 'b5e24c6a48beb5ee0273055c25ee1d22'
BOT_TOKEN = '8577200923:AAHLYtksJkBt4WzX_b35YxzIw1edeD5iEHw'
NUM_WORKERS = 16

# Создаем клиент сразу
app = Client(
    "line_anti_scam",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=NUM_WORKERS
)

# Изображения (оригинальные ссылки)
IMAGES = {
    'scam': 'https://ibb.co/fYgNLDyd',
    'scam2': 'https://ibb.co/r2KYKP9p',
    'user': 'https://ibb.co/wj33nJJ',
    'owner': 'https://ibb.co/V0ZmmCHZ',
    'stajer': 'https://ibb.co/FLxZW02S',
    'director': 'https://ibb.co/2QNV7n4',
    'president': 'https://ibb.co/zThMmnQ5',
    'admin': 'https://ibb.co/VWzz0V6c',
    'garant': 'https://ibb.co/TMvp6ST1',
    'trusted': 'http://ibb.co/SXYrqQ',
    'coder': 'https://ibb.co/wj33nJJ',
    'appeal': 'https://ibb.co/wj33nJJ'
}

# Страны для выбора
COUNTRIES = {
    "🇷🇺 Россия": "RU",
    "🇺🇦 Украина": "UA", 
    "🇧🇾 Беларусь": "BY",
    "🇰🇿 Казахстан": "KZ",
    "🇺🇸 США": "US",
    "🇩🇪 Германия": "DE",
    "🇬🇧 Великобритания": "GB",
    "🇹🇷 Турция": "TR",
    "🇨🇳 Китай": "CN",
    "🇯🇵 Япония": "JP",
    "🇰🇷 Корея": "KR",
    "🇮🇳 Индия": "IN",
    "🇧🇷 Бразилия": "BR",
    "🇨🇦 Канада": "CA",
    "🇦🇺 Австралия": "AU",
    "🇵🇱 Польша": "PL",
    "🇨🇿 Чехия": "CZ",
    "🇫🇷 Франция": "FR",
    "🇮🇹 Италия": "IT",
    "🇪🇸 Испания": "ES"
}

# Глобальные переменные
connection = None
cursor = None
callback_storage = {}
user_requests = defaultdict(list)
user_appeals = defaultdict(dict)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ========== БАЗА ДАННЫХ ==========
def init_db():
    """Инициализация базы данных"""
    global connection, cursor
    try:
        connection = sqlite3.connect('line_anti_scam.db', check_same_thread=False)
        cursor = connection.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admins(
                id INTEGER PRIMARY KEY NOT NULL,
                balance INTEGER DEFAULT 0,
                status INTEGER,
                kurator INTEGER DEFAULT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY NOT NULL,
                search INTEGER DEFAULT 0,
                leaked INTEGER DEFAULT 0,
                country TEXT DEFAULT 'Не указана'
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS casino_users(
                id INTEGER PRIMARY KEY NOT NULL,
                balance INTEGER DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS garants(
                id INTEGER PRIMARY KEY,
                channel TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trusteds(
                id INTEGER PRIMARY KEY,
                garant_id INTEGER NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scammers(
                id INTEGER PRIMARY KEY,
                proofs_link TEXT,
                reason TEXT,
                procent INTEGER
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_countries(
                user_id INTEGER PRIMARY KEY,
                country TEXT DEFAULT 'Не указана'
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS appeals(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                appeal_text TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                admin_id INTEGER DEFAULT NULL,
                resolved_at TIMESTAMP DEFAULT NULL
            )
        ''')
        
        connection.commit()
        logger.info("✅ База данных инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации базы данных: {e}")
        raise

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
def get_user_data(user_id):
    """Получить все данные о пользователе"""
    try:
        cursor.execute("SELECT * FROM admins WHERE id = ?", (user_id,))
        admin_data = cursor.fetchone()

        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user_data = cursor.fetchone()

        cursor.execute("SELECT * FROM garants WHERE id = ?", (user_id,))
        garant_data = cursor.fetchone()

        cursor.execute("SELECT * FROM trusteds WHERE id = ?", (user_id,))
        trusted_data = cursor.fetchone()

        cursor.execute("SELECT * FROM scammers WHERE id = ?", (user_id,))
        scammer_data = cursor.fetchone()

        cursor.execute("SELECT * FROM casino_users WHERE id = ?", (user_id,))
        casino_user_data = cursor.fetchone()
        
        cursor.execute("SELECT country FROM user_countries WHERE user_id = ?", (user_id,))
        country_data = cursor.fetchone()
        country = country_data[0] if country_data else 'Не указана'

        return admin_data, user_data, garant_data, trusted_data, scammer_data, country
    except Exception as e:
        logger.error(f"Ошибка получения данных пользователя {user_id}: {e}")
        return None, None, None, None, None, 'Не указана'

def check_status(user_id):
    """Проверить статус пользователя"""
    try:
        cursor.execute('SELECT status FROM admins WHERE id = ?', (user_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    except Exception as e:
        logger.error(f"Ошибка проверки статуса: {e}")
        return None

def check_owner(user_id):
    """Проверить, является ли пользователь владельцем"""
    return user_id in OWNER_ID

def format_date_russian(date):
    """Форматирование даты на русском"""
    try:
        return format_date(date, locale='ru_RU')
    except:
        return date.strftime("%d.%m.%Y")

def increment_search_count(user_id):
    """Увеличить счетчик проверок пользователя"""
    try:
        cursor.execute('INSERT OR IGNORE INTO users(id) VALUES (?)', (user_id,))
        cursor.execute('UPDATE users SET search = search + 1 WHERE id = ?', (user_id,))
        connection.commit()
    except Exception as e:
        logger.error(f"Ошибка увеличения счетчика проверок: {e}")

def increment_leaked_count(user_id):
    """Увеличить счетчик слитых скаммеров"""
    try:
        cursor.execute('INSERT OR IGNORE INTO users(id) VALUES (?)', (user_id,))
        cursor.execute('UPDATE users SET leaked = leaked + 1 WHERE id = ?', (user_id,))
        connection.commit()
    except Exception as e:
        logger.error(f"Ошибка увеличения счетчика слитых: {e}")

def set_user_country(user_id, country):
    """Установить страну пользователя"""
    try:
        cursor.execute('INSERT OR REPLACE INTO user_countries(user_id, country) VALUES (?, ?)', (user_id, country))
        connection.commit()
        return True
    except Exception as e:
        logger.error(f"Ошибка установки страны: {e}")
        return False

def create_appeal(user_id, appeal_text):
    """Создать апелляцию"""
    try:
        cursor.execute('''
            INSERT INTO appeals (user_id, appeal_text, status)
            VALUES (?, ?, 'pending')
        ''', (user_id, appeal_text))
        connection.commit()
        return cursor.lastrowid
    except Exception as e:
        logger.error(f"Ошибка создания апелляции: {e}")
        return None

def get_pending_appeals():
    """Получить все ожидающие апелляции"""
    try:
        cursor.execute('''
            SELECT * FROM appeals 
            WHERE status = 'pending'
            ORDER BY created_at ASC
        ''')
        return cursor.fetchall()
    except Exception as e:
        logger.error(f"Ошибка получения ожидающих апелляций: {e}")
        return []

def update_appeal_status(appeal_id, status, admin_id=None):
    """Обновить статус апелляции"""
    try:
        cursor.execute('''
            UPDATE appeals 
            SET status = ?, 
                admin_id = ?,
                resolved_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (status, admin_id, appeal_id))
        connection.commit()
        return True
    except Exception as e:
        logger.error(f"Ошибка обновления статуса апелляции: {e}")
        return False

def delete_from_scammers(user_id):
    """Удалить пользователя из базы скаммеров"""
    try:
        cursor.execute('DELETE FROM scammers WHERE id = ?', (user_id,))
        connection.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Ошибка удаления из базы скаммеров: {e}")
        return False

# ========== ТЕКСТОВЫЕ ШАБЛОНЫ ==========
def scam_text(first_name, leaked, search, prithc, proof, user_id, country):
    date = format_date_russian(datetime.now())
    time = datetime.now().strftime("%H:%M")
    text = f'''
⚖️ <b>Результат по поиску в <i>базе</i> об {first_name}:</b>

🛡️ <b>Репутация:</b> <b>❗ СКАМ</b>
<b>🌍 Страна:</b> {country}

<b>Пруфы:</b> <a href="{proof}">🖱️ Перейти</a>  
<b>Причина:</b> {prithc}

🆔 <b>Айди:</b> <code>{user_id}</code>

<b>Шанс скама человека:</b> <u>100%</u>

💰 <b>Скаммеров слито:</b> {leaked}  
📅 <b>Дата проверки:</b> <i>{time} - {date}</i>

🔎 <b>Проверено:</b> {search} раз

'''
    return text

def scam_text2(first_name, leaked, search, prithc, proof, user_id, country):
    date = format_date_russian(datetime.now())
    time = datetime.now().strftime("%H:%M")

    text = f'''
⚖️ <b>Результат по поиску в <i>базе</i> об {first_name}:</b>

🛡️ <b>Репутация:</b> <b>⚠️ Возможно скаммер</b>
<b>🌍 Страна:</b> {country}

<b>Пруфы:</b> <a href="{proof}">🖱️ Перейти</a>  
<b>Причина:</b> {prithc}

🆔 <b>Айди:</b> <code>{user_id}</code>

<b>Шанс скама человека:</b> <u>75%</u>

💰 <b>Скаммеров слито:</b> {leaked}  
📅 <b>Дата проверки:</b> <i>{time} - {date}</i>

🔎 <b>Проверено:</b> {search} раз
'''
    return text

def no_data_text(first_name, user_id, leaked, search, country, scam_chance="30%"):
    date = format_date_russian(datetime.now())
    time = datetime.now().strftime("%H:%M")

    text = f'''
⚖️ <b>Результат по поиску в <i>базе</i> об {first_name}:</b>

🛡️ <b>Репутация:</b> <b>Нет В Базе!</b>
<b>🌍 Страна:</b> {country}

🆔 <b>Айди:</b> <code>{user_id}</code>

<b>Шанс скама человека:</b> <u>{scam_chance}</u>

💰 <b>Помог слить скаммеров:</b> {leaked} раз  
📅 <b>Дата проверки:</b> <i>{time} - {date}</i>

🔎 <b>Проверено:</b> {search} раз
'''
    return text

async def stajer(first_name, user_id, leaked, search, curator, zayv, country):
    date = format_date_russian(datetime.now())
    time = datetime.now().strftime("%H:%M")

    curator_username = "Неизвестный куратор"

    try:
        curator_user = await app.get_users(curator)
        if curator_user and curator_user.username:
            curator_username = f"@{curator_user.username}"
        else:
            curator_username = f"ID: {curator}"
    except Exception as e:
        logger.error(f"Ошибка получения имени куратора: {e}")
        curator_username = f"ID: {curator}"

    text = f'''
⚖️ <b>Результат по поиску в <i>базе</i> об {first_name}:</b>

🛡️ <b>Репутация:</b> <b>Стажер базы!</b>
<b>🌍 Страна:</b> {country}

<b>Куратор:</b> {curator_username}

🔢 Заявок: {zayv if zayv else 'Нет заявок'}

🆔 <b>Айди:</b> <code>{user_id}</code>

<b>Шанс скама человека:</b> <u>3%</u>

💰 <b>Помог слить скаммеров:</b> {leaked if leaked else '0'} раз  
📅 <b>Дата проверки:</b> <i>{time} - {date}</i>

🔎 <b>Проверено:</b> {search if search else '0'} раз
'''
    return text

def garant(first_name, user_id, leaked, search, country):
    date = format_date_russian(datetime.now())
    time = datetime.now().strftime("%H:%M")

    text = f'''
⚖️ <b>Результат по поиску в <i>базе</i> об {first_name}:</b>

🛡️ <b>Репутация:</b> <b>Гарант Базы!</b>
<b>🌍 Страна:</b> {country}

<b>✅ Можно доверять, официальный гарант базы!</b>

🆔 <b>Айди:</b> <code>{user_id}</code>

💰 <b>Скаммеров слито:</b> {leaked} раз  
📅 <b>Дата проверки:</b> <i>{time} - {date}</i>

🔎 <b>Проверено:</b> {search} раз
'''
    return text

def admin2(first_name, user_id, leaked, search, zayv, country):
    date = format_date_russian(datetime.now())
    time = datetime.now().strftime("%H:%M")

    text = f'''
⚖️ <b>Результат по поиску в <i>базе</i> об {first_name}:</b>

🛡️ <b>Репутация:</b> <b>Администратор базы!</b>
<b>🌍 Страна:</b> {country}

🔢 Заявок: {zayv}

🆔 <b>Айди:</b> <code>{user_id}</code>

💰 <b>Помог слить скаммеров:</b> {leaked} раз  
📅 <b>Дата проверки:</b> <i>{time} - {date}</i>

🔎 <b>Проверено:</b> {search} раз
'''
    return text

def director(first_name, user_id, leaked, search, zayv, country):
    date = format_date_russian(datetime.now())
    time = datetime.now().strftime("%H:%M")

    text = f'''
⚖️ <b>Результат по поиску в <i>базе</i> об {first_name}:</b>

🛡️ <b>Репутация:</b> <b>Директор базы!</b>
<b>🌍 Страна:</b> {country}

🔢 Заявок: {zayv}

🆔 <b>Айди:</b> <code>{user_id}</code>

💰 <b>Помог слить скаммеров:</b> {leaked} раз  
📅 <b>Дата проверки:</b> <i>{time} - {date}</i>

🔎 <b>Проверено:</b> {search} раз
'''
    return text

def prezident(first_name, user_id, leaked, search, zayv, country):
    date = format_date_russian(datetime.now())
    time = datetime.now().strftime("%H:%M")

    text = f'''
⚖️ <b>Результат по поиску в <i>базе</i> об {first_name}:</b>

🛡️ <b>Репутация:</b> <b>Президент базы!</b>
<b>🌍 Страна:</b> {country}

🔢 Заявок: {zayv}

🆔 <b>Айди:</b> <code>{user_id}</code>

💰 <b>Помог слить скаммеров:</b> {leaked} раз  
📅 <b>Дата проверки:</b> <i>{time} - {date}</i>

🔎 <b>Проверено:</b> {search} раз
'''
    return text

def owner(first_name, user_id, leaked, search, zayv, country):
    date = format_date_russian(datetime.now())
    time = datetime.now().strftime("%H:%M")

    text = f'''
⚖️ <b>Результат по поиску в <i>базе</i> об {first_name}:</b>

🛡️ <b>Репутация:</b> <b>Создатель базы!</b>
<b>🌍 Страна:</b> {country}

🔢 Заявок: {zayv}

🆔 <b>Айди:</b> <code>{user_id}</code>

💰 <b>Помог слить скаммеров:</b> {leaked} раз  
📅 <b>Дата проверки:</b> <i>{time} - {date}</i>

🔎 <b>Проверено:</b> {search} раз
'''
    return text

def coder(first_name, user_id, leaked, search, zayv, country):
    date = format_date_russian(datetime.now())
    time = datetime.now().strftime("%H:%M")

    text = f'''
⚖️ <b>Результат по поиску в <i>базе</i> об {first_name}:</b>

🛡️ <b>Репутация:</b> <b>Кодер базы!</b>
<b>🌍 Страна:</b> {country}

🔢 Заявок: {zayv}

🆔 <b>Айди:</b> <code>{user_id}</code>

💰 <b>Помог слить скаммеров:</b> {leaked} раз  
📅 <b>Дата проверки:</b> <i>{time} - {date}</i>

🔎 <b>Проверено:</b> {search} раз
'''
    return text

def trusted_text(first_name, user_id, leaked, search, garant_username, country):
    date = format_date_russian(datetime.now())
    time = datetime.now().strftime("%H:%M")
    
    text = f'''
⚖️ <b>Результат по поиску в <i>базе</i> об {first_name}:</b>

🛡️ <b>Репутация:</b> <b>Проверен Гарантом!</b>
<b>🌍 Страна:</b> {country}

<b>✅ Проверен гарантом:</b> {garant_username}

🆔 <b>Айди:</b> <code>{user_id}</code>

<b>Шанс скама человека:</b> <u>10%</u>

💰 <b>Помог слить скаммеров:</b> {leaked} раз  
📅 <b>Дата проверки:</b> <i>{time} - {date}</i>

🔎 <b>Проверено:</b> {search} раз
'''
    return text

# ========== ОСНОВНОЙ ПРОЦЕСС ПРОВЕРКИ ==========
async def check_user_func(app: Client, message: Message, user_id):
    """Основная функция проверки пользователя"""
    if not user_id:
        return None, None

    try:
        user1 = await app.get_users(user_id)
        first_name = user1.first_name if user1 and user1.first_name else "Unknown"
    except Exception as e:
        logger.error(f"Ошибка получения данных пользователя {user_id}: {e}")
        user1 = None
        first_name = "Unknown"

    admin_data, user_data, garant_data, trusted_data, scammer_data, country = get_user_data(user_id)
    
    if user_data:
        search = user_data[1] if len(user_data) > 1 else 0
        leaked = user_data[2] if len(user_data) > 2 else 0
    else:
        search = 0
        leaked = 0

    increment_search_count(user_id)

    if garant_data:
        return IMAGES['garant'], garant(first_name, user_id, leaked, search, country)
    
    elif trusted_data:
        garant_id = trusted_data[1]
        try:
            garants = await app.get_users(garant_id)
            garant_username = f"@{garants.username}" if garants and garants.username else f"ID: {garant_id}"
        except:
            garant_username = f"ID: {garant_id}"
            
        text = trusted_text(first_name, user_id, leaked, search, garant_username, country)
        return IMAGES['trusted'], text
    
    elif admin_data:
        status = admin_data[2]
        balance = admin_data[1] if len(admin_data) > 1 else 0
        kurator = admin_data[3] if len(admin_data) > 3 else None
        
        if status == 5:
            return IMAGES['owner'], owner(first_name, user_id, leaked, search, balance, country)
        elif status == 4:
            return IMAGES['president'], prezident(first_name, user_id, leaked, search, balance, country)
        elif status == 3:
            return IMAGES['director'], director(first_name, user_id, leaked, search, balance, country)
        elif status == 2:
            if balance > 1000:
                return IMAGES['coder'], coder(first_name, user_id, leaked, search, balance, country)
            else:
                return IMAGES['admin'], admin2(first_name, user_id, leaked, search, balance, country)
        elif status == 1:
            return IMAGES['stajer'], await stajer(first_name, user_id, leaked, search, kurator, balance, country)
    
    elif scammer_data:
        status = scammer_data[3] if len(scammer_data) > 3 else 2
        reason = scammer_data[2] if len(scammer_data) > 2 else "Не указана"
        proof = scammer_data[1] if len(scammer_data) > 1 else "#"
        
        if status == 1:
            return IMAGES['scam2'], scam_text2(first_name, leaked, search, reason, proof, user_id, country)
        else:
            return IMAGES['scam'], scam_text(first_name, leaked, search, reason, proof, user_id, country)
    
    return IMAGES['user'], no_data_text(first_name, user_id, leaked, search, country)

# ========== КОМАНДЫ АДМИНИСТРАЦИИ ==========
def admin_func(user_id, status):
    """Назначить админа"""
    try:
        cursor.execute('SELECT status FROM admins WHERE id = ?', (user_id,))
        status2 = cursor.fetchone()

        if status2:
            cursor.execute('UPDATE admins SET status = ? WHERE id = ?', (status, user_id))
        else:
            cursor.execute('INSERT INTO admins(id, status) VALUES (?, ?)', (user_id, status))

        connection.commit()
        return True
    except Exception as e:
        logger.error(f"Ошибка назначения админа: {e}")
        connection.rollback()
        return False

def scam_func(user_id, proof, reason, status, added_by):
    """Добавить скаммера"""
    try:
        cursor.execute("INSERT OR REPLACE INTO scammers VALUES (?, ?, ?, ?)", 
                      (user_id, proof, reason, status))
        connection.commit()
        increment_leaked_count(added_by)
        return True
    except Exception as e:
        logger.error(f"Ошибка добавления скаммера: {e}")
        connection.rollback()
        return False

# ========== УЛУЧШЕННЫЙ ФИЛЬТР ДЛЯ КОМАНД ==========
def command_filter(commands):
    """Фильтр команд для работы в чатах и ЛС, включая команды без префикса"""
    async def func(flt, client, message):
        text = message.text or ""
        if not text:
            return False
        
        # Проверяем команды без префикса
        for cmd in flt.commands:
            # Просто команда (например, "чек")
            if text.lower().strip() == cmd.lower():
                return True
            # Команда с аргументами (например, "чек ми")
            if text.lower().startswith(cmd.lower() + " "):
                return True
        
        # Проверяем команды с префиксами
        for prefix in ['/', '!', '.', '-']:
            for cmd in flt.commands:
                # Проверяем команду с префиксом
                if text.startswith(f"{prefix}{cmd}") or text.startswith(f"{prefix}{cmd} "):
                    return True
                # Также проверяем команду с ботом (если есть упоминание)
                if f"@{client.me.username}" in text:
                    if f"{prefix}{cmd}@{client.me.username}" in text:
                        return True
        return False
    
    class SimpleFilter(filters.Filter):
        def __init__(self, commands):
            self.commands = commands
            
        async def __call__(self, client, message):
            return await func(self, client, message)
    
    return SimpleFilter(commands)

# ========== КОМАНДА CHECK (РАБОТАЕТ В ЧАТАХ И ЛС, ВКЛЮЧАЯ БЕЗ ПРЕФИКСА) ==========
@app.on_message(command_filter(['check', 'чек', 'проверить']))
async def check_user_command(app: Client, message: Message):
    """Проверка пользователя - работает в чатах и ЛС, включая без префикса"""
    try:
        user_id = message.from_user.id
        
        # Проверка лимитов
        status = check_status(user_id)
        if status is None or status < 1:
            MAX_REQUESTS = 10
            TIME_LIMIT = 30 * 60
            REQUEST_INTERVAL = 10
            
            current_time = time.time()
            if user_id not in user_requests:
                user_requests[user_id] = []
            
            user_requests[user_id] = [t for t in user_requests[user_id] if current_time - t < TIME_LIMIT]
            
            if len(user_requests[user_id]) >= MAX_REQUESTS:
                await message.reply('⚠️ Вы превысили лимит запросов. Пожалуйста, подождите 30 минут.')
                return
            
            if user_requests[user_id] and (current_time - user_requests[user_id][-1] < REQUEST_INTERVAL):
                await message.reply('⚠️ Пожалуйста, подождите 10 секунд перед следующим запросом.')
                return
            
            user_requests[user_id].append(current_time)
        
        # Определяем ID для проверки
        user_id_to_check = None
        
        if message.reply_to_message:
            user_id_to_check = message.reply_to_message.from_user.id
        else:
            text = message.text or ""
            
            # Определяем, какая команда использована
            command_used = None
            for cmd in ['check', 'чек', 'проверить']:
                if text.lower().startswith(cmd.lower()):
                    command_used = cmd
                    break
            
            # Проверяем, является ли это командой без префикса
            is_prefixless = False
            if command_used:
                # Если текст начинается с команды и нет префикса перед ней
                if not any(text.startswith(prefix + command_used) for prefix in ['/', '!', '.', '-']):
                    is_prefixless = True
            
            if is_prefixless:
                # Команда без префикса
                if text.lower().strip() == command_used.lower():
                    # Просто "чек" без аргументов - проверяем себя
                    user_id_to_check = message.from_user.id
                else:
                    # "чек ми" или "чек аргумент"
                    args = text[len(command_used):].strip()
                    if args:
                        first_arg = args.split()[0].strip()
                        if first_arg.lower() in ['ми', 'меня', 'me', 'myself']:
                            user_id_to_check = message.from_user.id
                        elif first_arg.isdigit():
                            user_id_to_check = int(first_arg)
                        elif first_arg.startswith('@'):
                            try:
                                user_obj = await app.get_users(first_arg)
                                user_id_to_check = user_obj.id
                            except:
                                await message.reply('⚠️ Пользователь не найден.')
                                return
                        else:
                            # Если аргумент не распознан, проверяем себя
                            user_id_to_check = message.from_user.id
                    else:
                        user_id_to_check = message.from_user.id
            else:
                # Команда с префиксом
                for prefix in ['/', '!', '.', '-']:
                    for cmd in ['check', 'чек', 'проверить']:
                        if text.startswith(f"{prefix}{cmd}"):
                            text = text[len(f"{prefix}{cmd}"):].strip()
                            break
                
                # Удаляем упоминание бота если есть
                if f"@{app.me.username}" in text:
                    text = text.replace(f"@{app.me.username}", "").strip()
                
                if text:
                    arg = text.split()[0].strip() if text else ""
                    if arg.lower() in ['ми', 'меня', 'me']:
                        user_id_to_check = message.from_user.id
                    elif arg.isdigit():
                        user_id_to_check = int(arg)
                    elif arg.startswith('@'):
                        try:
                            user_obj = await app.get_users(arg)
                            user_id_to_check = user_obj.id
                        except:
                            await message.reply('⚠️ Пользователь не найден.')
                            return
                    else:
                        # Если аргумент не распознан, проверяем себя
                        user_id_to_check = message.from_user.id
                else:
                    user_id_to_check = message.from_user.id
        
        if not user_id_to_check:
            await message.reply('⚠️ Не указан пользователь для проверки')
            return
        
        msg = await message.reply('🔎 Проверяется в базе данных...')
        photo, text_result = await check_user_func(app, message, user_id_to_check)
        
        if not text_result:
            await msg.edit_text('❌ Не удалось получить информацию о пользователе')
            return
        
        try:
            user = await app.get_users(user_id_to_check)
            profile_link = f'https://t.me/{user.username}' if user.username else f'tg://user?id={user_id_to_check}'
        except:
            profile_link = f'tg://user?id={user_id_to_check}'
        
        admin_data, user_data, garant_data, trusted_data, scammer_data, country = get_user_data(user_id_to_check)
        
        buttons = []
        buttons.append([InlineKeyboardButton("👥 Профиль", url=profile_link)])
        
        # В чатах показываем меньше кнопок
        if message.chat.type == enums.ChatType.PRIVATE:
            if user_id_to_check == message.from_user.id:
                buttons.append([InlineKeyboardButton("🌍 Изменить страну", callback_data="change_country")])
            
            if scammer_data and user_id_to_check == message.from_user.id:
                buttons.append([InlineKeyboardButton("📝 Подать апелляцию", 
                                                   callback_data=f"appeal_{user_id_to_check}")])
        
        keyboard = InlineKeyboardMarkup(buttons) if buttons else None
        
        try:
            if photo:
                await message.reply_photo(
                    photo=photo,
                    caption=text_result,
                    reply_markup=keyboard
                )
            else:
                await message.reply(
                    text_result,
                    reply_markup=keyboard
                )
        except Exception as e:
            logger.error(f"Ошибка отправки результата: {e}")
            await message.reply(text_result, reply_markup=keyboard)
        
        await msg.delete()
        
    except Exception as e:
        logger.error(f"Ошибка в check_user_command: {e}")
        await message.reply(f'❌ Ошибка при проверке: {str(e)}')

# ========== КОМАНДА START ==========
@app.on_message(command_filter(['start']))
async def start_command(app: Client, message: Message):
    """Команда старта"""
    try:
        keyboard = ReplyKeyboardMarkup(
            [
                ["Мой профиль 🆔", "Слить скаммера 😡", "Частые вопросы ❓"],
                ["Гаранты 🔥", "Волонтёры 🌴", "Статистика 📊"]
            ],
            resize_keyboard=True
        )
        await message.reply('🔎 Приветствую в скам базе Line Anti Scam. Выбери что ты хочешь сделать:', reply_markup=keyboard)
        
        user_id = message.from_user.id
        cursor.execute("INSERT OR IGNORE INTO users(id) VALUES (?)", (user_id,))
        cursor.execute("INSERT OR IGNORE INTO user_countries(user_id, country) VALUES (?, ?)", (user_id, 'Не указана'))
        connection.commit()
        
    except Exception as e:
        logger.error(f"Ошибка в start_command: {e}")

# ========== КОМАНДА SCAM (РАБОТАЕТ В ЧАТАХ И ЛС) ==========
@app.on_message(command_filter(['scam', 'скам']))
async def scam_command(app: Client, message: Message):
    """Команда добавления скаммера - работает в чатах и ЛС"""
    try:
        user_id = message.from_user.id
        status = check_status(user_id)
        
        if not status or status not in (2, 3, 4, 5):
            await message.reply('⚠️ У вас нет прав для использования этой команды')
            return
        
        # Определяем пользователя для добавления
        target_user_id = None
        target_user_name = "Неизвестный"
        proof_link = ""
        reason = ""
        
        # Проверяем, используется ли команда с ответом на сообщение
        if message.reply_to_message:
            # Работаем в чате с ответом на сообщение
            target_user_id = message.reply_to_message.from_user.id
            try:
                target_user = await app.get_users(target_user_id)
                target_user_name = target_user.first_name or f"ID: {target_user_id}"
            except:
                target_user_name = f"ID: {target_user_id}"
            
            text = message.text or ""
            # Удаляем префикс команды
            for prefix in ['/', '!', '.', '-']:
                if text.startswith(f"{prefix}scam"):
                    text = text[len(f"{prefix}scam"):].strip()
                    break
                elif text.startswith(f"{prefix}скам"):
                    text = text[len(f"{prefix}скам"):].strip()
                    break
            
            if text:
                # Парсим аргументы: ссылка причина
                args = text.split()
                if len(args) >= 2:
                    proof_link = args[0].strip()
                    reason = ' '.join(args[1:]).strip()
                elif len(args) == 1:
                    proof_link = args[0].strip()
                    reason = "Не указана"
                else:
                    # Если аргументов нет, запрашиваем их
                    await message.reply('⚠️ Укажите ссылку на пруфы и причину через пробел\nПример: /scam https://example.com "Мошенничество"')
                    return
            else:
                await message.reply('⚠️ Укажите ссылку на пруфы и причину через пробел\nПример: /scam https://example.com "Мошенничество"')
                return
        else:
            # Работаем в ЛС или команда с аргументами
            text = message.text or ""
            # Удаляем префикс команды
            for prefix in ['/', '!', '.', '-']:
                if text.startswith(f"{prefix}scam"):
                    text = text[len(f"{prefix}scam"):].strip()
                    break
                elif text.startswith(f"{prefix}скам"):
                    text = text[len(f"{prefix}скам"):].strip()
                    break
            
            if not text:
                await message.reply('⚠️ Используйте: /scam ID/@username ссылка_на_пруфы причина\n\nПримеры:\n/scam 123456789 https://t.me/c/123/456 "Обман при продаже"\n/scam @username https://ibb.co/example "Мошенничество"')
                return
            
            # Парсим аргументы
            args = text.split()
            if len(args) < 3:
                await message.reply('⚠️ Недостаточно аргументов. Формат: /scam ID/@username ссылка_на_пруфы причина\n\nПричина должна быть в кавычках если содержит пробелы.')
                return
            
            target_input = args[0].strip()
            proof_link = args[1].strip()
            reason = ' '.join(args[2:]).strip()
            
            # Определяем ID пользователя
            if target_input.isdigit():
                target_user_id = int(target_input)
            elif target_input.startswith('@'):
                try:
                    user_obj = await app.get_users(target_input)
                    target_user_id = user_obj.id
                except:
                    await message.reply('⚠️ Пользователь не найден')
                    return
            elif 't.me/' in target_input:
                username = target_input.split('t.me/')[-1].split('/')[-1].split('?')[0]
                try:
                    user_obj = await app.get_users(f"@{username}")
                    target_user_id = user_obj.id
                except:
                    await message.reply('⚠️ Пользователь не найден')
                    return
            else:
                await message.reply('⚠️ Неверный формат. Используйте ID, @username или ссылку')
                return
            
            try:
                target_user = await app.get_users(target_user_id)
                target_user_name = target_user.first_name or f"ID: {target_user_id}"
            except:
                target_user_name = f"ID: {target_user_id}"
        
        if not target_user_id:
            await message.reply('⚠️ Не удалось определить ID пользователя')
            return
        
        # Проверяем, не пытаемся ли добавить администратора
        target_status = check_status(target_user_id)
        if target_status and target_status >= 2:
            await message.reply('⚠️ Нельзя добавить администраторов базы в скам')
            return
        
        # Убираем кавычки если есть
        if reason.startswith('"') and reason.endswith('"'):
            reason = reason[1:-1]
        elif reason.startswith("'") and reason.endswith("'"):
            reason = reason[1:-1]
        
        # Проверяем, что ссылка не пустая (принимаем ЛЮБУЮ ссылку)
        if not proof_link:
            proof_link = "#"
        
        # Создаем клавиатуру для выбора типа скама
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("⚠️ Возможно скаммер", callback_data=f"scam_type_1_{target_user_id}"),
                InlineKeyboardButton("❗ СКАМ", callback_data=f"scam_type_2_{target_user_id}")
            ]
        ])
        
        # Сохраняем данные для callback
        user_appeals[user_id] = {
            'action': 'scam',
            'target_id': target_user_id,
            'proof': proof_link,
            'reason': reason
        }
        
        await message.reply(
            f'🎯 <b>Подтвердите добавление скаммера:</b>\n\n'
            f'👤 <b>Пользователь:</b> {target_user_name}\n'
            f'🆔 <b>ID:</b> <code>{target_user_id}</code>\n'
            f'📝 <b>Причина:</b> {reason}\n'
            f'🔗 <b>Пруфы:</b> {proof_link}\n\n'
            f'<b>Выберите тип скама:</b>\n'
            f'<b>⚠️ Возможно скаммер</b> - 75% шанс скама\n'
            f'<b>❗ СКАМ</b> - 100% шанс скама',
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Ошибка в scam_command: {e}")
        await message.reply(f'❌ Ошибка: {str(e)}')

# ========== КОМАНДА NOSCAM (УДАЛИТЬ ИЗ БАЗЫ СКАММЕРОВ) ==========
@app.on_message(command_filter(['noscam', 'unscam', 'унскам', 'удалитьскам']))
async def noscam_command(app: Client, message: Message):
    """Команда удаления пользователя из базы скаммеров"""
    try:
        user_id = message.from_user.id
        status = check_status(user_id)
        
        # Только админы могут удалять из базы
        if not status or status not in (2, 3, 4, 5):
            await message.reply('⚠️ У вас нет прав для использования этой команды')
            return
        
        # Определяем пользователя для удаления
        target_user_id = None
        target_user_name = "Неизвестный"
        
        # Проверяем, используется ли команда с ответом на сообщение
        if message.reply_to_message:
            # Работаем в чате с ответом на сообщение
            target_user_id = message.reply_to_message.from_user.id
            try:
                target_user = await app.get_users(target_user_id)
                target_user_name = target_user.first_name or f"ID: {target_user_id}"
            except:
                target_user_name = f"ID: {target_user_id}"
        else:
            # Работаем в ЛС или команда с аргументами
            text = message.text or ""
            # Удаляем префикс команды
            for prefix in ['/', '!', '.', '-']:
                if text.startswith(f"{prefix}noscam"):
                    text = text[len(f"{prefix}noscam"):].strip()
                    break
                elif text.startswith(f"{prefix}unscam"):
                    text = text[len(f"{prefix}unscam"):].strip()
                    break
                elif text.startswith(f"{prefix}унскам"):
                    text = text[len(f"{prefix}унскам"):].strip()
                    break
                elif text.startswith(f"{prefix}удалитьскам"):
                    text = text[len(f"{prefix}удалитьскам"):].strip()
                    break
            
            if not text:
                await message.reply('⚠️ Используйте: /noscam ID/@username\n\nПримеры:\n/noscam 123456789\n/noscam @username')
                return
            
            # Определяем ID пользователя
            target_input = text.split()[0].strip()
            
            if target_input.isdigit():
                target_user_id = int(target_input)
            elif target_input.startswith('@'):
                try:
                    user_obj = await app.get_users(target_input)
                    target_user_id = user_obj.id
                except:
                    await message.reply('⚠️ Пользователь не найден')
                    return
            elif 't.me/' in target_input:
                username = target_input.split('t.me/')[-1].split('/')[-1].split('?')[0]
                try:
                    user_obj = await app.get_users(f"@{username}")
                    target_user_id = user_obj.id
                except:
                    await message.reply('⚠️ Пользователь не найден')
                    return
            else:
                await message.reply('⚠️ Неверный формат. Используйте ID, @username или ссылку')
                return
            
            try:
                target_user = await app.get_users(target_user_id)
                target_user_name = target_user.first_name or f"ID: {target_user_id}"
            except:
                target_user_name = f"ID: {target_user_id}"
        
        if not target_user_id:
            await message.reply('⚠️ Не удалось определить ID пользователя')
            return
        
        # Проверяем, есть ли пользователь в базе скаммеров
        cursor.execute('SELECT * FROM scammers WHERE id = ?', (target_user_id,))
        scammer_data = cursor.fetchone()
        
        if not scammer_data:
            await message.reply(f'⚠️ Пользователь {target_user_name} не найден в базе скаммеров')
            return
        
        # Удаляем пользователя из базы скаммеров
        if delete_from_scammers(target_user_id):
            await message.reply(
                f'✅ <b>Пользователь удален из базы скаммеров!</b>\n\n'
                f'👤 <b>Пользователь:</b> {target_user_name}\n'
                f'🆔 <b>ID:</b> <code>{target_user_id}</code>\n'
                f'👮 <b>Администратор:</b> {message.from_user.mention}\n'
                f'📅 <b>Дата удаления:</b> {datetime.now().strftime("%d.%m.%Y %H:%M")}'
            )
        else:
            await message.reply('❌ Ошибка при удалении пользователя из базы')
        
    except Exception as e:
        logger.error(f"Ошибка в noscam_command: {e}")
        await message.reply(f'❌ Ошибка: {str(e)}')

# ========== КОМАНДА MUTE (РАБОТАЕТ В ЧАТАХ) ==========
@app.on_message(command_filter(['mute', 'мут']))
async def mute_command(app: Client, message: Message):
    """Команда мута"""
    try:
        if message.chat.type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            await message.reply('⚠️ Эта команда работает только в группах')
            return
        
        user_id = message.from_user.id
        status = check_status(user_id)
        
        if not status or status not in (2, 3, 4, 5):
            await message.reply('⚠️ Нет прав')
            return

        if message.reply_to_message:
            target_user = message.reply_to_message.from_user
            user_id_target = target_user.id
            
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("5 мин", callback_data=f"mute_5_{user_id_target}"),
                    InlineKeyboardButton("15 мин", callback_data=f"mute_15_{user_id_target}"),
                    InlineKeyboardButton("30 мин", callback_data=f"mute_30_{user_id_target}")
                ],
                [
                    InlineKeyboardButton("1 час", callback_data=f"mute_60_{user_id_target}"),
                    InlineKeyboardButton("3 часа", callback_data=f"mute_180_{user_id_target}"),
                    InlineKeyboardButton("12 часов", callback_data=f"mute_720_{user_id_target}")
                ],
                [
                    InlineKeyboardButton("1 день", callback_data=f"mute_1440_{user_id_target}"),
                    InlineKeyboardButton("3 дня", callback_data=f"mute_4320_{user_id_target}"),
                    InlineKeyboardButton("7 дней", callback_data=f"mute_10080_{user_id_target}")
                ],
                [
                    InlineKeyboardButton("Навсегда", callback_data=f"mute_permanent_{user_id_target}")
                ]
            ])
            
            await message.reply(
                f'⏰ Выберите время мута для пользователя {target_user.first_name}:',
                reply_markup=keyboard
            )
        else:
            await message.reply('⚠️ Ответьте на сообщение пользователя, которого хотите замутить')
            
    except Exception as e:
        logger.error(f"Ошибка в mute_command: {e}")
        await message.reply(f'❌ Ошибка: {str(e)}')

# ========== КОМАНДА СПАСИБО ==========
@app.on_message(command_filter(['спасибо', 'thanks', '+спасибо']))
async def thanks_command(app: Client, message: Message):
    """Команда спасибо"""
    try:
        if message.reply_to_message:
            target_user = message.reply_to_message.from_user
            target_id = target_user.id
            
            increment_leaked_count(target_id)
            
            cursor.execute("SELECT leaked FROM users WHERE id = ?", (target_id,))
            result = cursor.fetchone()
            current_leaked = result[0] if result else 0
            
            await message.reply(
                f'✅ Спасибо учтено!\n'
                f'👤 Пользователь: {target_user.first_name}\n'
                f'💰 Всего слито скаммеров: {current_leaked}\n\n'
                f'🙏 Благодарим за помощь в борьбе со скамом!'
            )
        else:
            await message.reply('⚠️ Ответьте на сообщение пользователя, которому хотите сказать спасибо')
            
    except Exception as e:
        logger.error(f"Ошибка в thanks_command: {e}")
        await message.reply(f'❌ Ошибка: {str(e)}')

# ========== КОМАНДА АПЕЛЛЯЦИЙ ==========
@app.on_message(command_filter(['appeals', 'апелляции']) & filters.private)
async def view_appeals_command(app: Client, message: Message):
    """Просмотр апелляций"""
    try:
        user_id = message.from_user.id
        status = check_status(user_id)
        
        if not status or status not in (2, 3, 4, 5):
            await message.reply('⚠️ У вас нет прав для просмотра апелляций')
            return
        
        appeals = get_pending_appeals()
        
        if not appeals:
            await message.reply("📋 <b>Список апелляций</b>\n\n✅ <i>Нет ожидающих апелляций</i>")
            return
        
        text = "📋 <b>Ожидающие апелляции:</b>\n\n"
        
        buttons = []
        for appeal in appeals:
            appeal_id, appeal_user_id, appeal_text, appeal_status, created_at, admin_id, resolved_at = appeal
            
            try:
                user = await app.get_users(appeal_user_id)
                user_name = user.first_name
            except:
                user_name = f"ID: {appeal_user_id}"
            
            short_text = appeal_text[:50] + "..." if len(appeal_text) > 50 else appeal_text
            
            text += f"🔹 <b>Апелляция #{appeal_id}</b>\n"
            text += f"👤 <b>Пользователь:</b> {user_name}\n"
            text += f"📅 <b>Дата:</b> {created_at}\n"
            text += f"📝 <b>Текст:</b> {short_text}\n\n"
            
            buttons.append([
                InlineKeyboardButton(
                    f"📝 Рассмотреть апелляцию #{appeal_id}",
                    callback_data=f"view_appeal_{appeal_id}"
                )
            ])
        
        keyboard = InlineKeyboardMarkup(buttons)
        await message.reply(text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Ошибка в view_appeals_command: {e}")
        await message.reply(f'❌ Ошибка: {str(e)}')

# ========== КОМАНДЫ АДМИНИСТРАЦИИ С ПРЕФИКСОМ + ==========
def plus_command_filter(commands):
    """Фильтр для команд с префиксом +"""
    async def func(flt, client, message):
        text = message.text or ""
        if not text:
            return False
        
        for cmd in flt.commands:
            if text.startswith(f"+{cmd}") or text.startswith(f"+{cmd} "):
                return True
        return False
    
    class PlusFilter(filters.Filter):
        def __init__(self, commands):
            self.commands = commands
            
        async def __call__(self, client, message):
            return await func(self, client, message)
    
    return PlusFilter(commands)

@app.on_message(plus_command_filter(["ВыдатьСоздателя", "ВыдатьПрезидента", "ВыдатьАдмина", "ВыдатьСтажера", "ВыдатьДиректора", "ВыдатьГаранта"]))
async def promote_handler(app, message: Message):
    """Выдача ролей"""
    try:
        user_id = message.from_user.id
        owner = check_owner(user_id)
        status = check_status(user_id)
        
        if not owner and status not in [4, 5]:
            await message.reply('❌ Нет прав')
            return

        text = message.text or ""
        command = text.split()[0]
        
        target_id = None
        if message.reply_to_message:
            target_id = message.reply_to_message.from_user.id
        else:
            args = text.split()
            if len(args) > 1:
                try:
                    target_user = await app.get_users(args[1])
                    target_id = target_user.id
                except:
                    await message.reply('❌ Неверный юзер')
                    return
            else:
                await message.reply('❌ Укажите пользователя')
                return
        
        if command == "+ВыдатьСоздателя":
            if owner:
                admin_func(target_id, 5)
                await message.reply('✅ Юзеру выдан создатель.')
            else:
                await message.reply('❌ Нет прав')

        elif command == "+ВыдатьПрезидента":
            if owner:
                admin_func(target_id, 4)
                await message.reply('✅ Юзеру выдан президент.')
            else:
                await message.reply('❌ Нет прав')
                
        elif command == "+ВыдатьДиректора":
            if owner or status in [4, 5]:
                admin_func(target_id, 3)
                await message.reply('✅ Юзеру выдан директор.')
            else:
                await message.reply('❌ Нет прав')
                
        elif command == "+ВыдатьАдмина":
            if owner or status in [4, 5]:
                admin_func(target_id, 2)
                await message.reply('✅ Юзеру выдан администратор.')
            else:
                await message.reply('❌ Нет прав')
                
        elif command == "+ВыдатьСтажера":
            if owner or status in [4, 5]:
                args = text.split()
                if len(args) >= 2:
                    if message.reply_to_message:
                        kurator = args[1]
                        try:
                            if kurator.isdigit():
                                cursor.execute('INSERT INTO admins(id, status, kurator) VALUES (?, ?, ?)', 
                                              (target_id, 1, int(kurator)))
                            elif kurator.startswith('@'):
                                kurator_user = await app.get_users(kurator)
                                if kurator_user:
                                    cursor.execute('INSERT INTO admins(id, status, kurator) VALUES (?, ?, ?)', 
                                                  (target_id, 1, kurator_user.id))
                                else:
                                    await message.reply('❌ Куратор не найден')
                                    return
                            connection.commit()
                            await message.reply('✅ Стажер с куратором выдан')
                        except Exception as e:
                            logger.error(f"Ошибка выдачи стажера: {e}")
                            await message.reply('❌ Ошибка выдачи стажера')
                    else:
                        await message.reply('🚫 Используйте ответом на сообщение: +ВыдатьСтажера @юзкуратора')
                else:
                    await message.reply('🚫 Формат: +ВыдатьСтажера @юзстажера @юзкуратора')
            else:
                await message.reply('❌ Нет прав')

        elif command == "+ВыдатьГаранта":
            if owner or status in [5]:
                try:
                    cursor.execute('INSERT OR IGNORE INTO garants(id) VALUES(?)', (target_id,))
                    connection.commit()
                    await message.reply('✅ Гарант успешно выдан.')
                except Exception as e:
                    logger.error(f"Ошибка выдачи гаранта: {e}")
                    await message.reply('❌ Ошибка выдачи гаранта')
            else:
                await message.reply('❌ Нет прав.')
                
    except Exception as e:
        logger.error(f"Ошибка в promote_handler: {e}")
        await message.reply(f'❌ Ошибка: {str(e)}')

# ========== ОБРАБОТКА КОЛБЭКОВ ==========
@app.on_callback_query(filters.regex(r'^scam_type_'))
async def scam_type_callback(app: Client, callback_query: CallbackQuery):
    """Обработка выбора типа скама"""
    try:
        data = callback_query.data
        parts = data.split('_')
        
        if len(parts) < 4:
            await callback_query.answer("❌ Ошибка данных", show_alert=True)
            return
        
        scam_type = int(parts[2])  # 1 = возможно скаммер, 2 = скамер
        target_user_id = int(parts[3])
        
        user_id = callback_query.from_user.id
        
        if user_id not in user_appeals:
            await callback_query.answer("❌ Сессия истекла", show_alert=True)
            return
        
        data = user_appeals[user_id]
        if data['action'] != 'scam' or 'target_id' not in data:
            await callback_query.answer("❌ Неверный шаг", show_alert=True)
            return
        
        target_id = data['target_id']
        reason = data['reason']
        proof = data['proof']
        
        if scam_func(target_id, proof, reason, scam_type, user_id):
            try:
                target_user = await app.get_users(target_id)
                target_name = target_user.first_name
            except:
                target_name = f"ID: {target_id}"
            
            scam_type_text = "⚠️ Возможно скаммер" if scam_type == 1 else "❗ СКАМ"
            
            await callback_query.edit_message_text(
                f"✅ <b>Пользователь добавлен в базу скаммеров!</b>\n\n"
                f"👤 <b>Пользователь:</b> {target_name}\n"
                f"🆔 <b>ID:</b> <code>{target_id}</code>\n"
                f"📝 <b>Причина:</b> {reason}\n"
                f"🔗 <b>Пруфы:</b> {proof}\n"
                f"🎯 <b>Тип:</b> {scam_type_text}\n"
                f"👮 <b>Администратор:</b> {callback_query.from_user.mention}"
            )
            
            del user_appeals[user_id]
        else:
            await callback_query.answer("❌ Ошибка при добавлении в базу скаммеров", show_alert=True)
        
        await callback_query.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в scam_type_callback: {e}")
        await callback_query.answer("❌ Произошла ошибка", show_alert=True)

@app.on_callback_query(filters.regex(r'^mute_'))
async def mute_time_callback(app: Client, callback_query: CallbackQuery):
    """Обработка мута"""
    try:
        data = callback_query.data
        parts = data.split('_')
        
        if len(parts) < 3:
            await callback_query.answer("❌ Ошибка данных", show_alert=True)
            return
        
        time_str = parts[1]
        target_user_id = int(parts[2])
        
        try:
            target_user = await app.get_users(target_user_id)
            target_name = target_user.first_name
        except:
            target_name = f"ID: {target_user_id}"
        
        chat_id = callback_query.message.chat.id
        
        admin_id = callback_query.from_user.id
        status = check_status(admin_id)
        
        if not status or status not in (2, 3, 4, 5):
            await callback_query.answer("⚠️ У вас нет прав", show_alert=True)
            return
        
        target_status = check_status(target_user_id)
        if target_status and target_status >= 2:
            await callback_query.answer("⚠️ Нельзя мутить администраторов", show_alert=True)
            return
        
        permissions = ChatPermissions(
            can_send_messages=False,
            can_send_media_messages=False,
            can_send_other_messages=False,
            can_add_web_page_previews=False
        )
        
        if time_str == "permanent":
            mute_until = datetime.now() + timedelta(days=31)
            time_text = "навсегда"
        else:
            minutes = int(time_str)
            mute_until = datetime.now() + timedelta(minutes=minutes)
            
            if minutes < 60:
                time_text = f"на {minutes} минут"
            elif minutes < 1440:
                hours = minutes // 60
                time_text = f"на {hours} час{'а' if 2 <= hours % 10 <= 4 and not 10 <= hours <= 20 else ''}"
            else:
                days = minutes // 1440
                time_text = f"на {days} день{'я' if 2 <= days % 10 <= 4 and not 10 <= days <= 20 else 'ей'}"
        
        try:
            await app.restrict_chat_member(chat_id, target_user_id, permissions, until_date=mute_until)
            
            await callback_query.edit_message_text(
                f'✅ <b>Пользователь замучен</b>\n\n'
                f'👤 <b>Пользователь:</b> {target_name}\n'
                f'⏰ <b>Время:</b> {time_text}\n'
                f'👮 <b>Администратор:</b> {callback_query.from_user.mention}\n\n'
                f'<i>Чат для оффтопа: @LineReports</i>'
            )
            
        except ChatAdminRequired:
            await callback_query.answer("❌ У бота нет прав администратора", show_alert=True)
        except Exception as e:
            logger.error(f"Ошибка мута: {e}")
            await callback_query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
            
    except Exception as e:
        logger.error(f"Ошибка в mute_time_callback: {e}")
        await callback_query.answer("❌ Произошла ошибка", show_alert=True)

@app.on_callback_query(filters.regex(r'^setcountry_'))
async def set_country_callback(app: Client, callback_query: CallbackQuery):
    """Установка страны"""
    try:
        country_name = callback_query.data.split('_', 1)[1].replace('_', ' ')
        
        user_id = callback_query.from_user.id
        set_user_country(user_id, country_name)
        
        await callback_query.answer(f"✅ Страна установлена: {country_name}", show_alert=True)
        
        await callback_query.edit_message_text(
            f"✅ Ваша страна установлена: {country_name}\n\n"
            f"Теперь вы можете проверить свой профиль командой /check или через меню."
        )
        
    except Exception as e:
        logger.error(f"Ошибка установки страны: {e}")
        await callback_query.answer("❌ Произошла ошибка", show_alert=True)

@app.on_callback_query(filters.regex(r'^cancel_country$'))
async def cancel_country_callback(app: Client, callback_query: CallbackQuery):
    """Отмена страны"""
    await callback_query.edit_message_text("❌ Выбор страны отменен.")

@app.on_callback_query(filters.regex(r'^change_country$'))
async def change_country_callback(app: Client, callback_query: CallbackQuery):
    """Смена страны"""
    try:
        buttons = []
        row = []
        countries_list = list(COUNTRIES.items())
        
        for i, (name, code) in enumerate(countries_list):
            row.append(InlineKeyboardButton(name, callback_data=f"setcountry_{name}"))
            if len(row) == 2 or i == len(countries_list) - 1:
                buttons.append(row)
                row = []
        
        buttons.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_country")])
        
        keyboard = InlineKeyboardMarkup(buttons)
        
        await callback_query.message.edit_text(
            "🌍 <b>Выберите вашу страну:</b>\n\n"
            "Это поможет другим пользователям узнать, откуда вы.\n"
            "Страна будет отображаться в вашем профиле под репутацией.",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Ошибка выбора страны: {e}")
        await callback_query.answer("❌ Произошла ошибка", show_alert=True)

@app.on_callback_query(filters.regex(r'^appeal_'))
async def appeal_callback(app: Client, callback_query: CallbackQuery):
    """Апелляция"""
    try:
        user_id = int(callback_query.data.split('_')[1])
        
        if callback_query.from_user.id != user_id:
            await callback_query.answer("❌ Это не ваша кнопка апелляции", show_alert=True)
            return
        
        cursor.execute('SELECT id FROM appeals WHERE user_id = ? AND status = "pending"', (user_id,))
        existing_appeal = cursor.fetchone()
        
        if existing_appeal:
            await callback_query.answer("❌ У вас уже есть ожидающая апелляция", show_alert=True)
            return
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Отменить апелляцию", callback_data="cancel_appeal")]
        ])
        
        await callback_query.message.reply(
            "Вы начали процесс апелляции\n\n"
            "Опишите подробно причины, по которой вы считаете, что вы не должны быть в базе скамеров. а также оставьте свои контактые данные @юз\n\n"
            "❌ Нажмите кнопку ниже для отмены процесса апеляции",
            reply_markup=keyboard
        )
        
        user_appeals[user_id] = {
            'action': 'appeal',
            'step': 'text'
        }
        
        await callback_query.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в appeal_callback: {e}")
        await callback_query.answer("❌ Произошла ошибка", show_alert=True)

@app.on_callback_query(filters.regex(r'^cancel_appeal$'))
async def cancel_appeal_callback(app: Client, callback_query: CallbackQuery):
    """Отмена апелляции"""
    try:
        user_id = callback_query.from_user.id
        
        if user_id in user_appeals and user_appeals[user_id]['action'] == 'appeal':
            del user_appeals[user_id]
        
        await callback_query.message.edit_text("❌ Процесс апелляции отменен.")
        await callback_query.answer("Апелляция отменена")
        
    except Exception as e:
        logger.error(f"Ошибка в cancel_appeal_callback: {e}")
        await callback_query.answer("❌ Произошла ошибка", show_alert=True)

@app.on_callback_query(filters.regex(r'^view_appeal_'))
async def view_appeal_callback(app: Client, callback_query: CallbackQuery):
    """Просмотр апелляции"""
    try:
        appeal_id = int(callback_query.data.split('_')[2])
        
        cursor.execute('SELECT * FROM appeals WHERE id = ?', (appeal_id,))
        appeal = cursor.fetchone()
        
        if not appeal:
            await callback_query.answer("❌ Апелляция не найдена", show_alert=True)
            return
        
        appeal_id, appeal_user_id, appeal_text, appeal_status, created_at, admin_id, resolved_at = appeal
        
        try:
            user = await app.get_users(appeal_user_id)
            user_name = user.first_name
            user_mention = user.mention if user.first_name else f"ID: {appeal_user_id}"
        except:
            user_name = f"ID: {appeal_user_id}"
            user_mention = f"ID: {appeal_user_id}"
        
        admin_data, user_data, garant_data, trusted_data, scammer_data, country = get_user_data(appeal_user_id)
        
        text = f"📋 <b>Апелляция #{appeal_id}</b>\n\n"
        text += f"👤 <b>Пользователь:</b> {user_mention}\n"
        text += f"🆔 <b>ID:</b> <code>{appeal_user_id}</code>\n"
        
        if scammer_data:
            reason = scammer_data[2] if len(scammer_data) > 2 else "Не указана"
            proof = scammer_data[1] if len(scammer_data) > 1 else "#"
            text += f"⚠️ <b>Причина скама:</b> {reason}\n"
            text += f"🔗 <b>Пруфы:</b> <a href='{proof}'>Ссылка</a>\n"
        
        text += f"📅 <b>Дата подачи:</b> {created_at}\n"
        text += f"📝 <b>Текст апелляции:</b>\n<code>{appeal_text}</code>\n\n"
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_appeal_{appeal_id}"),
                InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_appeal_{appeal_id}")
            ],
            [
                InlineKeyboardButton("👤 Проверить профиль", callback_data=f"check_{appeal_user_id}")
            ],
            [
                InlineKeyboardButton("🔙 Назад к списку", callback_data="back_to_appeals")
            ]
        ])
        
        await callback_query.edit_message_text(text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Ошибка в view_appeal_callback: {e}")
        await callback_query.answer("❌ Произошла ошибка", show_alert=True)

@app.on_callback_query(filters.regex(r'^(approve|reject)_appeal_'))
async def handle_appeal_decision(app: Client, callback_query: CallbackQuery):
    """Решение по апелляции"""
    try:
        action = callback_query.data.split('_')[0]
        appeal_id = int(callback_query.data.split('_')[2])
        
        cursor.execute('SELECT * FROM appeals WHERE id = ?', (appeal_id,))
        appeal = cursor.fetchone()
        
        if not appeal:
            await callback_query.answer("❌ Апелляция не найдена", show_alert=True)
            return
        
        appeal_id, appeal_user_id, appeal_text, appeal_status, created_at, admin_id, resolved_at = appeal
        
        if action == "approve":
            cursor.execute('DELETE FROM scammers WHERE id = ?', (appeal_user_id,))
            new_status = "approved"
            status_text = "✅ Одобрена"
            user_message = "✅ Ваша апелляция одобрена! Вы удалены из базы скаммеров."
        else:
            new_status = "rejected"
            status_text = "❌ Отклонена"
            user_message = "❌ Ваша апелляция отклонена. Вы остаетесь в базе скаммеров."
        
        update_appeal_status(appeal_id, new_status, callback_query.from_user.id)
        
        try:
            await app.send_message(
                appeal_user_id,
                f"📋 <b>Решение по вашей апелляции</b>\n\n"
                f"{user_message}\n\n"
                f"📅 <b>Дата решения:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
                f"👮 <b>Администратор:</b> {callback_query.from_user.mention}"
            )
        except:
            pass
        
        await callback_query.edit_message_text(
            f"📋 <b>Апелляция #{appeal_id}</b>\n\n"
            f"👮 <b>Решение принято:</b> {status_text}\n"
            f"👤 <b>Пользователь:</b> ID: {appeal_user_id}\n"
            f"📅 <b>Дата решения:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
            f"👮 <b>Администратор:</b> {callback_query.from_user.mention}"
        )
        
        await callback_query.answer(f"Апелляция {status_text}", show_alert=True)
        
    except Exception as e:
        logger.error(f"Ошибка в handle_appeal_decision: {e}")
        await callback_query.answer("❌ Произошла ошибка", show_alert=True)

@app.on_callback_query(filters.regex(r'^back_to_appeals$'))
async def back_to_appeals_callback(app: Client, callback_query: CallbackQuery):
    """Назад к апелляциям"""
    try:
        await view_appeals_command(app, callback_query.message)
    except:
        await callback_query.answer("❌ Ошибка возврата", show_alert=True)

@app.on_callback_query(filters.regex(r'^check_'))
async def check_callback(app: Client, callback_query: CallbackQuery):
    """Проверка по кнопке"""
    try:
        user_id_to_check = int(callback_query.data.split('_')[1])
        
        photo, text = await check_user_func(app, callback_query.message, user_id_to_check)
        
        if text:
            try:
                user = await app.get_users(user_id_to_check)
                profile_link = f'https://t.me/{user.username}' if user.username else f'tg://user?id={user_id_to_check}'
            except:
                profile_link = f'tg://user?id={user_id_to_check}'
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("👥 Профиль", url=profile_link)]
            ])
            
            if photo:
                await callback_query.message.reply_photo(photo, caption=text, reply_markup=keyboard)
            else:
                await callback_query.message.reply(text, reply_markup=keyboard)
            
            await callback_query.answer("✅ Информация отправлена")
        else:
            await callback_query.answer("❌ Не удалось получить информацию", show_alert=True)
            
    except Exception as e:
        logger.error(f"Ошибка в check_callback: {e}")
        await callback_query.answer("❌ Произошла ошибка", show_alert=True)

# ========== ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ ==========
@app.on_message(filters.private & filters.text)
async def handle_text_messages(app: Client, message: Message):
    """Обработка текстовых сообщений в ЛС"""
    try:
        text = message.text or ""
        
        # Пропускаем команды (они обрабатываются отдельно)
        if text.startswith('/') or text.startswith('!') or text.startswith('.') or text.startswith('-') or text.startswith('+'):
            return
        
        user_id = message.from_user.id
        
        # Обработка апелляций
        if user_id in user_appeals:
            data = user_appeals[user_id]
            
            if data['action'] == 'appeal' and data['step'] == 'text':
                appeal_id = create_appeal(user_id, text)
                
                if appeal_id:
                    del user_appeals[user_id]
                    
                    await message.reply(
                        f"✅ <b>Апелляция подана успешно!</b>\n\n"
                        f"📋 <b>Номер апелляции:</b> #{appeal_id}\n"
                        f"📝 <b>Ваш текст:</b>\n<code>{text[:100]}...</code>\n\n"
                        f"ℹ️ Администраторы рассмотрят вашу апелляцию в ближайшее время.\n"
                        f"ℹ️ Вы получите уведомление о результате."
                    )
                    
                    try:
                        cursor.execute('SELECT id FROM admins WHERE status >= 2')
                        admins = cursor.fetchall()
                        
                        for admin in admins:
                            try:
                                await app.send_message(
                                    admin[0],
                                    f"📣 <b>Новая апелляция!</b>\n\n"
                                    f"📋 <b>Апелляция #{appeal_id}</b>\n"
                                    f"👤 <b>Пользователь:</b> ID: {user_id}\n"
                                    f"📝 <b>Текст:</b> {text[:100]}...\n\n"
                                    f"ℹ️ Используйте /appeals для просмотра"
                                )
                            except:
                                continue
                    except:
                        pass
                    
                else:
                    await message.reply('❌ Ошибка при создании апелляции')
            
            return
        
        # Обработка меню
        if text == "Мой профиль 🆔":
            user_id = message.from_user.id
            
            cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
            if cursor.fetchone() is None:
                cursor.execute("INSERT INTO users(id) VALUES (?)", (user_id,))
                cursor.execute("INSERT OR IGNORE INTO user_countries(user_id, country) VALUES (?, ?)", (user_id, 'Не указана'))
                connection.commit()
            
            msg = await message.reply('🔎 Проверяется в базе данных...')
            
            photo, profile_text = await check_user_func(app, message, user_id)
            
            if profile_text:
                buttons = []
                buttons.append([InlineKeyboardButton("🌍 Изменить страну", callback_data="change_country")])
                
                admin_data, user_data, garant_data, trusted_data, scammer_data, country = get_user_data(user_id)
                if scammer_data:
                    buttons.append([InlineKeyboardButton("📝 Подать апелляцию", 
                                                       callback_data=f"appeal_{user_id}")])
                
                keyboard = InlineKeyboardMarkup(buttons) if buttons else None
                
                if photo:
                    await message.reply_photo(photo, caption=profile_text, reply_markup=keyboard)
                else:
                    await message.reply(profile_text, reply_markup=keyboard)
            
            await msg.delete()
            
        elif text == "Слить скаммера 😡":
            button = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        text="✅ Предложка",
                        url='https://t.me/LineReports'
                    )
                ]
            ])
            await message.reply("❗ Чтобы слить скамера переходите в предложку", reply_markup=button)

        elif text == "Частые вопросы ❓":
            await message.reply("📚 Частые вопросы:\n\n1. Как проверить пользователя?\n- Используйте команду /чек или кнопку 'Мой профиль'\n\n2. Как стать гарантом?\n- Обратитесь к администраторам базы\n\n3. Как добавить скаммера?\n- Используйте команду /scam")

        elif text == "Гаранты 🔥":
            cursor.execute('SELECT id FROM garants')
            garants = cursor.fetchall()
            if not garants:
                await message.reply("❌ Гарантов на данный момент нет")
                return

            buttons = []
            for garant in garants:
                try:
                    user = await app.get_users(garant[0])
                    first_name = user.first_name
                    username = getattr(user, 'username', 'Нету!')

                    buttons.append(
                        [InlineKeyboardButton(text=f"✅ {first_name} : @{username}",
                                              callback_data=f"check_{user.id}")]
                    )
                except:
                    continue

            reply_markup = InlineKeyboardMarkup(buttons)
            await message.reply(f"✅ Все гаранты базы: ({len(garants)}):", reply_markup=reply_markup)

        elif text == "Волонтёры 🌴":
            cursor.execute('SELECT id FROM admins')
            admins = cursor.fetchall()

            if not admins:
                await message.reply("❌ Волонтеров на данный момент нет")
                return

            buttons = []
            for admin_user in admins:
                try:
                    user = await app.get_users(admin_user[0])
                    first_name = user.first_name
                    username = getattr(user, 'username', 'Нету!')

                    buttons.append(
                        [InlineKeyboardButton(text=f"🌴 {first_name} : @{username}",
                                              callback_data=f"check_{user.id}")]
                    )
                except:
                    continue

            if len(buttons) > 100:
                await message.reply("Слишком много волонтёров для отображения.")
                return

            reply_markup = InlineKeyboardMarkup(buttons)
            await message.reply(f"🌴 Все волонтеры базы: ({len(admins)})", reply_markup=reply_markup)

        elif text == "Статистика 📊":
            cursor.execute('SELECT id FROM scammers')
            scammers = cursor.fetchall()
            scams_count = len(scammers)

            cursor.execute('SELECT id FROM users')
            users = cursor.fetchall()
            users_count = len(users)
            
            cursor.execute('SELECT id FROM admins')
            admins_count = len(cursor.fetchall())
            
            cursor.execute('SELECT id FROM garants')
            garants_count = len(cursor.fetchall())
            
            await message.reply(f'''
📊 Статистика бота:
🔎 Слито скаммеров: {scams_count}  
👥 Пользователей бота: {users_count}
🌴 Волонтёров: {admins_count}
🔥 Гарантов: {garants_count}
''')

    except Exception as e:
        logger.error(f"Ошибка в handle_text_messages: {e}")

# ========== ЗАПУСК БОТА ==========
if __name__ == "__main__":
    try:
        print("=" * 50)
        print("🔄 Инициализация Line Anti Scam Database...")
        print("=" * 50)
        
        init_db()
        
        print("✅ База данных инициализирована")
        print("🤖 Запуск бота...")
        print("=" * 50)
        
        app.run()
        
    except KeyboardInterrupt:
        print("\n\n🛑 Остановка бота по запросу пользователя...")
    except Exception as e:
        logger.error(f"Критическая ошибка запуска: {e}")
        print(f"❌ Критическая ошибка: {e}")
    finally:
        if connection:
            connection.close()
            print("🔒 Соединение с БД закрыто")
        print("👋 Бот остановлен")
