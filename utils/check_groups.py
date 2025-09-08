import os
import re
from typing import List, Set
import ast


DATA_DIR = "/home/karst3nz/PycharmProjects/new_mtc_helper_bot/data"
CONFIG_PY_PATH = "/home/karst3nz/PycharmProjects/new_mtc_helper_bot/config.py"
GROUP_PATTERN = re.compile(r"\¦(\d{4})\¦")




def extract_groups_from_text(text: str) -> Set[str]:
    matches = GROUP_PATTERN.findall(text)
    return set(matches)




def collect_unique_groups(data_dir: str = DATA_DIR) -> List[str]:
    unique_groups: Set[str] = set()

    for root, _dirs, files in os.walk(data_dir):
        for filename in files:
            if not filename.lower().endswith(".txt"):
                continue
            file_path = os.path.join(root, filename)
            try:
                with open(file_path, "r", encoding="windows-1251", errors="ignore") as f:
                    content = f.read()
                unique_groups.update(extract_groups_from_text(content))
            except Exception:
                # Пропускаем проблемные файлы
                continue

    return sorted(unique_groups)




from utils.db import DB

def collect_unique_groups_from_db() -> List[str]:
    """Возвращает отсортированный список уникальных групп из БД (таблица users.group_id)."""
    db = DB()
    db.cursor.execute("SELECT DISTINCT group_id FROM users WHERE group_id IS NOT NULL AND group_id != ''")
    rows = db.cursor.fetchall()
    groups = [str(row[0]) for row in rows]
    return sorted(set(groups))


def groups_missing_in_schedule() -> List[str]:
    """Группы, которые есть в БД, но отсутствуют в текущем расписании (по txt-файлам)."""
    schedule_groups = collect_unique_groups()
    db_groups = collect_unique_groups_from_db()
    missing = sorted(set(db_groups) - set(schedule_groups))
    return missing



def print_missing_groups(schedule_groups: List[str]) -> None:
    from config import groups
    missing = sorted(set(groups) - set(schedule_groups))
    if missing != []:
        raise Exception(f"Отсутствуют в расписании (из config.py): {missing}")



def run():
    groups = collect_unique_groups()
    print_missing_groups(groups)


def return_missing_groups():
    from config import groups
    return sorted(set(groups) - set(collect_unique_groups()))


if __name__ == "__main__":
    run()
