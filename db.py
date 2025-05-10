import sqlite3
from aiogram import types
import os
from log import create_logger

logger = create_logger(__name__)



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
        
       
    def run(self):
        """
        Создание таблиц БД
        """
        # Создание основной таблицы с пользователями
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id             INTEGER PRIMARY KEY,
                user_id        INTEGER NOT NULL,
                tg_username    TEXT,
                group_id       INTEGER NOT NULL,
                sec_group_id   INTEGER,
                rasp_data      TEXT,
                mng_time       TEXT,
                mng_send_state TEXT,
                call_data      TEXT,
                UNIQUE (user_id,tg_username) 
            )
        ''')
        self.conn.commit()
    
    def insert(self, user_id: int, tg_username: str, tg_firstname: str):
        """
        Вставка пользователя в основную БД после подтверждения
        """
        is_user = DB.get(user_id=user_id, data="user_id", table=DB.users_table)
        if is_user is None:
            self.cursor.execute(
                'INSERT INTO users (user_id, tg_username, tg_firstname, username, balance, cash_circulation, percentage, percentage_edit_type, _is_banned, all_time_balance) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (user_id, tg_username, tg_firstname, tg_firstname, 0, 0, 50, "auto", "False", 0))
            self.conn.commit()
        else:
            pass


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
            logger.error(e)

    
