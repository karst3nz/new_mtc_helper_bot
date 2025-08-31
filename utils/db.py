import asyncio
import sqlite3
from aiogram import types
import os
from utils.log import logging



class DB:

    users_table = "users"

    def __init__(self):
        from config import db_DIR, bot
        if not os.path.isdir(db_DIR):
            os.mkdir(db_DIR)
        self.conn = sqlite3.connect(db_DIR + "db.db", check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.run()
        self.users_table = "users"
        self.logger = logging.getLogger("DataBase")
        
       
    def run(self):
        """
        Создание таблиц БД
        """
        # Создание основной таблицы с пользователями
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id                          INTEGER PRIMARY KEY,
                user_id                     INTEGER NOT NULL,
                tg_username                 TEXT,
                group_id                    INTEGER NOT NULL,
                sec_group_id                INTEGER,
                missed_hours                INTEGER,
                show_missed_hours_mode      TEXT,
                UNIQUE (user_id,tg_username) 
            )
        ''')
        self.conn.commit()

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS groups (
                id          INTEGER,
                user_id     INTEGER NOT NULL,
                "group"     INTEGER NOT NULL
            )
        ''')
    
        self.conn.commit()

    def insert(self, user_id: int, tg_username: str, group_id: int, sec_group_id: int):
        """
        Вставка пользователя в основную БД после подтверждения
        """
        if self.is_exists(user_id) is False:
            self.cursor.execute(
                'INSERT INTO users (user_id, tg_username, group_id, sec_group_id, missed_hours, show_missed_hours_mode)'
                'VALUES (?, ?, ?, ?, ?, ?)',
                (user_id, tg_username, group_id, sec_group_id, 0, None))
            self.conn.commit()
        from config import bot, ADMIN_ID
        text = f"DB: New user added to db [ui={user_id}; tg_username=@{tg_username}; group_id={group_id}]"
        btns = [
            [types.InlineKeyboardButton(text="Профиль", url=f"tg://user?id={user_id}")]
        ]
        user_text = (
            "🎉 Спасибо, что выбрали моего бота!\n"
            "Если возникнут вопросы или пожелания, пишите — @Karst3nz\n"
        )
        user_btns = [
            [types.InlineKeyboardButton(text="🔔 Подписаться на канал", url="https://t.me/+Poh4QOaM6oplMWIy")],
            [types.InlineKeyboardButton(text="💬 Связаться с автором", url=f"tg://user?id={ADMIN_ID}")]
        ]
        asyncio.create_task(bot.send_message(chat_id=user_id, text=user_text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=user_btns)))
        asyncio.create_task(bot.send_message(chat_id=ADMIN_ID, text=text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=btns)))

    def insert_group(self, id: int, user_id: int, group: int):
        if self.is_group_exists(id) is False:
            self.cursor.execute(
                'INSERT INTO groups (id, user_id, "group")'
                'VALUES (?, ?, ?)',
                (id, user_id, group))
            self.conn.commit()

    def is_group_exists(self, id: int):
        self.cursor.execute(f"SELECT id FROM groups WHERE id = ?", (id,))
        return False if self.cursor.fetchone() is None else True

    def is_exists(self, user_id: int):
        return False if self.get(user_id=user_id, data="user_id", table=DB.users_table) is None else True

    def get(self, user_id: int, data: str, table: str):
        """
        Получние данных из БД по user_id
        """
        
        self.cursor.execute(
            f"SELECT {data} FROM {table} WHERE user_id = ?",
            (user_id, ))
        
        result = self.cursor.fetchone()
        if result is not None:
            return result[0]
        else:
            return None
    
    def get_without_user_id(self, data: str, table: str):
        """
        Получние данных из БД без user_id
        """
        
        self.cursor.execute(f"SELECT {data} FROM {table}")
        result = self.cursor.fetchone()
        if result is not None:
            return result[0]
        else:
            return None
        
    def get_all_user_id(self, user_id: int, data: str, table: str):
        """
        Получение всех данных из БД по user_id и data 
        """
        
        self.cursor.execute(f"SELECT {data} FROM {table} WHERE user_id = ?", (user_id, ))
        fetch = self.cursor.fetchall()
        result = []
        for item in fetch:
            item = item[0]
            result.append(item)
        return result
    
    def get_all_usersWgroup(self) -> dict:
        _dict = {}
        from config import groups
        for group in groups:
            self.cursor.execute("SELECT user_id FROM users WHERE group_id = ?", (group,))
            user_ids = [user_id[0] for user_id in self.cursor.fetchall()]
            _dict[group] = user_ids
        return _dict

    
    def get_all_TGgroupsWgroup(self) -> dict:
        _dict = {}
        from config import groups
        for group in groups:
            self.cursor.execute("SELECT id FROM groups WHERE \"group\" = ?", (group,))
            user_ids = [user_id[0] for user_id in self.cursor.fetchall()]
            _dict[group] = user_ids
        return _dict

    def get_all_usersBYgroup(self, group) -> dict:
        _dict = {}
        self.cursor.execute("SELECT user_id FROM users WHERE group_id = ?", (group,))
        user_ids = [user_id[0] for user_id in self.cursor.fetchall()]
        _dict[group] = user_ids
        return _dict        

    def get_all_TGgroupsBYgroup(self, group) -> dict:
        _dict = {}
        self.cursor.execute("SELECT id FROM groups WHERE \"group\" = ?", (group,))
        user_ids = [user_id[0] for user_id in self.cursor.fetchall()]
        _dict[group] = user_ids
        return _dict        

    def get_all(self, data: str, table: str):
        """
        Получение всех данных из БД по data
        """
        self.cursor.execute(f"SELECT {data} FROM {table}")
        fetch = self.cursor.fetchall()
        result = []
        for item in fetch:
            item = item[0]
            result.append(item)
        return result

    def get_user_groups(self, user_id: int):
        self.cursor.execute(f"SELECT group_id, sec_group_id FROM {self.users_table} WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()
        if result is not None:
            return result[0], result[1]
        else:
            return None, None       

    def delete(self, user_id: int, table: str):
        """
        Удаление строчки из БД
        """
        
        try:
            self.cursor.execute(f"DELETE from {table} where user_id = ?", (user_id,))
            self.conn.commit()
            return True
        except Exception:
            return False

    def update(self, user_id: int, column: str, new_data: str, table: str):
        """
        Обновление данных в БД
        """
        
        try:
            self.cursor.execute(f"UPDATE {table} SET {column} = ? WHERE user_id = ?", (new_data, user_id))
            self.conn.commit()
            return True
        except Exception:
            return False
    
    def update_without_user_id(self, column: str, new_data: str, table: str):
        """
        Обновление данных в БД
        """
        
        try:
            self.cursor.execute(f"UPDATE {table} SET {column} = ?", (new_data, ))
            self.conn.commit()
            return True
        except Exception as e:
            self.logger.error(e)

    def get_user_dataclass(self, user_id: int):
        from utils.dataclasses_ import User
        if self.is_exists(user_id):
            r = self.cursor.execute("SELECT id, user_id, tg_username, group_id, sec_group_id, missed_hours, show_missed_hours_mode FROM users WHERE user_id = ?", (user_id,)).fetchone()
            user = User(*r)   
            return user
        else:
            return User(None, None, None, None, None, None, None)
            
    def update_hours_mode(self, user_id: int, mode: str):
        cur_mode = self.get_user_dataclass(user_id).show_missed_hours_mode
        if cur_mode is not None:
            if mode in cur_mode: 
                cur_mode = cur_mode.replace(mode, "")
            else: 
                cur_mode += f"{mode}"
        else:
            cur_mode = f"{mode}"
        self.update(user_id=user_id, column="show_missed_hours_mode", new_data=cur_mode, table=self.users_table)
        self.conn.commit()
        
    def return_user_data(self, user_id: int):
        if self.is_exists(user_id) is False: return f"Пользователь <b>{user_id}</b> не найден в базе!"
        try:
            user = self.get_user_dataclass(user_id)
            text = (
                f"Информация о пользователе:\n"
                f"- DB_ID: {user.id}\n"
                f'- Telegram ID: {user.user_id}\n'
                f'- Telegram username: @{user.tg_username}\n'
                f'- Номер группы: {user.group_id}\n'
                f'- Доп. номер группы: {user.sec_group_id}\n'
                f'- Кол. пропущенных часов: {user.missed_hours}\n'
                f'- Режим показа пропущенных часов: {user.show_missed_hours_mode}\n'
            )
            return text
        except Exception as e:
            self.logger.error(e)    
