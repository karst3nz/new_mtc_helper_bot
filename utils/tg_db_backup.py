import os
from pathlib import Path
from config import *



async def send_db_to_admin():
    bot = Bot(token=BOT_TOKEN)
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
        finally:
            await bot.session.close()

if __name__ == "__main__":
    asyncio.run(send_db_to_admin())
