from utils.check_groups import groups_missing_in_schedule
from utils.db import DB

def run():
    db = DB()
    missing_groups = groups_missing_in_schedule()
    for group in missing_groups:
        db.cursor.execute("DELETE FROM users WHERE group_id = ?", (group,))
    db.conn.commit()
    
