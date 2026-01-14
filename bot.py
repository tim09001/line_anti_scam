import os
from pyrogram.types import Message
from pyrogram import Client

from datetime import datetime, timedelta
from babel.dates import format_date

from pyrogram import Client, types, filters, errors, enums
from pyrogram.types import Message, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent, CallbackQuery, ReplyKeyboardMarkup, InputMediaPhoto
from pyrogram.filters import command, text, regex
from pyrogram.errors import UserAdminInvalid, ChatAdminRequired

import time
from collections import defaultdict
import asyncio

import sqlite3
import pytz
import re

from datetime import timedelta, datetime

import hashlib

import logging

OWNER_ID = [6257985367, 7724765203]

API_ID = 28760873
API_HASH = 'b5e24c6a48beb5ee0273055c25ee1d22'

NUM_WORKERS = 16

app = Client("line_anti_scam", bot_token='8577200923:AAEbAk2s4NR5SGVuY58hJ1RUQU8N_L4NO04', api_id=API_ID, api_hash=API_HASH, workers=NUM_WORKERS)


image_scam = 'https://ibb.co/fYgNLDyd'
image_scam2 = 'http://ibb.co/SXYrqQh'
image_user = 'https://ibb.co/wj33nJJ'
image_owner = 'https://ibb.co/V0ZmmCHZ'
image_stajer = 'https://ibb.co/FLxZW02S'
image_director = 'https://ibb.co/2QNV7n4'
image_president = 'https://ibb.co/zThMmnQ5'
image_admin = 'http://ibb.co/bWCYL4d'
image_garant = 'https://ibb.co/TMvp6ST1'
image_trusted = 'http://ibb.co/SXYrqQ'

# Глобальное соединение с базой данных
connection = None
cursor = None

def init_db():
    global connection, cursor
    try:
        connection = sqlite3.connect('line_anti_scam.db', check_same_thread=False)
        cursor = connection.cursor()
        
        # Создаем таблицы если их нет
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admins(
                id INTEGER PRIMARY KEY NOT NULL,
                balance INTEGER DEFAULT 0,
                status INTEGER,
                kurator INTEGER DEFAULT NULL
            )
        ''')
        
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY NOT NULL,
                search INTEGER DEFAULT 0,
                leaked INTEGER DEFAULT 0
            );
            
            CREATE TABLE IF NOT EXISTS casino_users(
                id INTEGER PRIMARY KEY NOT NULL,
                balance INTEGER DEFAULT 0
            );
            
            CREATE TABLE IF NOT EXISTS garants(
                id INTEGER PRIMARY KEY,
                channel TEXT
            );
            
            CREATE TABLE IF NOT EXISTS trusteds(
                id INTEGER PRIMARY KEY,
                garant_id INTEGER NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS scammers(
                id INTEGER PRIMARY KEY,
                proofs_link TEXT,
                reason TEXT,
                procent INTEGER
            )
        """)
        
        connection.commit()
        logging.info("База данных инициализирована")
    except Exception as e:
        logging.error(f"Ошибка инициализации базы данных: {e}")
        raise

def get_user_data(id):
    try:
        cursor.execute("SELECT * FROM admins WHERE id = ?", (id,))
        admin_data = cursor.fetchone()

        cursor.execute("SELECT * FROM users WHERE id = ?", (id,))
        user_data = cursor.fetchone()

        cursor.execute("SELECT * FROM garants WHERE id = ?", (id,))
        garant_data = cursor.fetchone()

        cursor.execute("SELECT * FROM trusteds WHERE id = ?", (id,))
        trusted_data = cursor.fetchone()

        cursor.execute("SELECT * FROM scammers WHERE id = ?", (id,))
        scammer_data = cursor.fetchone()

        cursor.execute("SELECT * FROM casino_users WHERE id = ?", (id,))
        casino_user_data = cursor.fetchone()

        return admin_data, user_data, garant_data, trusted_data, scammer_data
    except Exception as e:
        logging.error(f"Ошибка получения данных пользователя {id}: {e}")
        return None, None, None, None, None


def check_curator(id, id2):
    try:
        cursor.execute('SELECT kurator FROM admins WHERE id = ?', (id,))
        result = cursor.fetchone()
        if result and id2 == result[0]:
            return id2
        else:
            return None
    except Exception as e:
        logging.error(f"Ошибка проверки куратора: {e}")
        return None


def admin(id, status):
    try:
        cursor.execute('SELECT status FROM admins WHERE id = ?', (id,))
        status2 = cursor.fetchone()

        if status2:
            cursor.execute('UPDATE admins SET status = ? WHERE id = ?', (status, id))
        else:
            cursor.execute('INSERT INTO admins(id, status) VALUES (?, ?)', (id, status))

        connection.commit()
    except Exception as e:
        logging.error(f"Ошибка назначения админа: {e}")
        connection.rollback()


def format_date_russian(date):
    try:
        return format_date(date, locale='ru_RU')
    except:
        return date.strftime("%d.%m.%Y")


def scam_text(first_name, leaked, search, prithc, proof, user_id):
    date = format_date_russian(datetime.now())
    time = datetime.now().strftime("%H:%M")
    text = f'''
⚖️ <b>Результат по поиску в <i>базе</i> об {first_name}:</b>

🛡️ <b>Репутация:</b> <b>❗ СКАМ</b>

<b>Пруфы:</b> <a href="{proof}">🖱️ Перейти</a>  
<b>Причина:</b> {prithc}

🆔 <b>Айди:</b> <code>{user_id}</code>

<b>Шанс скама человека:</b> <u>100%</u>

💰 <b>Скаммеров слито:</b> {leaked}  
📅 <b>Дата проверки:</b> <i>{time} - {date}</i>

🔎 <b>Проверено:</b> {search} раз

'''
    return text


def scam_text2(first_name, leaked, search, prithc, proof, user_id):
    date = format_date_russian(datetime.now())
    time = datetime.now().strftime("%H:%M")

    text = f'''
⚖️ <b>Результат по поиску в <i>базе</i> об {first_name}:</b>

🛡️ <b>Репутация:</b> <b>⚠️ Возможно скаммер</b>

<b>Пруфы:</b> <a href="{proof}">🖱️ Перейти</a>  
<b>Причина:</b> {prithc}

🆔 <b>Айди:</b> <code>{user_id}</code>

<b>Шанс скама человека:</b> <u>75%</u>

💰 <b>Скаммеров слито:</b> {leaked}  
📅 <b>Дата проверки:</b> <i>{time} - {date}</i>

🔎 <b>Проверено:</b> {search} раз
'''
    return text


def no_data_text(first_name, user_id, leaked, search, scam_chance="30%"):
    date = format_date_russian(datetime.now())
    time = datetime.now().strftime("%H:%M")

    text = f'''
⚖️ <b>Результат по поиску в <i>базе</i> об {first_name}:</b>

🛡️ <b>Репутация:</b> <b>Нет В Базе!</b>

🆔 <b>Айди:</b> <code>{user_id}</code>

<b>Шанс скама человека:</b> <u>{scam_chance}</u>

💰 <b>Помог слить скаммеров:</b> {leaked} раз  
📅 <b>Дата проверки:</b> <i>{time} - {date}</i>

🔎 <b>Проверено:</b> {search} раз
'''
    return text


async def stajer(first_name, user_id, leaked, search, curator, zayv):
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
        logging.error(f"Ошибка получения имени куратора: {e}")
        curator_username = f"ID: {curator}"

    text = f'''
⚖️ <b>Результат по поиску в <i>базе</i> об {first_name}:</b>

🛡️ <b>Репутация:</b> <b>Стажер базы!</b>

<b>Куратор:</b> {curator_username}

🔢 Заявок: {zayv if zayv else 'Нет заявок'}

🆔 <b>Айди:</b> <code>{user_id}</code>

<b>Шанс скама человека:</b> <u>3%</u>

💰 <b>Помог слить скаммеров:</b> {leaked if leaked else '0'} раз  
📅 <b>Дата проверки:</b> <i>{time} - {date}</i>

🔎 <b>Проверено:</b> {search if search else '0'} раз
'''
    return text


def garant(first_name, user_id, leaked, search):
    date = format_date_russian(datetime.now())
    time = datetime.now().strftime("%H:%M")

    text = f'''
⚖️ <b>Результат по поиску в <i>базе</i> об {first_name}:</b>

🛡️ <b>Репутация:</b> <b>Гарант Базы!</b>

<b>✅ Можно доверять, официальный гарант базы!</b>

🆔 <b>Айди:</b> <code>{user_id}</code>

💰 <b>Скаммеров слито:</b> {leaked} раз  
📅 <b>Дата проверки:</b> <i>{time} - {date}</i>

🔎 <b>Проверено:</b> {search} раз
'''
    return text


def trusted(first_name, guarantee_username, user_id, leaked, search, scam_chance):
    date = format_date_russian(datetime.now())
    time = datetime.now().strftime("%H:%M")

    guarantee_text = f"<b>✅ Проверен гарантом:</b> <a href='https://t.me/{guarantee_username}'>@{guarantee_username}</a>\n" if guarantee_username else ""

    text = f'''
⚖️ <b>Результат по поиску в <i>базе</i> об {first_name}:</b>

🛡️ <b>Репутация:</b> <b>Проверен Гарантом!</b>

{guarantee_text}

🆔 <b>Айди:</b> <code>{user_id}</code>

<b>Шанс скама человека:</b> <u>{scam_chance}</u>

💰 <b>Помог слить скаммеров:</b> {leaked} раз  
📅 <b>Дата проверки:</b> <i>{time} - {date}</i>

🔎 <b>Проверено:</b> {search} раз
'''
    return text


def admin2(first_name, user_id, leaked, search, zayv):
    date = format_date_russian(datetime.now())
    time = datetime.now().strftime("%H:%M")

    text = f'''
⚖️ <b>Результат по поиску в <i>базе</i> об {first_name}:</b>

🛡️ <b>Репутация:</b> <b>Администратор базы!</b>

🔢 Заявок: {zayv}

🆔 <b>Айди:</b> <code>{user_id}</code>

💰 <b>Помог слить скаммеров:</b> {leaked} раз  
📅 <b>Дата проверки:</b> <i>{time} - {date}</i>

🔎 <b>Проверено:</b> {search} раз
'''
    return text


def director(first_name, user_id, leaked, search, zayv):
    date = format_date_russian(datetime.now())
    time = datetime.now().strftime("%H:%M")

    text = f'''
⚖️ <b>Результат по поиску в <i>базе</i> об {first_name}:</b>

🛡️ <b>Репутация:</b> <b>Директор базы!</b>

🔢 Заявок: {zayv}

🆔 <b>Айди:</b> <code>{user_id}</code>

💰 <b>Помог слить скаммеров:</b> {leaked} раз  
📅 <b>Дата проверки:</b> <i>{time} - {date}</i>

🔎 <b>Проверено:</b> {search} раз
'''
    return text


def prezident(first_name, user_id, leaked, search, zayv):
    date = format_date_russian(datetime.now())
    time = datetime.now().strftime("%H:%M")

    text = f'''
⚖️ <b>Результат по поиску в <i>базе</i> об {first_name}:</b>

🛡️ <b>Репутация:</b> <b>Президент базы!</b>

🔢 Заявок: {zayv}

🆔 <b>Айди:</b> <code>{user_id}</code>

💰 <b>Помог слить скаммеров:</b> {leaked} раз  
📅 <b>Дата проверки:</b> <i>{time} - {date}</i>

🔎 <b>Проверено:</b> {search} раз
'''
    return text


def owner(first_name, user_id, leaked, search, zayv):
    date = format_date_russian(datetime.now())
    time = datetime.now().strftime("%H:%M")

    text = f'''
⚖️ <b>Результат по поиску в <i>базе</i> об {first_name}:</b>

🛡️ <b>Репутация:</b> <b>Создатель базы!</b>

🔢 Заявок: {zayv}

🆔 <b>Айди:</b> <code>{user_id}</code>

💰 <b>Помог слить скаммеров:</b> {leaked} раз  
📅 <b>Дата проверки:</b> <i>{time} - {date}</i>

🔎 <b>Проверено:</b> {search} раз
'''
    return text


def get_user_from_db(user_id):
    try:
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        return cursor.fetchone()
    except Exception as e:
        logging.error(f"Ошибка получения пользователя из БД: {e}")
        return None


def insert_user_into_db(user_id):
    try:
        cursor.execute('INSERT OR IGNORE INTO users(id) VALUES (?)', (user_id,))
        connection.commit()
    except Exception as e:
        logging.error(f"Ошибка добавления пользователя в БД: {e}")
        connection.rollback()


async def process_user_status(app, message, user_id, user1, first_name, leaks, search,
                              admin_data, garant_data, trusted_data, scammer_data):
    if user1 is None:
        return await handle_invalid_user_id(message, user_id, leaks, search, scammer_data)

    if garant_data:
        return image_garant, garant(first_name, user_id, leaks, search)

    if trusted_data:
        return await handle_trusted_user(app, trusted_data, first_name, user_id, leaks, search)

    if admin_data:
        return await handle_admin_status(admin_data, first_name, user_id, leaks, search)

    if scammer_data:
        return handle_scammer_status(scammer_data, first_name, user_id, leaks, search)

    return image_user, no_data_text(first_name, user_id, leaks, search)


async def handle_invalid_user_id(message, user_id, leaks, search, scammer_data):
    if len(str(user_id)) < 7:
        await message.reply('⚠️ Некорректный айди')
        return None, None
    if scammer_data:
        return handle_scammer_status(scammer_data, "Не найдено", user_id, leaks, search)

    return image_user, no_data_text('Не найдено', user_id, leaks, search)


async def handle_trusted_user(app, trusted_data, first_name, user_id, leaks, search):
    garant_id = trusted_data[1]
    try:
        garants = await app.get_users(garant_id)
        garant_username = garants.username if garants else "Unknown"
    except:
        garant_username = "Unknown"
    return image_trusted, trusted(first_name, garant_username, user_id, leaks, search, '10%')


async def handle_admin_status(admin_data, first_name, user_id, leaks, search):
    status = admin_data[2]
    balance = admin_data[1] if len(admin_data) > 1 else 0
    kurator = admin_data[3] if len(admin_data) > 3 else None

    if status == 5:
        return image_owner, owner(first_name, user_id, leaks, search, balance)
    elif status == 4:
        return image_president, prezident(first_name, user_id, leaks, search, balance)
    elif status == 3:
        return image_director, director(first_name, user_id, leaks, search, balance)
    elif status == 2:
        return image_admin, admin2(first_name, user_id, leaks, search, balance)
    elif status == 1:
        return image_stajer, await stajer(first_name, user_id, leaks, search, kurator, balance)
    else:
        return image_user, no_data_text(first_name, user_id, leaks, search)


def handle_scammer_status(scammer_data, first_name, user_id, leaks, search):
    status = scammer_data[3]
    if status == 1:
        return image_scam2, scam_text2(first_name, leaks, search, scammer_data[2], scammer_data[1], user_id)
    elif status == 2:
        return image_scam, scam_text(first_name, leaks, search, scammer_data[2], scammer_data[1], user_id)
    else:
        return image_user, no_data_text(first_name, user_id, leaks, search)


async def check(app: Client, message: Message, user_id):
    if user_id is None:
        return None, None

    try:
        user1 = await app.get_users(user_id)
        first_name = user1.first_name if user1 and user1.first_name else "Unknown"
    except Exception as e:
        logging.error(f"Ошибка получения данных пользователя {user_id}: {e}")
        user1 = None
        first_name = "Unknown"

    try:
        user = get_user_from_db(user_id)
        if not user:
            insert_user_into_db(user_id)
            user = get_user_from_db(user_id)
        
        if user:
            user_id_db, search, leaks = user
        else:
            search = 0
            leaks = 0
            
    except Exception as e:
        logging.error(f"Ошибка работы с БД для пользователя {user_id}: {e}")
        return None, None

    admin_data, user_data, garant_data, trusted_data, scammer_data = get_user_data(user_id)

    return await process_user_status(app, message, user_id, user1, first_name, leaks, search,
                                     admin_data, garant_data, trusted_data, scammer_data)


def scam(user_id, status, reason, proof):
    try:
        cursor.execute("INSERT OR REPLACE INTO scammers VALUES (?, ?, ?, ?)", (user_id, proof, reason, status))
        connection.commit()
    except Exception as e:
        logging.error(f"Ошибка добавления скаммера: {e}")
        connection.rollback()


def unadmin(id, target_status):
    try:
        cursor.execute('SELECT status FROM admins WHERE id = ?', (id,))
        result = cursor.fetchone()

        if result is None:
            return False

        current_status = result[0]

        if target_status == 0:
            cursor.execute('DELETE FROM admins WHERE id = ?', (id,))
            connection.commit()
            return True

        if current_status > target_status:
            new_status = current_status - 1
            cursor.execute('UPDATE admins SET status = ? WHERE id = ?', (new_status, id))
            connection.commit()
            return True

        return False
    except Exception as e:
        logging.error(f"Ошибка понижения админа: {e}")
        connection.rollback()
        return False


def check_status(id):
    try:
        cursor.execute('SELECT status FROM admins WHERE id = ?', (id,))
        status2 = cursor.fetchone()
        if status2:
            return status2[0]
        return None
    except Exception as e:
        logging.error(f"Ошибка проверки статуса: {e}")
        return None


def check_owner(id):
    if id in OWNER_ID:
        return id
    else:
        return None


async def process_admin_command(app: Client, message: Message, user_id, command_prefix):
    owner = check_owner(user_id)
    status = check_status(user_id)
    id = message.reply_to_message.from_user.id if message.reply_to_message else None
    messages = message.text.split()

    if not id:
        args = message.text.split()
        if len(args) > 1:
            try:
                user = args[1]
                user = await app.get_users(user)
                if user:
                    id = user.id
                else:
                    await message.reply('❌ Неверный юзер')
                    return
            except Exception as e:
                logging.error(f"Ошибка получения пользователя: {e}")
                await message.reply('❌ Ошибка получения пользователя')
                return
        else:
            await message.reply('❌ Укажите пользователя')
            return

    if command_prefix == '+':
        if messages[0] == '+ВыдатьСоздателя':
            if owner:
                admin(id, 5)
                await message.reply('✅ Юзеру выдан создатель.')
            else:
                await message.reply('❌ Нет прав')

        elif messages[0] == '+ВыдатьПрезидента':
            if owner:
                admin(id, 4)
                await message.reply('✅ Юзеру выдан президент.')
            else:
                await message.reply('❌ Нет прав')
        elif messages[0] == '+ВыдатьДиректора':
            if owner or status in [4, 5]:
                admin(id, 3)
                await message.reply('✅ Юзеру выдан директор.')
            else:
                await message.reply('❌ Нет прав')
        elif messages[0] == '+ВыдатьАдмина':
            if owner or status in [4, 5]:
                admin(id, 2)
                await message.reply('✅ Юзеру выдан администратор.')
            else:
                await message.reply('❌ Нет прав')
        elif messages[0] == '+ВыдатьСтажера':
            if owner or status in [4, 5]:
                kurator_parts = message.text.split()
                if len(kurator_parts) >= 2:
                    if message.reply_to_message:
                        kurator = kurator_parts[1]
                        try:
                            if kurator.isdigit():
                                cursor.execute('INSERT INTO admins(id, status, kurator) VALUES (?, ?, ?)', (id, 1, int(kurator)))
                            elif kurator.startswith('@'):
                                kurator_user = await app.get_users(kurator)
                                if kurator_user:
                                    cursor.execute('INSERT INTO admins(id, status, kurator) VALUES (?, ?, ?)', (id, 1, kurator_user.id))
                                else:
                                    await message.reply('❌ Куратор не найден')
                                    return
                            connection.commit()
                            await message.reply('✅ Стажер с куратором выдан')
                        except Exception as e:
                            logging.error(f"Ошибка выдачи стажера: {e}")
                            await message.reply('❌ Ошибка выдачи стажера')
                    else:
                        await message.reply('🚫 Используйте ответом на сообщение: +ВыдатьСтажера @юзкуратора')
                else:
                    await message.reply('🚫 Формат: +ВыдатьСтажера @юзстажера @юзкуратора')
            else:
                await message.reply('❌ Нет прав')

        elif messages[0] == '+ВыдатьГаранта':
            if owner or status in [5]:
                try:
                    cursor.execute('INSERT OR IGNORE INTO garants(id) VALUES(?)', (id,))
                    connection.commit()
                    await message.reply('✅ Гарант успешно выдан.')
                except Exception as e:
                    logging.error(f"Ошибка выдачи гаранта: {e}")
                    await message.reply('❌ Ошибка выдачи гаранта')
            else:
                await message.reply('❌ Нет прав.')

    elif command_prefix == '-':
        if messages[0] == '-ЗабратьСоздателя':
            if owner:
                response = unadmin(id, 4)
                if response:
                    await message.reply('✅ Создатель понижен до президента.')
                else:
                    await message.reply('❌ Юзер не является создателем')
            else:
                await message.reply('❌ Нет прав')

        elif messages[0] == '-ЗабратьПрезидента':
            if owner:
                response = unadmin(id, 3)
                if response:
                    await message.reply('✅ Президент понижен до директора.')
                else:
                    await message.reply('❌ Юзер не является президентом')
            else:
                await message.reply('❌ Нет прав')
        elif messages[0] == '-ЗабратьДиректора':
            if owner or status in [4, 5]:
                response = unadmin(id, 2)
                if response:
                    await message.reply('✅ Директор понижен до администратора.')
                else:
                    await message.reply('❌ Юзер не является директором.')
            else:
                await message.reply('❌ Нет прав.')
        elif messages[0] == '-ЗабратьАдмина':
            if owner or status in [3, 4, 5]:
                response = unadmin(id, 1)
                if response:
                    await message.reply('✅ Администратор понижен до стажера.')
                else:
                    await message.reply('❌ Юзер не является админом.')
            else:
                await message.reply('❌ Нет прав.')

        elif messages[0] == '-ЗабратьСтажера':
            if owner or status in [3, 4, 5]:
                response = unadmin(id, 0)
                if response:
                    await message.reply('✅ Юзер теперь является обычным пользователем.')
                else:
                    await message.reply('❌ Юзер не является админом.')
            else:
                await message.reply('❌ Нет прав.')

        elif messages[0] == '-ЗабратьГаранта':
            if owner or status in [5]:
                try:
                    cursor.execute('SELECT * FROM garants WHERE id = ?', (id,))
                    if cursor.fetchone():
                        cursor.execute('DELETE FROM garants WHERE id = ?', (id,))
                        connection.commit()
                        await message.reply('✅ Гарант успешно удален.')
                    else:
                        await message.reply('❌ Человек не является гарантом.')
                except Exception as e:
                    logging.error(f"Ошибка удаления гаранта: {e}")
                    await message.reply('❌ Ошибка удаления гаранта')
            else:
                await message.reply('❌ Нет прав.')



logging.basicConfig(level=logging.INFO)

NUM_WORKERS = 16


@app.on_message(command('start'))
async def start_handler(app: Client, message: Message):
    try:
        keyboard = ReplyKeyboardMarkup(
            [
                ["Мой профиль 🆔", "Слить скаммера 😡", "Частые вопросы ❓"],
                ["Гаранты 🔥", "Волонтёры 🌴", "Статистика 📊"]
            ],
            resize_keyboard=True
        )
        await message.reply('🔎 Приветствую в скам базе Line Anti Scam. Выбери что ты хочешь сделать:', reply_markup=keyboard)
    except Exception as e:
        logging.error(f"Ошибка в start handler: {e}")


@app.on_message(filters.command(
    ["ВыдатьСоздателя", "ВыдатьПрезидента", "ВыдатьАдмина", "ВыдатьСтажера", "ВыдатьДиректора", "ВыдатьГаранта"],
    prefixes="+"))
async def promote_handler(app, message: Message):
    try:
        user_id = message.from_user.id
        await process_admin_command(app, message, user_id, "+")
    except Exception as e:
        logging.error(f"Ошибка в promote_handler: {e}")


@app.on_message(filters.command(
    ["ЗабратьСоздателя", "ЗабратьПрезидента", "ЗабратьАдмина", "ЗабратьСтажера", "ЗабратьДиректора", "ЗабратьГаранта"],
    prefixes="-"))
async def demote_handler(app, message: Message):
    try:
        user_id = message.from_user.id
        await process_admin_command(app, message, user_id, "-")
    except Exception as e:
        logging.error(f"Ошибка в demote_handler: {e}")


@app.on_message(filters.command(["delmute", "делмут"], ['/', '.', '-']))
async def mute_handler(app: Client, message: Message):
    try:
        user_id = message.from_user.id
        chat_id = message.chat.id
        
        if message.chat.type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP, enums.ChatType.CHANNEL]:
            await message.reply('⚠️ Эта команда работает только в группых и чатах')
            return
        
        status = check_status(user_id)
        if not status or status not in (2, 3, 4, 5):
            await message.reply('⚠️ Нет прав')
            return

        if message.reply_to_message:
            reply_message = message.reply_to_message
            user = reply_message.from_user.id
            username = reply_message.from_user.first_name
            try:
                time_str = message.command[1]
                reason = ' '.join(message.command[2:]) if len(message.command) > 2 else ''
            except IndexError:
                return await message.reply('⚠️ Команда введена неправильно')
        else:
            if len(message.command) < 3:
                return await message.reply('⚠️ Команда введена неправильно')

            username = message.command[1]
            time_str = message.command[2]
            reason = ' '.join(message.command[3:]) if len(message.command) > 3 else ''

            try:
                if username.startswith('@'):
                    user_obj = await app.get_users(username)
                else:
                    user_obj = await app.get_users(int(username) if username.isdigit() else username)
                user = user_obj.id
                username = user_obj.first_name
            except Exception:
                return await message.reply('⚠️ Пользователь не найден')

        try:
            chat_member = await app.get_chat_member(chat_id, user)
            if chat_member.status == enums.ChatMemberStatus.ADMINISTRATOR:
                return await message.reply('❗ Нельзя мутить администраторов.')
        except Exception:
            return await message.reply('❗ Пользователь не находится в чате')

        match = re.match(r'(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?$', time_str)
        if not match:
            return await message.reply('❗ Исправьте указанное время')

        days = int(match.group(1) or 0)
        hours = int(match.group(2) or 0)
        minutes = int(match.group(3) or 0)

        total_mute_duration = timedelta(days=days, hours=hours, minutes=minutes)
        mute_until = datetime.now(pytz.timezone('Europe/Moscow')) + total_mute_duration

        permissions = ChatPermissions(
            can_send_messages=False,
            can_send_media_messages=False,
            can_send_other_messages=False,
            can_add_web_page_previews=False
        )

        try:
            if message.reply_to_message:
                await app.delete_messages(message.chat.id, message.reply_to_message.id)
            await app.restrict_chat_member(chat_id, user, permissions, until_date=mute_until)
            await message.reply(f'''
✅ Пользователь: [{username}](tg://openmessage?user_id={user}) 
Был замучен на <i>{days} д, {hours} ч, {minutes} м</i>. 
Причина: {reason}

<i>Чат для оффтопа: @LineReports</i>
''')
        except errors.UserNotParticipant:
            await message.reply('❗ Пользователь не находится в чате')
        except Exception as ex:
            await message.reply(f'❗ Мут не удалось выдать, \nОшибка: <code>{ex}</code>')
    except Exception as e:
        logging.error(f"Ошибка в mute_handler: {e}")


@app.on_message(command('оффтоп'))
async def offtop(app, message: Message):
    try:
        user_id = message.from_user.id
        chat_id = message.chat.id
        
        if message.chat.type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            await message.reply('❗ Команда работает только в группах')
            return
        
        status = check_status(user_id)

        if status in (1, 2, 3, 4, 5):
            if message.reply_to_message:
                user = message.reply_to_message.from_user.id
                username = message.reply_to_message.from_user.first_name
            else:
                return await message.reply('❗ Команда доступна только ответом на сообщение')

            try:
                permissions = ChatPermissions(
                    can_send_messages=False,
                    can_send_media_messages=False,
                    can_send_other_messages=False,
                    can_add_web_page_previews=False
                )
                await app.restrict_chat_member(chat_id, user, permissions,
                                               datetime.now() + timedelta(minutes=5))
                username2 = message.reply_to_message.from_user.username
                if username2:
                    link = f'[{username}](https://t.me/{username2})'
                else:
                    link = f'[{username}](tg://openmessage?user_id={user})'
                await message.reply(
                    f'✅ {link} Был выдан мут на 5 минут за оффтоп\n<code>Чат для оффтопа: @LineReports</code>',
                    disable_web_page_preview=True)
            except Exception as ex:
                await message.reply(f'❗ Произошло ошибка! \nОшибка: <code>{ex}</code>')
        else:
            await message.reply('⚠️ Нет прав.')
    except Exception as e:
        logging.error(f"Ошибка в offtop: {e}")


@app.on_message(filters.command(
    ['unban', 'разбан', 'разбанить', 'анбан', 'unmute', 'размут', 'размутить', 'анмут'],
    ["/", ".", "-"]) & filters.text)
async def unban(app: Client, message: Message):
    try:
        user_id = message.from_user.id
        chat_id = message.chat.id
        
        if message.chat.type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            await message.reply('⚠️ Эта команда работает только в группах')
            return
        
        status = check_status(user_id)

        if not status or status not in (2, 3, 4, 5):
            await message.reply('⚠️ Нет прав')
            return
        
        args = message.text.split()
        if message.reply_to_message:
            person_to_unban = message.reply_to_message.from_user.id
            username = message.reply_to_message.from_user.first_name
        elif len(args) < 2:
            await message.reply('❌ Вы не указали, кого хотите разбанить/размутить')
            return
        else:
            try:
                if args[1].startswith('@'):
                    user_obj = await app.get_users(args[1])
                else:
                    user_obj = await app.get_users(int(args[1]) if args[1].isdigit() else args[1])
                person_to_unban = user_obj.id
                username = user_obj.first_name
            except Exception:
                await message.reply('❌ Пользователь не найден')
                return

        try:
            permissions = ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
            await app.restrict_chat_member(chat_id, person_to_unban, permissions)
            
            await app.unban_chat_member(chat_id, person_to_unban)

            await message.reply(f'✅ {username} разблокирован и размучен')
        except ChatAdminRequired:
            await message.reply(f'❌ У бота нет админки')
        except Exception as e:
            await message.reply(f'✅ Команда выполнена для {username}')
    except Exception as e:
        logging.error(f"Ошибка в unban: {e}")


@app.on_message(filters.command(['ban', 'бан'], ["/", "."]) & filters.text)
async def answer(app, message: Message):
    try:
        if message.chat.type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            await message.reply('⚠️ Эта команда работает только в группах')
            return
        
        user_status = message.from_user.id

        if check_status(user_status) in [2, 3, 4, 5]:
            message.text = message.text.lower()
            args = message.text.split()

            bantime = None
            bantext = 'навсегда'

            if message.reply_to_message:
                person_to_ban = message.reply_to_message.from_user.id
                username = message.reply_to_message.from_user.first_name

                if len(args) > 1:
                    if args[1].endswith('m') or args[1].endswith('minutes') \
                            or args[1].endswith('м') or args[1].endswith('минут'):
                        bantime = timedelta(minutes=int(args[1][:-1]))
                        bantext = f'на {args[1][:-1]} минут'

                    if args[1].endswith('h') or args[1].endswith('hours') \
                            or args[1].endswith('ч') or args[1].endswith('часов'):
                        bantime = timedelta(hours=int(args[1][:-1]))
                        bantext = f'на {args[1][:-1]} часов'

                    if args[1].endswith('d') or args[1].endswith('days') \
                            or args[1].endswith('д') or args[1].endswith('дней'):
                        bantime = timedelta(days=int(args[1][:-1]))
                        bantext = f'на {args[1][:-1]} дней'
            else:
                if len(args) < 2:
                    await message.reply('❌ Укажите юзера для бана')
                    return
                else:
                    try:
                        if args[1].startswith('@'):
                            user_obj = await app.get_users(args[1])
                        else:
                            user_obj = await app.get_users(int(args[1]) if args[1].isdigit() else args[1])
                        person_to_ban = user_obj.id
                        username = user_obj.first_name
                    except Exception:
                        await message.reply('❌ Пользователь не найден')
                        return

                    if len(args) > 2:
                        if args[2].endswith('m') or args[2].endswith('minutes') \
                                or args[2].endswith('м') or args[2].endswith('минут'):
                            bantime = timedelta(minutes=int(args[2][:-2]))
                            bantext = f'на {args[2][:-2]} минут'

                        if args[2].endswith('h') or args[2].endswith('hours') \
                                or args[2].endswith('ч') or args[2].endswith('часов'):
                            bantime = timedelta(hours=int(args[2][:-2]))
                            bantext = f'на {args[2][:-2]} часов'

                        if args[2].endswith('d') or args[2].endswith('days') \
                                or args[2].endswith('д') or args[2].endswith('дней'):
                            bantime = timedelta(days=int(args[2][:-2]))
                            bantext = f'на {args[2][:-2]} дней'

            try:
                if bantime:
                    await app.ban_chat_member(message.chat.id, person_to_ban, datetime.now() + bantime)
                else:
                    await app.ban_chat_member(message.chat.id, person_to_ban)

                await message.reply(f'✅ {username} был забанен \n{bantext}')
            except ChatAdminRequired:
                await message.reply(f'❌ Дайте мне админку, без неё я не могу банить')
            except Exception as e:
                await message.reply(f'Произошла ошибка: <pre>{e}</pre>')
        else:
            await message.reply('⚠️ Нет прав.')
            return
    except Exception as e:
        logging.error(f"Ошибка в ban: {e}")


user_requests = defaultdict(list)


@app.on_message(command(['check', 'чек'], ['/', '']))
async def check_user(app: Client, message: Message):
    try:
        user_id = message.from_user.id
        status = check_status(user_id)

        if status is None or status < 1 or status > 6:
            MAX_REQUESTS = 10
            TIME_LIMIT = 30 * 60
            REQUEST_INTERVAL = 10

            if user_id not in user_requests:
                user_requests[user_id] = []

            current_time = time.time()
            user_requests[user_id] = [timestamp for timestamp in user_requests[user_id] if
                                      current_time - timestamp < TIME_LIMIT]

            if len(user_requests[user_id]) >= MAX_REQUESTS:
                await message.reply('⚠️ Вы превысили лимит запросов. Пожалуйста, подождите 30 минут.')
                return

            if user_requests[user_id] and (current_time - user_requests[user_id][-1] < REQUEST_INTERVAL):
                await message.reply('⚠️ Пожалуйста, подождите 10 секунд перед следующим запросом.')
                return

            user_requests[user_id].append(current_time)

        try:
            user_id_to_check = None

            if message.reply_to_message:
                user_id_to_check = message.reply_to_message.from_user.id
            else:
                args = message.text.split(maxsplit=2)
                if len(args) == 2:
                    user = args[1]
                    if user.isdigit():
                        user_id_to_check = int(user)
                    elif user.startswith('@'):
                        try:
                            user_obj = await app.get_users(user)
                            user_id_to_check = user_obj.id
                        except Exception:
                            await message.reply('⚠️ Пользователь не найден.')
                            return
                    elif user.lower() in ['ми', 'я']:
                        user_id_to_check = message.from_user.id
                else:
                    await message.reply('⚠️ Используйте команду в виде <code>чек @id</code> или ответьте ей на сообщение.')
                    return

        except Exception as ex:
            logging.error(f"Error while determining user ID: {ex}")
            await message.reply('⚠️ Произошла ошибка при получении ID пользователя.')
            return

        if user_id_to_check is None:
            await message.reply('⚠️ ID пользователя не определён.')
            return

        try:
            user = await app.get_users(user_id_to_check)
            link = f'https://t.me/{user.username}' if user.username else f'https://t.me/user?id={user_id_to_check}'
        except Exception as e:
            logging.error(f"Error while fetching user: {e}")
            link = f'https://t.me/user?id={user_id_to_check}'

        button = InlineKeyboardMarkup([[InlineKeyboardButton(text="👥 Профиль", url=link)]])
        msg = await message.reply('🔎 Проверяется в базе данных...')

        try:
            stop_check = False

            async def update_message_with_dots():
                nonlocal stop_check, msg
                dot_patterns = ['.', '..', '...']
                index = 0

                while not stop_check:
                    new_text = f"🔎 Проверяется в базе данных{dot_patterns[index]}"
                    try:
                        await msg.edit_text(new_text)
                    except:
                        pass
                    index = (index + 1) % len(dot_patterns)
                    await asyncio.sleep(1)

            task = asyncio.create_task(update_message_with_dots())

            photo, text = await check(app, message, user_id_to_check)
            
            # Увеличиваем счетчик проверок только один раз
            cursor.execute('UPDATE users SET search = search + 1 WHERE id = ?', (user_id_to_check,))
            connection.commit()

            if photo and text:
                try:
                    await message.reply_photo(
                        photo=photo,
                        caption=text,
                        reply_markup=button
                    )
                except Exception as e:
                    logging.error(f"Ошибка отправки фото: {e}")
                    await message.reply(text, reply_markup=button)
            else:
                await message.reply('⚠️ Данные не найдены.')

            stop_check = True
            try:
                await task
            except:
                pass

            try:
                await msg.delete()
            except:
                pass

        except Exception as e:
            logging.error(f"Error while processing user check: {e}")
            await message.reply('⚠️ Произошла ошибка при проверке пользователя.')
            try:
                await msg.delete()
            except:
                pass
    except Exception as e:
        logging.error(f"Ошибка в check_user: {e}")


@app.on_message(command('noscam'))
async def noscam(app: Client, message: Message):
    try:
        user = message.from_user.id
        if check_status(user) in [2, 3, 4, 5]:
            if message.reply_to_message:
                cursor.execute('DELETE FROM scammers WHERE id = ?', (message.reply_to_message.from_user.id,))
                await message.reply('✅ Скаммер успешно удален.')
            else:
                args = message.text.split()
                if len(args) > 1:
                    username = args[1]
                    if username.isdigit():
                        cursor.execute('DELETE FROM scammers WHERE id = ?', (username,))
                        await message.reply('✅ Скаммер успешно удален.')
                    elif username.startswith('@'):
                        user_obj = await app.get_users(username)
                        cursor.execute('DELETE FROM scammers WHERE id = ?', (user_obj.id,))
                        await message.reply('✅ Скаммер успешно удален.')
            connection.commit()
        else:
            await message.reply('🚫 Нет прав.')
    except Exception as e:
        logging.error(f"Ошибка в noscam: {e}")


@app.on_message(command(['ДатьТраст', 'trust'], ['/', '+']))
async def trust(app: Client, message: Message):
    try:
        id = message.from_user.id
        cursor.execute('SELECT id FROM garants WHERE id = ?', (id,))
        if cursor.fetchone():
            args = message.text.split()
            trusted = None
            
            if message.reply_to_message:
                trusted = message.reply_to_message.from_user.id
            elif len(args) == 2:
                if args[1].isdigit():
                    trusted = int(args[1])
                elif args[1].startswith('@'):
                    user = await app.get_users(args[1])
                    trusted = user.id
                else:
                    await message.reply('⚠️ Некорректный юзер.')
                    return
            else:
                await message.reply('⚠️ Команда должна иметь юзера или быть ответом на сообщение')
                return
            
            if trusted:
                cursor.execute('INSERT OR REPLACE INTO trusteds VALUES (?, ?)', (trusted, message.from_user.id))
                connection.commit()
                await message.reply('✅ Траст успешно выдан')
        else:
            await message.reply('⚠️ Нет прав')
    except Exception as e:
        logging.error(f"Ошибка в trust: {e}")
        await message.reply('⚠️ Ошибка выдачи траста')


@app.on_message(command(['СнятьТраст', 'untrust'], ['/', '-']))
async def untrust(app: Client, message: Message):
    try:
        id = message.from_user.id
        cursor.execute('SELECT id FROM garants WHERE id = ?', (id,))
        if cursor.fetchone():
            args = message.text.split()
            trusted = None
            
            if message.reply_to_message:
                trusted = message.reply_to_message.from_user.id
            elif len(args) == 2:
                if args[1].isdigit():
                    trusted = int(args[1])
                elif args[1].startswith('@'):
                    user = await app.get_users(args[1])
                    trusted = user.id
                else:
                    await message.reply('⚠️ Некорректный юзер.')
                    return
            else:
                await message.reply('⚠️ Команда должна иметь юзера или быть ответом на сообщение')
                return
            
            if trusted:
                cursor.execute('SELECT garant_id FROM trusteds WHERE id = ?', (trusted,))
                result = cursor.fetchone()
                if result:
                    garant_id = result[0]
                    if message.from_user.id == garant_id:
                        cursor.execute('DELETE FROM trusteds WHERE id = ?', (trusted,))
                        connection.commit()
                        await message.reply('✅ Траст успешно снят')
                    else:
                        await message.reply('⚠️ Не вы выдавали траст пользователю')
                else:
                    await message.reply('⚠️ Пользователь не найден в списке трастов')
        else:
            await message.reply('⚠️ Нет прав')
    except Exception as e:
        logging.error(f"Ошибка в untrust: {e}")
        await message.reply('⚠️ Ошибка снятия траста')


@app.on_message(filters.command('scam'))
async def scamm(app: Client, message: Message):
    try:
        user = message.from_user.id
        if check_status(user) in [1, 2, 3, 4, 5]:
            args = message.text.split()
            if len(args) < 4:
                await message.reply("⚠️ Недостаточно аргументов. Используйте: /scam <id/юзернейм> <ссылка на пруфы> <причина>")
                return

            id = args[1]
            link = args[2]
            
            # Берем все оставшиеся слова как причину
            prufy = ' '.join(args[3:])

            # Проверяем, является ли ссылка корректной
            if not link.startswith(('https://', 'http://', 't.me/')):
                await message.reply('⚠️ Некорректная ссылка на пруфы. Укажите полную ссылку')
                return

            # Если ссылка в формате t.me/LineReports/номер, преобразуем в полную ссылку
            if link.startswith('t.me/'):
                link = 'https://' + link

            # Извлекаем ID сообщения из ссылки для сохранения в базе
            message_id = None
            if 'LineReports/' in link:
                try:
                    message_id = link.split('/')[-1]
                    if not message_id.isdigit():
                        await message.reply('⚠️ В ссылке не найден ID сообщения')
                        return
                except:
                    await message.reply('⚠️ Ошибка в обработке ссылки')
                    return
            else:
                # Если это не ссылка на LineReports, сохраняем как есть
                message_id = link

            if not id.isdigit():
                try:
                    userr = await app.get_users(id)
                    id = userr.id
                except:
                    await message.reply('⚠️ Ошибка в получении айди юзера')
                    return

            # Создаем короткие callback_data с хешированием для избежания ошибки
            import hashlib
            import json
            
            # Создаем уникальный идентификатор для callback
            callback_data_scam = hashlib.md5(f"scam_{user}_{id}_2".encode()).hexdigest()[:32]
            callback_data_possible = hashlib.md5(f"scam_{user}_{id}_1".encode()).hexdigest()[:32]
            
            # Сохраняем данные во временное хранилище
            callback_storage[callback_data_scam] = {
                "type": "scam",
                "user_id": user,
                "scammer_id": id,
                "prufy": prufy,
                "message_id": message_id,
                "status": "2"
            }
            
            callback_storage[callback_data_possible] = {
                "type": "scam",
                "user_id": user,
                "scammer_id": id,
                "prufy": prufy,
                "message_id": message_id,
                "status": "1"
            }

            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(text="❌ Скаммер!", callback_data=callback_data_scam),
                    InlineKeyboardButton(text="⚠️ Возможно скаммер!", callback_data=callback_data_possible)
                ]
            ])
            await message.reply('🔻 Выберите статус скаммера.', reply_markup=buttons)
        else:
            await message.reply('🚫 Нет прав.')
    except Exception as e:
        logging.error(f"Ошибка в scamm: {e}")
        await message.reply(f'⚠️ Ошибка: {str(e)}')


# Глобальное хранилище для callback данных
callback_storage = {}

@app.on_message(filters.text)
async def handle_all_messages(app: Client, message: Message):
    try:
        if message.from_user:
            user_id = message.from_user.id
            
            for table in ['users', 'casino_users']:
                cursor.execute(f"SELECT id FROM {table} WHERE id = ?", (user_id,))
                if cursor.fetchone() is None:
                    cursor.execute(f"INSERT INTO {table} (id) VALUES (?)", (user_id,))
                    connection.commit()

        if message.text == 'Мой профиль 🆔':
            id = message.from_user.id
            
            photo, text = await check(app, message, id)
            msg = await message.reply('🔎 Проверяется в базе данных...')
            
            # Увеличиваем счетчик проверок только один раз
            cursor.execute('UPDATE users SET search = search + 1 WHERE id = ?', (id,))
            connection.commit()
            
            if photo and text:
                try:
                    await message.reply_photo(
                        photo=photo,
                        caption=text,
                    )
                except:
                    await message.reply(text)
            await msg.delete()
            return

        elif message.text == 'Слить скаммера 😡':
            button = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        text="✅ Предложка",
                        url='https://t.me/LineReports'
                    )
                ]
            ])
            await message.reply("❗ Чтобы слить скамера переходите в предложку", reply_markup=button)

        elif message.text == 'Частые вопросы ❓':
            await message.reply("📚 Частые вопросы:\n\n1. Как проверить пользователя?\n- Используйте команду /чек или кнопку 'Мой профиль'\n\n2. Как стать гарантом?\n- Обратитесь к администраторам базы\n\n3. Как добавить скаммера?\n- Используйте команду /scam")

        elif message.text == 'Гаранты 🔥':
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
                        [InlineKeyboardButton(text=f"✅ {first_name} : @{user.username}",
                                              callback_data=f"check_{user.id}")]
                    )
                except:
                    continue

            reply_markup = InlineKeyboardMarkup(buttons)
            await message.reply(f"✅ Все гаранты базы: ({len(garants)}):", reply_markup=reply_markup)

        elif message.text == 'Волонтёры 🌴':
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

        elif message.text == "Статистика 📊":
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
🌴 Волонтеров: {admins_count}
🔥 Гарантов: {garants_count}
''')

        elif message.text.lower() == 'id':
            await message.reply(f'🆔 Ваш айди: {message.from_user.id}')

    except Exception as e:
        logging.error(f"Ошибка в handle_all_messages: {e}")


@app.on_callback_query()
async def callback_handler(app: Client, callback_query: CallbackQuery):
    try:
        data = callback_query.data

        if data.startswith('check'):
            data_parts = data.split('_')
            if len(data_parts) > 1:
                user_id = data_parts[1]
                try:
                    user = await app.get_users(user_id)
                    link = f'https://t.me/{user.username}' if user.username else f'https://t.me/user?id={user_id}'
                    button = InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton(
                                text="👥 Профиль",
                                url=link
                            )
                        ]
                    ])
                    photo, text = await check(app, callback_query.message, user_id)
                    
                    if photo and text:
                        try:
                            await app.edit_message_caption(
                                message_id=callback_query.message.id,
                                chat_id=callback_query.message.chat.id,
                                caption=text,
                                reply_markup=button
                            )
                        except:
                            await app.edit_message_text(
                                message_id=callback_query.message.id,
                                chat_id=callback_query.message.chat.id,
                                text=text,
                                reply_markup=button
                            )
                except Exception as e:
                    logging.error(f"Ошибка обработки check: {e}")

        elif data in callback_storage:
            # Обработка callback из хранилища
            callback_data = callback_storage[data]
            
            if callback_data["type"] == "scam":
                user_id = callback_data["user_id"]
                scammer_id = callback_data["scammer_id"]
                prufy = callback_data["prufy"]
                message_id = callback_data["message_id"]
                status = callback_data["status"]
                
                # Формируем ссылку на основе переданного message_id
                if message_id.startswith(('http://', 'https://')):
                    link = message_id
                else:
                    link = f'https://t.me/LineReports/{message_id}'

                if check_status(user_id) in [1, 2, 3, 4, 5]:
                    if check_status(user_id) in [2, 3, 4, 5]:
                        try:
                            scam(scammer_id, status, prufy, link)
                            await callback_query.edit_message_text('✅ Скаммер занесен.')
                        except Exception as e:
                            logging.error(f"Error while adding scammer: {e}")
                            await callback_query.edit_message_text('❗ Произошла ошибка при добавлении скамера.')
                    else:
                        try:
                            cursor.execute('SELECT kurator FROM admins WHERE id = ?', (user_id,))
                            kurator_check = cursor.fetchone()
                            if kurator_check is None:
                                await callback_query.answer('🚫 Вы не являетесь куратором стажера.', show_alert=True)
                                return
                            kurator_id = kurator_check[0]

                            # Создаем callback для принятия/отклонения заявки
                            accept_callback = hashlib.md5(f"accept_{user_id}_{scammer_id}_{status}".encode()).hexdigest()[:32]
                            decline_callback = hashlib.md5(f"decline_{user_id}_{scammer_id}".encode()).hexdigest()[:32]
                            
                            callback_storage[accept_callback] = {
                                "type": "accept",
                                "curator_id": user_id,
                                "scammer_id": scammer_id,
                                "prufy": prufy,
                                "message_id": message_id,
                                "status": status
                            }
                            
                            callback_storage[decline_callback] = {
                                "type": "decline",
                                "curator_id": user_id,
                                "scammer_id": scammer_id,
                                "message_id": message_id
                            }

                            buttons = InlineKeyboardMarkup([
                                [
                                    InlineKeyboardButton(text="✅ Принять", callback_data=accept_callback),
                                    InlineKeyboardButton(text="❌ Отклонить", callback_data=decline_callback)
                                ]
                            ])

                            application_link = f'https://t.me/{callback_query.message.chat.id}/{callback_query.message.id}'
                            await app.send_message(kurator_id,
                                                   f'✅ Новая заявка от пользователя: {callback_query.from_user.id}. Ссылка на заявку: {application_link}')
                            await callback_query.edit_message_text('✅ Заявка отправлена куратору на проверку.')
                            await callback_query.edit_message_reply_markup(reply_markup=buttons)
                        except Exception as e:
                            logging.error(f"Database error: {e}")
                            await callback_query.edit_message_text('❗ Произошла ошибка при получении куратора.')
                else:
                    await callback_query.answer('❌ У вас нет прав для выполнения этого действия.', show_alert=True)
                
                # Удаляем использованный callback из хранилища
                if data in callback_storage:
                    del callback_storage[data]

        elif "accept" in data or "decline" in data:
            # Это старый формат, оставляем для обратной совместимости
            if data.startswith('accept:'):
                data_parts = data.split(':')
                if len(data_parts) >= 6:
                    curator_id = data_parts[1]
                    scammer_id = data_parts[2]
                    prufy = data_parts[3]
                    message_id = data_parts[4]
                    status = data_parts[5]
                    application_link = f'https://t.me/{callback_query.message.chat.id}/{callback_query.message.id}'
                    
                    # Формируем ссылку на основе переданного message_id
                    if message_id.startswith(('http://', 'https://')):
                        link = message_id
                    else:
                        link = f'https://t.me/LineReports/{message_id}'

                    cursor.execute('SELECT kurator FROM admins WHERE id = ?', (curator_id,))
                    kurator_check = cursor.fetchone()
                    if kurator_check is None:
                        await callback_query.answer('🚫 Вы не являетесь куратором стажера.', show_alert=True)
                        return

                    try:
                        scam(scammer_id, status, prufy, link)
                        await app.send_message(curator_id,
                                               f'✅ Ваша заявка принята куратором. Ссылка на заявку: {application_link}')
                        await app.send_message(callback_query.from_user.id,
                                               f'✅ Ваша заявка принята куратором. Ссылка на заявку: {application_link}')
                        await callback_query.edit_message_text('✅ Заявка принята куратором.')
                    except Exception as e:
                        logging.error(f"Error while accepting the scam request: {e}")
                        await callback_query.edit_message_text('❗ Произошла ошибка при принятии заявки.')

            elif data.startswith('decline:'):
                data_parts = data.split(':')
                if len(data_parts) >= 4:
                    curator_id = data_parts[1]
                    scammer_id = data_parts[2]
                    application_link = f'https://t.me/{callback_query.message.chat.id}/{callback_query.message.id}'

                    cursor.execute('SELECT kurator FROM admins WHERE id = ?', (curator_id,))
                    kurator_check = cursor.fetchone()
                    if kurator_check is None:
                        await callback_query.answer('🚫 Вы не являетесь куратором стажера.', show_alert=True)
                        return

                    await callback_query.edit_message_text('❌ Заявка отклонена куратором.')
                    await app.send_message(curator_id,
                                           f'❌ Заявка от пользователя {callback_query.from_user.id} была отклонена. Ссылка на заявку: {application_link}')
                    await app.send_message(callback_query.from_user.id,
                                           f'❌ Ваша заявка была отклонена куратором. Ссылка на заявку: {application_link}')
    except Exception as e:
        logging.error(f"Ошибка в callback_handler: {e}")


if __name__ == "__main__":
    try:
        print("🔄 Инициализация базы данных...")
        init_db()
        print("✅ База данных инициализирована")
        print("🤖 Запуск бота...")
        app.run()
    except KeyboardInterrupt:
        print("\n⏹️ Остановка бота...")
    except Exception as e:
        logging.error(f"Критическая ошибка запуска: {e}")
        print(f"❌ Критическая ошибка: {e}")
    finally:
        if connection:
            connection.close()
            print("🔒 Соединение с БД закрыто")
