import asyncio
import sqlite3
from typing import Literal
from aiogram import types
import os

from utils.log import logging



class DB:

    users_table = "users"
    
    # Whitelist для безопасных имен таблиц и колонок
    ALLOWED_TABLES = {"users", "groups", "notification_settings", "hours_history", "schedule_changes", "favorites",
                      "admin_logs", "broadcasts", "user_activity", "blocked_users", "system_errors", "bot_settings"}
    ALLOWED_COLUMNS = {
        "id", "user_id", "tg_username", "group_id", "sec_group_id", 
        "missed_hours", "show_missed_hours_mode", "smena", "group", "pin_new_rasp",
        "daily_schedule", "daily_schedule_time", "lesson_reminder", "lesson_reminder_minutes",
        "hours_threshold", "hours_notification", "hours", "date", "diff_text", "created_at",
        "action", "position", "last_hours_notification", "last_activity", "is_blocked",
        "admin_id", "target_id", "details", "timestamp", "message_text", "filter_type",
        "filter_params", "total_users", "success_count", "error_count", "status", "completed_at",
        "blocked_by", "reason", "blocked_at", "error_type", "error_message", "traceback",
        "key", "value", "updated_at"
    }

    def __init__(self):
        from config import db_DIR, bot
        if not os.path.isdir(db_DIR):
            os.mkdir(db_DIR)
        self.conn = sqlite3.connect(db_DIR + "db.db", check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.users_table = "users"
        self.logger = logging.getLogger("DataBase")
        self.run()
    
    def _validate_identifier(self, name: str, allowed_set: set, identifier_type: str = "identifier"):
        """Валидация имен таблиц и колонок для предотвращения SQL injection"""
        if name not in allowed_set:
            raise ValueError(f"Invalid {identifier_type}: {name}")
        return name
        
       
    def insert_column(self, column: str, table: str, type: Literal["TEXT", "INTEGER", "REAL", "BOOL"], default_value = None):
        self.cursor.execute("PRAGMA table_info({})".format(table))
        columns_in_table = [column_info[1] for column_info in self.cursor.fetchall()]
        if column not in columns_in_table:
            # Создаем столбец, если его нет в таблице
            self.cursor.execute("ALTER TABLE {} ADD COLUMN {} {}".format(table, column, type))
            self.cursor.execute(f"UPDATE {table} SET {column} = ?", (default_value,))
            self.conn.commit()
            _log_text = f"Столбец {column} был добавлен в таблицу {table} (type={type}, default_value={default_value})"
            try: 
                self.logger.info(_log_text)
            except Exception as e:
                print(f"{_log_text} (logging not initialized: {e})")
        else:
            return

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
                smena                       TEXT,
                UNIQUE (user_id,tg_username) 
            )
        ''')
        self.conn.commit()

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS groups (
                id              INTEGER,
                user_id         INTEGER NOT NULL,
                "group"         INTEGER NOT NULL,
                pin_new_rasp    TEXT
            )
        ''')
    
        self.conn.commit()

        # Таблица настроек уведомлений
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS notification_settings (
                user_id                     INTEGER PRIMARY KEY,
                daily_schedule              INTEGER DEFAULT 0,
                daily_schedule_time         TEXT DEFAULT '20:00',
                lesson_reminder             INTEGER DEFAULT 0,
                lesson_reminder_minutes     INTEGER DEFAULT 15,
                hours_threshold             INTEGER DEFAULT 20,
                hours_notification          INTEGER DEFAULT 0,
                last_hours_notification     INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        self.conn.commit()

        # Таблица истории пропущенных часов
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS hours_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                hours       INTEGER NOT NULL,
                date        TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        self.conn.commit()

        # Таблица истории изменений расписания
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS schedule_changes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                date        TEXT NOT NULL,
                group_id    TEXT NOT NULL,
                diff_text   TEXT NOT NULL,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

        # Таблица избранного
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS favorites (
                user_id     INTEGER NOT NULL,
                action      TEXT NOT NULL,
                position    INTEGER NOT NULL,
                PRIMARY KEY (user_id, action),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        self.conn.commit()

        # Таблица логов действий администратора
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id    INTEGER NOT NULL,
                action      TEXT NOT NULL,
                target_id   INTEGER,
                details     TEXT,
                timestamp   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

        # Таблица истории рассылок
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS broadcasts (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id        INTEGER NOT NULL,
                message_text    TEXT NOT NULL,
                filter_type     TEXT,
                filter_params   TEXT,
                total_users     INTEGER,
                success_count   INTEGER DEFAULT 0,
                error_count     INTEGER DEFAULT 0,
                status          TEXT DEFAULT 'pending',
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at    TIMESTAMP
            )
        ''')
        self.conn.commit()

        # Таблица активности пользователей
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_activity (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                action      TEXT NOT NULL,
                details     TEXT,
                timestamp   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        self.conn.commit()

        # Таблица заблокированных пользователей
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS blocked_users (
                user_id     INTEGER PRIMARY KEY,
                blocked_by  INTEGER NOT NULL,
                reason      TEXT,
                blocked_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        self.conn.commit()

        # Таблица системных ошибок
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_errors (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                error_type      TEXT NOT NULL,
                error_message   TEXT NOT NULL,
                traceback       TEXT,
                user_id         INTEGER,
                timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

        # Таблица настроек бота
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_settings (
                key         TEXT PRIMARY KEY,
                value       TEXT NOT NULL,
                updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

        self.insert_column("pin_new_rasp", "groups", "BOOL", False)
        self.insert_column("smena", "users", "TEXT", "1")
        self.insert_column("last_hours_notification", "notification_settings", "INTEGER", 0)
        self.insert_column("created_at", "users", "TIMESTAMP", None)
        self.insert_column("last_activity", "users", "TIMESTAMP", None)
        self.insert_column("is_blocked", "users", "INTEGER", 0)

    def insert(self, user_id: int, tg_username: str, group_id: int, sec_group_id: int):
        """
        Вставка пользователя в основную БД после подтверждения
        """
        if self.is_exists(user_id) is False:
            self.cursor.execute(
                'INSERT INTO users (user_id, tg_username, group_id, sec_group_id, missed_hours, show_missed_hours_mode, smena)'
                'VALUES (?, ?, ?, ?, ?, ?, ?)',
                (user_id, tg_username, group_id, sec_group_id, 0, None, "1"))
            self.conn.commit()
        from config import bot, ADMIN_ID
        user_text = (
            "🎉 Спасибо, что выбрали моего бота!\n"
            "Если возникнут вопросы или пожелания, пишите — @Karst3nz\n"
        )
        user_btns = [
            [types.InlineKeyboardButton(text="🔔 Подписаться на канал", url="https://t.me/+Poh4QOaM6oplMWIy")],
            [types.InlineKeyboardButton(text="💬 Связаться с автором", url=f"tg://user?id={ADMIN_ID}")]
        ]
        
        async def _send_welcome():
            try:
                await bot.send_message(chat_id=user_id, text=user_text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=user_btns))
            except Exception as e:
                self.logger.error(f"Failed to send welcome message to {user_id}: {e}")
        
        asyncio.create_task(_send_welcome())

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
        return False if self.get_column(user_id=user_id, data="user_id", table=DB.users_table) is None else True

    async def get(self, user_id: int):
        """
        Получение всех данных пользователя из БД
        Возвращает кортеж: (id, user_id, tg_username, group_id, sec_group_id, missed_hours, show_missed_hours_mode, smena)
        """
        self.cursor.execute(
            "SELECT id, user_id, tg_username, group_id, sec_group_id, missed_hours, show_missed_hours_mode, smena FROM users WHERE user_id = ?",
            (user_id,)
        )
        return self.cursor.fetchone()

    def get_column(self, user_id: int, data: str, table: str):
        """
        Получние конкретной колонки из БД по user_id
        """
        # Валидация имен для безопасности
        data = self._validate_identifier(data, self.ALLOWED_COLUMNS, "column")
        table = self._validate_identifier(table, self.ALLOWED_TABLES, "table")
        
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
        # Валидация имен для безопасности
        data = self._validate_identifier(data, self.ALLOWED_COLUMNS, "column")
        table = self._validate_identifier(table, self.ALLOWED_TABLES, "table")
        
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
        # Валидация имен для безопасности
        data = self._validate_identifier(data, self.ALLOWED_COLUMNS, "column")
        table = self._validate_identifier(table, self.ALLOWED_TABLES, "table")
        
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
        # Валидация имен для безопасности
        data = self._validate_identifier(data, self.ALLOWED_COLUMNS, "column")
        table = self._validate_identifier(table, self.ALLOWED_TABLES, "table")
        
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
        # Валидация имени таблицы для безопасности
        table = self._validate_identifier(table, self.ALLOWED_TABLES, "table")
        
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
        # Валидация имен для безопасности
        column = self._validate_identifier(column, self.ALLOWED_COLUMNS, "column")
        table = self._validate_identifier(table, self.ALLOWED_TABLES, "table")
        
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
        # Валидация имен для безопасности
        column = self._validate_identifier(column, self.ALLOWED_COLUMNS, "column")
        table = self._validate_identifier(table, self.ALLOWED_TABLES, "table")
        
        try:
            self.cursor.execute(f"UPDATE {table} SET {column} = ?", (new_data, ))
            self.conn.commit()
            return True
        except Exception as e:
            self.logger.error(e)

    def get_user_dataclass(self, user_id: int):
        from utils.dataclasses_ import User
        if self.is_exists(user_id):
            r = self.cursor.execute(
                "SELECT id, user_id, tg_username, group_id, rasp_data, mng_time, mng_send_state, "
                "sec_group_id, msg_max_length, format_rasp, missed_hours, show_missed_hours_mode, smena "
                "FROM users WHERE user_id = ?", 
                (user_id,)
            ).fetchone()
            user = User(*r)   
            return user
        else:
            return User(None, None, None, None, None, None, None, None, None, None, None, None, None)
            
    def get_TGgroup_dataclass(self, id: int):
        from utils.dataclasses_ import TGgroup
        if self.is_group_exists(id):
            r = self.cursor.execute("SELECT * FROM groups WHERE id = ?", (id,)).fetchone()
            tggroup = TGgroup(*r)
            return tggroup
        else:
            return TGgroup(None, None, None, None)

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

    def get_all_users_in_group(self, group: str):
        self.cursor.execute(f"SELECT user_id FROM {self.users_table} WHERE group_id = ?", (group,))
        r = self.cursor.fetchall()
        users = []
        for i in r: users.append(i[0])
        return users

    async def return_group_data(self, group: str):
        if group not in config.groups: 
            return f"❌ Группа <b>{group}</b> не найдена в конфиге!"
        
        users = self.get_all_users_in_group(group)
        if not users:
            return f"📭 В группе <b>{group}</b> нет пользователей."
        
        text = f"👥 Пользователи в группе <b>{group}</b> ({len(users)} чел.):\n"
        text += "─" * 20 + "\n"
        
        for idx, user_id in enumerate(users, start=1):
            user = self.get_user_dataclass(user_id)
            username = user.tg_username if user.tg_username else (await config.bot.get_chat(user.user_id)).full_name
            if len(username) == 0: username = "Нет юзера"
            link_to_chat = f"tg://user?id={user.user_id}"
            link_to_info = f"/user {user.user_id}"
            # Форматирование с выравниванием
            if user.tg_username:
                text += f"{idx:2d}. @{username} | ID: <code>{user.user_id}</code>\n"
            else:
                text += f"{idx:2d}. <a href='{link_to_chat}'>{username}</a> | ID: <code>{user.user_id}</code>\n"
        
        return text

    # ========== МЕТОДЫ ДЛЯ NOTIFICATION_SETTINGS ==========
    
    def get_notification_settings(self, user_id: int):
        """Получить настройки уведомлений пользователя"""
        self.cursor.execute(
            "SELECT * FROM notification_settings WHERE user_id = ?", 
            (user_id,)
        )
        result = self.cursor.fetchone()
        if result:
            return {
                "user_id": result[0],
                "daily_schedule": bool(result[1]),
                "daily_schedule_time": result[2],
                "lesson_reminder": bool(result[3]),
                "lesson_reminder_minutes": result[4],
                "hours_threshold": result[5],
                "hours_notification": bool(result[6])
            }
        return None
    
    def create_notification_settings(self, user_id: int):
        """Создать настройки уведомлений для нового пользователя"""
        try:
            self.cursor.execute(
                "INSERT INTO notification_settings (user_id) VALUES (?)",
                (user_id,)
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            # Настройки уже существуют
            return False
    
    def update_notification_setting(self, user_id: int, setting: str, value):
        """Обновить конкретную настройку уведомлений"""
        # Валидация имени колонки
        allowed_settings = {
            "daily_schedule", "daily_schedule_time", "lesson_reminder",
            "lesson_reminder_minutes", "hours_threshold", "hours_notification",
            "last_hours_notification"
        }
        if setting not in allowed_settings:
            raise ValueError(f"Invalid setting: {setting}")
        
        # Создаем настройки если их нет
        if not self.get_notification_settings(user_id):
            self.create_notification_settings(user_id)
        
        self.cursor.execute(
            f"UPDATE notification_settings SET {setting} = ? WHERE user_id = ?",
            (value, user_id)
        )
        self.conn.commit()
    
    def get_users_with_daily_schedule(self):
        """Получить всех пользователей с включенным ежедневным расписанием"""
        self.cursor.execute(
            "SELECT user_id, daily_schedule_time FROM notification_settings WHERE daily_schedule = 1"
        )
        return self.cursor.fetchall()
    
    def get_users_with_lesson_reminder(self):
        """Получить всех пользователей с включенными напоминаниями о парах"""
        self.cursor.execute(
            "SELECT user_id, lesson_reminder_minutes FROM notification_settings WHERE lesson_reminder = 1"
        )
        return self.cursor.fetchall()
    
    # ========== МЕТОДЫ ДЛЯ HOURS_HISTORY ==========
    
    def add_hours_history(self, user_id: int, hours: int, date: str = None):
        """Добавить запись в историю пропущенных часов"""
        if date is None:
            from datetime import datetime
            date = datetime.now().strftime("%Y-%m-%d")
        
        self.cursor.execute(
            "INSERT INTO hours_history (user_id, hours, date) VALUES (?, ?, ?)",
            (user_id, hours, date)
        )
        self.conn.commit()
    
    def get_hours_history(self, user_id: int, days: int = 30):
        """Получить историю пропущенных часов за последние N дней"""
        self.cursor.execute(
            """
            SELECT date, hours FROM hours_history 
            WHERE user_id = ? AND date >= date('now', '-' || ? || ' days')
            ORDER BY date ASC
            """,
            (user_id, days)
        )
        return self.cursor.fetchall()
    
    def get_total_hours_by_period(self, user_id: int, start_date: str, end_date: str):
        """Получить общее количество пропущенных часов за период"""
        self.cursor.execute(
            """
            SELECT SUM(hours) FROM hours_history 
            WHERE user_id = ? AND date BETWEEN ? AND ?
            """,
            (user_id, start_date, end_date)
        )
        result = self.cursor.fetchone()
        return result[0] if result[0] else 0
    
    # ========== МЕТОДЫ ДЛЯ SCHEDULE_CHANGES ==========
    
    def add_schedule_change(self, date: str, group_id: str, diff_text: str):
        """Добавить запись об изменении расписания"""
        self.cursor.execute(
            "INSERT INTO schedule_changes (date, group_id, diff_text) VALUES (?, ?, ?)",
            (date, group_id, diff_text)
        )
        self.conn.commit()
    
    def get_schedule_changes(self, group_id: str = None, limit: int = 10):
        """Получить историю изменений расписания"""
        if group_id:
            self.cursor.execute(
                """
                SELECT date, group_id, diff_text, created_at 
                FROM schedule_changes 
                WHERE group_id = ?
                ORDER BY created_at DESC 
                LIMIT ?
                """,
                (group_id, limit)
            )
        else:
            self.cursor.execute(
                """
                SELECT date, group_id, diff_text, created_at 
                FROM schedule_changes 
                ORDER BY created_at DESC 
                LIMIT ?
                """,
                (limit,)
            )
        return self.cursor.fetchall()
    
    # ========== МЕТОДЫ ДЛЯ FAVORITES ==========
    
    def add_favorite(self, user_id: int, action: str, position: int = 0):
        """Добавить действие в избранное"""
        try:
            self.cursor.execute(
                "INSERT INTO favorites (user_id, action, position) VALUES (?, ?, ?)",
                (user_id, action, position)
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def remove_favorite(self, user_id: int, action: str):
        """Удалить действие из избранного"""
        self.cursor.execute(
            "DELETE FROM favorites WHERE user_id = ? AND action = ?",
            (user_id, action)
        )
        self.conn.commit()
    
    def get_favorites(self, user_id: int):
        """Получить список избранного пользователя"""
        self.cursor.execute(
            "SELECT action, position FROM favorites WHERE user_id = ? ORDER BY position ASC",
            (user_id,)
        )
        return self.cursor.fetchall()
    
    def update_favorite_position(self, user_id: int, action: str, new_position: int):
        """Обновить позицию избранного действия"""
        self.cursor.execute(
            "UPDATE favorites SET position = ? WHERE user_id = ? AND action = ?",
            (new_position, user_id, action)
        )
        self.conn.commit()


        
