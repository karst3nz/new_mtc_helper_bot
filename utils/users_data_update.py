from config import *
from utils.db import DB

async def update():
    db = DB()
    users = db.get_all("user_id", db.users_table)
    
    async def task(user_id):
        userTG = await bot.get_chat(user_id)
        userDB = db.get_user_dataclass(user_id)
        if userTG.username != userDB.tg_username:
            db.update(user_id=user_id, column="tg_username", new_data=userTG.username, table=db.users_table)
    tasks = []
    for user_id in users: tasks.append(task(user_id))
    asyncio.gather(*tasks)
