import os
from pathlib import Path
from config import *
from utils.log import create_logger

logger = create_logger(__name__)



async def send_db_to_admin():
    from config import bot
    import glob
    files = glob.glob(f"{db_DIR}/*.db")
    for file in files:
        db_path = os.path.abspath(Path(file))
        try:
            db_file = types.FSInputFile(db_path)
            import sqlite3
            
            conn = sqlite3.connect(db_path)
            try:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM users")
                user_count = cur.fetchone()[0]
            except Exception:
                user_count = "неизвестно"
            finally:
                conn.close()
            caption = f"Пользователей в базе: {user_count}"
            await bot.send_document(chat_id=BACKUP_CHAT_ID, document=db_file, caption=caption)
        except Exception as e:
            logger.error(f"Ошибка при отправке бэкапа БД: {e}")

if __name__ == "__main__":
    asyncio.run(send_db_to_admin())
